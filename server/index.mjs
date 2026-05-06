import { createServer } from 'node:http';
import { loadDotEnv } from './env.mjs';
import { generateJson, generateText, getPublicProfiles } from './llmGateway.mjs';

loadDotEnv();

const port = Number(process.env.PORT || process.env.LLM_SERVER_PORT || 8787);

const server = createServer(async (req, res) => {
  try {
    if (req.method === 'OPTIONS') {
      sendJson(res, 204, null);
      return;
    }

    const url = new URL(req.url ?? '/', `http://${req.headers.host ?? '127.0.0.1'}`);
    if (req.method === 'GET' && url.pathname === '/api/health') {
      sendJson(res, 200, { ok: true });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/api/llm/providers') {
      sendJson(res, 200, { providers: await getPublicProfiles(), qualities: ['fast', 'standard'] });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/llm/generate') {
      const body = await readJson(req);
      sendJson(res, 200, await generateText(body));
      return;
    }

    if (req.method === 'POST' && url.pathname === '/api/llm/generate-json') {
      const body = await readJson(req);
      sendJson(res, 200, await generateJson(body));
      return;
    }

    sendJson(res, 404, { error: 'Not found' });
  } catch (error) {
    sendJson(res, 500, { error: error?.message ?? String(error) });
  }
});

server.listen(port, '127.0.0.1', () => {
  console.log(`[llm-server] listening on http://127.0.0.1:${port}`);
});

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) {
        req.destroy(new Error('Request body too large'));
      }
    });
    req.on('error', reject);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error('Invalid JSON request body'));
      }
    });
  });
}

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Private-Network', 'true');
  if (statusCode === 204) {
    res.end();
    return;
  }
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(payload));
}
