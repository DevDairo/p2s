import { useState, useEffect } from 'react'
import { fetchLibrary, deleteSong } from '../services/api.js'
import { usePlayer } from '../context/PlayerContext.jsx'
import './LibraryPage.css'

export default function LibraryPage() {
  const [songs,    setSongs]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [deleting, setDeleting] = useState(null)
  const { state, controls, song: activeSong } = usePlayer()

  const load = async () => {
    setLoading(true)
    const data = await fetchLibrary()
    setSongs(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handlePlay = (song, idx) => {
    if (activeSong?.id === song.id) {
      controls.toggle()
    } else {
      controls.setQueue(songs, idx)
    }
  }

  const handleDelete = async (song) => {
    if (!confirm(`¿Eliminar "${song.title}"?`)) return
    setDeleting(song.id)
    await deleteSong(song.id)
    setSongs(p => p.filter(s => s.id !== song.id))
    setDeleting(null)
  }

  const formatDur = (s) => {
    if (!s) return null
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = Math.floor(s % 60)
    return h > 0
      ? `${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`
      : `${m}:${String(sec).padStart(2,'0')}`
  }

  const formatSize = (bytes) => {
    if (!bytes) return null
    return bytes > 1e6
      ? `${(bytes/1e6).toFixed(1)} MB`
      : `${(bytes/1e3).toFixed(0)} KB`
  }

  const fmtBadge = { m4a:'M4A', mp3:'MP3', eac3:'Atmos', ac3:'AC3', best:'BEST', opus:'Opus' }

  const isPlaying = (song) => activeSong?.id === song.id && state.playing
  const isActive  = (song) => activeSong?.id === song.id

  return (
    <div className="lib">
      <header className="lib-header">
        <div>
          <h1 className="lib-title">Tu biblioteca</h1>
          <p className="lib-sub">
            {loading ? 'Cargando…' : `${songs.length} canción${songs.length !== 1 ? 'es' : ''}`}
          </p>
        </div>
        <button className="btn-ghost lib-refresh" onClick={load} disabled={loading}>
          <RefreshIco className={loading ? 'spinning' : ''} /> Actualizar
        </button>
      </header>

      {loading && (
        <div className="lib-loading">
          <span className="spin" />
          <p>Cargando biblioteca…</p>
        </div>
      )}

      {!loading && songs.length === 0 && (
        <div className="lib-empty">
          <span className="lib-empty-ico">🎶</span>
          <p className="lib-empty-title">Biblioteca vacía</p>
          <p className="lib-empty-sub">Las canciones que descargues aparecerán aquí.</p>
        </div>
      )}

      {!loading && songs.length > 0 && (
        <div className="lib-list">
          {songs.map((song, idx) => (
            <div
              key={song.id}
              className={`scard ${isActive(song) ? 'scard--playing' : ''}`}
            >
              <span className="scard-num">{String(idx + 1).padStart(2, '0')}</span>

              <div className="scard-thumb" onClick={() => handlePlay(song, idx)} style={{cursor:'pointer'}}>
                <img
                  src={song.cover_url}
                  alt={song.title}
                  loading="lazy"
                  onError={e => { e.target.style.display = 'none' }}
                />
                <div className="scard-thumb-fallback"><MusicIco /></div>
                {isActive(song) && (
                  <div className="scard-thumb-overlay">
                    {isPlaying(song) ? <PauseIco /> : <PlayIco />}
                  </div>
                )}
              </div>

              <div className="scard-info">
                <p className="scard-title">{song.title}</p>
                <p className="scard-meta">
                  <span>{song.artist}</span>
                  {song.year      && <><span className="dot">·</span><span>{song.year}</span></>}
                  {song.duration  && <><span className="dot">·</span><span>{formatDur(song.duration)}</span></>}
                  {song.file_size && <><span className="dot">·</span><span>{formatSize(song.file_size)}</span></>}
                </p>
              </div>

              <div className="scard-actions">
                <span className={`fmt-badge fmt-badge--${song.format}`}>
                  {fmtBadge[song.format] || song.format?.toUpperCase()}
                </span>

                <button
                  className={`scard-btn scard-btn--play ${isActive(song) ? 'active' : ''}`}
                  onClick={() => handlePlay(song, idx)}
                  aria-label={isPlaying(song) ? 'Pausar' : 'Reproducir'}
                >
                  {isPlaying(song) ? <PauseIco /> : <PlayIco />}
                </button>

                <a
                  className="scard-btn"
                  href={song.audio_url}
                  download
                  aria-label="Descargar archivo"
                >
                  <DownIco />
                </a>

                <button
                  className="scard-btn scard-btn--del"
                  onClick={() => handleDelete(song)}
                  disabled={deleting === song.id}
                  aria-label="Eliminar"
                >
                  {deleting === song.id
                    ? <span className="spin" style={{width:14,height:14}} />
                    : <TrashIco />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const MusicIco   = () => <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
const RefreshIco = ({className}) => <svg className={className} width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
const PlayIco    = () => <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
const PauseIco   = () => <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
const DownIco    = () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
const TrashIco   = () => <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
