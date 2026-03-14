import api from '../lib/api'

interface Document {
  id: string
  filename: string
  file_type: string
  total_pages: number
  total_chunks: number
  uploaded_at: string
}

interface Props {
  documents: Document[]
  onDeleted: () => void
}

export default function DocumentList({ documents, onDeleted }: Props) {
  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return
    await api.delete(`/documents/${docId}`)
    onDeleted()
  }

  if (documents.length === 0) {
    return <p className="text-gray-400 text-sm">No documents uploaded yet.</p>
  }

  return (
    <ul className="divide-y divide-gray-200">
      {documents.map((doc) => (
        <li key={doc.id} className="py-3 flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-800">{doc.filename}</p>
            <p className="text-xs text-gray-400">
              {doc.file_type}{doc.total_pages > 0 && <> &middot; {doc.total_pages} pages</>} &middot; {doc.total_chunks} chunks
            </p>
          </div>
          <button
            onClick={() => handleDelete(doc.id)}
            className="text-red-500 hover:text-red-700 text-sm"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
