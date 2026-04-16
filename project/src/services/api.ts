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

export const signup = async (name: string, email: string, password: string, role: string = 'user') => {
    const res = await api.post('/auth/signup', { name, email, password, role });
    return res.data;
};

export const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
};

export const predict = async (type: 'lung_cancer' | 'diabetes' | 'heart_disease', features: Record<string, any>) => {
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

// --- Alert System Endpoints ---

export const getAlerts = async (filters: { patient_id?: string; status?: string; alert?: boolean } = {}) => {
    const res = await api.get('/api/alerts', { params: filters });
    return res.data;
};

export const updateAlertStatus = async (alertId: number | string, acknowledged?: boolean, resolved?: boolean) => {
    const updates: any = {};
    if (acknowledged !== undefined) updates.acknowledged = acknowledged;
    if (resolved !== undefined) updates.resolved = resolved;
    const res = await api.patch(`/api/alerts/${alertId}`, updates);
    return res.data;
};

export const postMonitoringData = async (data: any) => {
    const res = await api.post('/api/alert/data', data);
    return res.data;
};

// --- Gamification Endpoints ---

export const updateSteps = async (steps: number) => {
    const res = await api.post('/api/steps/update', { steps });
    return res.data;
};

export const getShopItems = async () => {
    const res = await api.get('/api/shop');
    return res.data;
};

export const buyItem = async (itemId: number) => {
    const res = await api.post('/api/shop/buy', { itemId });
    return res.data;
};

export const getWorkoutPlan = async (goal?: string, level?: string) => {
    const params: any = {};
    if (goal) params.goal = goal;
    if (level) params.level = level;
    const res = await api.get('/api/workout-plan', { params });
    return res.data;
};

export const analyzeReport = async (file: File | null, onUploadProgress?: (progressEvent: AxiosProgressEvent) => void, healthData?: any) => {
    const fd = new FormData();
    if (file) fd.append('report', file);
    if (healthData) fd.append('health_data', JSON.stringify(healthData));
    const res = await api.post('/api/analyze-report', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress,
        timeout: 120000,  // 2 min timeout for OCR processing
    });
    return res.data;
};

export const triggerSOS = async (data: { patient_id?: string; room_number?: string; latitude?: number; longitude?: number } = {}) => {
    const res = await api.post('/api/alert/sos', data);
    return res.data;
};

export const getNearestHospital = async (lat: number, lng: number) => {
    const res = await api.get('/api/nearest-hospital', { params: { lat, lng } });
    return res.data;
};

// --- Profile & User Management ---

export const getProfile = async () => {
    const res = await api.get('/auth/profile');
    return res.data;
};

export const updateProfile = async (data: { age?: number; sex?: string; weight?: number; height?: number }) => {
    const res = await api.put('/auth/profile', data);
    return res.data;
};

export const searchUsers = async (query: string) => {
    const res = await api.get('/auth/users/search', { params: { q: query } });
    return res.data;
};

export const updatePatientProfile = async (userId: string | number, data: { hospitals: string[] }) => {
    const res = await api.put(`/auth/users/${userId}/profile`, data);
    return res.data;
};

export const getDoctorsByHospital = async (hospitalName: string) => {
    const res = await api.get('/auth/doctors/by-hospital', { params: { hospital: hospitalName } });
    return res.data;
};

// --- Doctor Appointment Management ---

export const getDoctorAppointments = async (doctorId: string | number, status?: string) => {
    const params = status ? { status } : {};
    const res = await api.get(`/api/doctor_appointments/doctor/${doctorId}`, { params });
    return res.data;
};

export const approveAppointment = async (id: string | number) => {
    const res = await api.post(`/api/doctor_appointments/${id}/approve`);
    return res.data;
};

export const rejectAppointment = async (id: string | number, suggestedDates: string[], suggestedTimes: string[]) => {
    const res = await api.post(`/api/doctor_appointments/${id}/reject`, {
        suggested_dates: suggestedDates,
        suggested_times: suggestedTimes
    });
    return res.data;
};

export const updateAppointmentClinicalStatus = async (id: string | number, isChecked?: boolean, isAdmitted?: boolean) => {
    const res = await api.patch(`/api/doctor_appointments/${id}/update-status`, {
        isChecked,
        isAdmitted
    });
    return res.data;
};

export const deleteAppointment = async (id: string | number) => {
    const res = await api.delete(`/api/doctor_appointments/${id}/delete`);
    return res.data;
};

export const assignWard = async (appointmentId: string | number, wardNumber: string) => {
    const res = await api.post(`/api/doctor_appointments/${appointmentId}/assign-ward`, { ward_number: wardNumber });
    return res.data;
};

// --- Meal Plan & Export ---

export const getMealPlan = async () => {
    const res = await api.get('/api/meal-plan');
    return res.data;
};

export const exportHealthReport = async () => {
    const res = await api.post('/api/export-report', {}, { responseType: 'blob' });
    return res.data;
};

export const exportReportAnalysis = async (analysisData: any) => {
    const res = await api.post('/api/export-report-analysis', analysisData, { responseType: 'blob' });
    return res.data;
};