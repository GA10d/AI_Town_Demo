import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const serverDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(serverDir, '..');
const promptRoot = path.join(projectRoot, 'prompt');
const systemPromptFileNames = ['system.md', 'system.txt', 'prompt.md', 'prompt.txt'];

export async function loadSystemPrompt(promptId) {
  if (!promptId) {
    return '';
  }

  const promptPath = resolvePromptPath(promptId);
  const filePath = await resolvePromptFile(promptPath);
  return (await readFile(filePath, 'utf8')).trim();
}

function resolvePromptPath(promptId) {
  const safeId = String(promptId)
    .replace(/\\/g, '/')
    .split('/')
    .filter(Boolean)
    .join('/');
  const resolvedPath = path.resolve(promptRoot, safeId);
  const relativePath = path.relative(promptRoot, resolvedPath);

  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    throw new Error(`Invalid prompt id: ${promptId}`);
  }

  return resolvedPath;
}

async function resolvePromptFile(promptPath) {
  if (await fileExists(promptPath)) {
    return promptPath;
  }

  for (const fileName of systemPromptFileNames) {
    const candidate = path.join(promptPath, fileName);
    if (await fileExists(candidate)) {
      return candidate;
    }
  }

  throw new Error(`Prompt file not found under ${path.relative(projectRoot, promptPath)}`);
}

async function fileExists(filePath) {
  try {
    return (await stat(filePath)).isFile();
  } catch {
    return false;
  }
}
