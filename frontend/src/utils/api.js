import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 minutes for LLM generation
})

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

// Response interceptor for error normalization
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || err.message || 'Unknown error'
    throw new Error(message)
  }
)

// ─── Documents API ────────────────────────────────────────────────────────────

export const uploadDocument = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  })
  return res.data
}

export const listDocuments = async () => {
  const res = await api.get('/documents/')
  return res.data
}

export const getDocument = async (id) => {
  const res = await api.get(`/documents/${id}`)
  return res.data
}

export const deleteDocument = async (id) => {
  await api.delete(`/documents/${id}`)
}

// ─── Query API ────────────────────────────────────────────────────────────────

export const askQuestion = async (query, documentIds = null, topK = null, includeDebug = false) => {
  const res = await api.post('/query/ask', {
    query,
    document_ids: documentIds,
    top_k: topK,
    include_debug: includeDebug,
  })
  return res.data
}

export const searchDocuments = async (query, documentIds = null, topK = 5) => {
  const res = await api.post('/query/search', {
    query,
    document_ids: documentIds,
    top_k: topK,
  })
  return res.data
}

// ─── Health ───────────────────────────────────────────────────────────────────

export const checkHealth = async () => {
  const res = await axios.get('/health')
  return res.data
}
