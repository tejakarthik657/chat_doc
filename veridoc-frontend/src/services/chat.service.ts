import api from '@/lib/api';

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
}

export interface ChatHistoryItem {
    question: string;
    answer: string;
    sources: SourceCitation[];
    timestamp: string;
}

export const chatService = {
    async sendMessage(docId: string, question: string, strictMode = false) {
        const response = await api.post<ChatResponse>(`/chat/${docId}`, { question, strict_mode: strictMode });
        return response.data;
    },

    async getHistory(docId: string) {
        const response = await api.get<ChatHistoryItem[]>(`/chat/${docId}/history`);
        return response.data;
    },

    async clearMemory(docId: string) {
        await api.delete(`/chat/${docId}/memory`);
    },

    // ── Projects Chat API Callers ──
    async sendMessageProject(projectId: string, question: string, strictMode = false, scopedSources?: string[]) {
        const response = await api.post<ChatResponse>(`/chat/project/${projectId}`, { 
            question, 
            strict_mode: strictMode,
            scoped_sources: scopedSources
        });
        return response.data;
    },

    async getHistoryProject(projectId: string) {
        const response = await api.get<ChatHistoryItem[]>(`/chat/project/${projectId}/history`);
        return response.data;
    },

    async clearMemoryProject(projectId: string) {
        await api.delete(`/chat/project/${projectId}/memory`);
    }
};
