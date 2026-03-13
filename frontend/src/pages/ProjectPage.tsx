import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import FileUpload from '../components/FileUpload'
import DocumentList from '../components/DocumentList'
import ChatPanel from '../components/ChatPanel'
import AnalysisPanel from '../components/AnalysisPanel'

interface Project {
  id: string
  name: string
  description: string
}

interface Document {
  id: string
  filename: string
  file_type: string
  total_pages: number
  total_chunks: number
  uploaded_at: string
}

type Tab = 'documents' | 'analysis'

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [activeTab, setActiveTab] = useState<Tab>('documents')

  useEffect(() => {
    if (projectId) {
      loadProject()
      loadDocuments()
    }
  }, [projectId])

  const loadProject = async () => {
    try {
      const res = await api.get(`/projects/${projectId}`)
      setProject(res.data)
    } catch {
      navigate('/')
    }
  }

  const loadDocuments = async () => {
    const res = await api.get(`/documents/${projectId}`)
    setDocuments(res.data.documents)
  }

  if (!project) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-500 hover:text-gray-700">
            &larr; Back
          </button>
          <h1 className="text-xl font-bold">{project.name}</h1>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === 'documents'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Documents
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              activeTab === 'analysis'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Analysis
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {activeTab === 'documents' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Upload + Documents */}
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-3">Upload Documents</h2>
                <FileUpload projectId={projectId!} onUploaded={loadDocuments} />
              </div>
              <div>
                <h2 className="text-lg font-semibold mb-3">Documents ({documents.length})</h2>
                <DocumentList documents={documents} onDeleted={loadDocuments} />
              </div>
            </div>

            {/* Right: Chat */}
            <div className="bg-white rounded-lg shadow p-4 flex flex-col" style={{ minHeight: '500px' }}>
              <h2 className="text-lg font-semibold mb-3">Q&A Chat</h2>
              <ChatPanel projectId={projectId!} />
            </div>
          </div>
        )}

        {activeTab === 'analysis' && (
          <AnalysisPanel projectId={projectId!} />
        )}
      </main>
    </div>
  )
}
