import { walkRepo } from "./walker";
import { chunkFile } from "./chunker";

async function main() {
  const repoPath = process.argv[2]; // pass the folder to scan as a command-line argument

  if (!repoPath) {
    console.error("Usage: ts-node run.ts <path-to-repo>");
    process.exit(1);
  }

  console.log(`\nWalking repo: ${repoPath}\n`);
  const files = walkRepo(repoPath);

  console.log(`Found ${files.length} file(s) to index:`);
  for (const f of files) {
    console.log(`  - ${f.relativePath}`);
  }

  console.log(`\nChunking...\n`);

  let totalChunks = 0;
  for (const f of files) {
    const chunks = await chunkFile(f.filePath);
    totalChunks += chunks.length;

    console.log(`${f.relativePath} → ${chunks.length} chunk(s)`);
    for (const chunk of chunks) {
      console.log(
        `   [${chunk.type}] ${chunk.name}  (lines ${chunk.startLine}-${chunk.endLine})`
      );
    }
  }

  console.log(`\nTotal chunks found: ${totalChunks}`);
}

main();