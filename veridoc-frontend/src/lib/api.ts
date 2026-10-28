import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// ── In-Memory Fast Cache & In-Flight Request Deduplication ───────────────────────
interface CacheEntry {
    timestamp: number;
    data: any;
}

const memoryCache = new Map<string, CacheEntry>();
const inFlightRequests = new Map<string, Promise<any>>();
const DEFAULT_TTL_MS = 8000; // 8-second fast read cache for snappy tab switches

// Safe endpoints eligible for deduplication and short-term caching
const CACHEABLE_ROUTES = [
    '/auth/me',
    '/analytics/summary',
    '/projects',
    '/documents',
];

export function invalidateApiCache(urlPrefix?: string) {
    if (!urlPrefix) {
        memoryCache.clear();
        return;
    }
    for (const key of memoryCache.keys()) {
        if (key.includes(urlPrefix)) {
            memoryCache.delete(key);
        }
    }
}

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,    // 30s for general API calls
    headers: {
        'Content-Type': 'application/json',
    },
});

// Dedicated instance for chat endpoints — needs longer timeout (LLM generation can take 5–15s)
export const chatApi = axios.create({
    baseURL: BASE_URL,
    timeout: 60000,    // 60s for chat/RAG requests
    headers: {
        'Content-Type': 'application/json',
    },
});

// Apply auth + 401 handling + deduplication + cache to instances
function applyInterceptors(instance: AxiosInstance) {
    instance.interceptors.request.use(
        (config: InternalAxiosRequestConfig) => {
            const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }

            // Invalidate cache on mutations
            const method = (config.method || 'get').toLowerCase();
            if (['post', 'put', 'delete', 'patch'].includes(method)) {
                const url = config.url || '';
                if (url.includes('/projects')) invalidateApiCache('/projects');
                if (url.includes('/documents')) invalidateApiCache('/documents');
                if (url.includes('/echo')) invalidateApiCache('/echo');
            }

            return config;
        },
        (error) => Promise.reject(error)
    );

    instance.interceptors.response.use(
        (response) => {
            // Cache successful GET responses for exact cacheable routes
            const method = (response.config.method || 'get').toLowerCase();
            const url = response.config.url || '';
            const isCacheable = CACHEABLE_ROUTES.some(route => url === route || url.endsWith(route) || url.endsWith(`${route}/`));
            if (method === 'get' && isCacheable) {
                memoryCache.set(url, {
                    timestamp: Date.now(),
                    data: response.data
                });
            }
            return response;
        },
        (error) => {
            if (error.response?.status === 401) {
                if (typeof window !== 'undefined') {
                    localStorage.removeItem('token');
                    invalidateApiCache();
                    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
                        window.location.href = '/login';
                    }
                }
            }
            return Promise.reject(error);
        }
    );
}

applyInterceptors(api);
applyInterceptors(chatApi);

// ── Fast Cached GET helper ───────────────────────────────────────────────────
export async function fastGet<T = any>(url: string, params?: any, customTtlMs?: number): Promise<T> {
    const ttl = customTtlMs ?? DEFAULT_TTL_MS;
    const cacheKey = params ? `${url}?${JSON.stringify(params)}` : url;
    const cached = memoryCache.get(cacheKey);

    // Return instant cached data if fresh
    if (cached && (Date.now() - cached.timestamp < ttl)) {
        return cached.data as T;
    }

    // Deduplicate in-flight requests (avoids double-fetching when multiple components mount)
    if (inFlightRequests.has(cacheKey)) {
        return inFlightRequests.get(cacheKey) as Promise<T>;
    }

    const requestPromise = api.get<T>(url, { params })
        .then(res => {
            memoryCache.set(cacheKey, { timestamp: Date.now(), data: res.data });
            inFlightRequests.delete(cacheKey);
            return res.data;
        })
        .catch(err => {
            inFlightRequests.delete(cacheKey);
            throw err;
        });

    inFlightRequests.set(cacheKey, requestPromise);
    return requestPromise;
}

export default api;
