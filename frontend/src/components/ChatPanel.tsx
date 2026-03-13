import { useState } from 'react'
import api from '../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ doc_name: string; page?: number; excerpt?: string }>
}

interface Props {
  projectId: string
}

export default function ChatPanel({ projectId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    const q = input.trim()
    if (!q) return
    setInput('')
    const userMsg: Message = { role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }))
      const res = await api.post(`/chat/${projectId}`, { question: q, history })
      const assistantMsg: Message = {
        role: 'assistant',
        content: res.data.answer,
        sources: res.data.sources,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error getting answer. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm">Ask questions about your uploaded documents.</p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg ${
              msg.role === 'user'
                ? 'bg-blue-100 text-blue-900 ml-8'
                : 'bg-white border border-gray-200 mr-8'
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-2 text-xs text-gray-500">
                <p className="font-medium">Sources:</p>
                {msg.sources.map((s, j) => (
                  <p key={j}>
                    {s.doc_name}{s.page ? `, p.${s.page}` : ''}
                    {s.excerpt && <span className="italic"> — "{s.excerpt.slice(0, 80)}..."</span>}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <p className="text-gray-400 text-sm animate-pulse">Thinking...</p>}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask a question..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}
