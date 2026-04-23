import React, { useState, useEffect, useRef } from 'react';
import { Activity, AlertCircle, Clock, ChevronDown, Activity as Pulse } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { predict } from '../services/api';
import AnimatedBackground from '../components/AnimatedBackground';

const Diabetes = () => {
  /* === Diabetes UI Integration Start: Logic & State === */
  const [formData, setFormData] = useState<Record<string, any>>({
    HighBP: null, HighChol: null, CholCheck: null, BMI: 25, Smoker: null, Stroke: null,
    HeartDiseaseorAttack: null, PhysActivity: null, Fruits: null, Veggies: null,
    HvyAlcoholConsump: null, AnyHealthcare: null, DiffWalk: null, Sex: null, Age: '',
    GenHlth: null, MentHlth: '', PhysHlth: ''
  });

  const [result, setResult] = useState<{ prediction: string, confidence: number | null, probability?: number } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const TOTAL_FIELDS = 18;
  const resultRef = useRef<HTMLDivElement>(null);

  // Risk factor weights for UI visualization
  const featureWeights = {
    'GenHlth': 0.18, 'BMI': 0.16, 'Age': 0.13, 'HighBP': 0.10,
    'PhysHlth': 0.07, 'DiffWalk': 0.07, 'HighChol': 0.06,
    'HeartDiseaseorAttack': 0.05, 'Stroke': 0.04, 'Smoker': 0.03,
    'PhysActivity': 0.03, 'HvyAlcoholConsump': 0.02,
    'Fruits': 0.01, 'Veggies': 0.01, 'CholCheck': 0.01,
    'AnyHealthcare': 0.01, 'MentHlth': 0.01, 'Sex': 0.01,
  };

  const featureLabels: Record<string, string> = {
    'GenHlth': 'General health', 'BMI': 'BMI', 'Age': 'Age group',
    'HighBP': 'High blood pressure', 'PhysHlth': 'Physical health days',
    'DiffWalk': 'Difficulty walking', 'HighChol': 'High cholesterol',
    'HeartDiseaseorAttack': 'Heart disease', 'Stroke': 'Stroke history',
    'Smoker': 'Smoker', 'PhysActivity': 'Physical activity',
    'HvyAlcoholConsump': 'Heavy alcohol'
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  useEffect(() => {
    let filled = 0;
    filled += 1; // BMI
    const fieldsToCheck = [
      'HighBP', 'HighChol', 'CholCheck', 'Smoker', 'PhysActivity', 'Fruits', 'Veggies',
      'HvyAlcoholConsump', 'Stroke', 'HeartDiseaseorAttack', 'AnyHealthcare', 'DiffWalk',
      'Sex', 'Age', 'GenHlth', 'MentHlth', 'PhysHlth'
    ];

    fieldsToCheck.forEach(f => {
      if (formData[f] !== null && formData[f] !== '') filled++;
    });

    const pct = Math.min(100, Math.round((filled / TOTAL_FIELDS) * 100));
    setProgress(pct);
  }, [formData]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const missing = Object.entries(formData).filter(([k, v]) => v === null || v === '').map(([k]) => featureLabels[k] || k);
    if (missing.length > 0) {
      setErrorMessage(`Please complete all fields. Missing: ${missing.join(', ')}`);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const data = await predict('diabetes', formData);
      setResult({
        prediction: data.prediction,
        confidence: data.confidence,
        probability: data.probability
      });

      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 300);
    } catch (err: any) {
      console.error('Prediction error:', err);
      setErrorMessage(err?.response?.data?.error || err?.message || 'Prediction failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const getBMICategory = (val: number) => {
    if (val < 18.5) return 'Underweight';
    if (val < 25) return 'Normal weight';
    if (val < 30) return 'Overweight';
    if (val < 35) return 'Obese (Class I)';
    if (val < 40) return 'Obese (Class II)';
    return 'Severely Obese';
  };
  /* === Diabetes UI Integration End: Logic & State === */

  return (
    <div className="relative min-h-screen selection:bg-indigo-500 selection:text-white pb-20">
      <AnimatedBackground />

      {/* Styles Injection */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');
        
        .diabetes-container { font-family: 'DM Sans', sans-serif; }
        .diabetes-heading { font-family: 'Instrument Serif', serif; }
        
        .section-glass {
          background: rgba(255, 255, 255, 0.4);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.5);
          border-radius: 24px;
          box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        }

        .toggle-chip input:checked + label {
          background: #4f46e5;
          border-color: #4f46e5;
          color: white;
          box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }

        .scale-chip input:checked + label {
          background: #4f46e5;
          border-color: #4f46e5;
          color: white;
          font-weight: 500;
          box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }

        .gauge-fill {
          transition: width 1.5s cubic-bezier(.4,0,.2,1);
          background: linear-gradient(90deg, #2d6a4f, #e65100, #c84b2f);
          background-size: 300% 100%;
        }

        .input-glass {
          background: rgba(255, 255, 255, 0.5);
          border: 1.5px solid rgba(255, 255, 255, 0.6);
          backdrop-filter: blur(4px);
        }
        
        .input-glass:focus {
          background: rgba(255, 255, 255, 0.9);
          border-color: #4f46e5;
          box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
        }
      `}</style>

      {/* Header (Integrated with app theme) */}
      <header className="relative pt-32 pb-12 px-8 text-center overflow-hidden">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-5xl mx-auto relative z-10"
        >
          <div className="inline-flex p-4 bg-white/30 backdrop-blur-md rounded-2xl border border-white/40 shadow-sm mb-6">
            <Activity className="w-10 h-10 text-indigo-600" />
          </div>
          <h1 className="diabetes-heading text-5xl md:text-6xl font-normal tracking-tight text-gray-900 mb-4">
            Diabetes Risk Assessment
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto text-lg leading-relaxed">
            Harnessing Machine Learning to evaluate 18 specific indicators
            based on CDC health surveillance data.
          </p>

          <div className="flex justify-center gap-3 mt-8">
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                animate={{ scale: progress >= (i + 1) * 20 ? 1.2 : 1 }}
                className={`w-3 h-3 rounded-full transition-colors duration-500 ${progress >= (i + 1) * 20 ? 'bg-indigo-500' : 'bg-gray-300'}`}
              />
            ))}
          </div>
        </motion.div>
      </header>

      {/* Sticky Progress Bar */}
      <div className="sticky top-0 z-50 h-1.5 bg-gray-200/50 backdrop-blur-sm overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <main className="max-w-4xl mx-auto px-6 pt-12 diabetes-container relative z-10">
        {/* Section 1: Blood & Cholesterol */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="section-glass mb-8 overflow-hidden"
        >
          <div className="px-8 py-5 border-b border-white/50 bg-white/20 flex items-center gap-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-200">1</div>
            <h2 className="diabetes-heading text-xl text-gray-800">Cardiovascular Vitals</h2>
          </div>
          <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              { id: 'HighBP', label: 'High Blood Pressure', hint: 'Diagnostic history of HBP' },
              { id: 'HighChol', label: 'High Cholesterol', hint: 'Confirmed by lab test' },
              { id: 'CholCheck', label: 'Routine Checkup', hint: 'Tested in last 5 years' }
            ].map(f => (
              <div key={f.id} className="flex flex-col gap-3">
                <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">{f.label}</label>
                <div className="flex gap-2">
                  {[{ l: 'No', v: 0 }, { l: 'Yes', v: 1 }].map(opt => (
                    <div key={opt.v} className="toggle-chip flex-1">
                      <input type="radio" id={`${f.id}-${opt.v}`} name={f.id} className="hidden" checked={formData[f.id] === opt.v} onChange={() => handleInputChange(f.id, opt.v)} />
                      <label htmlFor={`${f.id}-${opt.v}`} className="block text-center py-2.5 px-4 border border-white/60 rounded-xl text-xs cursor-pointer transition-all hover:bg-white/40 text-gray-700">{opt.l}</label>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-gray-400 font-medium italic">{f.hint}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Section 2: Body & Lifestyle */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="section-glass mb-8 overflow-hidden"
        >
          <div className="px-8 py-5 border-b border-white/50 bg-white/20 flex items-center gap-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-200">2</div>
            <h2 className="diabetes-heading text-xl text-gray-800">Biometrics & Lifestyle</h2>
          </div>
          <div className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-10">
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Body Mass Index (BMI)</label>
                  <span className="px-3 py-1 bg-white/60 rounded-lg text-[10px] font-bold text-indigo-600 border border-white/80">{getBMICategory(formData.BMI)}</span>
                </div>
                <div className="flex items-center gap-6">
                  <input type="range" min="10" max="70" value={formData.BMI} onChange={(e) => handleInputChange('BMI', parseInt(e.target.value))} className="flex-1 h-2 bg-indigo-100 rounded-full appearance-none cursor-pointer accent-indigo-600" />
                  <span className="diabetes-heading text-3xl font-normal text-indigo-600">{formData.BMI}</span>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Smoking Status</label>
                <div className="flex gap-2">
                  {[{ l: 'Non-Smoker', v: 0 }, { l: 'Smoker (100+ lifetime)', v: 1 }].map(opt => (
                    <div key={opt.v} className="toggle-chip flex-1">
                      <input type="radio" id={`Smoker-${opt.v}`} name="Smoker" className="hidden" checked={formData.Smoker === opt.v} onChange={() => handleInputChange('Smoker', opt.v)} />
                      <label htmlFor={`Smoker-${opt.v}`} className="block text-center py-2.5 px-4 border border-white/60 rounded-xl text-xs cursor-pointer transition-all hover:bg-white/40 text-gray-700 leading-tight">{opt.l}</label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { id: 'PhysActivity', label: 'Activity', hint: 'Past 30 days' },
                { id: 'Fruits', label: 'Fruits', hint: '1+ Daily' },
                { id: 'Veggies', label: 'Veggies', hint: '1+ Daily' },
                { id: 'HvyAlcoholConsump', label: 'Alcohol', hint: 'Heavy Intake' }
              ].map(f => (
                <div key={f.id} className="flex flex-col gap-2">
                  <label className="text-[9px] uppercase tracking-widest font-bold text-gray-500 text-center">{f.label}</label>
                  <div className="flex gap-1">
                    {[{ l: 'N', v: 0 }, { l: 'Y', v: 1 }].map(opt => (
                      <div key={opt.v} className="toggle-chip flex-1">
                        <input type="radio" id={`${f.id}-${opt.v}`} name={f.id} className="hidden" checked={formData[f.id] === opt.v} onChange={() => handleInputChange(f.id, opt.v)} />
                        <label htmlFor={`${f.id}-${opt.v}`} className="block text-center py-2 border border-white/60 rounded-lg text-[10px] cursor-pointer transition-all text-gray-600">{opt.l}</label>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Section 3: Medical History */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="section-glass mb-8 overflow-hidden"
        >
          <div className="px-8 py-5 border-b border-white/50 bg-white/20 flex items-center gap-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-200">3</div>
            <h2 className="diabetes-heading text-xl text-gray-800">Clinical History</h2>
          </div>
          <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-10">
            {[
              { id: 'Stroke', label: 'Stroke Incidence', hint: 'Ever suffered a stroke?' },
              { id: 'HeartDiseaseorAttack', label: 'Coronary Health', hint: 'Heart disease or MI history?' },
              { id: 'AnyHealthcare', label: 'Clinical Access', hint: 'Have health insurance/coverage?' },
              { id: 'DiffWalk', label: 'Mobility Status', hint: 'Difficulty walking/stairs?' }
            ].map(f => (
              <div key={f.id} className="flex flex-col gap-3">
                <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">{f.label}</label>
                <div className="flex gap-2">
                  {[{ l: 'No', v: 0 }, { l: 'Yes', v: 1 }].map(opt => (
                    <div key={opt.v} className="toggle-chip flex-1">
                      <input type="radio" id={`${f.id}-${opt.v}`} name={f.id} className="hidden" checked={formData[f.id] === opt.v} onChange={() => handleInputChange(f.id, opt.v)} />
                      <label htmlFor={`${f.id}-${opt.v}`} className="block text-center py-2.5 px-4 border border-white/60 rounded-xl text-xs cursor-pointer transition-all hover:bg-white/40 text-gray-700">{opt.l}</label>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-gray-400 font-medium italic">{f.hint}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Section 4: Health Status */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="section-glass mb-8 overflow-hidden"
        >
          <div className="px-8 py-5 border-b border-white/50 bg-white/20 flex items-center gap-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-200">4</div>
            <h2 className="diabetes-heading text-xl text-gray-800">Subjective Wellbeing</h2>
          </div>
          <div className="p-8">
            <div className="mb-10">
              <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Self-Perceived Health State</label>
              <div className="grid grid-cols-5 gap-3 mt-4">
                {[
                  { l: 'Excellent', v: 1, e: '✨' }, { l: 'Very Good', v: 2, e: '💪' }, { l: 'Good', v: 3, e: '👍' }, { l: 'Fair', v: 4, e: '😐' }, { l: 'Poor', v: 5, e: '😟' }
                ].map(opt => (
                  <div key={opt.v} className="scale-chip">
                    <input type="radio" id={`gh-${opt.v}`} name="GenHlth" className="hidden" checked={formData.GenHlth === opt.v} onChange={() => handleInputChange('GenHlth', opt.v)} />
                    <label htmlFor={`gh-${opt.v}`} className="flex flex-col items-center justify-center h-20 border border-white/60 rounded-2xl text-[9px] font-bold text-gray-600 cursor-pointer transition-all hover:bg-white/40 px-2 text-center">
                      <span className="text-2xl mb-1">{opt.e}</span>
                      {opt.l}
                    </label>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Mental Health Downtime</label>
                <div className="relative">
                  <input type="number" min="0" max="30" value={formData.MentHlth} onChange={(e) => handleInputChange('MentHlth', e.target.value)} className="w-full px-5 py-3 rounded-2xl input-glass outline-none transition-all text-sm font-medium" placeholder="Days (0-30)" />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-gray-400 font-bold">DAYS</span>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Physical Ailment Duration</label>
                <div className="relative">
                  <input type="number" min="0" max="30" value={formData.PhysHlth} onChange={(e) => handleInputChange('PhysHlth', e.target.value)} className="w-full px-5 py-3 rounded-2xl input-glass outline-none transition-all text-sm font-medium" placeholder="Days (0-30)" />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-gray-400 font-bold">DAYS</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Section 5: Demographics */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="section-glass mb-12 overflow-hidden"
        >
          <div className="px-8 py-5 border-b border-white/50 bg-white/20 flex items-center gap-4">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-lg shadow-indigo-200">5</div>
            <h2 className="diabetes-heading text-xl text-gray-800">Demographics</h2>
          </div>
          <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="flex flex-col gap-3">
              <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Sex Assigned at Birth</label>
              <div className="flex gap-2">
                {[{ l: 'Female', v: 0 }, { l: 'Male', v: 1 }].map(opt => (
                  <div key={opt.v} className="toggle-chip flex-1">
                    <input type="radio" id={`Sex-${opt.v}`} name="Sex" className="hidden" checked={formData.Sex === opt.v} onChange={() => handleInputChange('Sex', opt.v)} />
                    <label htmlFor={`Sex-${opt.v}`} className="block text-center py-3 px-4 border border-white/60 rounded-xl text-xs cursor-pointer transition-all hover:bg-white/40 text-gray-700">{opt.l}</label>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500">Age Category</label>
              <div className="relative">
                <select value={formData.Age} onChange={(e) => handleInputChange('Age', e.target.value)} className="w-full px-5 py-3 rounded-2xl input-glass appearance-none outline-none text-sm font-medium cursor-pointer">
                  <option value="">— Select Bracket —</option>
                  {['18–24', '25–29', '30–34', '35–39', '40–44', '45–49', '50–54', '55–59', '60–64', '65–69', '70–74', '75–79', '80 or older'].map((label, i) => (
                    <option key={i} value={i + 1}>{label}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Submit Area */}
        <div className="text-center mb-24">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleSubmit()}
            disabled={isLoading}
            className={`inline-flex items-center gap-3 px-12 py-5 bg-indigo-600 text-white rounded-2xl font-bold text-lg transition-all shadow-xl shadow-indigo-200 hover:shadow-indigo-300 ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {isLoading ? <Clock className="w-6 h-6 animate-spin" /> : <Pulse className="w-6 h-6" />}
            {isLoading ? 'Processing Health Matrix...' : 'Generate Risk Analysis'}
          </motion.button>

          <AnimatePresence>
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="mt-8 p-5 bg-red-50/80 backdrop-blur-md border border-red-100 rounded-2xl flex items-center justify-center gap-3 text-red-600 text-sm font-medium max-w-lg mx-auto shadow-sm"
              >
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                {errorMessage}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Result Section */}
        <div ref={resultRef}>
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="section-glass border-none shadow-2xl overflow-hidden mb-20"
              >
                <div className={`p-12 flex items-center gap-8 ${result.probability! < 40 ? 'bg-emerald-100/60' : result.probability! < 70 ? 'bg-amber-100/60' : 'bg-rose-100/60'}`}>
                  <div className="text-7xl animate-bounce">
                    {result.probability! < 40 ? '✅' : result.probability! < 70 ? '⚠️' : '🔴'}
                  </div>
                  <div>
                    <h3 className={`diabetes-heading text-4xl mb-2 ${result.probability! < 40 ? 'text-emerald-700' : result.probability! < 70 ? 'text-amber-700' : 'text-rose-700'}`}>
                      {result.probability! < 40 ? 'Optimistic Outcome' : result.probability! < 70 ? 'Moderate Alert' : 'Critical Risk Profile'}
                    </h3>
                    <p className="text-gray-600 font-medium">Predictive analysis complete based on clinical surveillance patterns.</p>
                  </div>
                </div>

                <div className="p-12">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
                    <div className="text-center md:text-left">
                      <div className="diabetes-heading text-8xl font-normal text-gray-900 leading-none">
                        {Math.round(result.probability!)}<span className="text-3xl text-gray-400 ml-2">%</span>
                      </div>
                      <p className="text-[11px] uppercase tracking-[0.3em] text-gray-400 mt-4 font-black">Computed Probability Score</p>

                      <div className="mt-12 p-8 bg-indigo-50/40 rounded-3xl border-l-8 border-indigo-500 text-gray-700 leading-relaxed font-medium italic">
                        {result.probability! < 40 ?
                          "Your metrics align with low-risk statistical clusters. Consistent physical activity and glycemic monitoring are advised for long-term maintenance." :
                          result.probability! < 70 ?
                            "Moderate risk detected. We recommend a clinical consultation for a Fasting Plasma Glucose (FPG) test and metabolic review." :
                            "High risk detected. Immediate medical consultation for HbA1c testing is strongly advised to rule out clinical diabetes or pre-diabetes."
                        }
                      </div>
                    </div>

                    <div>
                      <div className="mb-10">
                        <div className="flex justify-between text-[11px] uppercase font-black text-gray-400 mb-4 tracking-widest">
                          <span>Stable Zone</span>
                          <span>Alert Zone</span>
                        </div>
                        <div className="h-4 bg-gray-100 rounded-full overflow-hidden p-1 shadow-inner">
                          <motion.div
                            className="h-full gauge-fill rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${result.probability}%` }}
                            transition={{ duration: 1.5, ease: "easeOut" }}
                          />
                        </div>
                      </div>

                      <div>
                        <h4 className="text-[11px] uppercase tracking-widest font-black text-gray-500 mb-8 flex items-center gap-3">
                          <Pulse className="w-4 h-4 text-indigo-500" />
                          Key Determinant Metrics
                        </h4>
                        <div className="space-y-6">
                          {Object.entries(featureWeights)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([feat, weight], idx) => {
                              const val = formData[feat];
                              let contribution = weight * 100;
                              if (['HighBP', 'HighChol', 'HeartDiseaseorAttack', 'Stroke'].includes(feat)) {
                                contribution = val === 1 ? contribution : contribution * 0.2;
                              }
                              return (
                                <div key={feat} className="flex flex-col gap-2">
                                  <div className="flex justify-between items-center px-1">
                                    <span className="text-xs font-bold text-gray-600">{featureLabels[feat] || feat}</span>
                                    <span className="text-[10px] font-black text-indigo-400">{Math.round(contribution)}%</span>
                                  </div>
                                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                    <motion.div
                                      className="h-full bg-indigo-400"
                                      initial={{ width: 0 }}
                                      whileInView={{ width: `${contribution}%` }}
                                      transition={{ duration: 1, delay: idx * 0.1 }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Diabetes;