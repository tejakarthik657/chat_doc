import api, { fastGet, invalidateApiCache } from '@/lib/api';

export interface UserLogin {
    email: string;
    password: string;
}

export interface UserRegister {
    email: string;
    password: string;
    name?: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

export interface UserOut {
    id: string;
    email: string;
    name?: string;
    auth_provider?: string;
    plan: string;
    storage_used_mb: number;
    created_at: string;
}

export const authService = {
    async login(credentials: UserLogin) {
        const response = await api.post<TokenResponse>('/auth/login', credentials);
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
        }
        return response.data;
    },

    async register(data: UserRegister) {
        const response = await api.post<TokenResponse>('/auth/register', data);
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
        }
        return response.data;
    },

    async getMe() {
        return await fastGet<UserOut>('/auth/me');
    },

    async updateProfile(name: string) {
        const response = await api.patch<UserOut>('/auth/me', { name });
        invalidateApiCache('/auth/me');
        return response.data;
    },

    async changePassword(current_password: string, new_password: string) {
        const response = await api.post<{ status: string }>('/auth/change-password', {
            current_password,
            new_password,
        });
        return response.data;
    },

    logout() {
        localStorage.removeItem('token');
        invalidateApiCache();
        window.location.href = '/login';
    }
};
