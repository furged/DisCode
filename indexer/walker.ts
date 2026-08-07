import * as fs from "fs";
import * as path from "path";

// Folder names we NEVER want to walk into.
// These either aren't "your code" (dependencies) or aren't useful for RAG (build output, git internals).
const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".next",
  "coverage",
]);

// File types we know how to chunk meaningfully right now.
// We'll add more languages later — starting small on purpose.
const SUPPORTED_EXTENSIONS = new Set([".js", ".ts", ".jsx", ".tsx"]);

// Anything bigger than this is probably a generated/minified file, not real hand-written code.
const MAX_FILE_SIZE_BYTES = 500_000; // ~500kb

export interface WalkResult {
  filePath: string; // full path on disk
  relativePath: string; // path relative to the repo root, easier to read/display
}

/**
 * Walks a folder recursively and returns the list of files we should index.
 * Skips junk folders and unsupported/oversized files.
 */
export function walkRepo(rootDir: string): WalkResult[] {
  const results: WalkResult[] = [];

  function walk(currentDir: string) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);

      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) {
          continue; // skip this folder entirely, don't even look inside
        }
        walk(fullPath); // recurse into subfolder
        continue;
      }

      // it's a file — check if we care about it
      const ext = path.extname(entry.name);
      if (!SUPPORTED_EXTENSIONS.has(ext)) {
        continue;
      }

      const stats = fs.statSync(fullPath);
      if (stats.size > MAX_FILE_SIZE_BYTES) {
        continue; // too big, probably not hand-written code
      }

      results.push({
        filePath: fullPath,
        relativePath: path.relative(rootDir, fullPath),
      });
    }
  }

  walk(rootDir);
  return results;
}