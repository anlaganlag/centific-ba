import { useState } from 'react'

interface AcceptanceCriterion {
  given: string
  when: string
  then: string
}

interface UserStory {
  story_id: string
  as_a: string
  i_want: string
  so_that: string
  acceptance_criteria: AcceptanceCriterion[]
  business_rules: string[]
  dependencies: string[]
}

interface Feature {
  feature_id: string
  title: string
  problem_statement: string
  benefit: string
  business_process: string
  scope: string
  sources: string[]
  user_stories: UserStory[]
}

interface Props {
  features: Feature[]
}

export default function FeatureList({ features }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-3">
      {features.map(feat => (
        <div key={feat.feature_id} className="bg-white rounded-lg shadow border">
          {/* Header */}
          <button
            onClick={() => toggle(feat.feature_id)}
            className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-50 transition"
          >
            <div>
              <span className="text-xs font-mono text-blue-600 mr-2">{feat.feature_id}</span>
              <span className="font-semibold">{feat.title}</span>
              <span className="ml-3 text-xs text-gray-500">
                {feat.user_stories?.length || 0} stories
              </span>
            </div>
            <svg
              className={`w-5 h-5 text-gray-400 transition-transform ${expanded.has(feat.feature_id) ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Expanded content */}
          {expanded.has(feat.feature_id) && (
            <div className="px-5 pb-5 border-t">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-sm">
                <div>
                  <h4 className="font-medium text-gray-700 mb-1">Problem</h4>
                  <p className="text-gray-600">{feat.problem_statement}</p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-700 mb-1">Benefit</h4>
                  <p className="text-gray-600">{feat.benefit}</p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-700 mb-1">Business Process</h4>
                  <p className="text-gray-600">{feat.business_process}</p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-700 mb-1">Scope</h4>
                  <p className="text-gray-600">{feat.scope}</p>
                </div>
              </div>

              {/* User Stories */}
              {feat.user_stories && feat.user_stories.length > 0 && (
                <div className="mt-5">
                  <h4 className="font-semibold text-gray-800 mb-3">User Stories</h4>
                  <div className="space-y-3">
                    {feat.user_stories.map(story => (
                      <div key={story.story_id} className="bg-gray-50 rounded-lg p-4 text-sm">
                        <p className="font-medium mb-2">
                          <span className="font-mono text-blue-600 mr-1">{story.story_id}:</span>
                          As a <strong>{story.as_a}</strong>, I want <strong>{story.i_want}</strong>,
                          so that <strong>{story.so_that}</strong>
                        </p>

                        {story.acceptance_criteria.length > 0 && (
                          <div className="mt-2">
                            <p className="text-gray-500 font-medium text-xs uppercase mb-1">Acceptance Criteria</p>
                            <ul className="space-y-1">
                              {story.acceptance_criteria.map((ac, i) => (
                                <li key={i} className="text-gray-600 ml-3">
                                  <span className="text-green-700">Given</span> {ac.given},{' '}
                                  <span className="text-amber-700">When</span> {ac.when},{' '}
                                  <span className="text-blue-700">Then</span> {ac.then}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {story.business_rules.length > 0 && (
                          <div className="mt-2">
                            <p className="text-gray-500 font-medium text-xs uppercase mb-1">Business Rules</p>
                            <ul className="list-disc ml-6 text-gray-600">
                              {story.business_rules.map((rule, i) => (
                                <li key={i}>{rule}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {story.dependencies.length > 0 && (
                          <p className="mt-2 text-gray-500 text-xs">
                            Dependencies: {story.dependencies.join(', ')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sources */}
              {feat.sources && feat.sources.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-gray-500 font-medium uppercase mb-1">Sources</p>
                  <ul className="text-xs text-gray-500 space-y-0.5">
                    {feat.sources.map((src, i) => (
                      <li key={i}>{src}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
