import React, { createContext, useContext, useState, useEffect } from 'react';
import io from 'socket.io-client';

export interface SOSState {
  isActive: boolean;
  isMinimized: boolean;
  isResolved: boolean;
  userCoords: { lat: number; lng: number } | null;
  startedAt: number | null;
}

interface SOSContextType {
  sosState: SOSState;
  activateSOS: (lat: number, lng: number) => void;
  minimizeSOS: () => void;
  restoreSOS: () => void;
  resolveSOS: () => void;
  closeSOS: () => void;
}

const defaultState: SOSState = {
  isActive: false,
  isMinimized: false,
  isResolved: false,
  userCoords: null,
  startedAt: null,
};

const SOSContext = createContext<SOSContextType | null>(null);

export const useSOSContext = () => {
  const context = useContext(SOSContext);
  if (!context) {
    throw new Error('useSOSContext must be used within an SOSProvider');
  }
  return context;
};

export const SOSProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sosState, setSosState] = useState<SOSState>(() => {
    try {
      const saved = localStorage.getItem('sos_state');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Could not read SOS state from localStorage', e);
    }
    return defaultState;
  });

  // Persist state to localStorage on changes
  useEffect(() => {
    localStorage.setItem('sos_state', JSON.stringify(sosState));
  }, [sosState]);

  // Connect to websocket when SOS is active
  useEffect(() => {
    if (!sosState.isActive) return;

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
    const socket = io(API_URL);

    socket.on('connect', () => {
      console.log('[SOSContext] WebSocket connected');
    });

    socket.on('SOS_RESOLVED', (data) => {
      console.log('[SOSContext] Received SOS_RESOLVED event from backend', data);
      resolveSOS();
    });

    return () => {
      socket.disconnect();
    };
  }, [sosState.isActive]);

  const activateSOS = (lat: number, lng: number) => {
    setSosState({
      isActive: true,
      isMinimized: false,
      isResolved: false,
      userCoords: { lat, lng },
      startedAt: Date.now(),
    });
  };

  const minimizeSOS = () => {
    setSosState((prev) => ({ ...prev, isMinimized: true }));
  };

  const restoreSOS = () => {
    setSosState((prev) => ({ ...prev, isMinimized: false }));
  };

  const resolveSOS = () => {
    setSosState({
      ...defaultState,
      isResolved: true,
    });
  };

  const closeSOS = () => {
    setSosState(defaultState);
  };

  return (
    <SOSContext.Provider
      value={{
        sosState,
        activateSOS,
        minimizeSOS,
        restoreSOS,
        resolveSOS,
        closeSOS,
      }}
    >
      {children}
    </SOSContext.Provider>
  );
};
