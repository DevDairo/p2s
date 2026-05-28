import { useState, useRef, useEffect, useCallback } from 'react'
import { searchSongs, startDownload } from '../services/api.js'
import DownloadProgress from '../components/DownloadProgress.jsx'
import './SearchPage.css'

const FORMATS = [
  { id: 'm4a',   label: 'M4A',       desc: 'Alta calidad AAC' },
  { id: 'mp3',   label: 'MP3',       desc: 'Máxima compatibilidad' },
  { id: 'atmos', label: '🎧 Atmos',  desc: 'Dolby Atmos si disponible' },
  { id: 'best',  label: '⭐ Mejor',  desc: 'Sin conversión' },
]

export default function SearchPage({ onGoToLibrary }) {
  const [query,   setQuery]   = useState('')
  const [urlVal,  setUrlVal]  = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [format,  setFormat]  = useState('m4a')
  const [tasks,   setTasks]   = useState([])
  const [toasts,  setToasts]  = useState([])
  const inputRef  = useRef(null)
  const debounceRef = useRef(null)

  const addToast = (title) => {
    const id = Date.now()
    setToasts(p => [...p, { id, title }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4000)
  }

  // ── Búsqueda con debounce automático ──────────────────────────────────
  const doSearch = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); return }
    setLoading(true)
    const data = await searchSongs(q.trim())
    setResults(data)
    setLoading(false)
  }, [])

  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (!query.trim()) { setResults([]); setLoading(false); return }
    setLoading(true)
    debounceRef.current = setTimeout(() => doSearch(query), 500)
    return () => clearTimeout(debounceRef.current)
  }, [query, doSearch])

  // ── Descarga ──────────────────────────────────────────────────────────
  const enqueue = async ({ url, title, thumbnail }) => {
    const res = await startDownload(url, format)
    if (res.status === 'already_exists') {
      alert(`"${title}" ya está en tu biblioteca.`)
      return
    }
    if (res.task_id) setTasks(p => [...p, { taskId: res.task_id, title, thumbnail }])
  }

  const handleUrlSubmit = async (e) => {
    e.preventDefault()
    const url = urlVal.trim(); if (!url) return
    await enqueue({ url, title: url, thumbnail: null })
    setUrlVal('')
  }

  const removeTask = id => setTasks(p => p.filter(t => t.taskId !== id))

  const fmtDur = (s) => {
    if (!s) return null
    return `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`
  }

  return (
    <div className="sp">
      {/* ── Toasts ── */}
      <div style={{
        position: 'fixed', top: 16, left: 16, zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'none',
      }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: 'var(--bg-3)',
            border: '1px solid rgba(16,185,129,0.4)',
            borderRadius: 'var(--r-md)',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            boxShadow: 'var(--shadow-md)',
            animation: 'slideIn 0.3s var(--ease)',
            maxWidth: 320,
          }}>
            <span style={{ color: '#34d399', display: 'flex', flexShrink: 0 }}><CheckIco /></span>
            <span style={{
              fontSize: 13, color: 'var(--t1)', fontWeight: 500,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>{t.title}</span>
          </div>
        ))}
      </div>

      <header className="sp-hero">
        <h1 className="sp-title">Descarga música</h1>
        <p className="sp-sub">Busca por nombre o pega un enlace de YouTube</p>
      </header>

      {/* ── Format selector ── */}
      <div className="sp-formats">
        {FORMATS.map(f => (
          <button
            key={f.id}
            className={`fchip ${format === f.id ? 'fchip--on' : ''}`}
            onClick={() => setFormat(f.id)}
            title={f.desc}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Search — dispara automáticamente ── */}
      <div className="sp-searchbar">
        <div className="sbar-wrap">
          <span className="sbar-ico">
            {loading ? <span className="spin" style={{width:16,height:16}} /> : <SearchIco />}
          </span>
          <input
            ref={inputRef}
            className="sbar-input"
            type="text"
            placeholder="Artista, canción o álbum…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          {query && (
            <button type="button" className="sbar-clear" onClick={() => { setQuery(''); setResults([]); inputRef.current?.focus() }}>
              <XIco />
            </button>
          )}
        </div>
      </div>

      {/* ── URL input ── */}
      <form className="sp-urlbar" onSubmit={handleUrlSubmit}>
        <div className="sbar-wrap sbar-wrap--url">
          <span className="sbar-ico"><LinkIco /></span>
          <input
            className="sbar-input"
            type="url"
            placeholder="https://www.youtube.com/watch?v=…"
            value={urlVal}
            onChange={e => setUrlVal(e.target.value)}
          />
        </div>
        <button className="btn-ghost" type="submit" disabled={!urlVal.trim()}>
          <DownloadIco /> Descargar URL
        </button>
      </form>

      {/* ── Active downloads — siempre visibles, no se desmontan ── */}
      {tasks.length > 0 && (
        <section className="sp-section">
          <p className="section-label">Descargando ahora</p>
          <div className="sp-tasks">
            {tasks.map(t => (
              <DownloadProgress
                key={t.taskId}
                taskId={t.taskId}
                title={t.title}
                thumbnail={t.thumbnail}
                onDone={() => {
                  addToast(t.title)
                  setTimeout(() => removeTask(t.taskId), 3500)
                }}
                onError={() => setTimeout(() => removeTask(t.taskId), 6000)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Results ── */}
      {results.length > 0 && (
        <section className="sp-section">
          <p className="section-label">{results.length} resultados</p>
          <div className="sp-grid">
            {results.map(song => (
              <article key={song.id} className="rcard">
                <div className="rcard-img">
                  <img src={song.thumbnail} alt={song.title} loading="lazy" />
                  <button
                    className="rcard-dl"
                    onClick={() => enqueue(song)}
                    aria-label={`Descargar ${song.title}`}
                  >
                    <DownloadIco />
                  </button>
                  {song.duration && (
                    <span className="rcard-dur">{fmtDur(song.duration)}</span>
                  )}
                </div>
                <div className="rcard-info">
                  <p className="rcard-title">{song.title}</p>
                  <p className="rcard-artist">{song.artist}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {!loading && !query && results.length === 0 && tasks.length === 0 && (
        <div className="sp-welcome">
          <div className="sp-welcome-card">
            <span className="sp-welcome-ico">🎵</span>
            <p className="sp-welcome-title">Empieza buscando</p>
            <p className="sp-welcome-sub">Escribe el nombre de una canción o artista — los resultados aparecen al instante.</p>
          </div>
        </div>
      )}
    </div>
  )
}

const CheckIco    = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
const SearchIco   = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
const XIco        = () => <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
const LinkIco     = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
const DownloadIco = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
