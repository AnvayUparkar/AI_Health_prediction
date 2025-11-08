// Modified by Cursor integration: 2025-11-07 — use AxiosProgressEvent type for upload progress callback to satisfy TS.
import axios, { type AxiosProgressEvent } from 'axios';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json'
    },
    withCredentials: false
});

// Attach token from localStorage to every request if present
api.interceptors.request.use((cfg) => {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || localStorage.getItem('auth_token');
    if (token) {
        cfg.headers = cfg.headers || {};
        cfg.headers['Authorization'] = `Bearer ${token}`;
    }
    return cfg;
});

export default api;

export const signup = async (name: string, email: string, password: string) => {
    const res = await api.post('/auth/signup', { name, email, password });
    return res.data;
};

export const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
};

export const predict = async (type: 'lung_cancer' | 'diabetes', features: Record<string, any>) => {
    const res = await api.post('/api/predict', { type, features });
    return res.data;
};

// Use AxiosProgressEvent type so the onUploadProgress callback type matches axios expectations
export const uploadReport = async (file: File, onUploadProgress?: (progressEvent: AxiosProgressEvent) => void) => {
    const fd = new FormData();
    fd.append('report', file);
    const res = await api.post('/api/upload-report', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress
    });
    return res.data;
};

export const getWorkoutPlan = async (goal?: string, level?: string) => {
    const params: any = {};
    if (goal) params.goal = goal;
    if (level) params.level = level;
    const res = await api.get('/api/workout-plan', { params });
    return res.data;
};