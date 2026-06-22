import api from '@/lib/api';

export interface DocumentInsights {
    doc_id: string;
    filename: string;
    document_type: string;
    document_type_confidence: number;
    summary: string;
    keyphrases: string[];
    entities: Record<string, string[]>;
    readability_band: string;
    outlier_sections: { section_index: number; anomaly_score: number; snippet: string }[];
    suggested_questions: string[];
}

export interface VerifyAnswerResponse {
    label: 'supported' | 'partially_supported' | 'weak_support' | 'insufficient' | string;
    confidence: number;
    best_snippet: string;
}

export const featuresService = {
    async getInsights(docId: string) {
        const response = await api.get<DocumentInsights>(`/features/${docId}/insights`);
        return response.data;
    },

    async verifyAnswer(docId: string, answer: string) {
        const response = await api.post<VerifyAnswerResponse>(`/features/${docId}/verify`, { answer });
        return response.data;
    },

    async rewriteSimple(text: string, style: 'simple' | 'professional' = 'simple') {
        const response = await api.post<{ rewritten_text: string }>(`/features/rewrite`, { text, style });
        return response.data;
    },
};
