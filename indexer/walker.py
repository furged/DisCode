import os
from chunker import EXTENSION_TO_LANGUAGE

# Folder names we NEVER want to walk into.
# These either aren't "your code" (dependencies) or aren't useful for RAG (build output, git internals).
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "coverage",
    "target", "__pycache__", ".venv", "venv", "vendor", "bin", "obj",
}

# File types we know how to chunk meaningfully right now. Derived from
# chunker.py's EXTENSION_TO_LANGUAGE so this list can never silently
# drift out of sync with what the chunker actually supports (this used
# to happen: .ts was "supported" here but parsed with the wrong grammar).
SUPPORTED_EXTENSIONS = set(EXTENSION_TO_LANGUAGE.keys())

# Anything bigger than this is probably a generated/minified file, not real hand-written code.
MAX_FILE_SIZE_BYTES = 500_000  # ~500kb


def walk_repo(root_dir):
    """
    Walks a folder recursively and returns the list of files we should index.
    Skips junk folders and unsupported/oversized files.
    Returns a list of dicts: {"file_path": ..., "relative_path": ...}
    """
    results = []

    for current_dir, dir_names, file_names in os.walk(root_dir):
        # Modify dir_names IN PLACE to stop os.walk from ever entering skipped folders.
        dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]

        for file_name in file_names:
            ext = os.path.splitext(file_name)[1]
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(current_dir, file_name)

            if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                continue  # too big, probably not hand-written code

            relative_path = os.path.relpath(full_path, root_dir)

            results.append({
                "file_path": full_path,
                "relative_path": relative_path,
            })

    return results