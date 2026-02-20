import api from '@/lib/api';

export interface SourceCitation {
    page: number;
    chunk_id: string;
    snippet: string;
}

export interface ChatResponse {
    answer: string;
    sources: SourceCitation[];
    grounded: boolean;
    doc_id: string;
    timestamp: string;
}

export interface ChatHistoryItem {
    question: string;
    answer: string;
    sources: SourceCitation[];
    timestamp: string;
}

export const chatService = {
    async sendMessage(docId: string, question: string) {
        const response = await api.post<ChatResponse>(`/chat/${docId}`, { question });
        return response.data;
    },

    async getHistory(docId: string) {
        const response = await api.get<ChatHistoryItem[]>(`/chat/${docId}/history`);
        return response.data;
    },

    async clearMemory(docId: string) {
        await api.delete(`/chat/${docId}/memory`);
    }
};
