import { useState, useEffect, useRef } from 'react'

function timeAgo(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)

  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)
  if (minutes === 1) return '1 min ago'
  if (minutes < 60) return `${minutes} min ago`

  const hours = Math.floor(minutes / 60)
  if (hours === 1) return '1 hour ago'
  if (hours < 24) return `${hours} hours ago`

  const days = Math.floor(hours / 24)
  if (days === 1) return '1 day ago'
  if (days < 7) return `${days} days ago`

  return date.toLocaleDateString()
}

export default function App() {
  const [running, setRunning] = useState(false)
  const [step, setStep] = useState(null)
  const [stepStatus, setStepStatus] = useState({})
  const [disasters, setDisasters] = useState([])
  const [ngoLinks, setNgoLinks] = useState([])
  const [emailCount, setEmailCount] = useState(0)
  const [emailPreviews, setEmailPreviews] = useState([])
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [progressText, setProgressText] = useState('')
  const [complete, setComplete] = useState(false)

  const endRef = useRef(null)

  // Auto-scroll when new content appears
  useEffect(() => {
    if (running && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [running, stepStatus, disasters, ngoLinks, emailPreviews, complete])

  const runPipeline = async () => {
    setRunning(true)
    setStep(null)
    setStepStatus({})
    setDisasters([])
    setNgoLinks([])
    setEmailCount(0)
    setEmailPreviews([])
    setSelectedEmail(null)
    setProgressText('')
    setComplete(false)

    const eventSource = new EventSource('/api/run-pipeline')

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'status':
          setStep(data.step)
          setStepStatus(prev => ({ ...prev, [data.step]: data.status }))
          break
        case 'disasters':
          setDisasters(data.data)
          break
        case 'ngo_progress':
          setProgressText(`Finding NGOs for ${data.disaster_name}...`)
          break
        case 'ngos_found':
          setNgoLinks(prev => [
            ...prev,
            ...data.ngos.map(ngo => ({
              ngo,
              disasterIndex: data.disaster_index
            }))
          ])
          break
        case 'all_ngo_links':
          break
        case 'email_sent':
          setEmailCount(data.total)
          setEmailPreviews(prev => [...prev, data.preview])
          setProgressText(`Sending email ${data.index + 1} of ${data.total}...`)
          break
        case 'emails_complete':
          setEmailCount(data.count)
          setProgressText('')
          break
        case 'pipeline_complete':
          setComplete(true)
          setRunning(false)
          eventSource.close()
          break
      }
    }

    eventSource.onerror = () => {
      setRunning(false)
      eventSource.close()
    }
  }

  const getStepNumber = (stepName) => {
    const status = stepStatus[stepName]
    if (status === 'complete') return 'complete'
    if (status === 'loading') return 'active'
    return ''
  }

  const getLoadingClass = (stepName) => {
    const status = stepStatus[stepName]
    if (status === 'complete') return 'complete'
    if (status === 'loading') return 'indeterminate'
    return ''
  }

  return (
    <div className="container">
      <div className="header">
        <img src="/logo.png" alt="Poseidon" className="logo" />
        <div className="header-actions">
          <span className="auto-run-note">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            Runs every 30 min
          </span>
          <button
            className="start-btn"
            onClick={runPipeline}
            disabled={running}
          >
            {running ? 'Running...' : 'Run Pipeline'}
          </button>
        </div>
      </div>

      <div className="pipeline">
        {/* Step 1: Disasters */}
        <div className="step">
          <div className="step-header">
            <div className={`step-number ${getStepNumber('disasters')}`}>1</div>
            <span className="step-title">Fetch Recent Disasters</span>
            {stepStatus.disasters && (
              <span className="step-status">
                {stepStatus.disasters === 'loading' ? 'Searching...' : `${disasters.length} found`}
              </span>
            )}
          </div>
          <div className="loading-bar">
            <div className={`loading-bar-fill ${getLoadingClass('disasters')}`} />
          </div>
          {disasters.length > 0 && (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Disaster</th>
                    <th>Type</th>
                    <th>Location</th>
                    <th>Severity</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {disasters.map((d, i) => (
                    <tr key={i}>
                      <td>{d.name}</td>
                      <td>{d.disaster_type}</td>
                      <td>{d.location}, {d.country}</td>
                      <td><span className={`severity ${d.severity}`}>{d.severity}</span></td>
                      <td>{timeAgo(d.occurred_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {(stepStatus.disasters === 'complete' || stepStatus.ngos) && (
          <div className="connector" />
        )}

        {/* Step 2: NGOs */}
        {(stepStatus.disasters === 'complete' || stepStatus.ngos) && (
          <div className="step">
            <div className="step-header">
              <div className={`step-number ${getStepNumber('ngos')}`}>2</div>
              <span className="step-title">Match NGOs to Disasters</span>
              {stepStatus.ngos && (
                <span className="step-status">
                  {stepStatus.ngos === 'loading' ? 'Matching...' : `${ngoLinks.length} NGOs matched`}
                </span>
              )}
            </div>
            <div className="loading-bar">
              <div className={`loading-bar-fill ${getLoadingClass('ngos')}`} />
            </div>
            {progressText && <div className="progress-text">{progressText}</div>}
            {ngoLinks.length > 0 && (
              <div className="linked-ngos">
                {disasters.map((disaster, dIdx) => {
                  const linkedNgos = ngoLinks.filter(l => l.disasterIndex === dIdx)
                  if (linkedNgos.length === 0) return null
                  return (
                    <div className="disaster-ngo-group" key={dIdx}>
                      <div className="disaster-label">
                        <div className="disaster-dot" />
                        <span className="disaster-name">{disaster.name}</span>
                      </div>
                      <div className="ngo-list">
                        {linkedNgos.map((link, nIdx) => (
                          <div className="ngo-item" key={nIdx}>
                            <div className="ngo-connector">
                              <div className="connector-line" />
                              <div className="connector-dot" />
                            </div>
                            <div className="ngo-info">
                              <div className="ngo-name">{link.ngo.name}</div>
                              <div className="ngo-details">
                                {link.ngo.aid_type} • {link.ngo.ngo_type} • {link.ngo.contact_email}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {(stepStatus.ngos === 'complete' || stepStatus.emails) && (
          <div className="connector" />
        )}

        {/* Step 3: Emails */}
        {(stepStatus.ngos === 'complete' || stepStatus.emails) && (
          <div className="step">
            <div className="step-header">
              <div className={`step-number ${getStepNumber('emails')}`}>3</div>
              <span className="step-title">Send Alert Emails</span>
              {stepStatus.emails && (
                <span className="step-status">
                  {stepStatus.emails === 'loading'
                    ? `${emailPreviews.length}/${emailCount || '?'} sent`
                    : `${emailCount} sent`}
                </span>
              )}
            </div>
            <div className="loading-bar">
              <div className={`loading-bar-fill ${getLoadingClass('emails')}`} />
            </div>
            {stepStatus.emails === 'loading' && progressText && (
              <div className="progress-text">{progressText}</div>
            )}
            {emailPreviews.length > 0 && (
              <div className="email-list">
                {emailPreviews.map((email, idx) => (
                  <div
                    key={idx}
                    className="email-card animate-in"
                    style={{ animationDelay: `${idx * 0.05}s` }}
                    onClick={() => setSelectedEmail(email)}
                  >
                    <div className="email-icon">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="M22 6l-10 7L2 6" />
                      </svg>
                    </div>
                    <div className="email-info">
                      <div className="email-to">{email.ngo_name}</div>
                      <div className="email-subject">{email.subject}</div>
                    </div>
                    <div className="email-status">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {complete && (
          <div className="connector" />
        )}

        {complete && (
          <div className="step">
            <div className="step-header">
              <div className="step-number complete">✓</div>
              <span className="step-title">Pipeline Complete</span>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={endRef} />
      </div>

      {/* Email Preview Modal */}
      {selectedEmail && (
        <div className="modal-overlay" onClick={() => setSelectedEmail(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Email Preview</div>
              <button className="modal-close" onClick={() => setSelectedEmail(null)}>×</button>
            </div>
            <div className="modal-meta">
              <div><strong>To:</strong> {selectedEmail.to}</div>
              <div><strong>Subject:</strong> {selectedEmail.subject}</div>
            </div>
            <div className="modal-body">
              <div dangerouslySetInnerHTML={{ __html: selectedEmail.html }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
