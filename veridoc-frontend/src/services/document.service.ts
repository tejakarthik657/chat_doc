import api, { fastGet, invalidateApiCache } from '@/lib/api';

export interface DocumentOut {
    id: string;
    filename: string;
    size_mb: number;
    page_count: number;
    uploaded_at: string;
    status: 'processing' | 'ready' | 'error';
    error_message?: string;
}

export interface DocumentList {
    documents: DocumentOut[];
    total_storage_mb: number;
    storage_limit_mb: number;
}

export const documentService = {
    async list() {
        return await fastGet<DocumentList>('/documents', undefined, 6000);
    },

    async get(docId: string) {
        return await fastGet<DocumentOut>(`/documents/${docId}`, undefined, 6000);
    },

    async upload(file: File) {
        invalidateApiCache('/documents');
        const formData = new FormData();
        formData.append('file', file);

        const config = {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 60000,
        };

        const response = await api.post<DocumentOut>('/documents/upload', formData, config);
        return response.data;
    },

    async delete(docId: string) {
        invalidateApiCache('/documents');
        await api.delete(`/documents/${docId}`);
    }
};
