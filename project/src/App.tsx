import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import FloatingNavbar from './components/FloatingNavbar';
import Home from './pages/Home';
import Login from './pages/Login'
import Signup from './pages/Signup';
import LungCancer from './pages/LungCancer';
import Diabetes from './pages/Diabetes';
import HeartDisease from './pages/HeartDisease';
import About from './pages/About';
import WhatWeDo from './pages/WhatWeDo';
import BookAppointment from './pages/BookAppointment';
import Predictions from './pages/Predictions';
import DietPlanner from './pages/DietPlanner';
import ReportAnalyzer from './pages/ReportAnalyzer';
import Shop from './pages/Shop';
import Profile from './pages/Profile';
import GoogleCallback from './pages/GoogleCallback';
import AdmittedPatients from './pages/AdmittedPatients';
import PatientMonitoringPage from './pages/PatientMonitoring';
import AdminLogin from './pages/AdminLogin';
import ManageDoctors from './pages/ManageDoctors';
import ManageAppointments from './pages/ManageAppointments';
import ApprovalGuard from './components/ApprovalGuard';
import GamificationWidget from './components/GamificationWidget';
import { AIChatBot } from './components/AIChatBot';
import SOSButton from './components/SOSButton';
import SOSNavigationModal from './components/SOSNavigationModal';
import GestureMonitor from './components/GestureMonitor';
import { Toaster } from 'react-hot-toast';


// ProtectedRoute Component
const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

// MedicalRoute Component - Restricted to doctors, nurses and admins
const MedicalRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');
  if (!token || !userStr) {
    return <Navigate to="/login" replace />;
  }
  try {
    const user = JSON.parse(userStr);
    const role = user.role?.toLowerCase();
    if (role === 'doctor' || role === 'nurse' || role === 'admin') {
      return children;
    }
  } catch (e) {}
  
  return <Navigate to="/" replace />;
};

// AdminRoute Component
const AdminRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');
  if (!token || !userStr) return <Navigate to="/admin-login" replace />;
  try {
    const user = JSON.parse(userStr);
    if (user.role === 'admin') return children;
  } catch (e) {}
  return <Navigate to="/admin-login" replace />;
};

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-transparent">
        <Toaster position="top-right" />
        <FloatingNavbar />
        <GamificationWidget />
        <AIChatBot />
        <SOSButton />
        <SOSNavigationModal />
        <GestureMonitor />

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/google-callback" element={<GoogleCallback />} />
          <Route path="/about" element={<About />} />
          <Route path="/what-we-do" element={<WhatWeDo />} />
          <Route path="/admin-login" element={<AdminLogin />} />
          
          <Route 
            path="/manage-doctors" 
            element={
              <AdminRoute>
                <ManageDoctors />
              </AdminRoute>
            } 
          />
          
          {/* Protected Routes */}
          <Route 
            path="/lung-cancer" 
            element={
              <ProtectedRoute>
                <LungCancer />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/diabetes" 
            element={
              <ProtectedRoute>
                <Diabetes />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/heart-disease" 
            element={
              <ProtectedRoute>
                <HeartDisease />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/book-appointment" 
            element={
              <ProtectedRoute>
                <BookAppointment />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/manage-appointments" 
            element={
              <MedicalRoute>
                <ManageAppointments />
              </MedicalRoute>
            } 
          />
          <Route 
            path="/predictions" 
            element={
              <ProtectedRoute>
                <Predictions />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/diet-planner" 
            element={
              <ProtectedRoute>
                <DietPlanner />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/report-analyzer" 
            element={
              <ProtectedRoute>
                <ReportAnalyzer />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/shop" 
            element={
              <ProtectedRoute>
                <Shop />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admitted-patients" 
            element={
              <MedicalRoute>
                <ApprovalGuard>
                  <AdmittedPatients />
                </ApprovalGuard>
              </MedicalRoute>
            } 
          />
          <Route 
            path="/patient/:patientId/monitor" 
            element={
              <MedicalRoute>
                <ApprovalGuard>
                  <PatientMonitoringPage />
                </ApprovalGuard>
              </MedicalRoute>
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;