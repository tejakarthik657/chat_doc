import api from '@/lib/api';

export interface DocumentOut {
    id: string;
    filename: string;
    size_mb: number;
    page_count: number;
    uploaded_at: string;
    status: 'processing' | 'ready' | 'error';
}

export interface DocumentList {
    documents: DocumentOut[];
    total_storage_mb: number;
    storage_limit_mb: number;
}

export const documentService = {
    async list() {
        const response = await api.get<DocumentList>('/documents');
        return response.data;
    },

    async get(docId: string) {
        const response = await api.get<DocumentOut>(`/documents/${docId}`);
        return response.data;
    },

    async upload(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        // Config for file upload
        const config = {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        };

        const response = await api.post<DocumentOut>('/documents/upload', formData, config);
        return response.data;
    },

    async delete(docId: string) {
        await api.delete(`/documents/${docId}`);
    }
};
