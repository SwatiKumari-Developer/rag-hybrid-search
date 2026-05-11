# 🔍 RAG Application with Hybrid Search

A production-ready **Retrieval-Augmented Generation (RAG)** system featuring a hybrid search pipeline that combines **dense vector search** (pgvector) with **sparse keyword search** (BM25), fused via **Reciprocal Rank Fusion (RRF)**, and powered by **Anthropic Claude** for answer generation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                   │
│  Upload → Parse → Chunk → Embed → Store (pgvector)      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    RETRIEVAL PIPELINE                    │
│  Query → [Dense Search] + [BM25 Search] → RRF Fusion   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   GENERATION PIPELINE                    │
│  Top-K Chunks + Query → Claude LLM → Cited Answer       │
└─────────────────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Web Framework** | FastAPI (Python) | Async-native, auto OpenAPI docs, Pydantic validation |
| **Vector Database** | PostgreSQL + pgvector | Store & query 384-dim embeddings directly in SQL |
| **ORM** | SQLAlchemy | Type-safe Python ↔ Postgres interface |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | Fast, lightweight, 384-dim dense vectors |
| **Sparse Search** | BM25 (rank-bm25) | Probabilistic keyword ranking with TF-IDF weighting |
| **Hybrid Fusion** | Reciprocal Rank Fusion (RRF) | Rank-based fusion — no score normalization needed |
| **LLM** | Anthropic Claude (Haiku) | Context-grounded answer generation |
| **Frontend** | React + Vite | Fast, modern SPA with React Router |
| **Containerization** | Docker + Docker Compose | Reproducible dev & prod environments |
| **Deployment** | Render.com | Free-tier PostgreSQL + Python + Static hosting |
| **CI/CD** | GitHub Actions | Automated lint + build on every push |

---

## 📚 Key Concepts Explained

### Why Hybrid Search?
- **Dense search** (vector similarity): Finds semantically related content. "Car" matches "automobile".
- **Sparse search** (BM25): Finds exact keyword matches. Better for technical terms, names, codes.
- **Hybrid**: Neither is universally better — combining them consistently outperforms either alone.

### Reciprocal Rank Fusion (RRF)
```
RRF(d) = Σ weight_i / (k + rank_i(d))
```
- Uses **ranks** not scores (so dense cosine similarity and BM25 scores don't need normalization)
- `k=60` smoothing constant prevents top-ranked docs from dominating
- Proven to outperform score averaging across diverse retrieval tasks

### pgvector Cosine Search
```sql
SELECT id, text, 1 - (embedding <=> $query_vector) AS similarity
FROM chunks ORDER BY embedding <=> $query_vector LIMIT 10
```
- `<=>` operator = cosine distance (1 - similarity)
- Stored as a native PostgreSQL column type — no separate vector DB needed

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Anthropic API key

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/rag-hybrid-search.git
cd rag-hybrid-search

# 2. Set your API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# 3. Start everything
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option B: Manual Setup

```bash
# ── Backend ──────────────────────────────────────────────
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill .env
cp .env.example .env
# Edit .env: set DATABASE_URL and ANTHROPIC_API_KEY

# Start PostgreSQL (via Docker)
docker run -d --name rag_postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=rag_db \
  -p 5432:5432 ankane/pgvector

# Start backend
uvicorn app.main:app --reload --port 8000

# ── Frontend (new terminal) ───────────────────────────────
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 📡 API Reference

### Upload a Document
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
file: <your_file>
```

### Ask a Question (Full RAG)
```http
POST /api/v1/query/ask
Content-Type: application/json

{
  "query": "What is the main finding?",
  "top_k": 5,
  "include_debug": true
}
```

### Hybrid Search Only
```http
POST /api/v1/query/search
Content-Type: application/json

{
  "query": "machine learning methodology",
  "top_k": 10
}
```

Full interactive docs at: **http://localhost:8000/docs**

---

## ☁️ Deploy to Render

## 📁 Project Structure

```
rag-hybrid-search/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   │   ├── documents.py   # Upload/list/delete endpoints
│   │   │   ├── query.py       # RAG and search endpoints
│   │   │   └── schemas.py     # Pydantic request/response models
│   │   ├── core/          # Config, DB, logging
│   │   ├── models/        # SQLAlchemy ORM models
│   │   │   ├── document.py    # Document table
│   │   │   └── chunk.py       # Chunk + vector column
│   │   ├── services/      # Business logic
│   │   │   ├── ingestion.py   # Parse → chunk → embed → store
│   │   │   ├── search.py      # Dense + BM25 + RRF
│   │   │   └── llm.py         # Claude answer generation
│   │   └── main.py        # FastAPI app entry point
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx    # Drag & drop upload
│   │   │   ├── DocumentsPage.jsx # Document library
│   │   │   ├── QueryPage.jsx     # Chat-style RAG interface
│   │   │   └── SearchPage.jsx    # Raw hybrid search results
│   │   ├── utils/api.js      # Axios API client
│   │   └── App.jsx           # Router + layout
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── render.yaml              # Render.com deployment blueprint
└── .github/workflows/ci.yml # GitHub Actions CI
```

---

## 🔧 Configuration

All settings are in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 512 | Words per chunk |
| `CHUNK_OVERLAP` | 64 | Overlap between chunks |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence-Transformers model |
| `TOP_K_DENSE` | 10 | Dense search candidates |
| `TOP_K_SPARSE` | 10 | BM25 search candidates |
| `TOP_K_FINAL` | 5 | Final chunks sent to LLM |
| `DENSE_WEIGHT` | 0.6 | RRF weight for dense results |
| `SPARSE_WEIGHT` | 0.4 | RRF weight for sparse results |
| `LLM_MODEL` | claude-3-haiku-20240307 | Anthropic model |

---

## 📝 License

MIT License — free to use, modify, and deploy.
