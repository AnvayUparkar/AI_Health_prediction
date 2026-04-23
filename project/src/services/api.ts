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

// --- Nurse Handoff & Medication APIs ---

export const addMedicine = async (data: any) => {
    const res = await api.post('/api/add-medicine', data);
    return res.data;
};

export const deleteMedicine = async (medId: string | number) => {
    const res = await api.delete(`/api/delete-medicine/${medId}`);
    return res.data;
};

export const getPatientMedicines = async (patientId: any) => {
    const res = await api.get(`/api/patient-medicines`, { params: { patient_id: patientId } });
    return res.data;
};

export const markMedicationGiven = async (logId: any) => {
    const res = await api.patch('/api/mark-given', { log_id: logId });
    return res.data;
};

export const getPendingNotifications = async () => {
    const res = await api.get('/api/pending-notifications');
    return res.data;
};

export const getHandoffReport = async (patientId: any) => {
    const res = await api.get(`/api/handoff-report`, { params: { patient_id: patientId } });
    return res.data;
};

export const updateHandoffReport = async (data: any) => {
    const res = await api.post('/api/handoff-report', data);
    return res.data;
};

export const signup = async (name: string, email: string, password: string, role: string = 'user', certificate?: File) => {
    if (role === 'doctor' && certificate) {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('email', email);
        fd.append('password', password);
        fd.append('role', role);
        fd.append('certificate', certificate);
        const res = await api.post('/auth/signup', fd, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return res.data;
    }
    const res = await api.post('/auth/signup', { name, email, password, role });
    return res.data;
};

export const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
};

// --- Admin & Doctor Verification Endpoints ---

export const getPendingDoctors = async () => {
    const res = await api.get('/api/admin/pending-doctors');
    return res.data;
};

export const getDoctorDetails = async (userId: string | number) => {
    const res = await api.get(`/api/admin/doctor/${userId}`);
    return res.data;
};

export const approveDoctor = async (userId: string | number) => {
    const res = await api.post(`/api/admin/approve/${userId}`);
    return res.data;
};

export const rejectDoctor = async (userId: string | number, reason: string) => {
    const res = await api.post(`/api/admin/reject/${userId}`, { reason });
    return res.data;
};

export const uploadDoctorCertificate = async (file: File) => {
    const fd = new FormData();
    fd.append('certificate', file);
    const res = await api.post('/auth/doctor/upload-certificate', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
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

export const updateAlertStatus = async (alertId: number | string, acknowledged?: boolean, resolved?: boolean, escalate?: boolean) => {
    const updates: any = {};
    if (acknowledged !== undefined) updates.acknowledged = acknowledged;
    if (resolved !== undefined) updates.resolved = resolved;
    if (escalate !== undefined) updates.escalate = escalate;
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

export const updateProfile = async (data: { 
    age?: number; 
    sex?: string; 
    weight?: number; 
    height?: number;
    diet_preference?: string;
    non_veg_preferences?: string[];
    allergies?: string[];
}) => {
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

export const getDoctorsByHospitalId = async (hospitalId: string | number) => {
    const res = await api.get(`/api/hospitals/${hospitalId}/doctors`);
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

export const searchHospitals = async (query: string) => {
    const res = await api.get('/api/hospitals/search', { params: { q: query } });
    return res.data;
};

// --- Admitted Patient Monitoring ---

export const getAdmittedPatients = async () => {
    const res = await api.get('/api/patients/admitted');
    return res.data;
};

export const getPatientMonitoring = async (patientId: number | string, days: number = 7) => {
    const res = await api.get(`/api/patient/${patientId}/monitoring`, { params: { days } });
    return res.data;
};

export const updatePatientMonitoring = async (patientId: number | string, data: {
    time_slot: string;
    glucose?: number;
    bp_systolic?: number;
    bp_diastolic?: number;
    spo2?: number;
    breakfast_done?: boolean;
    lunch_done?: boolean;
    snacks_done?: boolean;
    dinner_done?: boolean;
}) => {
    const res = await api.post(`/api/patient/${patientId}/update-monitoring`, data);
    return res.data;
};

export const getPatientTimeseries = async (patientId: number | string, days: number = 7) => {
    const res = await api.get(`/api/patient/${patientId}/timeseries`, { params: { days } });
    return res.data;
};

export const getAIDietRecommendation = async (patientId: number | string, refresh: boolean = false) => {
    const res = await api.post(`/api/patient/${patientId}/diet-ai`, { refresh });
    return res.data;
};

export const getClinicalCopilotConsult = async (patientId: number | string) => {
    const res = await api.post(`/api/patient/${patientId}/clinical-copilot`);
    return res.data;
};

export const seedMonitoringData = async () => {
    const res = await api.post('/api/monitoring/seed');
    return res.data;
};

// --- Doctor Availability & Sub-slot Booking ---

export const getDoctorAvailability = async (doctorId: string, date: string) => {
    const res = await api.get(`/api/doctor/availability/${doctorId}`, { params: { date } });
    return res.data;
};

export const saveDoctorAvailability = async (data: {
    doctorId: string;
    date: string;
    hours: string[];
    avgConsultationTime: number;
}) => {
    const res = await api.post('/api/doctor/availability', data);
    return res.data;
};

export const bookSubSlot = async (data: {
    doctorId: string;
    date: string;
    slot: { start: string; end: string };
    userId: string;
}) => {
    const res = await api.post('/api/appointment/book', data);
    return res.data;
};

export const getAppointments = async (filters: any = {}) => {
    const res = await api.get('/api/appointments', { params: filters });
    return res.data;
};