import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import api from '../lib/api'

interface Project {
  id: string
  name: string
  description: string
  created_at: string
  document_count: number
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [showNew, setShowNew] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const navigate = useNavigate()
  const { user, fetchUser, logout } = useAuthStore()

  useEffect(() => {
    fetchUser()
    loadProjects()
  }, [])

  const loadProjects = async () => {
    const res = await api.get('/projects')
    setProjects(res.data)
  }

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/projects', { name, description })
    setName('')
    setDescription('')
    setShowNew(false)
    loadProjects()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">BA Toolkit</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">{user?.display_name}</span>
            <button onClick={logout} className="text-sm text-red-500 hover:underline">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Projects</h2>
          <button
            onClick={() => setShowNew(!showNew)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
          >
            New Project
          </button>
        </div>

        {showNew && (
          <form onSubmit={createProject} className="bg-white p-4 rounded-lg shadow mb-6 space-y-3">
            <input
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <input
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700"
            >
              Create
            </button>
          </form>
        )}

        {projects.length === 0 ? (
          <p className="text-gray-400">No projects yet. Create one to get started.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => navigate(`/projects/${p.id}`)}
                className="bg-white p-4 rounded-lg shadow hover:shadow-md cursor-pointer transition-shadow"
              >
                <h3 className="font-semibold text-gray-800">{p.name}</h3>
                {p.description && (
                  <p className="text-sm text-gray-500 mt-1">{p.description}</p>
                )}
                <p className="text-xs text-gray-400 mt-2">
                  {p.document_count} documents
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
