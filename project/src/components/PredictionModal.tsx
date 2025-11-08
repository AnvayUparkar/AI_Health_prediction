// Modified by Cursor integration: 2025-11-07 — removed unused handleChange and fixed Tailwind class conflict (kept text-sm)

import React, { useState } from 'react';
import { predict } from '../services/api';

interface Props {
  onClose: () => void;
  defaultType?: 'lung_cancer' | 'diabetes';
}

const PredictionModal: React.FC<Props> = ({ onClose, defaultType = 'lung_cancer' }) => {
  const [type, setType] = useState<'lung_cancer'|'diabetes'>(defaultType);
  const [features, setFeatures] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await predict(type, features);
      if (res && res.prediction) {
        setResult(res);
      } else {
        setError(res.error || 'Prediction failed');
      }
    } catch (err: any) {
      setError(err?.response?.data?.error || err.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-xl p-6 w-full max-w-lg">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold">Health Prediction</h3>
          <button onClick={onClose} className="text-gray-500">Close</button>
        </div>

        <form onSubmit={(e) => { submit(e); }}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Model</label>
            <select value={type} onChange={(e) => setType(e.target.value as any)} className="w-full border px-3 py-2 rounded">
              <option value="lung_cancer">Lung Cancer</option>
              <option value="diabetes">Diabetes</option>
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Features (JSON)</label>
            <textarea
              rows={6}
              placeholder='e.g. { "Age": 45, "Gender": "1", "Smoking": 2 }'
              className="w-full border px-3 py-2 rounded font-mono text-sm"
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value || '{}');
                  setFeatures(parsed);
                } catch {
                  // ignore parse errors for now
                }
              }}
            />
            <p className="text-xs text-gray-500 mt-1">Enter features as JSON. Keys must match model expected fields.</p>
          </div>

          <div className="flex items-center space-x-3">
            <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded">
              {loading ? 'Predicting...' : 'Predict'}
            </button>
            <button type="button" onClick={() => { setFeatures({}); setResult(null); setError(''); }} className="px-4 py-2 border rounded">Reset</button>
          </div>
        </form>

        {error && <div className="mt-4 text-red-500">{error}</div>}

        {result && (
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <div><strong>Prediction:</strong> {result.prediction}</div>
            <div><strong>Confidence:</strong> {result.confidence}%</div>
            <pre className="mt-2 text-sm bg-white p-2 rounded">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictionModal;