import * as fs from "fs";
import * as path from "path";
import { Parser, Language, Node as TSNode } from "web-tree-sitter";

export interface CodeChunk {
  type: "function" | "class" | "method"; // what kind of code block this is
  name: string; // e.g. "movePaddle" or "Ball"
  code: string; // the actual source code text of this chunk
  startLine: number;
  endLine: number;
  filePath: string; // which file this chunk came from
}

let parserReady: Promise<Parser> | null = null;

// tree-sitter needs to load its "brain" (the .wasm grammar file) once before it can parse anything.
// We only want to do this setup once and reuse it, not redo it for every file.
async function getParser(): Promise<Parser> {
  if (!parserReady) {
    parserReady = (async () => {
      await Parser.init();
      const parser = new Parser();
      const wasmPath = path.join(
        __dirname,
        "..",
        "node_modules",
        "tree-sitter-wasms",
        "out",
        "tree-sitter-javascript.wasm"
      );
      const Lang = await Language.load(wasmPath);
      parser.setLanguage(Lang);
      return parser;
    })();
  }
  return parserReady;
}

/**
 * Parses one file's code and pulls out each function/class as a separate chunk,
 * instead of just splitting the text every N characters (which would cut functions in half).
 */
export async function chunkFile(filePath: string): Promise<CodeChunk[]> {
  const parser = await getParser();
  const sourceCode = fs.readFileSync(filePath, "utf-8");
  const tree = parser.parse(sourceCode);
  if (!tree) {
    return []; // parsing failed (e.g. broken syntax) — skip this file instead of crashing
  }

  const chunks: CodeChunk[] = [];

  // "node" here means a piece of the parsed tree (e.g. one function), not Node.js the runtime.
  function visit(node: TSNode) {
    if (node.type === "function_declaration") {
      const nameNode = node.childForFieldName("name");
      chunks.push({
        type: "function",
        name: nameNode ? nameNode.text : "anonymous",
        code: node.text,
        startLine: node.startPosition.row + 1,
        endLine: node.endPosition.row + 1,
        filePath,
      });
      return; // don't look inside this function for nested chunks, it's already one whole unit
    }

    if (node.type === "class_declaration") {
      const nameNode = node.childForFieldName("name");
      chunks.push({
        type: "class",
        name: nameNode ? nameNode.text : "anonymous",
        code: node.text,
        startLine: node.startPosition.row + 1,
        endLine: node.endPosition.row + 1,
        filePath,
      });
      return; // treat the whole class (including its methods) as one chunk for now
    }

    // keep looking through children for more functions/classes
    for (let i = 0; i < node.childCount; i++) {
      const child = node.child(i);
      if (child) visit(child);
    }
  }

  visit(tree.rootNode);
  return chunks;
}