import api from '@/lib/api';

export interface UserLogin {
    email: string;
    password: string;
}

export interface UserRegister {
    email: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

export interface UserOut {
    id: string;
    email: string;
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
        const response = await api.get<UserOut>('/auth/me');
        return response.data;
    },

    logout() {
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
};
