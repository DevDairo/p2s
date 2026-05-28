import { createContext, useContext, useReducer, useRef, useEffect } from 'react'

const PlayerCtx = createContext(null)

const initial = {
  queue:    [],      // lista de canciones {id, title, artist, audio_url, cover_url, format, duration}
  index:    -1,      // índice activo en queue
  playing:  false,
  progress: 0,       // 0-100
  duration: 0,       // segundos
  volume:   1,
}

function reducer(state, action) {
  switch (action.type) {
    case 'PLAY_SONG': {
      const idx = state.queue.findIndex(s => s.id === action.song.id)
      if (idx !== -1) return { ...state, index: idx, playing: true }
      return { ...state, queue: [...state.queue, action.song], index: state.queue.length, playing: true }
    }
    case 'SET_QUEUE':
      return { ...state, queue: action.songs, index: action.index ?? 0, playing: true }
    case 'TOGGLE':
      return { ...state, playing: !state.playing }
    case 'PAUSE':
      return { ...state, playing: false }
    case 'NEXT': {
      const next = (state.index + 1) % state.queue.length
      return { ...state, index: next, playing: true, progress: 0 }
    }
    case 'PREV': {
      const prev = state.index > 0 ? state.index - 1 : state.queue.length - 1
      return { ...state, index: prev, playing: true, progress: 0 }
    }
    case 'SEEK':
      return { ...state, progress: action.progress }
    case 'SET_PROGRESS':
      return { ...state, progress: action.progress, duration: action.duration }
    case 'SET_VOLUME':
      return { ...state, volume: action.volume }
    default:
      return state
  }
}

export function PlayerProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initial)
  const audioRef = useRef(new Audio())

  const song = state.queue[state.index] ?? null

  // Cambiar fuente cuando cambia la canción
  useEffect(() => {
    const audio = audioRef.current
    if (!song) return
    if (audio.src !== song.audio_url) {
      audio.src = song.audio_url
      audio.load()
    }
    if (state.playing) audio.play().catch(() => {})
    else audio.pause()
  }, [song?.id])

  // Play/pause sin cambiar canción
  useEffect(() => {
    const audio = audioRef.current
    if (!song) return
    if (state.playing) audio.play().catch(() => {})
    else audio.pause()
  }, [state.playing])

  // Volumen
  useEffect(() => {
    audioRef.current.volume = state.volume
  }, [state.volume])

  // Seek externo
  useEffect(() => {
    const audio = audioRef.current
    if (!audio.duration) return
    const target = (state.progress / 100) * audio.duration
    if (Math.abs(audio.currentTime - target) > 1) {
      audio.currentTime = target
    }
  }, [state.progress])

  // Listeners del elemento audio
  useEffect(() => {
    const audio = audioRef.current

    const onTime = () => {
      if (!audio.duration) return
      dispatch({
        type: 'SET_PROGRESS',
        progress: (audio.currentTime / audio.duration) * 100,
        duration: audio.duration,
      })
    }

    const onEnded = () => dispatch({ type: 'NEXT' })
    const onErr   = () => dispatch({ type: 'PAUSE' })

    audio.addEventListener('timeupdate', onTime)
    audio.addEventListener('ended',      onEnded)
    audio.addEventListener('error',      onErr)
    return () => {
      audio.removeEventListener('timeupdate', onTime)
      audio.removeEventListener('ended',      onEnded)
      audio.removeEventListener('error',      onErr)
    }
  }, [])

  const controls = {
    play:      (song)    => dispatch({ type: 'PLAY_SONG', song }),
    setQueue:  (songs, i) => dispatch({ type: 'SET_QUEUE', songs, index: i }),
    toggle:    ()        => dispatch({ type: 'TOGGLE' }),
    next:      ()        => dispatch({ type: 'NEXT' }),
    prev:      ()        => dispatch({ type: 'PREV' }),
    seek:      (pct)     => dispatch({ type: 'SEEK', progress: pct }),
    setVolume: (v)       => dispatch({ type: 'SET_VOLUME', volume: v }),
  }

  return (
    <PlayerCtx.Provider value={{ state, controls, song }}>
      {children}
    </PlayerCtx.Provider>
  )
}

export function usePlayer() {
  const ctx = useContext(PlayerCtx)
  if (!ctx) throw new Error('usePlayer must be inside PlayerProvider')
  return ctx
}
