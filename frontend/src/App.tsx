import { useEffect, useState } from 'react'
import './App.css'

type Challenge = {
  challengeId: string
  mode: 'code' | 'ideation'
  submissionIds: string[]
}

function App() {
  const [challenges, setChallenges] = useState<Challenge[]>([])
  const [selectedChallenge, setSelectedChallenge] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [workspaceTab, setWorkspaceTab] = useState<'evidence' | 'requirements' | 'copilot' | 'verify'>('evidence')
  const [profiles, setProfiles] = useState<Record<string, unknown>>({})
  const [workspaceLoading, setWorkspaceLoading] = useState(false)
  const [decisions, setDecisions] = useState<Record<string, unknown>[]>([])
  const [ideationAnalysis, setIdeationAnalysis] = useState<{
    evaluation?: {
      evaluations?: Array<{
        criterion?: string
        ideaId?: string
        submissionId?: string
        reasoning?: string
        score?: number
        status?: string
      }>
    }
  } | null>(null)
  const [expandedIdea, setExpandedIdea] = useState<string | null>(null)
  const [ideationDecisions, setIdeationDecisions] = useState<
    Array<{
      requirementId?: string
      requirementTitle?: string
      state?: string
      selectedSubmissionId?: string | null
      recommendedSubmissionId?: string | null
      reason?: string
      recommendationScore?: number
      recommendationConfidence?: number
      evidenceRefs?: string[]
      alternativeSubmissionId?: string | null
      reviewer?: string | null
    }>
  >([])

  useEffect(() => {
    fetch('/api/challenges')
      .then((response) => {
        if (!response.ok) throw new Error(`API error: ${response.status}`)
        return response.json()
      })
      .then((data: { challenges: Challenge[] }) => {
        setChallenges(data.challenges)
        if (data.challenges.length > 0) {
          setSelectedChallenge(data.challenges[0].challengeId)
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const selected = challenges.find(
    (challenge) => challenge.challengeId === selectedChallenge,
  )

  useEffect(() => {
    if (!workspaceOpen || !selected) return

    setWorkspaceLoading(true)

    Promise.all(
      selected.submissionIds.map(async (submissionId) => {
        const response = await fetch(
          `/api/challenges/${selected.challengeId}/submissions/${submissionId}/profile`,
        )

        if (!response.ok) {
          throw new Error(`Profile API error: ${response.status}`)
        }

        return [submissionId, await response.json()] as const
      }),
    )
      .then((entries) => {
        setProfiles(Object.fromEntries(entries))
        if (selected.mode === 'ideation') {
          return fetch(`/api/challenges/${selected.challengeId}/ideation-analysis`)
            .then((response) => {
              if (!response.ok) {
                throw new Error(`Ideation API error: ${response.status}`)
              }
              return response.json()
            })
            .then((data) => {
              setIdeationAnalysis(data)
              setIdeationDecisions(data.decisions?.decisions ?? [])
            })
        }

        if (selected.mode === 'code') {
          return fetch(`/api/challenges/${selected.challengeId}/decisions`)
            .then((response) => {
              if (!response.ok) {
                throw new Error(`Decision API error: ${response.status}`)
              }
              return response.json()
            })
            .then((data) => {
              setDecisions(data.decisions ?? [])
            })
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setWorkspaceLoading(false))
  }, [workspaceOpen, selected])

  const ideationEvaluations = Array.isArray(ideationAnalysis?.evaluation?.evaluations)
    ? ideationAnalysis.evaluation.evaluations.reduce<
        Record<string, Array<{
          criterion?: string
          ideaId?: string
          submissionId?: string
          reasoning?: string
          score?: number
          status?: string
        }>>
      >((groups, evaluation) => {
        const key = String(evaluation.ideaId ?? evaluation.submissionId ?? 'unknown')
        if (!groups[key]) groups[key] = []
        groups[key].push(evaluation)
        return groups
      }, {})
    : {}

  if (workspaceOpen && selected) {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">TC</div>
            <div>
              <div className="brand-name">Topcoder Combinator</div>
              <div className="brand-subtitle">AI-assisted submission synthesis</div>
            </div>
          </div>

          <button
            className="back-button"
            onClick={() => setWorkspaceOpen(false)}
          >
            ← Back to challenges
          </button>
        </header>

        <main className="main workspace-main">
          <section className="workspace-title">
            <div>
              <p className="section-label">
                {selected.mode.toUpperCase()} WORKSPACE
              </p>
              <h1>{selected.challengeId}</h1>
              <p className="hero-copy">
                Review evidence and make Copilot decisions before generating
                the candidate.
              </p>
            </div>

            <div className="workspace-status">
              <span className="status-dot" />
              Ready for review
            </div>
          </section>

          <section className="workspace-tabs">
            <button
              className={`workspace-tab ${workspaceTab === 'evidence' ? 'active' : ''}`}
              onClick={() => setWorkspaceTab('evidence')}
            >
              01 Evidence
            </button>
            <button
              className={`workspace-tab ${workspaceTab === 'requirements' ? 'active' : ''}`}
              onClick={() => setWorkspaceTab('requirements')}
            >
              02 Requirements
            </button>
            <button
              className={`workspace-tab ${workspaceTab === 'copilot' ? 'active' : ''}`}
              onClick={() => setWorkspaceTab('copilot')}
            >
              03 Copilot
            </button>
            <button
              className={`workspace-tab ${workspaceTab === 'verify' ? 'active' : ''}`}
              onClick={() => setWorkspaceTab('verify')}
            >
              04 Verify
            </button>
          </section>

          {workspaceTab === 'requirements' && selected.mode === 'code' && (
            <section className="workspace-content">
              <div className="workspace-card">
                <div className="workspace-card-header">
                  <div>
                    <p className="section-label">REQUIREMENT MATRIX</p>
                    <h2>Coverage and recommendations</h2>
                  </div>
                  <span className="count-badge">{decisions.length}</span>
                </div>

                <div className="submission-list">
                  {decisions.map((decision, index) => (
                    <div className="submission-row" key={index}>
                      <div>
                        <strong>
                          {String(
                            decision.requirementTitle ??
                              decision.requirementId ??
                              `Requirement ${index + 1}`,
                          )}
                        </strong>
                        <span>
                          Recommended:{' '}
                          {String(
                            decision.recommendedSubmissionId ?? 'None',
                          )}
                        </span>
                      </div>
                      <span className="review-badge">
                        {decision.recommendationConfidence != null
                          ? `${(
                              Number(decision.recommendationConfidence) * 100
                            ).toFixed(0)}%`
                          : 'Pending'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {workspaceTab === 'requirements' && selected.mode === 'ideation' && (
            <section className="workspace-content">
              <div className="workspace-card">
                <div className="workspace-card-header">
                  <div>
                    <p className="section-label">IDEATION ANALYSIS</p>
                    <h2>Concept evaluation</h2>
                  </div>
                  <span className="count-badge">
                    {Array.isArray(ideationAnalysis?.evaluation?.evaluations)
                      ? ideationAnalysis.evaluation.evaluations.length
                      : 0}
                  </span>
                </div>

                <div className="submission-list">
                  {Object.entries(ideationEvaluations).length > 0 ? (
                    Object.entries(ideationEvaluations).map(
                      ([ideaId, evaluations]) => (
                        <div key={ideaId}>
                          <button
                            className="submission-row"
                            onClick={() =>
                              setExpandedIdea(
                                expandedIdea === ideaId ? null : ideaId,
                              )
                            }
                          >
                            <div>
                              <strong>{ideaId}</strong>
                              <span>
                                {evaluations
                                  .map(
                                    (evaluation) =>
                                      `${String(evaluation.criterion ?? 'Evaluation')}: ${
                                        evaluation.score != null
                                          ? `${(Number(evaluation.score) * 100).toFixed(0)}%`
                                          : String(evaluation.status ?? 'Review')
                                      }`,
                                  )
                                  .join(' · ')}
                              </span>
                            </div>
                            <span className="review-badge">
                              {evaluations.length} criteria
                            </span>
                          </button>

                          {expandedIdea === ideaId && (
                            <div className="idea-details">
                              {evaluations.map((evaluation, evaluationIndex) => (
                                <div
                                  className="idea-detail"
                                  key={`${ideaId}-${evaluationIndex}`}
                                >
                                  <div className="idea-detail-header">
                                    <strong>
                                      {String(evaluation.criterion ?? 'Evaluation')}
                                    </strong>
                                    <span className="review-badge">
                                      {evaluation.score != null
                                        ? `${(Number(evaluation.score) * 100).toFixed(0)}%`
                                        : String(evaluation.status ?? 'Review')}
                                    </span>
                                  </div>
                                  <p>
                                    {String(
                                      evaluation.reasoning ??
                                        'No reasoning available.',
                                    )}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ),
                    )
                  ) : (
                    <div className="empty-state">
                      <p>No ideation evaluation data available.</p>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {workspaceTab === 'evidence' && (
            <section className="workspace-content">
              <div className="workspace-card">
              <div className="workspace-card-header">
                <div>
                  <p className="section-label">SOURCE SUBMISSIONS</p>
                  <h2>Submission evidence</h2>
                </div>
                <span className="count-badge">
                  {selected.submissionIds.length}
                </span>
              </div>

              <div className="submission-list">
                {workspaceLoading && (
                  <div className="submission-row">
                    <div>
                      <strong>Loading evidence...</strong>
                      <span>Reading submission profiles</span>
                    </div>
                  </div>
                )}

                {!workspaceLoading &&
                  selected.submissionIds.map((submissionId) => {
                    const profile = profiles[submissionId] as
                      | Record<string, unknown>
                      | undefined

                    return (
                      <div className="submission-row" key={submissionId}>
                        <div>
                          <strong>{submissionId}</strong>
                          <span>
                            {selected.mode === 'code'
                              ? 'Runnable source submission'
                              : 'Idea source submission'}
                            {profile &&
                              ` · ${Object.keys(profile).length} profile fields`}
                            {profile?.repository_structure != null &&
                              ` · ${Object.keys(
                                profile.repository_structure as Record<string, unknown>,
                              ).length} structure sections`}
                          </span>
                        </div>
                        <span className="review-badge">
                          {profile ? 'Evidence ready' : 'Review'}
                        </span>
                      </div>
                    )
                  })}
              </div>
            </div>

            <div className="workspace-card">
              <div className="workspace-card-header">
                <div>
                  <p className="section-label">COPILOT</p>
                  <h2>Decision workspace</h2>
                </div>
              </div>

              <div className="copilot-placeholder">
                <div className="copilot-icon">AI</div>
                <h3>Evidence-driven decisions</h3>
                <p>
                  {selected.mode === 'code'
                    ? `${decisions.length} Copilot decisions loaded from the workspace.`
                    : 'Ideation decisions will be shown here.'}
                </p>
                {selected.mode === 'code' && decisions.length > 0 ? (
                  <div className="decision-summary">
                    {decisions.slice(0, 3).map((decision, index) => (
                      <div className="decision-item" key={index}>
                        <strong>
                          {String(
                            decision.requirementTitle ??
                              decision.requirementId ??
                              `Decision ${index + 1}`,
                          )}
                        </strong>
                        <span>
                          {String(decision.state ?? 'pending')}
                          {decision.recommendedSubmissionId
                            ? ` · ${String(decision.recommendedSubmissionId)}`
                            : ''}
                          {decision.recommendationConfidence != null
                            ? ` · ${(Number(decision.recommendationConfidence) * 100).toFixed(0)}% confidence`
                            : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : selected.mode === 'ideation' && ideationDecisions.length > 0 ? (
                  <div className="decision-summary">
                    {ideationDecisions.map((decision, index) => (
                      <div className="decision-item" key={decision.requirementId ?? index}>
                        <div>
                          <strong>
                            {String(
                              decision.requirementTitle ??
                                decision.requirementId ??
                                `Decision ${index + 1}`,
                            )}
                          </strong>
                          <span>
                            {String(decision.state ?? 'pending')}
                            {decision.recommendedSubmissionId
                              ? ` · Recommended: ${String(decision.recommendedSubmissionId)}`
                              : ' · Copilot selection required'}
                            {decision.recommendationConfidence != null
                              ? ` · ${(Number(decision.recommendationConfidence) * 100).toFixed(0)}% confidence`
                              : ''}
                          </span>
                        </div>
                        <span className="review-badge">
                          {String(decision.state ?? 'pending')}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <button className="primary-button">
                    Load recommendations
                  </button>
                )}
              </div>
              </div>
            </section>
          )}
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">TC</div>
          <div>
            <div className="brand-name">Topcoder Combinator</div>
            <div className="brand-subtitle">AI-assisted submission synthesis</div>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          System ready
        </div>
      </header>

      <main className="main">
        <section className="hero-section">
          <div>
            <p className="eyebrow">COMBINATOR WORKSPACE</p>
            <h1>Turn strong submissions into one stronger candidate.</h1>
            <p className="hero-copy">
              Compare evidence, make Copilot decisions, combine approved
              components, and verify the resulting candidate.
            </p>
          </div>

          <div className="hero-stat">
            <span className="stat-value">{challenges.length}</span>
            <span className="stat-label">Challenges loaded</span>
          </div>
        </section>

        {loading && (
          <div className="state-card">
            <div className="spinner" />
            Loading challenge workspace...
          </div>
        )}

        {error && (
          <div className="state-card error">
            <strong>Backend unavailable</strong>
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && (
          <section className="workspace-grid">
            <aside className="challenge-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">CHALLENGES</p>
                  <h2>Source challenges</h2>
                </div>
                <span className="count-badge">{challenges.length}</span>
              </div>

              <div className="challenge-list">
                {challenges.map((challenge) => (
                  <button
                    key={challenge.challengeId}
                    className={`challenge-item ${
                      selectedChallenge === challenge.challengeId
                        ? 'active'
                        : ''
                    }`}
                    onClick={() =>
                      setSelectedChallenge(challenge.challengeId)
                    }
                  >
                    <div className="challenge-mode">
                      <span
                        className={`mode-dot ${challenge.mode}`}
                      />
                      {challenge.mode}
                    </div>

                    <div className="challenge-id">
                      {challenge.challengeId}
                    </div>

                    <div className="challenge-meta">
                      {challenge.submissionIds.length} submissions
                    </div>
                  </button>
                ))}
              </div>
            </aside>

            <section className="detail-panel">
              {selected ? (
                <>
                  <div className="detail-header">
                    <div>
                      <p className="section-label">
                        {selected.mode.toUpperCase()} MODE
                      </p>
                      <h2>{selected.challengeId}</h2>
                      <p className="muted">
                        Select a challenge to inspect evidence and drive the
                        Copilot workflow.
                      </p>
                    </div>

                    <button className="primary-button" onClick={() => setWorkspaceOpen(true)}>
                      Open workspace
                    </button>
                  </div>

                  <div className="overview-cards">
                    <div className="overview-card">
                      <span className="card-label">SUBMISSIONS</span>
                      <strong>{selected.submissionIds.length}</strong>
                      <span className="card-hint">Available sources</span>
                    </div>

                    <div className="overview-card">
                      <span className="card-label">MODE</span>
                      <strong>
                        {selected.mode === 'code'
                          ? 'Code'
                          : 'Ideation'}
                      </strong>
                      <span className="card-hint">
                        {selected.mode === 'code'
                          ? 'Runnable candidate'
                          : 'Synthesized concept'}
                      </span>
                    </div>

                    <div className="overview-card">
                      <span className="card-label">COPILOT</span>
                      <strong>Ready</strong>
                      <span className="card-hint">
                        Review decisions before synthesis
                      </span>
                    </div>
                  </div>

                  <div className="workflow">
                    <div className="workflow-header">
                      <div>
                        <p className="section-label">WORKFLOW</p>
                        <h3>Combinator pipeline</h3>
                      </div>
                    </div>

                    <div className="workflow-steps">
                      <div className="workflow-step active-step">
                        <span className="step-number">01</span>
                        <div>
                          <strong>Evidence</strong>
                          <span>Inspect submissions and reviews</span>
                        </div>
                      </div>

                      <div className="workflow-step">
                        <span className="step-number">02</span>
                        <div>
                          <strong>Requirements</strong>
                          <span>Compare coverage and compatibility</span>
                        </div>
                      </div>

                      <div className="workflow-step">
                        <span className="step-number">03</span>
                        <div>
                          <strong>Copilot</strong>
                          <span>Accept, reject, or choose alternatives</span>
                        </div>
                      </div>

                      <div className="workflow-step">
                        <span className="step-number">04</span>
                        <div>
                          <strong>Verify</strong>
                          <span>Generate and validate the candidate</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  <h2>No challenge selected</h2>
                  <p>Select a challenge from the left panel.</p>
                </div>
              )}
            </section>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
