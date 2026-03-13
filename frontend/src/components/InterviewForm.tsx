import { useState } from 'react'

interface Question {
  question_id: string
  feature_id: string
  question: string
  question_type: string
  suggested_answer: string
  user_answer?: string
}

interface FeatureDraft {
  feature_id: string
  title: string
}

interface Props {
  questions: Question[]
  featureDrafts: FeatureDraft[]
  onSubmit: (answers: { question_id: string; user_answer: string }[]) => void
  loading: boolean
}

const TYPE_COLORS: Record<string, string> = {
  scope: 'bg-blue-100 text-blue-800',
  edge_case: 'bg-amber-100 text-amber-800',
  dependency: 'bg-purple-100 text-purple-800',
  business_value: 'bg-green-100 text-green-800',
}

const TYPE_LABELS: Record<string, string> = {
  scope: 'Scope',
  edge_case: 'Edge Case',
  dependency: 'Dependency',
  business_value: 'Business Value',
}

export default function InterviewForm({ questions, featureDrafts, onSubmit, loading }: Props) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    for (const q of questions) {
      initial[q.question_id] = q.user_answer || q.suggested_answer || ''
    }
    return initial
  })

  const handleSubmit = () => {
    const payload = questions.map(q => ({
      question_id: q.question_id,
      user_answer: answers[q.question_id] || q.suggested_answer,
    }))
    onSubmit(payload)
  }

  // Group questions by feature
  const featureMap = new Map<string, string>()
  for (const f of featureDrafts) {
    featureMap.set(f.feature_id, f.title)
  }

  const grouped = new Map<string, Question[]>()
  for (const q of questions) {
    if (!grouped.has(q.feature_id)) grouped.set(q.feature_id, [])
    grouped.get(q.feature_id)!.push(q)
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-2">Review Interview Answers</h3>
      <p className="text-gray-600 text-sm mb-6">
        Review and edit the AI-suggested answers below. Your edits will be used to generate more accurate user stories.
      </p>

      <div className="space-y-8">
        {Array.from(grouped.entries()).map(([featureId, featureQuestions]) => (
          <div key={featureId}>
            <h4 className="font-semibold text-gray-800 mb-3 border-b pb-2">
              <span className="font-mono text-blue-600 mr-2">{featureId}</span>
              {featureMap.get(featureId) || featureId}
            </h4>

            <div className="space-y-4">
              {featureQuestions.map(q => (
                <div key={q.question_id} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm font-medium text-gray-800 flex-1">{q.question}</p>
                    <span className={`ml-3 px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${TYPE_COLORS[q.question_type] || 'bg-gray-100 text-gray-700'}`}>
                      {TYPE_LABELS[q.question_type] || q.question_type}
                    </span>
                  </div>
                  <textarea
                    value={answers[q.question_id] || ''}
                    onChange={e => setAnswers(prev => ({ ...prev, [q.question_id]: e.target.value }))}
                    rows={3}
                    className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Submit & Generate Stories'}
        </button>
      </div>
    </div>
  )
}
