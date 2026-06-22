import api from '@/lib/api';

export interface ClusterSummary {
    cluster_id: number;
    label: string;
    question_count: number;
    sample_questions: string[];
}

export interface RecentActivityItem {
    id: string;
    question: string;
    document_filename: string;
    timestamp: string;
    citation_count: number;
}

export interface AnalyticsSummary {
    total_documents: number;
    total_questions: number;
    questions_today: number;
    daily_limit: number;
    top_clusters: ClusterSummary[];
    storage_used_mb: number;
    questions_by_day: { day: string, count: number, isToday: boolean }[];
    questions_by_document: { name: string, count: number }[];
    recent_activity: RecentActivityItem[];
}

export const analyticsService = {
    async getSummary() {
        const response = await api.get<AnalyticsSummary>('/analytics/summary');
        return response.data;
    }
};
