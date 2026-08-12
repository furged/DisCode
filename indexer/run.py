import sys
from walker import walk_repo
from chunker import chunk_file
from embedder import embed_chunks
from storage import get_connection, init_db, save_chunks


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <path-to-repo>")
        sys.exit(1)

    repo_path = sys.argv[1]

    files = walk_repo(repo_path)
    print(f"Found {len(files)} file(s) in {repo_path}")

    all_chunks = []
    for f in files:
        chunks = chunk_file(f["file_path"])
        all_chunks.extend(chunks)

    print(f"Extracted {len(all_chunks)} code chunks")

    embedded_chunks = embed_chunks(all_chunks)
    print(f"Embedded {len(embedded_chunks)} chunks successfully")

    conn = get_connection("codebase.db")
    init_db(conn)
    save_chunks(conn, embedded_chunks)
    print(f"Saved {len(embedded_chunks)} chunks to codebase.db")


if __name__ == "__main__":
    main()