import { useState, useEffect } from 'react'
import SearchPage  from './pages/SearchPage.jsx'
import LibraryPage from './pages/LibraryPage.jsx'
import PlayerBar   from './components/PlayerBar.jsx'
import { PlayerProvider } from './context/PlayerContext.jsx'
import './App.css'

export default function App() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem('mf-theme') || 'dark'
  )
  const [tab, setTab] = useState('search')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('mf-theme', theme)
  }, [theme])

  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  const isDark = theme === 'dark'

  return (
    <PlayerProvider>
      <div className="shell">
        <div className="mesh" aria-hidden />

        <aside className="sidebar">
          <div className="brand">
            <div className="brand-icon"><WaveIcon /></div>
            <span className="brand-name">FreeSong</span>
          </div>
          <nav className="sidenav">
            <NavBtn icon={<SearchIco />} label="Buscar"     active={tab==='search'}  onClick={() => setTab('search')}  />
            <NavBtn icon={<LibIco />}    label="Biblioteca" active={tab==='library'} onClick={() => setTab('library')} />
          </nav>
          <div className="sidebar-footer">
            <button className="theme-btn" onClick={toggle}>
              {isDark ? <SunIco /> : <MoonIco />}
              <span>{isDark ? 'Modo claro' : 'Modo oscuro'}</span>
            </button>
          </div>
        </aside>

        <main className="content">
          {tab === 'search'  && <SearchPage  onGoToLibrary={() => setTab('library')} />}
          {tab === 'library' && <LibraryPage />}
        </main>

        <nav className="bottomnav">
          <NavBtn icon={<SearchIco />} label="Buscar"     active={tab==='search'}  onClick={() => setTab('search')}  mobile />
          <NavBtn icon={<LibIco />}    label="Biblioteca" active={tab==='library'} onClick={() => setTab('library')} mobile />
          <button className="theme-btn-mobile" onClick={toggle}>
            {isDark ? <SunIco /> : <MoonIco />}
          </button>
        </nav>

        {/* PlayerBar vive FUERA de las páginas — no se desmonta al navegar */}
        <PlayerBar />
      </div>
    </PlayerProvider>
  )
}

function NavBtn({ icon, label, active, onClick, mobile }) {
  return (
    <button
      className={`navbtn ${active ? 'navbtn--active' : ''} ${mobile ? 'navbtn--mobile' : ''}`}
      onClick={onClick}
    >
      <span className="navbtn-icon">{icon}</span>
      <span className="navbtn-label">{label}</span>
      {active && !mobile && <span className="navbtn-pip" />}
    </button>
  )
}

const WaveIcon = () => <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round"><path d="M2 12s2-6 5-6 5 12 8 12 5-6 7-6"/></svg>
const SearchIco = () => <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
const LibIco    = () => <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
const SunIco    = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
const MoonIco   = () => <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
