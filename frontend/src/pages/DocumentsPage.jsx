import { useState, useEffect } from 'react'
import { Database, Trash2, RefreshCw, FileText, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { listDocuments, deleteDocument } from '../utils/api'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function timeAgo(isoDate) {
  if (!isoDate) return ''
  const d = new Date(isoDate)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await listDocuments()
      setDocs(data.documents)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (doc) => {
    if (!confirm(`Delete "${doc.filename}"? This removes all its chunks from the vector store.`)) return
    setDeleting(doc.id)
    try {
      await deleteDocument(doc.id)
      setDocs(prev => prev.filter(d => d.id !== doc.id))
      toast.success(`"${doc.filename}" deleted`)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setDeleting(null)
    }
  }

  const totalChunks = docs.filter(d => d.status === 'ready').reduce((s, d) => s + d.chunk_count, 0)
  const readyDocs = docs.filter(d => d.status === 'ready').length

  return (
    <div className="page">
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Documents</h1>
          <p className="page-subtitle">Manage your vector store · {readyDocs} ready · {totalChunks.toLocaleString()} chunks indexed</p>
        </div>
        <button className="btn btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-pulse' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { label: 'Total Documents', value: docs.length, color: 'var(--text-primary)' },
          { label: 'Ready for Search', value: readyDocs, color: 'var(--green)' },
          { label: 'Total Chunks', value: totalChunks.toLocaleString(), color: 'var(--accent)' },
        ].map(({ label, value, color }) => (
          <div key={label} className="card" style={{ padding: '20px 24px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: '1.8rem', fontFamily: 'var(--font-display)', fontWeight: 800, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Document list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton" style={{ height: 80, borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
      ) : docs.length === 0 ? (
        <div className="empty-state">
          <Database size={48} />
          <h3>No documents yet</h3>
          <p>Upload PDF, TXT, or DOCX files to start building your knowledge base.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {docs.map(doc => (
            <div key={doc.id} className="card" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
              <FileText size={20} color="var(--text-muted)" style={{ flexShrink: 0 }} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <span style={{ fontWeight: 500, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.title || doc.filename}
                  </span>
                  <span className={`badge badge-${doc.status}`}>{doc.status}</span>
                </div>

                <div style={{ display: 'flex', gap: 16, fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <span>{doc.chunk_count} chunks</span>
                  <span>{formatBytes(doc.file_size)}</span>
                  <span>.{doc.file_type}</span>
                  <span>{timeAgo(doc.created_at)}</span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }}>
                    {doc.id}
                  </span>
                </div>

                {doc.content_preview && (
                  <div style={{
                    marginTop: 6,
                    fontSize: '0.78rem',
                    color: 'var(--text-muted)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {doc.content_preview}
                  </div>
                )}
              </div>

              <button
                className="btn btn-ghost btn-sm"
                onClick={() => handleDelete(doc)}
                disabled={deleting === doc.id}
                style={{ flexShrink: 0 }}
              >
                {deleting === doc.id
                  ? <div className="spinner" style={{ width: 14, height: 14 }} />
                  : <Trash2 size={14} color="var(--red)" />
                }
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
