import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GoogleOAuthProvider } from '@react-oauth/google';
import App from './App.tsx';
import { SOSProvider } from './context/SOSContext';
import './index.css';

const GOOGLE_CLIENT_ID = "568214587847-unejk0j0bndg6umnv0lg4lt0ph7droug.apps.googleusercontent.com";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <SOSProvider>
        <App />
      </SOSProvider>
    </GoogleOAuthProvider>
  </StrictMode>
);
