
## Current Status

**✅ Complete:**
- Full indexing pipeline (walk repo → parse code → chunk by functions/classes)
- Embedding system (Gemini API integration)
- Vector storage (SQLite + sqlite-vec)
- Semantic search + self-correction (detects weak results, rewrites query, retries)
- MCP server (Claude Desktop / other tools can call it)
- Backend API (FastAPI, HTTP endpoints for web frontend)

**🚧 In Progress:**
- Frontend web app (chat UI, dark/terminal aesthetic)

**📋 Planned:**
- Multi-language support (currently JS/TS only)
- Final evaluation & report

## Quick Start

### Prerequisites
- Python 3.12
- Gemini API key (free tier available at https://aistudio.google.com/)

### Setup

```bash
# Create venv
python3.12 -m venv venv
source venv/bin/activate  # or venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env with your API key
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Index a Codebase

```bash
python indexer/run.py /path/to/your/repo
```

This walks the repo, chunks it, embeds every chunk, and saves to `codebase.db`.

### Ask Questions (CLI)

```bash
python indexer/ask.py "how does the ball move"
```

Returns the top 3 most relevant code chunks with distances (lower = more relevant).

### Use the Backend API

```bash
# In one terminal, start the server
python indexer/api.py

# In another, query it
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question": "how does the paddle movement work"}'
```

### Use with Claude Desktop (MCP)

The MCP server exposes `search_codebase` as a tool. Configure it in Claude Desktop to let Claude search your indexed repos automatically mid-conversation.

## Architecture

**Core Layers:**
- **`indexer/walker.py`** — File discovery (skips junk, finds real code)
- **`indexer/chunker.py`** — Code parsing via tree-sitter (AST-aware chunking)
- **`indexer/embedder.py`** — Turns code chunks into semantic vectors
- **`indexer/storage.py`** — SQLite + sqlite-vec (stores chunks + embeddings, enables fast similarity search)
- **`indexer/retriever.py`** — Semantic search with self-correction (detects weak results, auto-rewrites queries)
- **`indexer/server.py`** — MCP server (exposes retrieval as tools)
- **`indexer/api.py`** — FastAPI backend (HTTP interface for web frontend)

**Why this design:**
- **No local model inference** — all AI work is API calls (learned from earlier project that crashed on 4GB laptop)
- **Code-aware chunking** — functions/classes stay whole, never half-cut, preserving meaning
- **Self-correcting retrieval** — checks if results are weak and automatically retries instead of answering with low-confidence context
- **Production-ready storage** — SQLite scales to any single repo; architecture is source-agnostic so remote repos are easy to add later

## Tech Stack

| Layer | Technology |
|-------|------------|
| Parsing | tree-sitter (Python bindings) |
| Embeddings | Google Gemini API (`google-genai`) |
| Storage | SQLite + sqlite-vec |
| Search | Vector similarity (cosine distance) |
| MCP Server | Python MCP SDK |
| Backend API | FastAPI + Uvicorn |
| Frontend | JavaScript/TypeScript (React planned) |
| Dev Environment | Python 3.12, venv, GitHub Codespaces |

## Key Concepts

**RAG (Retrieval-Augmented Generation)** — Find real data first, then generate answers grounded in it, instead of trusting the AI's general knowledge.

**Embeddings** — Turning text/code into vectors (lists of numbers) where similar meaning = nearby coordinates in vector space. This enables "search by meaning" instead of keyword matching.

**Tree-sitter** — Parser that understands code's real structure (functions, classes) via AST parsing, so chunking respects syntactic boundaries instead of blindly cutting text.

**Self-correcting RAG** — When search results are weak (even the best match isn't close enough in meaning), automatically rewrite the query and retry instead of answering with poor context.

**Vector similarity search** — Finding the closest points in vector space (lowest distance) to find the most semantically related code chunks.

## Evaluation Plan

For the final project report, will measure:
- **Retrieval precision/recall** — Do searches find the right functions?
- **Answer faithfulness** — Do answers stick to retrieved context or add hallucinated details?
- **Self-correction effectiveness** — How often does retry actually improve results?

## Known Limitations

- **JS/TS only (for now)** — Chunker currently understands JavaScript/TypeScript. Other languages require adding tree-sitter grammars (architecture supports this, just not implemented yet).
- **Single-repo scope (v1)** — Currently indexes open workspace. Remote repos are a planned Phase 2 addition.
- **Threshold tuning** — Self-correction threshold (0.85) was picked empirically from real test data on Pong game; may need adjustment for different codebases.

## For Recruiters / Academics

This project demonstrates:
- **RAG systems in practice** — Not just theory, actual implementation with real tradeoffs
- **Semantic search** — Embeddings, vector databases, similarity metrics
- **Production thinking** — Handling concurrency (SQLite threading), API design, deployment considerations
- **Self-improving systems** — Agents that detect their own errors and retry
- **Code understanding** — AST parsing, syntactic chunking, language-aware analysis
- **Full-stack development** — ML pipeline + backend API + client integration (MCP)


## Next Steps

1. **Frontend web app** (next session) — Chat UI, displays retrieved chunks + self-correction indicator
2. **Multi-language support** — Add Python, Java, Go grammars
3. **Evaluation & report** — Measure retrieval quality, document findings
4. **Phase 2 (after project)** — Remote repo indexing, UI polish, potential release