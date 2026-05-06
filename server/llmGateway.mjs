import { envFirst } from './env.mjs';
import { getModelProfile, MODEL_QUALITIES } from './modelProfiles.mjs';
import { loadSystemPrompt } from './promptStore.mjs';

const DEFAULT_TIMEOUT_MS = 60000;

export function listProviderSummaries() {
  return MODEL_QUALITIES.reduce((qualities, quality) => {
    qualities[quality] = true;
    return qualities;
  }, {});
}

export function getPublicProfiles() {
  return import('./modelProfiles.mjs').then(({ MODEL_PROFILES }) =>
    MODEL_PROFILES.map((profile) => {
      const fastModel = resolveModel(profile, {}, 'fast');
      const standardModel = resolveModel(profile, {}, 'standard');
      return {
        id: profile.id,
        label: profile.label,
        provider: profile.provider,
        fastModel,
        standardModel,
        hasApiKey: Boolean(resolveApiKey(profile, {})),
        supportsJson: profile.supportsJson,
        supportsStreaming: profile.supportsStreaming,
      };
    }),
  );
}

export async function generateText(options) {
  const config = resolveModelConfig(options);
  const messages = await normalizeMessages(options);
  const startedAt = Date.now();
  const response = await callOpenAICompatible(config, messages);

  return {
    text: response.text,
    usage: response.usage,
    profileId: config.profile.id,
    provider: config.profile.provider,
    model: config.model,
    quality: config.quality,
    durationMs: Date.now() - startedAt,
  };
}

export async function generateJson(options) {
  const result = await generateText({
    ...options,
    systemPrompt: [options.systemPrompt, 'Return strict JSON only.'].filter(Boolean).join('\n'),
  });
  return {
    ...result,
    json: parseJsonFromText(result.text),
  };
}

export function resolveModelConfig(options = {}) {
  const quality = MODEL_QUALITIES.includes(options.quality) ? options.quality : 'standard';
  const profile = getModelProfile(options.profileId);
  const apiKey = resolveApiKey(profile, options);
  const baseUrl = normalizeBaseUrl(
    options.baseUrl ||
      envFirst(profile.baseUrlEnv) ||
      envFirst(['LLM_BASE_URL']) ||
      profile.baseUrl,
  );
  const model = resolveModel(profile, options, quality);
  const timeoutMs = resolveTimeoutMs(profile, quality);

  if (!apiKey) {
    throw new Error(`Missing API key for provider "${profile.id}". Expected one of: ${profile.apiKeyEnv.join(', ')}`);
  }
  if (!baseUrl) {
    throw new Error(`Missing base URL for provider "${profile.id}".`);
  }
  if (!model) {
    throw new Error(`Missing model for provider "${profile.id}" (${quality}).`);
  }

  return {
    profile,
    quality,
    apiKey,
    baseUrl,
    model,
    timeoutMs,
    temperature: numberOrDefault(options.temperature, numberOrDefault(process.env.LLM_TEMPERATURE, 0.7)),
    maxTokens: numberOrDefault(options.maxTokens, undefined),
  };
}

function resolveApiKey(profile, options) {
  return options.apiKey || envFirst(profile.apiKeyEnv) || envFirst(['LLM_API_KEY']);
}

function resolveModel(profile, options, quality) {
  if (options.model) {
    return options.model;
  }

  const qualityEnv = quality === 'fast' ? profile.fastModelEnv : profile.standardModelEnv;
  return (
    envFirst(qualityEnv) ||
    envFirst(profile.modelEnv) ||
    envFirst(['LLM_MODEL']) ||
    (quality === 'fast' ? profile.fastModel : profile.standardModel)
  );
}

function resolveTimeoutMs(profile, quality) {
  const envTimeout = envFirst([
    `TRPG_${profile.provider.toUpperCase()}_${quality.toUpperCase()}_TIMEOUT_MS`,
    `TRPG_${profile.id.toUpperCase().replace(/-/g, '_')}_${quality.toUpperCase()}_TIMEOUT_MS`,
    'LLM_TIMEOUT_MS',
  ]);
  return numberOrDefault(envTimeout, profile.timeoutMs?.[quality] ?? DEFAULT_TIMEOUT_MS);
}

async function normalizeMessages(options) {
  const systemPrompt = await resolveSystemPrompt(options);

  if (Array.isArray(options.messages) && options.messages.length > 0) {
    const messages = options.messages.map((message) => ({
      role: message.role,
      content: String(message.content ?? ''),
    }));
    return prependOrMergeSystemPrompt(messages, systemPrompt);
  }

  return [
    systemPrompt ? { role: 'system', content: systemPrompt } : null,
    { role: 'user', content: String(options.userPrompt ?? options.prompt ?? '') },
  ].filter(Boolean);
}

async function resolveSystemPrompt(options) {
  const promptFromFile = options.promptId ? await loadSystemPrompt(options.promptId) : '';
  return [promptFromFile, options.systemPrompt].filter(Boolean).join('\n\n');
}

function prependOrMergeSystemPrompt(messages, systemPrompt) {
  if (!systemPrompt) {
    return messages;
  }

  const systemIndex = messages.findIndex((message) => message.role === 'system');
  if (systemIndex < 0) {
    return [{ role: 'system', content: systemPrompt }, ...messages];
  }

  return messages.map((message, index) => {
    if (index !== systemIndex) {
      return message;
    }
    return {
      ...message,
      content: [systemPrompt, message.content].filter(Boolean).join('\n\n'),
    };
  });
}

async function callOpenAICompatible(config, messages) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs);

  try {
    const response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model,
        messages,
        temperature: config.temperature,
        max_tokens: config.maxTokens,
      }),
      signal: controller.signal,
    });

    const raw = await response.text();
    const data = safeJsonParse(raw);
    if (!response.ok) {
      const message = data?.error?.message || data?.message || raw || `LLM request failed: ${response.status}`;
      throw new Error(message);
    }

    return {
      text: data?.choices?.[0]?.message?.content ?? '',
      usage: data?.usage ?? null,
    };
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(`LLM request timed out after ${config.timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function parseJsonFromText(text) {
  const parsed = safeJsonParse(text);
  if (parsed) {
    return parsed;
  }

  const match = text.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
  if (!match) {
    throw new Error('LLM response did not contain JSON.');
  }
  return JSON.parse(match[0]);
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function normalizeBaseUrl(baseUrl) {
  return baseUrl ? String(baseUrl).replace(/\/+$/, '') : null;
}

function numberOrDefault(value, fallback) {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
