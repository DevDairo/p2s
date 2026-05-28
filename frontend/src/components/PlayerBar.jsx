import { usePlayer } from '../context/PlayerContext.jsx'
import './PlayerBar.css'

export default function PlayerBar() {
  const { state, controls, song } = usePlayer()
  const { playing, progress, duration, volume } = state

  if (!song) return null

  const fmtTime = (s) => {
    if (!s || isNaN(s)) return '0:00'
    return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
  }

  const elapsed = (progress / 100) * duration

  return (
    <div className="pbar">
      {/* ── Song info ── */}
      <div className="pbar-info">
        <div className="pbar-cover">
          <img
            src={song.cover_url}
            alt={song.title}
            onError={e => { e.target.style.display = 'none' }}
          />
          <div className="pbar-cover-fallback"><MusicIco /></div>
        </div>
        <div className="pbar-meta">
          <p className="pbar-title">{song.title}</p>
          <p className="pbar-artist">{song.artist}</p>
        </div>
      </div>

      {/* ── Controls ── */}
      <div className="pbar-center">
        <div className="pbar-btns">
          <button className="pbar-btn" onClick={controls.prev} aria-label="Anterior">
            <PrevIco />
          </button>
          <button className="pbar-btn pbar-btn--play" onClick={controls.toggle} aria-label={playing ? 'Pausar' : 'Reproducir'}>
            {playing ? <PauseIco /> : <PlayIco />}
          </button>
          <button className="pbar-btn" onClick={controls.next} aria-label="Siguiente">
            <NextIco />
          </button>
        </div>

        <div className="pbar-progress">
          <span className="pbar-time">{fmtTime(elapsed)}</span>
          <input
            type="range"
            className="pbar-range"
            min="0"
            max="100"
            step="0.1"
            value={progress}
            onChange={e => controls.seek(parseFloat(e.target.value))}
          />
          <span className="pbar-time">{fmtTime(duration)}</span>
        </div>
      </div>

      {/* ── Volume ── */}
      <div className="pbar-right">
        <span className="pbar-fmt">{song.format?.toUpperCase()}</span>
        <VolumeIco />
        <input
          type="range"
          className="pbar-range pbar-vol"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={e => controls.setVolume(parseFloat(e.target.value))}
        />
      </div>
    </div>
  )
}

const MusicIco = () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
const PlayIco  = () => <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
const PauseIco = () => <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
const PrevIco  = () => <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
const NextIco  = () => <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
const VolumeIco = () => <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
