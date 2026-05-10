import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import { FileText, Search, Upload, Activity, Cpu, Database } from 'lucide-react'
import { checkHealth } from './utils/api'
import UploadPage from './pages/UploadPage'
import DocumentsPage from './pages/DocumentsPage'
import QueryPage from './pages/QueryPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  const [health, setHealth] = useState(null)
  const location = useLocation()

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'offline' }))
  }, [])

  const isOnline = health?.status === 'ok'

  return (
    <div className="app-layout">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-body)',
          },
        }}
      />

      {/* ── Header ── */}
      <header className="app-header">
        <div className="logo">
          <div className="logo-icon">
            <Cpu size={16} color="white" />
          </div>
          RAG Hybrid Search
        </div>
        <span className="header-badge">v1.0 · pgvector + BM25 + Claude</span>

        <div className="header-status" style={{ marginLeft: 'auto' }}>
          <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
          {isOnline
            ? `API online · ${health?.embedding_model || ''}`
            : health === null ? 'Connecting...' : 'API offline'}
        </div>
      </header>

      {/* ── Sidebar ── */}
      <aside className="app-sidebar">
        <div className="nav-section-label">Main</div>

        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Upload size={16} />
          Upload Documents
        </NavLink>

        <NavLink to="/documents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Database size={16} />
          Documents
        </NavLink>

        <div className="nav-section-label">RAG Pipeline</div>

        <NavLink to="/query" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Cpu size={16} />
          Ask AI (Full RAG)
        </NavLink>

        <NavLink to="/search" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Search size={16} />
          Hybrid Search
        </NavLink>

        {/* Pipeline explanation */}
        <div style={{ marginTop: 'auto', padding: '16px 8px 8px' }}>
          <div style={{
            background: 'var(--accent-dim)',
            border: '1px solid var(--accent-border)',
            borderRadius: 'var(--radius-md)',
            padding: '12px',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', marginBottom: 6, fontSize: '0.68rem' }}>
              PIPELINE
            </div>
            📄 Upload → Chunk → Embed<br />
            🔍 Dense (pgvector) + BM25<br />
            ⚡ RRF Fusion → Claude LLM
          </div>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="app-main">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/query" element={<QueryPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  )
}
