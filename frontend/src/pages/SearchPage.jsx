import { useState } from 'react'
import { Search, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'
import { searchDocuments } from '../utils/api'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState({})
  const [topK, setTopK] = useState(5)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await searchDocuments(query, null, topK)
      setResults(data)
      setExpanded({})
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Hybrid Search</h1>
        <p className="page-subtitle">
          Inspect raw retrieval results before LLM generation. Shows dense + sparse scores and RRF fusion ranking.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: 32 }}>
        <input
          className="input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Enter a search query..."
          disabled={loading}
        />
        <select
          className="input"
          value={topK}
          onChange={e => setTopK(Number(e.target.value))}
          style={{ width: 80, flexShrink: 0 }}
        >
          {[3, 5, 10, 15, 20].map(n => <option key={n} value={n}>Top {n}</option>)}
        </select>
        <button className="btn btn-primary" type="submit" disabled={loading || !query.trim()} style={{ flexShrink: 0 }}>
          {loading ? <div className="spinner" style={{ width: 16, height: 16, borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : <Search size={16} />}
          Search
        </button>
      </form>

      {/* Debug info */}
      {results?.debug_info && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 10,
          marginBottom: 24,
          padding: '16px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
        }}>
          {[
            { label: 'Dense hits', value: results.debug_info.dense_count, color: 'var(--blue)' },
            { label: 'Sparse hits', value: results.debug_info.sparse_count, color: 'var(--yellow)' },
            { label: 'After RRF', value: results.debug_info.fused_count, color: 'var(--accent)' },
            { label: 'Returned', value: results.debug_info.final_count, color: 'var(--green)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color }}>{value}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <BarChart3 size={16} color="var(--text-muted)" />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              {results.total} results for "{results.query}"
            </span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 12, fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              <span>Dense weight: {results.debug_info?.dense_weight ?? 0.6}</span>
              <span>Sparse weight: {results.debug_info?.sparse_weight ?? 0.4}</span>
            </div>
          </div>

          {results.results.map((chunk, i) => (
            <ResultCard
              key={chunk.chunk_id}
              chunk={chunk}
              rank={i + 1}
              isExpanded={expanded[i]}
              onToggle={() => setExpanded(prev => ({ ...prev, [i]: !prev[i] }))}
            />
          ))}
        </div>
      )}

      {results?.total === 0 && (
        <div className="empty-state">
          <Search size={48} />
          <h3>No results found</h3>
          <p>Try a different query or upload more documents.</p>
        </div>
      )}
    </div>
  )
}

function ScoreBar({ value, max = 0.02, color }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)', width: 50, textAlign: 'right' }}>
        {value?.toFixed(5)}
      </span>
    </div>
  )
}

function ResultCard({ chunk, rank, isExpanded, onToggle }) {
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div
        style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
        onClick={onToggle}
      >
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: rank <= 3 ? 'var(--accent-dim)' : 'var(--bg-secondary)',
          border: `1px solid ${rank <= 3 ? 'var(--accent-border)' : 'var(--border)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-mono)', fontSize: '0.7rem',
          color: rank <= 3 ? 'var(--accent)' : 'var(--text-muted)',
          flexShrink: 0,
        }}>
          #{rank}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontWeight: 500, fontSize: '0.875rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {chunk.title || chunk.filename}
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
              chunk {chunk.chunk_index}
            </span>
            <span className={`badge badge-${chunk.retrieval_method}`}>{chunk.retrieval_method}</span>
          </div>

          {/* Score bars */}
          <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr', gap: '4px 8px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>RRF</span>
            <ScoreBar value={chunk.rrf_score} max={0.025} color="var(--accent)" />
            {chunk.dense_score != null && (
              <>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Dense</span>
                <ScoreBar value={chunk.dense_score} max={1} color="var(--blue)" />
              </>
            )}
          </div>
        </div>

        {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
      </div>

      {/* Expanded text */}
      {isExpanded && (
        <div style={{
          padding: '12px 18px 16px',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-secondary)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.7,
          fontFamily: 'var(--font-mono)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {chunk.text}
        </div>
      )}
    </div>
  )
}
