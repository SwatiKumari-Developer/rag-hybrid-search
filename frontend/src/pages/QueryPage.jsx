import { useState, useRef, useEffect } from 'react'
import { Send, Cpu, ChevronDown, ChevronUp, ExternalLink, Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { askQuestion } from '../utils/api'

export default function QueryPage() {
  const [query, setQuery] = useState('')
  const [history, setHistory] = useState([])  // { query, answer, sources, tokens, time }
  const [loading, setLoading] = useState(false)
  const [showDebug, setShowDebug] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const q = query.trim()
    setQuery('')
    setLoading(true)

    const start = Date.now()
    try {
      const result = await askQuestion(q, null, null, showDebug)
      const elapsed = ((Date.now() - start) / 1000).toFixed(1)
      setHistory(prev => [...prev, { query: q, result, elapsed }])
    } catch (e) {
      toast.error(e.message)
      setHistory(prev => [...prev, { query: q, error: e.message }])
    } finally {
      setLoading(false)
    }
  }

  const examples = [
    'What is the main topic of the uploaded documents?',
    'Summarize the key findings.',
    'What methodology was used?',
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px 32px 16px' }}>
        {history.length === 0 && !loading ? (
          <div style={{ maxWidth: 700, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 40 }}>
              <div style={{
                width: 64,
                height: 64,
                background: 'var(--accent-dim)',
                border: '1px solid var(--accent-border)',
                borderRadius: 16,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <Cpu size={28} color="var(--accent)" />
              </div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, marginBottom: 8 }}>
                Ask your documents
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                Full RAG pipeline: hybrid search → Claude LLM → cited answer
              </p>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              {examples.map(ex => (
                <button
                  key={ex}
                  className="card"
                  onClick={() => setQuery(ex)}
                  style={{
                    textAlign: 'left',
                    cursor: 'pointer',
                    padding: '14px 18px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    border: '1px solid var(--border)',
                    color: 'var(--text-secondary)',
                    fontSize: '0.875rem',
                    transition: 'all 0.15s',
                  }}
                >
                  <Zap size={14} color="var(--accent)" style={{ flexShrink: 0 }} />
                  {ex}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 28 }}>
            {history.map((item, i) => (
              <div key={i}>
                {/* User query */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                  <div style={{
                    background: 'var(--accent)',
                    color: 'white',
                    padding: '10px 16px',
                    borderRadius: '12px 12px 2px 12px',
                    fontSize: '0.9rem',
                    maxWidth: '80%',
                  }}>
                    {item.query}
                  </div>
                </div>

                {/* Answer */}
                {item.error ? (
                  <div style={{
                    background: 'var(--red-dim)',
                    border: '1px solid rgba(255,107,107,0.3)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '16px 20px',
                    color: 'var(--red)',
                    fontSize: '0.875rem',
                  }}>
                    Error: {item.error}
                  </div>
                ) : item.result ? (
                  <div className="card" style={{ padding: '20px 24px' }}>
                    {/* Answer text */}
                    <div style={{ fontSize: '0.9rem', lineHeight: 1.7, marginBottom: 16 }}>
                      <ReactMarkdown>{item.result.answer}</ReactMarkdown>
                    </div>

                    <div className="divider" />

                    {/* Sources */}
                    <SourcesList sources={item.result.sources} />

                    {/* Meta */}
                    <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      <span>Model: {item.result.model}</span>
                      <span>Tokens: {item.result.input_tokens} in / {item.result.output_tokens} out</span>
                      <span>{item.elapsed}s</span>
                    </div>
                  </div>
                ) : null}
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                  <div style={{
                    background: 'var(--accent)',
                    color: 'white',
                    padding: '10px 16px',
                    borderRadius: '12px 12px 2px 12px',
                    fontSize: '0.9rem',
                  }}>
                    {query || '...'}
                  </div>
                </div>
                <div className="card" style={{ padding: '20px 24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <div className="spinner" />
                    Running hybrid search → generating answer with Claude...
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div style={{
        padding: '16px 32px 24px',
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <textarea
                className="input"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) } }}
                placeholder="Ask a question about your documents... (Enter to send, Shift+Enter for newline)"
                rows={2}
                style={{ resize: 'none', minHeight: 'unset' }}
                disabled={loading}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <button className="btn btn-primary" type="submit" disabled={loading || !query.trim()}>
                {loading ? <div className="spinner" style={{ width: 16, height: 16, borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : <Send size={16} />}
              </button>
              <button
                type="button"
                className={`btn btn-sm ${showDebug ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setShowDebug(v => !v)}
                title="Toggle debug info"
                style={{ fontSize: '0.65rem', padding: '4px 8px' }}
              >
                DEBUG
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

function SourcesList({ sources }) {
  const [expanded, setExpanded] = useState(false)
  if (!sources?.length) return null

  const displayed = expanded ? sources : sources.slice(0, 3)

  return (
    <div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Sources ({sources.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {displayed.map((src, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '6px 10px',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.75rem',
          }}>
            <span className={`badge badge-${src.retrieval_method}`}>{src.retrieval_method}</span>
            <span style={{ color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {src.title || src.filename} · chunk {src.chunk_index}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.65rem', flexShrink: 0 }}>
              {src.rrf_score?.toFixed(4)}
            </span>
          </div>
        ))}
      </div>
      {sources.length > 3 && (
        <button className="btn btn-ghost btn-sm" onClick={() => setExpanded(v => !v)} style={{ marginTop: 6 }}>
          {expanded ? <><ChevronUp size={12} /> Show less</> : <><ChevronDown size={12} /> +{sources.length - 3} more</>}
        </button>
      )}
    </div>
  )
}
