import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Hand, X, Maximize2, Minimize2, AlertTriangle } from 'lucide-react';
import { io, Socket } from 'socket.io-client';

const GestureMonitor: React.FC = () => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const socketRef = useRef<Socket | null>(null);

    const [isActive, setIsActive] = useState(false);
    const [status, setStatus] = useState<'idle' | 'detecting' | 'fist'>('idle');
    const [isExpanded, setIsExpanded] = useState(false);
    const [handDetected, setHandDetected] = useState(false);
    const [userName, setUserName] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [sosFired, setSosFired] = useState(false);      // NEW: tracks SOS-triggered state
    const [sosCount, setSosCount] = useState(0);          // NEW: how many times triggered
    const [coords, setCoords] = useState<{lat: number, lon: number} | null>(null);

    // ── Auth check ────────────────────────────────────────────────────────────
    useEffect(() => {
        const checkAuth = () => {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                try {
                    const user = JSON.parse(userStr);
                    setIsAuthenticated(true);
                    setUserName(user.name || 'User');
                } catch {
                    setIsAuthenticated(false);
                }
            } else {
                setIsAuthenticated(false);
            }
        };
        checkAuth();
        window.addEventListener('storage', checkAuth);
        return () => window.removeEventListener('storage', checkAuth);
    }, []);

    // ── Socket setup (once, on mount) ─────────────────────────────────────────
    useEffect(() => {
        const socket = io('http://localhost:5000', {
            transports: ['websocket'],
            reconnectionAttempts: 5,
        });
        socketRef.current = socket;

        socket.on('gesture_result', (data) => {
            setHandDetected(data.hand_detected);

            if (data.gesture === 'CLOSED') {
                setStatus('fist');
            } else if (data.hand_detected) {
                setStatus('detecting');
            } else {
                setStatus('idle');
            }
        });

        // NEW: listen for the SOS event the backend emits after clench sequence
        socket.on('new_alert', (data) => {
            if (
                data?.reason?.includes('GESTURE') ||
                data?.reason?.includes('FIST')
            ) {
                setSosFired(true);
                setSosCount(prev => prev + 1);
                // Auto-reset SOS banner after 6 seconds
                setTimeout(() => setSosFired(false), 6000);
            }
        });

        return () => {
            socket.off('gesture_result');
            socket.off('new_alert');
            socket.disconnect();
        };
    }, []);

    // ── Camera setup ─────────────────────────────────────────────────────────
    // FIX: We render video/canvas always (hidden) so refs are available immediately.
    // Previously the video element only mounted AFTER isActive=true (inside AnimatePresence),
    // causing a race: the stream was assigned before the DOM element existed.
    const startCamera = async () => {
        setError(null);
        setSosFired(false);

        // Capture GPS location once per session for Remote SOS integration
        try {
            navigator.geolocation.getCurrentPosition(
                (pos) => setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
                (err) => console.warn('[Gesture] Geolocation failed:', err),
                { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
            );
        } catch (e) {
            console.warn('[Gesture] Browser does not support geolocation', e);
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 320, height: 240, frameRate: 10 },
            });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                // Wait for metadata before marking active so the first frame isn't blank
                videoRef.current.onloadedmetadata = () => {
                    videoRef.current?.play();
                    setIsActive(true);
                };
            }
        } catch (err: any) {
            console.error('Camera error:', err);
            setError(err.message || 'Camera access denied');
            setIsActive(false);
        }
    };

    const stopCamera = () => {
        if (videoRef.current?.srcObject) {
            (videoRef.current.srcObject as MediaStream)
                .getTracks()
                .forEach(t => t.stop());
            videoRef.current.srcObject = null;
        }
        setIsActive(false);
        setStatus('idle');
        setHandDetected(false);
        setSosFired(false);
        setCoords(null);
    };

    // ── Frame capture loop ────────────────────────────────────────────────────
    // FIX: canvas dimensions now match the video stream (320×240)
    const captureFrame = useCallback(() => {
        const socket = socketRef.current;
        if (!isActive || !videoRef.current || !canvasRef.current || !socket) return;

        const canvas = canvasRef.current;
        const video = videoRef.current;
        const ctx = canvas.getContext('2d');

        if (ctx && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frameData = canvas.toDataURL('image/jpeg', 0.6);

            socket.emit('gesture_frame', {
                frame: frameData,
                info: {
                    patient_id: userName || 'GUEST',
                    room_number: 'WEB_INTERFACE',
                    latitude: coords?.lat,
                    longitude: coords?.lon
                },
            });
        }
    }, [isActive, userName, coords]);

    useEffect(() => {
        if (!isActive) return;
        const interval = setInterval(captureFrame, 200); // 5 FPS
        return () => clearInterval(interval);
    }, [isActive, captureFrame]);

    // ─────────────────────────────────────────────────────────────────────────
    if (!isAuthenticated) return null;

    return (
        <>
            {/* Hidden-but-always-mounted video & canvas so refs are never null */}
            <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{ display: 'none' }}
            />
            {/* FIX: canvas now 320×240 to match stream resolution */}
            <canvas ref={canvasRef} width={320} height={240} style={{ display: 'none' }} />

            <div className="fixed top-24 left-6 z-[60] flex items-start space-x-4">

                {/* ── Toggle button ── */}
                <div className="flex flex-col items-start space-y-2">
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => (isActive ? stopCamera() : startCamera())}
                        className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg group relative transition-colors duration-300 ${isActive
                                ? 'bg-red-500'
                                : 'bg-gradient-to-br from-blue-500 to-purple-600'
                            }`}
                    >
                        {isActive ? (
                            <X className="h-6 w-6 text-white" />
                        ) : (
                            <Camera className="h-6 w-6 text-white" />
                        )}
                        <div className="absolute left-full ml-4 px-3 py-1 bg-white rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                            <span className="text-xs font-bold text-gray-700">
                                {isActive ? 'Stop Monitoring' : 'Enable Gesture SOS'}
                            </span>
                        </div>
                    </motion.button>

                    {error && (
                        <motion.span
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="bg-red-500 text-white text-[10px] px-2 py-1 rounded-lg shadow-lg font-bold max-w-[56px] text-center"
                        >
                            {error}
                        </motion.span>
                    )}
                </div>

                {/* ── Camera panel ── */}
                <AnimatePresence>
                    {isActive && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.8, x: -20 }}
                            animate={{ opacity: 1, scale: 1, x: 0 }}
                            exit={{ opacity: 0, scale: 0.8, x: -20 }}
                            // FIX: pointer-events-auto so overlay buttons inside are clickable
                            className={`
                                relative bg-gray-900 rounded-3xl overflow-hidden shadow-2xl border-4
                                pointer-events-auto transition-all duration-500
                                ${isExpanded ? 'w-80 h-60' : 'w-52 h-40'}
                                ${sosFired
                                    ? 'border-red-500 shadow-[0_0_40px_rgba(239,68,68,0.8)]'
                                    : status === 'fist'
                                        ? 'border-orange-400 shadow-[0_0_20px_rgba(251,146,60,0.5)]'
                                        : 'border-white/20'
                                }
                            `}
                        >
                            {/* Live video — this div mirrors the always-hidden <video> */}
                            {/* We use a second video element visible inside the panel */}
                            <VideoMirror srcObject={
                                videoRef.current?.srcObject as MediaStream | null
                            } />

                            {/* Status badge */}
                            <div className="absolute top-3 left-3 flex items-center space-x-1.5">
                                <div
                                    className={`w-2 h-2 rounded-full animate-pulse ${sosFired
                                            ? 'bg-red-400'
                                            : handDetected
                                                ? 'bg-green-400'
                                                : 'bg-yellow-400'
                                        }`}
                                />
                                <span className="text-[9px] font-bold text-white uppercase tracking-widest bg-black/50 px-2 py-0.5 rounded-full backdrop-blur-sm">
                                    {sosFired
                                        ? `SOS SENT (${sosCount})`
                                        : status === 'fist'
                                            ? 'FIST DETECTED'
                                            : handDetected
                                                ? 'MONITORING'
                                                : 'SCANNING…'}
                                </span>
                            </div>

                            {/* Controls */}
                            <div className="absolute bottom-3 right-3 flex items-center space-x-1">
                                <button
                                    onClick={() => setIsExpanded(e => !e)}
                                    className="p-1.5 bg-white/10 hover:bg-white/20 rounded-lg backdrop-blur-md transition-colors"
                                >
                                    {isExpanded ? (
                                        <Minimize2 className="h-3.5 w-3.5 text-white" />
                                    ) : (
                                        <Maximize2 className="h-3.5 w-3.5 text-white" />
                                    )}
                                </button>
                                <button
                                    onClick={stopCamera}
                                    className="p-1.5 bg-red-500/80 hover:bg-red-600 rounded-lg backdrop-blur-md transition-colors"
                                >
                                    <X className="h-3.5 w-3.5 text-white" />
                                </button>
                            </div>

                            {/* Fist overlay */}
                            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                                <AnimatePresence>
                                    {status === 'fist' && !sosFired && (
                                        <motion.div
                                            key="fist"
                                            initial={{ scale: 0.5, opacity: 0 }}
                                            animate={{ scale: 1.1, opacity: 1 }}
                                            exit={{ scale: 1.4, opacity: 0 }}
                                            className="bg-orange-500/80 p-4 rounded-full"
                                        >
                                            <Hand className="h-8 w-8 text-white fill-current" />
                                        </motion.div>
                                    )}
                                    {sosFired && (
                                        <motion.div
                                            key="sos"
                                            initial={{ scale: 0.5, opacity: 0 }}
                                            animate={{ scale: [1, 1.15, 1], opacity: 1 }}
                                            transition={{ repeat: Infinity, duration: 0.8 }}
                                            className="bg-red-600/90 px-4 py-3 rounded-2xl flex flex-col items-center gap-1"
                                        >
                                            <AlertTriangle className="h-6 w-6 text-white" />
                                            <span className="text-white text-[10px] font-black tracking-widest">
                                                SOS SENT
                                            </span>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Hint label at bottom-left */}
                            <div className="absolute bottom-3 left-3">
                                <span className="text-[8px] text-white/50 font-medium">
                                    ✊ Open → Close → Open to trigger SOS
                                </span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </>
    );
};

// ── Helper: mirrors a MediaStream into a visible <video> element ──────────────
// This decouples the always-hidden capture video from the displayed one.
const VideoMirror: React.FC<{ srcObject: MediaStream | null }> = ({ srcObject }) => {
    const ref = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        if (ref.current && srcObject) {
            ref.current.srcObject = srcObject;
            ref.current.play().catch(() => { });
        }
    }, [srcObject]);

    return (
        <video
            ref={ref}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover scale-x-[-1]"
        />
    );
};

export default GestureMonitor;