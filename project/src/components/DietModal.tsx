// Modified by Cursor integration: 2025-11-07 — modal component for diet file upload & showing the diet plan
// Detected: used Tailwind and glass design. This provides drag-drop and progress.

import React, { useState, useRef } from 'react';
import { uploadReport } from '../services/api';

interface Props {
  onClose: () => void;
}

const DietModal: React.FC<Props> = ({ onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = (f?: File) => {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError('');
  };

  const doUpload = async () => {
    if (!file) {
      setError('Please choose a file first');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const res = await uploadReport(file, (ev) => {
        if (ev.total) setProgress(Math.round((ev.loaded * 100) / ev.total));
      });
      setResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-xl p-6 w-full max-w-2xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold">Smart Diet Planner</h3>
          <button onClick={onClose} className="text-gray-500">Close</button>
        </div>

        <div
          onDrop={onDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-dashed border-2 border-gray-300 rounded p-6 text-center"
        >
          <input ref={inputRef} type="file" className="hidden" accept=".pdf,image/*" onChange={(e) => handleFile(e.target.files?.[0])} />
          {!file ? (
            <>
              <p className="mb-3">Drag & drop your health report (PDF or image) here, or</p>
              <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={() => inputRef.current?.click()}>Choose File</button>
            </>
          ) : (
            <>
              <p className="mb-2">Selected: <strong>{file.name}</strong></p>
              <div className="flex items-center space-x-3">
                <button className="px-4 py-2 bg-green-600 text-white rounded" onClick={doUpload} disabled={uploading}>{uploading ? 'Uploading...' : 'Upload'}</button>
                <button className="px-4 py-2 border rounded" onClick={() => setFile(null)} disabled={uploading}>Remove</button>
              </div>
            </>
          )}
        </div>

        {uploading && (
          <div className="mt-4">
            <div className="w-full bg-gray-100 rounded h-3 overflow-hidden">
              <div className="bg-blue-600 h-3" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-sm text-gray-500 mt-2">Uploading... {progress}%</p>
          </div>
        )}

        {error && <div className="mt-4 text-red-500">{error}</div>}

        {result && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded">
              <h4 className="font-semibold mb-2">Diet Plan</h4>
              <div><strong>Calories:</strong> {result.diet_plan?.calories_target}</div>
              <div><strong>Macros:</strong> Protein {result.diet_plan?.macros?.protein}, Carbs {result.diet_plan?.macros?.carbs}, Fat {result.diet_plan?.macros?.fats}</div>
              <div className="mt-2"><strong>Include:</strong> {result.diet_plan?.foods_to_include?.join(', ')}</div>
              <div className="mt-2"><strong>Avoid:</strong> {result.diet_plan?.foods_to_avoid?.join(', ')}</div>
              <div className="mt-2 text-sm text-gray-500">{result.diet_plan?.notes}</div>
            </div>
            <div className="p-4 bg-white rounded border">
              <h4 className="font-semibold mb-2">Extracted Text (preview)</h4>
              <pre className="text-xs max-h-64 overflow-auto bg-gray-50 p-2 rounded">{result.extracted_text || 'No text extracted'}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DietModal;