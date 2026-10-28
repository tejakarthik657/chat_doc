import api, { chatApi } from '@/lib/api';

export interface SourceCitation {
    page: number;
    chunk_id: string;
    snippet: string;
    url?: string;
    source_name?: string;
}

export interface ChatResponse {
    answer: string;
    sources: SourceCitation[];
    grounded: boolean;
    doc_id: string;
    timestamp: string;
    support_label?: string;
    support_confidence?: number;
    support_snippet?: string;
    evidence_trace?: any[];
    mode?: string;
    artifact?: any;
    mindspace_nodes?: any[];
}

export interface ChatHistoryItem {
    question: string;
    answer: string;
    sources: SourceCitation[];
    timestamp: string;
}

export const chatService = {
    async sendMessage(docId: string, question: string, strictMode = false) {
        // Use chatApi (60s timeout) — LLM generation takes 3–15s
        const response = await chatApi.post<ChatResponse>(`/chat/${docId}`, { question, strict_mode: strictMode });
        return response.data;
    },

    async askGeneralAI(question: string, docId = "general", contextHint?: string) {
        // Direct World Knowledge LLM query without document restrictions
        const response = await chatApi.post<ChatResponse>(`/chat/${docId}/general`, {
            question,
            doc_id: docId,
            context_hint: contextHint
        });
        return response.data;
    },

    async getHistory(docId: string) {
        if (!docId || docId === "onboarding") {
            return [];
        }
        try {
            const response = await api.get<ChatHistoryItem[]>(`/chat/${docId}/history`);
            return response.data;
        } catch (err: any) {
            if (err?.response?.status === 404) {
                return [];
            }
            throw err;
        }
    },

    async clearMemory(docId: string) {
        if (!docId || docId === "onboarding") return;
        try {
            await api.delete(`/chat/${docId}/memory`);
        } catch (err: any) {
            if (err?.response?.status !== 404) throw err;
        }
    },

    // ── Projects Chat API Callers ──
    async sendMessageProject(projectId: string, question: string, strictMode = false, scopedSources?: string[], mode: string = "standard") {
        // Use chatApi (60s timeout) — LLM generation takes 3–15s
        const response = await chatApi.post<ChatResponse>(`/chat/project/${projectId}`, { 
            question, 
            strict_mode: strictMode,
            scoped_sources: scopedSources,
            mode: mode
        });
        return response.data;
    },

    async getHistoryProject(projectId: string) {
        if (!projectId || projectId === "onboarding") {
            return [];
        }
        try {
            const response = await api.get<ChatHistoryItem[]>(`/chat/project/${projectId}/history`);
            return response.data;
        } catch (err: any) {
            if (err?.response?.status === 404) {
                return [];
            }
            throw err;
        }
    },

    async clearMemoryProject(projectId: string) {
        if (!projectId || projectId === "onboarding") return;
        try {
            await api.delete(`/chat/project/${projectId}/memory`);
        } catch (err: any) {
            if (err?.response?.status !== 404) throw err;
        }
    }
};
