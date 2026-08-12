import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=api_key)


def embed_chunk(chunk):
    """
    Takes one code chunk (a dict from chunker.py) and returns the same
    chunk with an added "embedding" field — a list of numbers representing
    the meaning of that code.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=chunk["code"],
    )
    chunk["embedding"] = result.embeddings[0].values
    return chunk


def embed_chunks(chunks):
    """
    Embeds a whole list of chunks, one at a time.
    Prints progress so we can see it's actually working on a real repo.
    """
    embedded = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Embedding {i}/{len(chunks)}: {chunk['name']} ({chunk['type']})")
        embedded.append(embed_chunk(chunk))
        time.sleep(0.5)  # small pause to be gentle on free-tier rate limits
    return embedded