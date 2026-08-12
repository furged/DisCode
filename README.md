# DisCode

## Current phase: Building the RAG core (pre-MCP, pre-frontend)

## Status

**Done:**
- [x] Indexing pipeline — file walker (`indexer/walker.py`)
- [x] Indexing pipeline — code-aware chunker (`indexer/chunker.py`)
- [x] Tested indexing pipeline on real repo (Pong game) — TypeScript first,
      then rebuilt in Python with identical results
- [x] Switched stack: Python for backend/MCP server, JS/TS for frontend only
- [x] Python 3.12 + venv set up locally
- [x] Gemini API key set up, stored in `.env`
- [x] Embedding pipeline (`indexer/embedder.py`) — tested on all 20 real
      Pong chunks, successful
- [x] Storage (`indexer/storage.py`) — SQLite + sqlite-vec, tested with
      fake data, then with real embedded Pong chunks — 20 chunks saved
      successfully to `codebase.db`
- [x] All of the above pushed to GitHub

**Not done yet:**
- [ ] Retrieval — given a question, embed it and search storage for closest
      matching chunks
- [ ] Self-correction logic — detect weak retrieval, retry with better query
- [ ] MCP server — expose retrieval as tools (`search_codebase`,
      `explain_function`, etc.)
- [ ] Backend API — connects frontend to MCP server
- [ ] Frontend web app — chat UI, dark/terminal style. Must show: the
      answer, the real retrieved code chunks used, a visible self-correction
      indicator. Session-only memory, no accounts.
- [ ] Support for languages beyond JS/TS
- [ ] Eval plan (retrieval precision/recall, answer faithfulness) for final
      report

## Stack

- Python (indexing, embeddings, storage, MCP server, backend)
- JavaScript/TypeScript (frontend only)
- tree-sitter (`tree-sitter`, `tree-sitter-languages`)
- Google Gemini API (`google-genai`) — embeddings
- SQLite + sqlite-vec
- python-dotenv

## Timeline

Estimated 6-8 weeks total at 2-3 hours/day. Started real coding.

## Next immediate step

Build retrieval: take a plain-text question, embed it, search `codebase.db`
for the closest-matching code chunks.