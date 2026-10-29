import api, { fastGet, invalidateApiCache } from '@/lib/api';

export interface ProjectOut {
    id: string;
    name: string;
    website_url: string;
    created_at: string;
    status: 'active' | 'crawling' | 'indexing' | 'error' | 'paused';
    pages_crawled: number;
    docs_found: number;
    use_dynamic_crawl?: boolean;
    sitemap_url?: string;
    login_url?: string;
    login_username?: string;
    login_password?: string;
    error_message?: string;
}

export interface ProjectCreate {
    name: string;
    website_url: string;
    max_pages?: number;
    use_dynamic_crawl?: boolean;
    sitemap_url?: string;
    login_url?: string;
    login_username?: string;
    login_password?: string;
}

export interface ProjectList {
    projects: ProjectOut[];
}

export interface CrawlJobOut {
    id: string;
    project_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    urls_found: number;
    urls_processed: number;
    pages_crawled?: number;
    docs_found?: number;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
}

export const projectService = {
    async list() {
        return await fastGet<ProjectList>('/projects', undefined, 6000);
    },

    async get(projectId: string) {
        return await fastGet<ProjectOut>(`/projects/${projectId}`, undefined, 4000);
    },

    async create(project: ProjectCreate) {
        invalidateApiCache('/projects');
        const response = await api.post<ProjectOut>('/projects/create', project);
        return response.data;
    },

    async delete(projectId: string) {
        invalidateApiCache('/projects');
        await api.delete(`/projects/${projectId}`);
    },

    async getCrawlStatus(projectId: string) {
        const response = await api.get<CrawlJobOut>(`/projects/${projectId}/crawl-status`);
        return response.data;
    },

    async getInventory(projectId: string) {
        const response = await api.get<{ web_pages: { url: string; title: string }[]; pdfs: { url: string; title: string }[] }>(`/projects/${projectId}/inventory`);
        return response.data;
    },

    async pauseCrawl(projectId: string) {
        const response = await api.post<{ status: string }>(`/projects/${projectId}/pause`);
        return response.data;
    },

    async resumeCrawl(projectId: string) {
        const response = await api.post<CrawlJobOut>(`/projects/${projectId}/resume`);
        return response.data;
    }
};
