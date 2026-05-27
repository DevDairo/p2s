import { useEffect, useState } from 'react'
import './DownloadProgress.css'

const STATUS_LABEL = {
  queued:      'En cola…',
  downloading: 'Descargando',
  processing:  'Procesando',
  done:        '¡Listo!',
  error:       'Error',
}

export default function DownloadProgress({ taskId, title, thumbnail, onDone, onError }) {
  const [state, setState] = useState({ status: 'queued', progress: 0, message: 'En cola…' })

  useEffect(() => {
    const src = new EventSource(`/api/v1/stream/${taskId}`)

    src.onmessage = ({ data }) => {
      try {
        const d = JSON.parse(data)
        setState({ status: d.status, progress: d.progress ?? 0, message: d.message })
        if (d.status === 'done')  { src.close(); onDone?.() }
        if (d.status === 'error') { src.close(); onError?.() }
      } catch { /* ignore parse errors */ }
    }

    src.onerror = () => {
      // Poll fallback si SSE falla (red muy restrictiva)
      src.close()
      const iv = setInterval(async () => {
        try {
          const r = await fetch(`/api/v1/status/${taskId}`)
          const d = await r.json()
          setState({ status: d.status, progress: d.progress ?? 0, message: d.message })
          if (d.status === 'done' || d.status === 'error') {
            clearInterval(iv)
            d.status === 'done' ? onDone?.() : onError?.()
          }
        } catch { clearInterval(iv) }
      }, 2000)
    }

    return () => src.close()
  }, [taskId])

  const { status, progress, message } = state
  const pct  = Math.round(Math.min(progress, 100))
  const done  = status === 'done'
  const error = status === 'error'

  return (
    <div className={`dlcard ${done ? 'dlcard--done' : ''} ${error ? 'dlcard--error' : ''}`}>
      {thumbnail && (
        <img className="dlcard-thumb" src={thumbnail} alt="" />
      )}
      <div className="dlcard-body">
        <div className="dlcard-top">
          <p className="dlcard-title">{title}</p>
          <span className={`dlcard-badge dlcard-badge--${status}`}>
            {done ? <CheckIcon /> : error ? <XIcon /> : <span className="spin" />}
            {STATUS_LABEL[status] || status}
          </span>
        </div>
        <p className="dlcard-msg">{message}</p>
        {!done && !error && (
          <div className="dlcard-bar-wrap">
            <div className="dlcard-bar" style={{ width: `${pct}%` }} />
          </div>
        )}
        {done && (
          <div className="dlcard-bar-wrap">
            <div className="dlcard-bar dlcard-bar--done" style={{ width: '100%' }} />
          </div>
        )}
      </div>
    </div>
  )
}

const CheckIcon = () => <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
const XIcon     = () => <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
