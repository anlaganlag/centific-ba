import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from openai import OpenAI
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


class VectorService:
    """ChromaDB vector storage service with local and remote support"""

    def __init__(
        self,
        persist_directory: str = "data/vectors",
        api_key: str = None,
        chromadb_host: Optional[str] = None,
        chromadb_port: Optional[int] = None
    ):
        """
        Initialize VectorService.

        Args:
            persist_directory: Local directory for persistent storage (local mode)
            api_key: OpenAI API key for embeddings
            chromadb_host: ChromaDB server host (remote mode)
            chromadb_port: ChromaDB server port (remote mode)
        """
        # Check environment for remote ChromaDB config
        host = chromadb_host or os.getenv("CHROMADB_HOST")
        port = chromadb_port or int(os.getenv("CHROMADB_PORT", "8000"))

        if host:
            # Remote mode: connect to ChromaDB HTTP server
            logger.info(f"Connecting to remote ChromaDB at {host}:{port}")
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False)
            )
            self.mode = "remote"
        else:
            # Local mode: use persistent client
            logger.info(f"Using local ChromaDB at {persist_directory}")
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            self.mode = "local"

        # Use regular OpenAI for embeddings (cheaper and no Azure deployment needed)
        self.openai_client = OpenAI(
            api_key=api_key or os.getenv('OPENAI_API_KEY')
        )

    def create_project_collection(self, project_id: str):
        """Create or get collection for project documents"""
        return self.client.get_or_create_collection(
            name=f"project_{project_id}",
            metadata={"project_id": project_id}
        )

    def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Generate embedding using OpenAI (synchronous version for single queries)

        Args:
            text: Text to embed
            model: OpenAI embedding model name

        Returns:
            List of floats representing the embedding
        """
        response = self.openai_client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding

    async def get_embedding_async(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Generate embedding using OpenAI (async version for parallel processing)

        Args:
            text: Text to embed
            model: OpenAI embedding model name

        Returns:
            List of floats representing the embedding
        """
        # Run synchronous OpenAI call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.openai_client.embeddings.create(input=text, model=model)
        )
        return response.data[0].embedding

    async def add_documents(self, project_id: str, chunks: List[Dict]):
        """
        Add document chunks to collection

        Args:
            project_id: Project identifier
            chunks: List of chunk dicts with 'id', 'doc_id', 'doc_name', 'content', 'page'
        """
        collection = self.create_project_collection(project_id)

        # Generate embeddings in parallel for 10-15x speedup
        embedding_model = 'text-embedding-3-small'
        texts = [chunk['content'] for chunk in chunks]
        embedding_tasks = [self.get_embedding_async(text, model=embedding_model) for text in texts]
        embeddings = await asyncio.gather(*embedding_tasks)

        # Prepare metadata
        metadatas = []
        for chunk in chunks:
            meta = {
                'doc_id': chunk['doc_id'],
                'doc_name': chunk['doc_name'],
                'chunk_id': chunk['id']
            }
            # Only add page if it exists (ChromaDB doesn't accept None)
            if chunk.get('page') is not None:
                meta['page'] = str(chunk['page'])
            metadatas.append(meta)

        ids = [chunk['id'] for chunk in chunks]

        # Add to ChromaDB
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Added {len(chunks)} chunks to collection project_{project_id}")

    def delete_document_chunks(self, project_id: str, doc_id: str):
        """Delete all chunks belonging to a specific document from the collection"""
        try:
            collection = self.create_project_collection(project_id)
            # ChromaDB where filter to find chunks by doc_id metadata
            collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted chunks for doc {doc_id} from project_{project_id}")
        except Exception as e:
            logger.warning(f"Failed to delete chunks for doc {doc_id}: {e}")

    async def query(self, project_id: str, question: str, n_results: int = 5) -> List[Dict]:
        """
        Query collection for relevant chunks

        Args:
            project_id: Project identifier
            question: User question
            n_results: Number of results to return

        Returns:
            List of relevant chunks with metadata
        """
        collection = self.create_project_collection(project_id)

        # Generate query embedding
        embedding_model = 'text-embedding-3-small'
        query_embedding = self.get_embedding(question, model=embedding_model)

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # Format results
        chunks = []
        for i in range(len(results['ids'][0])):
            chunks.append({
                'content': results['documents'][0][i],
                'doc_id': results['metadatas'][0][i]['doc_id'],
                'doc_name': results['metadatas'][0][i]['doc_name'],
                'page': results['metadatas'][0][i].get('page'),
                'distance': results['distances'][0][i] if 'distances' in results else None
            })

        return chunks

    def delete_project_collection(self, project_id: str):
        """Delete collection for project"""
        try:
            self.client.delete_collection(name=f"project_{project_id}")
            logger.info(f"Deleted collection project_{project_id}")
        except Exception:
            pass  # Collection doesn't exist

    def get_collection_count(self, project_id: str) -> int:
        """Get number of documents in collection"""
        try:
            collection = self.create_project_collection(project_id)
            return collection.count()
        except Exception:
            return 0

    def get_all_documents(self, project_id: str) -> List[Dict]:
        """Get all document chunks from a project collection"""
        try:
            collection = self.create_project_collection(project_id)
            count = collection.count()
            if count == 0:
                return []
            result = collection.get(
                include=["documents", "metadatas"],
                limit=count
            )
            chunks = []
            for i in range(len(result['ids'])):
                chunks.append({
                    'content': result['documents'][i] if result['documents'] else '',
                    'metadata': result['metadatas'][i] if result['metadatas'] else {}
                })
            return chunks
        except Exception:
            return []

    async def health_check(self) -> bool:
        """Check if ChromaDB is healthy"""
        try:
            # Try to get heartbeat (works for both local and remote)
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False
