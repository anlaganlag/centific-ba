import { useState, useEffect, useRef } from 'react'
import api from '../lib/api'
import FeatureList from './FeatureList'
import InterviewForm from './InterviewForm'

interface Props {
  projectId: string
}

type Status = 'idle' | 'extracting' | 'interviewing' | 'awaiting_answers' | 'generating' | 'done' | 'error'

interface AnalysisSession {
  session_id: string
  project_id: string
  mode: string
  status: Status
  error_message?: string
  progress_message?: string
  feature_drafts?: any[]
  questions?: any[]
  features?: any[]
}

const STEP_INFO: Record<string, { label: string; step: number }> = {
  extracting:  { label: 'Step 1/3: Extracting features from documents', step: 1 },
  interviewing: { label: 'Step 2/3: Generating interview questions', step: 2 },
  generating:  { label: 'Step 3/3: Writing user stories', step: 3 },
}

export default function AnalysisPanel({ projectId }: Props) {
  const [session, setSession] = useState<AnalysisSession | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [mode, setMode] = useState<'auto' | 'guided'>('auto')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const pollingRef = useRef<number | null>(null)

  useEffect(() => {
    loadStatus()
    return () => stopPolling()
  }, [projectId])

  const loadStatus = async () => {
    try {
      const res = await api.get(`/analysis/${projectId}/status`)
      setSession(res.data)
      setStatus(res.data.status)
      // If still processing, start polling
      if (['extracting', 'interviewing', 'generating'].includes(res.data.status)) {
        setLoading(true)
        startPolling()
      }
    } catch {
      setSession(null)
      setStatus('idle')
    }
  }

  const startPolling = () => {
    stopPolling()
    pollingRef.current = window.setInterval(async () => {
      try {
        const res = await api.get(`/analysis/${projectId}/status`)
        setSession(res.data)
        setStatus(res.data.status)
        if (['done', 'error', 'awaiting_answers'].includes(res.data.status)) {
          stopPolling()
          setLoading(false)
        }
      } catch {
        stopPolling()
        setLoading(false)
      }
    }, 2000)
  }

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const handleStart = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.post(`/analysis/${projectId}/start`, { mode })
      setSession(res.data)
      setStatus(res.data.status)
      // Always start polling — backend now returns immediately
      startPolling()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start analysis')
      setLoading(false)
    }
  }

  const handleSubmitAnswers = async (answers: { question_id: string; user_answer: string }[]) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.post(`/analysis/${projectId}/answers`, { answers })
      setSession(res.data)
      setStatus(res.data.status)
      // Start polling for step 3
      startPolling()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to submit answers')
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const res = await api.get(`/analysis/${projectId}/export`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `BA_Analysis.docx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      setError('Failed to export DOCX')
    }
  }

  const isProcessing = ['extracting', 'interviewing', 'generating'].includes(status)
  const stepInfo = STEP_INFO[status]
  const progressPct = status === 'extracting' ? 25
    : status === 'interviewing' ? 55
    : status === 'generating' ? 80
    : 0

  return (
    <div className="space-y-6">
      {/* Start controls */}
      {(status === 'idle' || status === 'done' || status === 'error') && !loading && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">BA Analysis</h3>
          <p className="text-gray-600 mb-4">
            AI will analyze your documents and generate features, interview Q&A, and user stories.
          </p>

          <div className="flex items-center gap-4 mb-4">
            <label className="text-sm font-medium">Mode:</label>
            <select
              value={mode}
              onChange={e => setMode(e.target.value as 'auto' | 'guided')}
              className="border rounded px-3 py-1.5 text-sm"
            >
              <option value="auto">Auto — AI handles everything</option>
              <option value="guided">Guided — Review answers before stories</option>
            </select>
          </div>

          <button
            onClick={handleStart}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition"
          >
            {status === 'done' ? 'Re-run Analysis' : 'Start Analysis'}
          </button>

          {error && (
            <p className="mt-3 text-red-600 text-sm">{error}</p>
          )}

          {status === 'error' && session?.error_message && (
            <p className="mt-3 text-red-600 text-sm">Last error: {session.error_message}</p>
          )}
        </div>
      )}

      {/* Processing indicator */}
      {(isProcessing || (loading && !['done', 'error', 'awaiting_answers'].includes(status))) && (
        <div className="bg-white rounded-lg shadow p-6">
          {/* Step indicator */}
          <div className="flex items-center gap-6 mb-5">
            {[1, 2, 3].map(step => (
              <div key={step} className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  stepInfo && step < stepInfo.step ? 'bg-green-500 text-white'
                  : stepInfo && step === stepInfo.step ? 'bg-blue-600 text-white animate-pulse'
                  : 'bg-gray-200 text-gray-500'
                }`}>
                  {stepInfo && step < stepInfo.step ? '\u2713' : step}
                </div>
                <span className={`text-sm ${
                  stepInfo && step === stepInfo.step ? 'text-blue-700 font-medium' : 'text-gray-500'
                }`}>
                  {step === 1 ? 'Extract' : step === 2 ? 'Interview' : 'Stories'}
                </span>
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Status text */}
          <div className="flex items-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full" />
            <span className="text-sm text-gray-700">
              {session?.progress_message || stepInfo?.label || 'Processing...'}
            </span>
          </div>
        </div>
      )}

      {/* Guided mode: interview form */}
      {status === 'awaiting_answers' && session?.questions && session?.feature_drafts && (
        <InterviewForm
          questions={session.questions}
          featureDrafts={session.feature_drafts}
          onSubmit={handleSubmitAnswers}
          loading={loading}
        />
      )}

      {/* Results */}
      {status === 'done' && session?.features && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Analysis Results</h3>
            <div className="flex items-center gap-3">
              {session.progress_message && (
                <span className="text-sm text-gray-500">{session.progress_message}</span>
              )}
              <button
                onClick={handleExport}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition text-sm"
              >
                Export DOCX
              </button>
            </div>
          </div>
          <FeatureList features={session.features} />
        </div>
      )}
    </div>
  )
}
