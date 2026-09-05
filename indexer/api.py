from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from storage import get_connection
from retriever import retrieve, RetrievalError

app = FastAPI(title="DisCode API")

MAX_QUESTION_LENGTH = 500  # generous for a search question; guards against abuse/accidents


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
    try:
        outcome = retrieve(conn, request.question, top_k=3)
    except RetrievalError as e:
        # The embedding API is down/exhausted retries — tell the client
        # cleanly instead of leaking a raw 500 + stack trace.
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        conn.close()

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