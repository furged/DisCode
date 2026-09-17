from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from storage import get_connection, init_db, clear_chunks, save_chunks
from retriever import retrieve, synthesize_answer, RetrievalError
from walker import walk_repo
from chunker import chunk_file
from embedder import embed_chunks
from repo_source import resolve_repo_source, RepoFetchError
import os
import threading
import time
import uuid

app = FastAPI(title="DisCode API")

# Wide open on purpose: this only ever runs on localhost for local dev
# (the frontend is opened as a plain HTML file, whose "file://" origin
# doesn't play nicely with a strict allowlist anyway). Do NOT ship this
# wide-open config if this API is ever deployed somewhere reachable
# from the internet — lock allow_origins down to the real frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

MAX_QUESTION_LENGTH = 500  # generous for a search question; guards against abuse/accidents

# In-memory job store for background indexing runs. This is fine for a
# local single-user dev tool - it resets on server restart, and there's
# no need for a real job queue (Celery/etc) at this scale. Keyed by a
# random job_id so the frontend can poll GET /api/index/{job_id}.
_index_jobs = {}
_index_jobs_lock = threading.Lock()

# Tracks the most recently *successfully* completed index, so the frontend
# can show "indexed: <repo>, N chunks" on page load without needing to have
# triggered that index itself in the current browser session.
_last_index_info = None
_last_index_lock = threading.Lock()


class IndexRequest(BaseModel):
    repo_path: str = Field(..., min_length=1)


class IndexJobStatus(BaseModel):
    status: str  # "fetching" | "walking" | "chunking" | "embedding" | "saving" | "done" | "error"
    total: int = 0
    processed: int = 0
    current_name: str | None = None
    failed: list[str] = []
    error: str | None = None
    source_label: str | None = None  # short human-readable name of what's being indexed


class LastIndexInfo(BaseModel):
    source_label: str
    chunk_count: int
    failed_count: int
    finished_at: float  # unix timestamp - frontend can render "2 min ago" itself


def _short_source_label(source):
    """Turns a path or GitHub URL into a short display name, e.g.
    'owner/repo' for a GitHub link or the last folder name for a local path."""
    from repo_source import GITHUB_URL_RE
    match = GITHUB_URL_RE.match(source.strip())
    if match:
        return f"{match.group('owner')}/{match.group('repo')}"
    return os.path.basename(os.path.normpath(source)) or source


def _run_indexing_job(job_id, source):
    """
    Runs the full fetch -> walk -> chunk -> embed -> save pipeline in a
    background thread, writing progress into _index_jobs[job_id] as it
    goes so GET /api/index/{job_id} has something live to report.
    `source` can be a local path OR a GitHub URL - resolve_repo_source
    handles telling those apart and downloading the latter.
    """
    global _last_index_info

    def set_status(**updates):
        with _index_jobs_lock:
            _index_jobs[job_id].update(updates)

    label = _short_source_label(source)
    set_status(source_label=label)

    try:
        set_status(status="fetching")
        try:
            repo_path = resolve_repo_source(source)
        except RepoFetchError as e:
            raise ValueError(str(e))  # caught below, becomes a clean "error" status

        if not os.path.isdir(repo_path):
            raise ValueError(f"Not a valid directory: {repo_path}")

        set_status(status="walking")
        files = walk_repo(repo_path)

        set_status(status="chunking")
        all_chunks = []
        for f in files:
            all_chunks.extend(chunk_file(f["file_path"]))
        set_status(total=len(all_chunks))

        set_status(status="embedding")

        def on_progress(processed, total, name):
            set_status(processed=processed, total=total, current_name=name)

        embedded_chunks, failed_chunks = embed_chunks(all_chunks, on_progress=on_progress)

        set_status(status="saving")
        conn = get_connection("codebase.db")
        try:
            init_db(conn)
            clear_chunks(conn)  # re-indexing replaces, not stacks on, the last run
            save_chunks(conn, embedded_chunks)
        finally:
            conn.close()

        set_status(status="done", failed=failed_chunks, current_name=None)

        with _last_index_lock:
            _last_index_info = LastIndexInfo(
                source_label=label,
                chunk_count=len(embedded_chunks),
                failed_count=len(failed_chunks),
                finished_at=time.time(),
            )

    except Exception as e:
        # Broad on purpose: this runs in a background thread with nothing
        # else watching it, so an uncaught exception here would otherwise
        # just vanish - the job would sit at "embedding" forever with no
        # way for the frontend to know it died.
        set_status(status="error", error=str(e))


@app.post("/api/index")
def start_indexing(request: IndexRequest):
    """
    Kicks off indexing a repo (local path OR GitHub URL) in the background
    and returns immediately with a job_id to poll. Indexing a real repo
    can take minutes (rate limited by the embedding API, and now
    potentially a repo download too), so this can't be a normal blocking
    request/response like /api/search. Path/URL validation happens inside
    the background job itself (see _run_indexing_job) so both cases behave
    consistently - reported through polling, not an instant 400.
    """
    source = request.repo_path.strip()

    job_id = str(uuid.uuid4())
    with _index_jobs_lock:
        _index_jobs[job_id] = {"status": "queued", "total": 0, "processed": 0,
                                "current_name": None, "failed": [], "error": None,
                                "source_label": None}

    thread = threading.Thread(target=_run_indexing_job, args=(job_id, source), daemon=True)
    thread.start()

    return {"job_id": job_id}


@app.get("/api/index/{job_id}")
def get_index_status(job_id: str) -> IndexJobStatus:
    with _index_jobs_lock:
        job = _index_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return IndexJobStatus(**job)


@app.get("/api/status")
def get_status():
    """Returns info about the last successful index, or null if nothing's
    been indexed yet since the server started - lets the frontend show
    'indexed: owner/repo, 25 chunks' on load without polling a job."""
    with _last_index_lock:
        return _last_index_info


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value):
        stripped = value.strip()
        if not stripped:
            raise ValueError("question can't be empty or just whitespace")
        return stripped


class CodeChunkResult(BaseModel):
    type: str
    name: str
    code: str
    file_path: str
    start_line: int
    end_line: int
    distance: float


class SearchResponse(BaseModel):
    answer: str | None
    results: list[CodeChunkResult]
    was_corrected: bool
    final_query: str


@app.post("/api/search")
def search(request: SearchRequest) -> SearchResponse:
    """
    Search the codebase for code relevant to a natural-language question,
    and synthesize an actual written answer from the retrieved code
    instead of just handing back raw chunks for the user to read themselves.
    """
    # Create a fresh connection for this request — SQLite connections
    # can't be shared across threads, so this is safer than trying to
    # reuse one connection.
    conn = get_connection("codebase.db")
    try:
        outcome = retrieve(conn, request.question, top_k=3)
    except RetrievalError as e:
        # The embedding API is down/exhausted retries — tell the client
        # cleanly instead of leaking a raw 500 + stack trace.
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()

    # Best-effort: if synthesis fails, the raw results are still useful,
    # so this never turns a working search into a 503.
    answer = synthesize_answer(request.question, outcome["results"])

    results = [CodeChunkResult(**r) for r in outcome["results"]]

    return SearchResponse(
        answer=answer,
        results=results,
        was_corrected=outcome["was_corrected"],
        final_query=outcome["final_query"],
    )


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)