import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import FloatingNavbar from './components/FloatingNavbar';
import Home from './pages/Home';
import Login from './pages/Login'
import Signup from './pages/Signup';
import LungCancer from './pages/LungCancer';
import Diabetes from './pages/Diabetes';
import About from './pages/About';
import WhatWeDo from './pages/WhatWeDo';
import BookAppointment from './pages/BookAppointment';
import Predictions from './pages/Predictions';
import DietPlanner from './pages/DietPlanner';

// ProtectedRoute Component
const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <FloatingNavbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/about" element={<About />} />
          <Route path="/what-we-do" element={<WhatWeDo />} />
          
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
            path="/book-appointment" 
            element={
              <ProtectedRoute>
                <BookAppointment />
              </ProtectedRoute>
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
        </Routes>
      </div>
    </Router>
  );
}

export default App;