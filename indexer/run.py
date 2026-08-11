import sys
from walker import walk_repo
from chunker import chunk_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <path-to-repo>")
        sys.exit(1)

    repo_path = sys.argv[1]

    print(f"\nWalking repo: {repo_path}\n")
    files = walk_repo(repo_path)

    print(f"Found {len(files)} file(s) to index:")
    for f in files:
        print(f"  - {f['relative_path']}")

    print(f"\nChunking...\n")

    total_chunks = 0
    for f in files:
        chunks = chunk_file(f["file_path"])
        total_chunks += len(chunks)

        print(f"{f['relative_path']} -> {len(chunks)} chunk(s)")
        for chunk in chunks:
            print(f"   [{chunk['type']}] {chunk['name']}  (lines {chunk['start_line']}-{chunk['end_line']})")

    print(f"\nTotal chunks found: {total_chunks}")


if __name__ == "__main__":
    main()