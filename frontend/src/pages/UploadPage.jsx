import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadDocument, getDocument } from '../utils/api'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'text/plain': ['.txt', '.md'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

function pollUntilReady(docId, onUpdate) {
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const doc = await getDocument(docId)
        onUpdate(doc)
        if (doc.status === 'ready') { clearInterval(interval); resolve(doc) }
        if (doc.status === 'error') { clearInterval(interval); reject(new Error(doc.error_message || 'Processing failed')) }
      } catch (e) { clearInterval(interval); reject(e) }
    }, 2000)
    setTimeout(() => { clearInterval(interval); reject(new Error('Timed out waiting for document')) }, 120000)
  })
}

export default function UploadPage() {
  const [uploads, setUploads] = useState([]) // { file, status, progress, doc, error }

  const updateUpload = (index, patch) =>
    setUploads(prev => prev.map((u, i) => i === index ? { ...u, ...patch } : u))

  const processFile = async (file, index) => {
    try {
      updateUpload(index, { status: 'uploading', progress: 0 })
      const doc = await uploadDocument(file, (pct) => updateUpload(index, { progress: pct }))
      updateUpload(index, { status: 'processing', doc, progress: 100 })
      const ready = await pollUntilReady(doc.id, (updated) => updateUpload(index, { doc: updated }))
      updateUpload(index, { status: 'done', doc: ready })
      toast.success(`"${file.name}" ingested — ${ready.chunk_count} chunks created`)
    } catch (err) {
      updateUpload(index, { status: 'error', error: err.message })
      toast.error(`Failed: ${err.message}`)
    }
  }

  const onDrop = useCallback((accepted) => {
    const newUploads = accepted.map(file => ({ file, status: 'pending', progress: 0, doc: null, error: null }))
    setUploads(prev => {
      const startIdx = prev.length
      newUploads.forEach((_, i) => {
        setTimeout(() => processFile(accepted[i], startIdx + i), i * 300)
      })
      return [...prev, ...newUploads]
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 10 * 1024 * 1024,
  })

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Upload Documents</h1>
        <p className="page-subtitle">
          PDF, TXT, DOCX, MD files · max 10MB · processed with Sentence-Transformers + pgvector
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        style={{
          border: `2px dashed ${isDragActive ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: 'var(--radius-xl)',
          padding: '60px 40px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
          background: isDragActive ? 'var(--accent-dim)' : 'var(--bg-card)',
          marginBottom: 32,
        }}
      >
        <input {...getInputProps()} />
        <Upload size={40} color={isDragActive ? 'var(--accent)' : 'var(--text-muted)'} style={{ margin: '0 auto 16px' }} />
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: 8 }}>
          {isDragActive ? 'Drop files here' : 'Drag & drop files, or click to browse'}
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          PDF, TXT, DOCX, Markdown · max 10 MB per file
        </p>
      </div>

      {/* Pipeline explanation */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 32 }}>
        {[
          { step: '01', label: 'Parse', desc: 'Extract raw text from PDF/DOCX/TXT' },
          { step: '02', label: 'Chunk', desc: '512-word sliding window with 64-word overlap' },
          { step: '03', label: 'Embed', desc: 'all-MiniLM-L6-v2 → 384-dim vectors' },
          { step: '04', label: 'Index', desc: 'Store in PostgreSQL via pgvector' },
        ].map(({ step, label, desc }) => (
          <div key={step} className="card" style={{ padding: '16px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--accent)', marginBottom: 6 }}>{step}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', marginBottom: 4 }}>
            Upload Queue ({uploads.length})
          </h3>
          {uploads.map((upload, i) => (
            <UploadCard key={i} upload={upload} />
          ))}
        </div>
      )}
    </div>
  )
}

function UploadCard({ upload }) {
  const { file, status, progress, doc, error } = upload

  const icons = {
    pending: <Loader size={18} color="var(--text-muted)" />,
    uploading: <div className="spinner" />,
    processing: <div className="spinner" style={{ borderTopColor: 'var(--yellow)' }} />,
    done: <CheckCircle size={18} color="var(--green)" />,
    error: <AlertCircle size={18} color="var(--red)" />,
  }

  const statusColors = {
    pending: 'var(--text-muted)',
    uploading: 'var(--accent)',
    processing: 'var(--yellow)',
    done: 'var(--green)',
    error: 'var(--red)',
  }

  return (
    <div className="card" style={{ padding: '16px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <File size={20} color="var(--text-muted)" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{ fontWeight: 500, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {file.name}
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.65rem',
              color: statusColors[status],
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              flexShrink: 0,
            }}>
              {status === 'processing' ? 'Processing...' : status}
            </span>
          </div>

          {(status === 'uploading' || status === 'processing') && (
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: status === 'processing' ? '100%' : `${progress}%`,
                  background: status === 'processing' ? 'var(--yellow)' : 'var(--accent)',
                  animation: status === 'processing' ? 'pulse 1s ease-in-out infinite' : 'none',
                }}
              />
            </div>
          )}

          {status === 'done' && doc && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {doc.chunk_count} chunks · {(file.size / 1024).toFixed(1)} KB · ID: {doc.id.slice(0, 8)}...
            </div>
          )}

          {status === 'error' && (
            <div style={{ fontSize: '0.75rem', color: 'var(--red)' }}>{error}</div>
          )}
        </div>
        {icons[status]}
      </div>
    </div>
  )
}
