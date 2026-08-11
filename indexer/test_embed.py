import os
from dotenv import load_dotenv
from google import genai

# Load the .env file so we can read GEMINI_API_KEY from it
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found. Check your .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

# Try embedding one simple piece of text, just to prove the connection works
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents="function movePaddle(paddle, direction) { paddle.y += 5; }"
)

embedding = result.embeddings[0].values

print(f"Success! Got an embedding with {len(embedding)} numbers.")
print(f"First 5 values: {embedding[:5]}")
