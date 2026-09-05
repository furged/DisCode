import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # doubles each retry: 2s, 4s, 8s


class EmbeddingError(Exception):
    """Raised when embedding a chunk fails after all retries."""


def _embed_with_retry(text):
    """
    Calls the Gemini embedding API with retry-with-backoff, since a
    single rate-limit hit or transient network error shouldn't kill an
    entire indexing run or a live search request.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
            )
            return result.embeddings[0].values
        except genai_errors.APIError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"Embedding call failed ({e}), retrying in {wait}s "
                      f"(attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
        except (ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"Network error ({e}), retrying in {wait}s "
                      f"(attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)

    raise EmbeddingError(f"Failed to embed text after {MAX_RETRIES} attempts: {last_error}")


def embed_chunk(chunk):
    """
    Takes one code chunk (a dict from chunker.py) and returns the same
    chunk with an added "embedding" field — a list of numbers representing
    the meaning of that code.
    Raises EmbeddingError if the API call fails after retries.
    """
    chunk["embedding"] = _embed_with_retry(chunk["code"])
    return chunk


def embed_chunks(chunks):
    """
    Embeds a whole list of chunks, one at a time.
    Prints progress so we can see it's actually working on a real repo.
    Skips (and reports) any chunk that fails after retries, instead of
    letting one bad chunk abort the whole indexing run.
    """
    embedded = []
    failed = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Embedding {i}/{len(chunks)}: {chunk['name']} ({chunk['type']})")
        try:
            embedded.append(embed_chunk(chunk))
        except EmbeddingError as e:
            print(f"  Skipping {chunk['name']}: {e}")
            failed.append(chunk["name"])
        time.sleep(0.5)  # small pause to be gentle on free-tier rate limits

    if failed:
        print(f"\n{len(failed)} chunk(s) failed to embed and were skipped: {', '.join(failed)}")

    return embedded