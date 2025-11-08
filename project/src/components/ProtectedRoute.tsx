// Modified by Cursor integration: 2025-11-07 — added ProtectedRoute for React Router v6
// Detected: app uses react-router v6 (Routes/Route), so this wrapper uses Navigate.
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export default ProtectedRoute;