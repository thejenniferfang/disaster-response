import { useState } from 'react'

function timeAgo(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)

  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString()
}

export default function App() {
  const [running, setRunning] = useState(false)
  const [step, setStep] = useState(null) // 'disasters' | 'ngos' | 'emails'
  const [stepStatus, setStepStatus] = useState({})
  const [disasters, setDisasters] = useState([])
  const [ngoLinks, setNgoLinks] = useState([])
  const [emailCount, setEmailCount] = useState(0)
  const [emailError, setEmailError] = useState(null)
  const [progressText, setProgressText] = useState('')
  const [complete, setComplete] = useState(false)

  const runPipeline = async () => {
    setRunning(true)
    setStep(null)
    setStepStatus({})
    setDisasters([])
    setNgoLinks([])
    setEmailCount(0)
    setEmailError(null)
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
          // Already handled incrementally
          break
        case 'emails_sent':
          setEmailCount(data.count)
          setEmailError(data.error || null)
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
        <h1>Disaster Response Pipeline</h1>
        <p>Real-time disaster detection, NGO matching, and notification system</p>
      </div>

      <button
        className="start-btn"
        onClick={runPipeline}
        disabled={running}
      >
        {running ? 'Running...' : 'Run Pipeline'}
      </button>

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
                  {stepStatus.emails === 'loading' ? 'Sending...' : `${emailCount} sent`}
                </span>
              )}
            </div>
            <div className="loading-bar">
              <div className={`loading-bar-fill ${getLoadingClass('emails')}`} />
            </div>
            {stepStatus.emails === 'complete' && !emailError && (
              <div className="email-success">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" fill="currentColor" />
                </svg>
                {emailCount} alert emails sent successfully
              </div>
            )}
            {stepStatus.emails === 'complete' && emailError && (
              <div className="email-error">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-5a1 1 0 112 0 1 1 0 01-2 0zm1-8a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" fill="currentColor" />
                </svg>
                <div>
                  <div>{emailCount} emails prepared (sending failed)</div>
                  <div className="error-detail">Resend API: Use delivered@resend.dev for testing</div>
                </div>
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
      </div>
    </div>
  )
}
