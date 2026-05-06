import { loadLlmSettings } from './LlmSettings';

export interface GenerateTextRequest {
    messages?: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>;
    promptId?: string;
    systemPrompt?: string;
    userPrompt?: string;
    temperature?: number;
    maxTokens?: number;
}

export interface GenerateTextResponse {
    text: string;
    profileId: string;
    provider: string;
    model: string;
    quality: string;
    durationMs: number;
    usage?: unknown;
}

export async function checkLlmBackend(): Promise<boolean> {
    const settings = loadLlmSettings();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);

    try {
        const response = await fetch(`${settings.serverUrl}/api/health`, {
            method: 'GET',
            signal: controller.signal,
        });
        return response.ok;
    } catch {
        return false;
    } finally {
        clearTimeout(timeout);
    }
}

export async function generateLlmText(request: GenerateTextRequest): Promise<GenerateTextResponse> {
    const settings = loadLlmSettings();
    const url = `${settings.serverUrl}/api/llm/generate`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);

    let response: Response;
    try {
        response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ...request,
                profileId: settings.providerId,
                quality: settings.quality,
            }),
            signal: controller.signal,
        });
    } catch (error) {
        const rawMessage = error?.message ?? String(error);
        const reason = error?.name === 'AbortError'
            ? '请求超时'
            : `无法连接 LLM 后端 ${settings.serverUrl}`;
        throw new Error(`${reason}。请先在项目目录运行 npm run start:llm，并确认设置里的后端地址正确。原始错误：${rawMessage}`);
    } finally {
        clearTimeout(timeout);
    }

    const raw = await response.text();
    const data = safeJsonParse(raw);
    if (!response.ok) {
        throw new Error(data?.error ?? raw ?? `LLM request failed: ${response.status}`);
    }
    if (!data) {
        throw new Error('LLM 后端返回了无法解析的响应。');
    }

    return data;
}

function safeJsonParse(text: string) {
    try {
        return text ? JSON.parse(text) : {};
    } catch {
        return null;
    }
}
