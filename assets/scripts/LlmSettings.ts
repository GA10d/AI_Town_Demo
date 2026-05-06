import { sys } from 'cc';

export type LlmQuality = 'fast' | 'standard';

export interface PlayerLlmSettings {
    providerId: string;
    quality: LlmQuality;
    serverUrl: string;
}

export const LLM_SETTINGS_KEY = 'aitown-llm-settings';

export const LLM_PROVIDER_OPTIONS = [
    { id: 'chatgpt', label: 'ChatGPT' },
    { id: 'deepseek', label: 'DeepSeek' },
    { id: 'gemini', label: 'Gemini' },
    { id: 'doubao', label: 'Doubao' },
    { id: 'qwen', label: 'Qwen' },
    { id: 'custom-openai-compatible', label: 'Custom' },
];

export const LLM_QUALITY_OPTIONS: Array<{ id: LlmQuality; label: string }> = [
    { id: 'fast', label: 'Fast' },
    { id: 'standard', label: 'Standard' },
];

export function loadLlmSettings(): PlayerLlmSettings {
    const defaults: PlayerLlmSettings = {
        providerId: 'chatgpt',
        quality: 'standard',
        serverUrl: 'http://127.0.0.1:8787',
    };

    const raw = sys.localStorage.getItem(LLM_SETTINGS_KEY);
    if (!raw) {
        return defaults;
    }

    try {
        return { ...defaults, ...JSON.parse(raw) };
    } catch {
        return defaults;
    }
}

export function saveLlmSettings(settings: PlayerLlmSettings) {
    sys.localStorage.setItem(LLM_SETTINGS_KEY, JSON.stringify(settings));
}
