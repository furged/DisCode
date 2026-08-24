from fastapi import FastAPI
from pydantic import BaseModel
from storage import get_connection
from retriever import retrieve

app = FastAPI(title="DisCode API")


class SearchRequest(BaseModel):
    question: str


class CodeChunkResult(BaseModel):
    type: str
    name: str
    code: str
    file_path: str
    start_line: int
    end_line: int
    distance: float


class SearchResponse(BaseModel):
    results: list[CodeChunkResult]
    was_corrected: bool
    final_query: str


@app.post("/api/search")
def search(request: SearchRequest) -> SearchResponse:
    """
    Search the codebase for code relevant to a natural-language question.
    """
    # Create a fresh connection for this request — SQLite connections
    # can't be shared across threads, so this is safer than trying to
    # reuse one connection.
    conn = get_connection("codebase.db")
    outcome = retrieve(conn, request.question, top_k=3)

    results = [CodeChunkResult(**r) for r in outcome["results"]]

    return SearchResponse(
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