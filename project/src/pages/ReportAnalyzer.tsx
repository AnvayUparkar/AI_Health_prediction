import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Download,
  Loader2 as Loader2Icon,
  Upload,
  FileText,
  Loader,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Microscope,
  Apple,
  Utensils,
  Droplets,
  ShieldAlert,
  Lightbulb,
  Heart,
  FileSearch,
  Stethoscope,
  Activity,
  BrainCircuit,
  Coffee,
  Drumstick,
} from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import { analyzeReport, getProfile } from '../services/api';

// ---------- Types ----------

interface ParameterInfo {
  value: string;
  unit: string;
  status: string;
  ref_range: string;
  ref_source?: string;
  is_important: boolean;
}

interface MealDish {
  title: string;
  items?: string[];
  components?: Record<string, string>;
  nutrient_tags?: string[];
  benefit: string;
}

// Gemini-powered diet plan shape
interface GeminiDietPlan {
  issues_detected: string[];
  recommended_foods: string[];
  foods_to_avoid: string[];
  meal_plan: {
    breakfast: MealDish;
    mid_morning: MealDish;
    lunch: MealDish;
    evening_snack: MealDish;
    dinner: MealDish;
  };
  hydration_tips: string[];
  lifestyle_tips: string[];
  parameter_reasoning: Record<string, string>;
  urgent_flags: string[];
  summary: string;
  safety_note: string;
  // Full Perfection Protocol fields
  status?: string;
  conditions_profile?: string[];
  clinical_protocol?: string[];
  synergy_pairing?: string[];
  blocked_foods_safety?: Record<string, string>;
  // Rule-based fallback fields
  diet_tips?: string[];
  hydration_notes?: string;
  meal_suggestions?: {
    breakfast: string[];
    lunch: string[];
    dinner: string[];
    snacks: string[];
  };
  disclaimer: string;
}

interface AnalysisResult {
  success: boolean;
  extracted_text: string;
  all_parameters: Record<string, ParameterInfo>;
  important_parameters: Record<string, ParameterInfo>;
  report_summary: string;
  diet_recommendation: GeminiDietPlan;
  diet_plan_text: string;
  diet_source: 'gemini' | 'rules_fallback' | 'error';
  diet_warning?: string;
  mode?: 'file' | 'manual';
}

// ---------- Helper components ----------

const StatusBadge = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    High: 'bg-red-100 text-red-700 border-red-200',
    Low: 'bg-amber-100 text-amber-700 border-amber-200',
    Normal: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    Abnormal: 'bg-red-100 text-red-700 border-red-200',
    Critical: 'bg-rose-200 text-rose-800 border-rose-300',
    Borderline: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  };
  const style = colors[status] || 'bg-gray-100 text-gray-700 border-gray-200';
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style}`}>
      {status}
    </span>
  );
};

// ---------- Main component ----------

const ReportAnalyzer = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState('');
  const [showExtractedText, setShowExtractedText] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [healthData, setHealthData] = useState({
    age: '',
    weight: '',
    height: '',
    activityLevel: 'moderate',
    dietaryPreference: 'none',
    healthConditions: ''
  });

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        const data = await getProfile();
        if (data && data.profile) {
          setHealthData((prev: any) => ({
            ...prev,
            age: data.profile.age?.toString() || prev.age,
            weight: data.profile.weight?.toString() || prev.weight,
            height: data.profile.height?.toString() || prev.height,
            dietaryPreference: data.profile.diet_preference || prev.dietaryPreference,
            healthConditions: data.profile.allergies?.join(', ') || prev.healthConditions
          }));
        }
      } catch (err) {
        console.error('Failed to fetch profile for auto-population', err);
      }
    };
    fetchProfileData();
  }, []);

  // File handlers
  const handleFileSelect = useCallback((f: File) => {
    setFile(f);
    setResult(null);
    setError('');
    setProgress(0);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setHealthData({
      ...healthData,
      [e.target.name]: e.target.value
    });
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    },
    [handleFileSelect]
  );

  // Submit
  const handleSubmit = async () => {
    if (!file && !healthData.age) return;
    setLoading(true);
    setError('');
    setProgress(0);

    try {
      const data = await analyzeReport(file, (ev) => {
        if (ev.total) setProgress(Math.round((ev.loaded * 100) / ev.total));
      }, !file ? healthData : undefined);

      if (data.success) {
        setResult(data);
        // Store clinical context for the chatbot to pick up
        if (data.important_parameters) {
          sessionStorage.setItem('active_clinical_context', JSON.stringify(data.important_parameters));
        }
      } else {
        setError(data.error || 'Analysis failed. Please try again.');
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.error ||
        err?.message ||
        'Failed to analyze report. Please check if the backend is running.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setResult(null);
    setError('');
    setProgress(0);
    setShowExtractedText(false);
    setHealthData({
      age: '',
      weight: '',
      height: '',
      activityLevel: 'moderate',
      dietaryPreference: 'none',
      healthConditions: ''
    });
  };

  // ── Export report analysis to PDF ───────────────────────────────────
  const handleExportAnalysis = async () => {
    if (!result) return;
    setExportLoading(true);
    const token = localStorage.getItem('token');
    try {
      const response = await fetch('http://localhost:5000/api/export-report-analysis', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(result),
      });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_analysis_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to export report analysis', err);
    } finally {
      setExportLoading(false);
    }
  };

  // ---- RESULTS VIEW ----
  if (result) {
    const { all_parameters, important_parameters, diet_recommendation, diet_source, diet_warning } = result;
    const paramCount = Object.keys(all_parameters).length;
    const importantCount = Object.keys(important_parameters).length;
    const isGemini = diet_source === 'gemini';

    // Normalize fields so we handle both Gemini and rule-based fallback
    const dr = diet_recommendation;
    const hydrationList: string[] = dr.hydration_tips?.length
      ? dr.hydration_tips
      : dr.hydration_notes ? [dr.hydration_notes] : [];
    const lifestyleTips: string[] = dr.lifestyle_tips ?? dr.diet_tips ?? [];
    const mealPlan = dr.meal_plan ?? {
      breakfast:     dr.meal_suggestions?.breakfast ?? [],
      mid_morning:   [],
      lunch:         dr.meal_suggestions?.lunch ?? [],
      evening_snack: dr.meal_suggestions?.snacks ?? [],
      dinner:        dr.meal_suggestions?.dinner ?? [],
    };
    const disclaimer = dr.safety_note ?? dr.disclaimer ?? '';
    const urgentFlags = dr.urgent_flags ?? [];
    const reasoning = dr.parameter_reasoning ?? {};
    const synergyPairing = dr.synergy_pairing ?? [];
    const safetyBlocks = dr.blocked_foods_safety ?? {};
    const profile = dr.conditions_profile ?? [];

    return (
      <div className="relative min-h-screen pt-20 pb-12">
        <AnimatedBackground />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            {/* Header */}
            <div className="text-center mb-10">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h1 className="text-5xl font-bold mb-3 bg-gradient-to-r from-teal-600 to-cyan-600 bg-clip-text text-transparent">
                Report Analysis Complete
              </h1>
              <p className="text-lg text-gray-600">
                Found <strong>{paramCount}</strong> parameters &middot;{' '}
                <strong className="text-amber-600">{importantCount}</strong> require attention
              </p>
              {/* Diet source badge */}
              <div className="mt-3 flex justify-center">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
                  isGemini
                    ? 'bg-violet-50 text-violet-700 border-violet-200'
                    : 'bg-gray-50 text-gray-600 border-gray-200'
                }`}>
                  {isGemini ? '✦ AI-Powered Clinical Co-Pilot' : '⚙ Data-Grounded Resilience Engine'}
                </span>
              </div>
              {diet_warning && (
                <p className="mt-2 text-xs text-amber-600">{diet_warning}</p>
              )}
            </div>
            
            {/* ---- Conditions Profile ---- */}
            {profile.length > 0 && (
              <div className="flex flex-wrap justify-center gap-2 mb-8">
                {profile.map((p, idx) => (
                  <span key={idx} className="px-4 py-1.5 bg-indigo-50 text-indigo-700 border border-indigo-100 rounded-lg text-sm font-bold shadow-sm">
                    {p}
                  </span>
                ))}
              </div>
            )}

            {/* ---- Urgent Flags ---- */}
            {urgentFlags.length > 0 && (
              <div className="mb-6 bg-red-50 border-2 border-red-300 rounded-xl p-5">
                <div className="flex items-center mb-3">
                  <ShieldAlert className="h-6 w-6 text-red-600 mr-2" />
                  <h2 className="text-lg font-bold text-red-800">Urgent — Seek Medical Attention</h2>
                </div>
                <ul className="space-y-1">
                  {urgentFlags.map((flag, idx) => (
                    <li key={idx} className="flex items-start text-sm text-red-700">
                      <span className="mr-2 text-red-500">!</span>{flag}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* ---- Extracted Parameters ---- */}
            <GlassCard className="p-6 mb-6">
              <div className="flex items-center mb-5">
                <Microscope className="h-6 w-6 text-blue-600 mr-3" />
                <h2 className="text-2xl font-bold text-gray-800">Detected Parameters</h2>
              </div>

              {paramCount === 0 ? (
                <div className="text-center py-8 bg-gray-50/50 rounded-2xl border border-dashed border-gray-200">
                  <p className="text-gray-400 italic text-sm">
                    {result.mode === 'manual' 
                      ? "No lab parameters provided. Recommendations are generated based on your health profile context."
                      : "No medical parameters were detected in the extracted report text."}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-2 font-semibold text-gray-700">Parameter</th>
                        <th className="text-left py-3 px-2 font-semibold text-gray-700">Value</th>
                        <th className="text-left py-3 px-2 font-semibold text-gray-700">Unit</th>
                        <th className="text-left py-3 px-2 font-semibold text-gray-700">Status</th>
                        <th className="text-left py-3 px-2 font-semibold text-gray-700">Ref Range</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(all_parameters)
                        .sort(([, a], [, b]) => Number(b.is_important) - Number(a.is_important))
                        .map(([name, info]) => (
                          <tr
                            key={name}
                            className={`border-b border-gray-100 ${
                              info.is_important ? 'bg-amber-50/60' : ''
                            }`}
                          >
                            <td className="py-3 px-2 font-medium text-gray-800">
                              {info.is_important && (
                                <AlertTriangle className="inline h-4 w-4 text-amber-500 mr-1.5 -mt-0.5" />
                              )}
                              {name}
                            </td>
                            <td className="py-3 px-2 font-mono text-gray-900">{info.value}</td>
                            <td className="py-3 px-2 text-gray-500">{info.unit}</td>
                            <td className="py-3 px-2">
                              <StatusBadge status={info.status} />
                            </td>
                            <td className="py-3 px-2 text-gray-500 font-mono text-xs">{info.ref_range}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>

            {/* ---- Diet Recommendations ---- */}
            {dr && (
              <>
                {/* Summary */}
                {dr.summary && (
                  <GlassCard className="p-5 mb-6 bg-gradient-to-r from-teal-50 to-cyan-50">
                    <p className="text-gray-700 text-sm leading-relaxed italic">"{dr.summary}"</p>
                  </GlassCard>
                )}

                {/* Status & Clinical Protocol Title */}
                {dr.status && (
                  <div className="mb-6 flex flex-col items-center">
                    <div className="bg-teal-100 text-teal-800 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider mb-2 shadow-sm border border-teal-200">
                      {dr.status}
                    </div>
                    <h2 className="text-3xl font-extrabold text-gray-900 text-center bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-cyan-600">
                      Perfect Clinical Protocol
                    </h2>
                  </div>
                )}

                {/* Conditions Profile */}
                {dr.conditions_profile && dr.conditions_profile.length > 0 && (
                  <GlassCard className="p-6 mb-6 bg-gradient-to-br from-teal-50/50 to-white">
                    <div className="flex items-center mb-4">
                      <Stethoscope className="h-6 w-6 text-teal-600 mr-3" />
                      <h2 className="text-2xl font-bold text-gray-800">Conditions Detected Profile</h2>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {dr.conditions_profile.map((cond, idx) => (
                        <span key={idx} className="bg-teal-50 text-teal-700 px-3 py-1 rounded-lg text-sm font-semibold border border-teal-100 shadow-sm flex items-center">
                          <Activity className="h-3.5 w-3.5 mr-1.5 opacity-70" />
                          {cond}
                        </span>
                      ))}
                    </div>
                  </GlassCard>
                )}

                {/* Clinical Protocol Registry */}
                {dr.clinical_protocol && dr.clinical_protocol.length > 0 && (
                  <GlassCard className="p-6 mb-6 border-l-4 border-l-cyan-500">
                    <div className="flex items-center mb-4">
                      <BrainCircuit className="h-6 w-6 text-cyan-600 mr-3" />
                      <h2 className="text-2xl font-bold text-gray-800">Clinical Optimization Protocol</h2>
                    </div>
                    <div className="space-y-3">
                      {dr.clinical_protocol.map((step, idx) => (
                        <div key={idx} className="flex items-start bg-gray-50/50 p-4 rounded-xl border border-gray-100">
                          <div className="bg-cyan-100 text-cyan-700 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mr-3 flex-shrink-0 mt-0.5">
                            {idx + 1}
                          </div>
                          <p className="text-gray-700 text-sm leading-relaxed font-medium">{step}</p>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                )}

                {/* Issues */}
                {dr.issues_detected.length > 0 && (
                  <GlassCard className="p-6 mb-6">
                    <div className="flex items-center mb-4">
                      <ShieldAlert className="h-6 w-6 text-amber-500 mr-3" />
                      <h2 className="text-2xl font-bold text-gray-800">Issues Detected</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {dr.issues_detected.map((issue, idx) => (
                        <div
                          key={idx}
                          className="flex items-start bg-amber-50 border border-amber-100 rounded-xl px-4 py-3"
                        >
                          <AlertTriangle className="h-5 w-5 text-amber-500 mr-2.5 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-800 text-sm">{issue}</span>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                )}

                {/* Foods Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  {/* Recommended Foods */}
                  <GlassCard className="p-6">
                    <div className="flex items-center mb-4">
                      <Apple className="h-6 w-6 text-green-500 mr-3" />
                      <h3 className="text-xl font-bold text-gray-800">Recommended Foods</h3>
                    </div>
                    <ul className="space-y-3">
                      {dr.recommended_foods.map((food, idx) => (
                        <li key={idx} className="flex items-start text-sm">
                          <CheckCircle className="h-4 w-4 text-green-500 mr-2.5 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700 leading-relaxed">{food}</span>
                        </li>
                      ))}
                    </ul>
                  </GlassCard>

                  {/* Safety Block Registry */}
                  <GlassCard className="p-6">
                    <div className="flex items-center mb-4">
                      <ShieldAlert className="h-6 w-6 text-rose-500 mr-3" />
                      <h3 className="text-xl font-bold text-gray-800">Foods to Avoid</h3>
                    </div>
                    <ul className="space-y-3">
                      {Object.keys(safetyBlocks).length > 0 ? (
                        Object.entries(safetyBlocks).map(([food, reason], idx) => (
                          <li key={idx} className="p-3 bg-rose-50 border border-rose-100 rounded-xl">
                            <div className="flex items-center mb-1">
                              <XCircle className="h-4 w-4 text-rose-500 mr-2" />
                              <span className="text-sm font-bold text-rose-900 font-mono italic">{food}</span>
                            </div>
                            <p className="text-xs text-rose-700 ml-6">{reason}</p>
                          </li>
                        ))
                      ) : (
                        dr.foods_to_avoid.map((food, idx) => (
                          <li key={idx} className="flex items-start text-sm">
                            <XCircle className="h-4 w-4 text-rose-400 mr-2.5 mt-0.5" />
                            <span className="text-gray-600 italic">{food}</span>
                          </li>
                        ))
                      )}
                    </ul>
                  </GlassCard>
                </div>

                {/* Synergy Protocol */}
                {synergyPairing.length > 0 && (
                  <GlassCard className="p-6 mb-6 bg-gradient-to-br from-indigo-50 to-blue-50 border-indigo-100">
                    <div className="flex items-center mb-5">
                      <Heart className="h-6 w-6 text-indigo-600 mr-3" />
                      <h2 className="text-2xl font-bold text-indigo-900">Biochemical Synergy Protocol</h2>
                    </div>
                    <div className="space-y-3">
                      {synergyPairing.map((pairing, idx) => (
                        <div key={idx} className="flex items-start bg-white/60 p-4 rounded-xl border border-indigo-200/50 shadow-sm">
                          <div className="p-2 bg-indigo-100 rounded-lg mr-4">
                            <Utensils className="h-5 w-5 text-indigo-600" />
                          </div>
                          <p className="text-indigo-900 text-sm font-medium leading-relaxed">
                            {pairing}
                          </p>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                )}

                {/* Daily Meal Plan - Premium UI (Diet-Planner Sync) */}
                <GlassCard className="p-8 mb-8 border-t-4 border-t-purple-500 shadow-2xl">
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center">
                      <div className="p-3 bg-purple-100 rounded-2xl mr-4 shadow-inner">
                        <Utensils className="h-8 w-8 text-purple-600" />
                      </div>
                      <div>
                        <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">Daily Clinical Meal Plan</h2>
                        <p className="text-sm text-gray-500 font-medium italic">Customized specifically for your biochemical profile</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
                    {/* Breakfast */}
                    <GlassCard className="p-6 border-l-4 border-l-yellow-500 bg-gradient-to-br from-yellow-50/30 to-white hover:shadow-xl transition-all duration-300">
                      <div className="flex items-center mb-4">
                        <Coffee className="h-6 w-6 text-yellow-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Breakfast</h3>
                      </div>
                      <div className="mb-4">
                        <h4 className="text-lg font-bold text-green-700 mb-2 leading-tight">{mealPlan.breakfast.title || 'Healthy Indian Breakfast'}</h4>
                        
                        {/* Nutrient Tags */}
                        {mealPlan.breakfast.nutrient_tags && mealPlan.breakfast.nutrient_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {mealPlan.breakfast.nutrient_tags.map((tag, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded-full border border-green-200">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="bg-white/40 rounded-lg p-3 border border-yellow-100/30 mb-3">
                          <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400 mb-2">Meal Components</p>
                          <ul className="space-y-1.5">
                            {Object.entries(mealPlan.breakfast.components || {}).map(([key, val], i) => (
                              <li key={i} className="text-sm text-gray-700 flex justify-between">
                                <span className="font-semibold text-gray-500">{key}:</span>
                                <span>{val}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        {mealPlan.breakfast.benefit && (
                          <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-100/50 shadow-sm">
                            <p className="text-[11px] leading-relaxed text-blue-700 font-medium">
                              <Lightbulb className="inline h-3.5 w-3.5 mr-2 -mt-0.5" />
                              <span className="font-bold underline decoration-blue-200 mr-1 italic">Clinical Benefit:</span>
                              {mealPlan.breakfast.benefit}
                            </p>
                          </div>
                        )}
                      </div>
                    </GlassCard>

                    {/* Mid-Morning */}
                    <GlassCard className="p-6 border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50/30 to-white hover:shadow-xl transition-all duration-300">
                      <div className="flex items-center mb-4">
                        <Apple className="h-6 w-6 text-emerald-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Mid-Morning Snack</h3>
                      </div>
                      <div className="mb-4">
                        <h4 className="text-lg font-bold text-emerald-700 mb-2 leading-tight">{mealPlan.mid_morning.title || 'Nutritious Snack'}</h4>
                        
                        {/* Nutrient Tags */}
                        {mealPlan.mid_morning.nutrient_tags && mealPlan.mid_morning.nutrient_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {mealPlan.mid_morning.nutrient_tags.map((tag, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded-full border border-emerald-200">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        {mealPlan.mid_morning.benefit && (
                          <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100/50 shadow-sm">
                            <p className="text-[11px] leading-relaxed text-emerald-700 font-medium">
                              <Lightbulb className="inline h-3.5 w-3.5 mr-2 -mt-0.5" />
                              <span className="font-bold underline decoration-emerald-200 mr-1 italic">Benefit:</span>
                              {mealPlan.mid_morning.benefit}
                            </p>
                          </div>
                        )}
                      </div>
                    </GlassCard>

                    {/* Lunch */}
                    <GlassCard className="p-6 border-l-4 border-l-orange-500 bg-gradient-to-br from-orange-50/30 to-white hover:shadow-xl transition-all duration-300">
                      <div className="flex items-center mb-4">
                        <Drumstick className="h-6 w-6 text-orange-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Lunch</h3>
                      </div>
                      <div className="mb-4">
                        <h4 className="text-lg font-bold text-orange-700 mb-2 leading-tight">{mealPlan.lunch.title || 'Balanced Indian Thali'}</h4>
                        
                        {/* Nutrient Tags */}
                        {mealPlan.lunch.nutrient_tags && mealPlan.lunch.nutrient_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {mealPlan.lunch.nutrient_tags.map((tag, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-orange-100 text-orange-700 text-[10px] font-bold rounded-full border border-orange-200">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}

                        <div className="bg-white/40 rounded-lg p-3 border border-orange-100/30 mb-3">
                          <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400 mb-2">Meal Components</p>
                          <ul className="space-y-1.5">
                            {Object.entries(mealPlan.lunch.components || {}).map(([key, val], i) => (
                              <li key={i} className="text-sm text-gray-700 flex justify-between">
                                <span className="font-semibold text-gray-500">{key}:</span>
                                <span>{val}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        {mealPlan.lunch.benefit && (
                          <div className="bg-orange-50/50 p-4 rounded-xl border border-orange-100/50 shadow-sm">
                            <p className="text-[11px] leading-relaxed text-orange-800 font-medium">
                              <Lightbulb className="inline h-3.5 w-3.5 mr-2 -mt-0.5" />
                              <span className="font-bold underline decoration-orange-200 mr-1 italic">Clinical Benefit:</span>
                              {mealPlan.lunch.benefit}
                            </p>
                          </div>
                        )}
                      </div>
                    </GlassCard>

                    {/* Evening Snack */}
                    <GlassCard className="p-6 border-l-4 border-l-purple-500 bg-gradient-to-br from-purple-50/30 to-white hover:shadow-xl transition-all duration-300">
                      <div className="flex items-center mb-4">
                        <Coffee className="h-6 w-6 text-purple-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Evening Snack</h3>
                      </div>
                      <div className="mb-4">
                        <h4 className="text-lg font-bold text-purple-700 mb-2 leading-tight">{mealPlan.evening_snack.title || 'Light Snack'}</h4>
                        
                        {/* Nutrient Tags */}
                        {mealPlan.evening_snack.nutrient_tags && mealPlan.evening_snack.nutrient_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {mealPlan.evening_snack.nutrient_tags.map((tag, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded-full border border-purple-200">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        {mealPlan.evening_snack.benefit && (
                          <div className="bg-purple-50/50 p-4 rounded-xl border border-purple-100/50 shadow-sm">
                            <p className="text-[11px] leading-relaxed text-purple-800 font-medium">
                              <Lightbulb className="inline h-3.5 w-3.5 mr-2 -mt-0.5" />
                              <span className="font-bold underline decoration-purple-200 mr-1 italic">Benefit:</span>
                              {mealPlan.evening_snack.benefit}
                            </p>
                          </div>
                        )}
                      </div>
                    </GlassCard>

                    {/* Dinner */}
                    <div className="md:col-span-2">
                      <GlassCard className="p-6 border-l-4 border-l-red-500 bg-gradient-to-br from-red-50/30 to-white hover:shadow-xl transition-all duration-300">
                        <div className="flex items-center mb-4">
                          <Utensils className="h-6 w-6 text-red-500 mr-3" />
                          <h3 className="text-xl font-bold text-gray-800">Dinner</h3>
                        </div>
                        <div className="mb-4">
                          <h4 className="text-lg font-bold text-red-700 mb-2 leading-tight">{mealPlan.dinner.title || 'Balanced Indian Dinner'}</h4>
                          
                          {/* Nutrient Tags */}
                          {mealPlan.dinner.nutrient_tags && mealPlan.dinner.nutrient_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              {mealPlan.dinner.nutrient_tags.map((tag, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded-full border border-red-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="bg-white/40 rounded-lg p-3 border border-red-100/30 mb-4">
                            <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400 mb-2">Meal Components</p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5">
                              {Object.entries(mealPlan.dinner.components || {}).map(([key, val], i) => (
                                <li key={i} className="text-sm text-gray-700 flex justify-between list-none">
                                  <span className="font-semibold text-gray-500">{key}:</span>
                                  <span>{val}</span>
                                </li>
                              ))}
                            </div>
                          </div>

                          {mealPlan.dinner.benefit && (
                            <div className="bg-red-50/50 p-4 rounded-xl border border-red-100/50 shadow-sm">
                              <p className="text-[11px] leading-relaxed text-red-800 font-medium">
                                <Lightbulb className="inline h-3.5 w-3.5 mr-2 -mt-0.5" />
                                <span className="font-bold underline decoration-red-200 mr-1 italic">Clinical Benefit:</span>
                                {mealPlan.dinner.benefit}
                              </p>
                            </div>
                          )}
                        </div>
                      </GlassCard>
                    </div>
                  </div>
                </GlassCard>

                {/* Hydration + Lifestyle side by side */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  {hydrationList.length > 0 && (
                    <GlassCard className="p-6">
                      <div className="flex items-center mb-4">
                        <Droplets className="h-6 w-6 text-blue-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Hydration Tips</h3>
                      </div>
                      <ul className="space-y-2">
                        {hydrationList.map((tip, idx) => (
                          <li key={idx} className="flex items-start text-sm">
                            <span className="text-blue-400 mr-2 mt-1">💧</span>
                            <span className="text-gray-700">{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </GlassCard>
                  )}
                  {lifestyleTips.length > 0 && (
                    <GlassCard className="p-6">
                      <div className="flex items-center mb-4">
                        <Lightbulb className="h-6 w-6 text-yellow-500 mr-3" />
                        <h3 className="text-xl font-bold text-gray-800">Lifestyle Tips</h3>
                      </div>
                      <ul className="space-y-2">
                        {lifestyleTips.map((tip, idx) => (
                          <li key={idx} className="flex items-start text-sm">
                            <span className="bg-yellow-100 text-yellow-700 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold mr-2 flex-shrink-0 mt-0.5">
                              {idx + 1}
                            </span>
                            <span className="text-gray-700">{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </GlassCard>
                  )}
                </div>

                {/* Parameter Reasoning (Gemini only) */}
                {isGemini && Object.keys(reasoning).length > 0 && (
                  <GlassCard className="p-6 mb-6">
                    <div className="flex items-center mb-4">
                      <Heart className="h-6 w-6 text-rose-500 mr-3" />
                      <h2 className="text-2xl font-bold text-gray-800">Why These Recommendations</h2>
                    </div>
                    <div className="space-y-3">
                      {Object.entries(reasoning).map(([param, reason]) => (
                        <div key={param} className="flex items-start">
                          <span className="bg-rose-100 text-rose-700 rounded-lg px-2 py-0.5 text-xs font-semibold mr-3 flex-shrink-0 mt-0.5">
                            {param}
                          </span>
                          <span className="text-gray-700 text-sm">{reason}</span>
                        </div>
                      ))}
                    </div>
                  </GlassCard>
                )}

                {/* Disclaimer */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                  <div className="flex items-start">
                    <Heart className="h-5 w-5 text-blue-500 mr-2.5 mt-0.5 flex-shrink-0" />
                    <p className="text-blue-800 text-sm">{disclaimer}</p>
                  </div>
                </div>
              </>
            )}

            {/* Extracted Text Toggle */}
            <GlassCard className="p-4 mb-6">
              <button
                onClick={() => setShowExtractedText(!showExtractedText)}
                className="flex items-center justify-between w-full text-left"
              >
                <div className="flex items-center">
                  <FileSearch className="h-5 w-5 text-gray-500 mr-2" />
                  <span className="text-sm font-medium text-gray-700">View Extracted Text (OCR output)</span>
                </div>
                {showExtractedText ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </button>
              <AnimatePresence>
                {showExtractedText && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <pre className="mt-4 p-4 bg-gray-50 rounded-xl text-xs text-gray-600 max-h-64 overflow-auto whitespace-pre-wrap font-mono">
                      {result.extracted_text || 'No text extracted'}
                    </pre>
                  </motion.div>
                )}
              </AnimatePresence>
            </GlassCard>

            {/* Sticky Floating Action Bar */}
            <div className="sticky bottom-6 mt-12 mb-6 px-1 flex items-center justify-center gap-4 flex-wrap z-20">
              <div className="bg-white/40 backdrop-blur-md border border-white/50 p-3 rounded-2xl shadow-2xl flex items-center justify-center gap-4 flex-wrap">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleExportAnalysis}
                  disabled={exportLoading}
                  className="flex items-center space-x-2 px-6 py-4 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-semibold shadow-xl hover:shadow-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  {exportLoading ? (
                    <Loader2Icon className="h-5 w-5 animate-spin" />
                  ) : (
                    <Download className="h-5 w-5 group-hover:translate-y-0.5 transition-transform" />
                  )}
                  <span>{exportLoading ? 'Generating PDF...' : 'Export to PDF'}</span>
                </motion.button>
                
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={resetForm}
                  className="px-8 py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-xl font-semibold shadow-xl hover:shadow-2xl transition-all duration-300"
                >
                  Analyze Another Report
                </motion.button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  // ---- UPLOAD VIEW ----
  return (
    <div className="relative min-h-screen pt-20 pb-12">
      <AnimatedBackground />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-teal-600 to-cyan-600 bg-clip-text text-transparent">
            Medical Report Analyzer
          </h1>
          <p className="text-xl text-gray-600">
            Upload your blood test report and get AI-powered diet recommendations
          </p>
        </motion.div>

        <GlassCard className="p-8">
          {/* File Upload */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300 ${
              dragActive
                ? 'border-teal-500 bg-teal-50/50'
                : file
                ? 'border-green-400 bg-green-50/30'
                : 'border-gray-300 hover:border-teal-400'
            }`}
          >
            <input
              type="file"
              id="report-upload"
              onChange={handleFileInput}
              accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp"
              className="hidden"
            />
            <label htmlFor="report-upload" className="cursor-pointer">
              {file ? (
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="flex flex-col items-center"
                >
                  <FileText className="h-12 w-12 text-green-500 mb-3" />
                  <p className="text-gray-800 font-semibold text-lg">{file.name}</p>
                  <p className="text-gray-500 text-sm mt-1">
                    {(file.size / 1024).toFixed(1)} KB &middot; Click to change
                  </p>
                </motion.div>
              ) : (
                <div className="flex flex-col items-center">
                  <Upload className="h-14 w-14 text-gray-400 mb-4" />
                  <p className="text-gray-700 text-lg font-medium mb-1">
                    Drop your medical report here
                  </p>
                  <p className="text-gray-500 text-sm">or click to browse</p>
                  <p className="text-gray-400 text-xs mt-3">
                    Supports JPG, PNG, PDF, BMP, TIFF &middot; Max 10 MB
                  </p>
                </div>
              )}
            </label>
          </div>

          {/* OR Divider */}
          {!loading && !file && (
            <div className="relative my-10">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500 font-bold uppercase tracking-widest text-xs">
                  Or Enter Parameters Manually
                </span>
              </div>
            </div>
          )}

          {/* Manual Entry Form */}
          {!loading && !file && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-700 text-sm font-semibold mb-2 block">Age</label>
                  <input
                    type="number"
                    name="age"
                    value={healthData.age}
                    onChange={handleInputChange}
                    placeholder="25"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none"
                  />
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-semibold mb-2 block">Weight (kg)</label>
                  <input
                    type="number"
                    name="weight"
                    value={healthData.weight}
                    onChange={handleInputChange}
                    placeholder="70"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none"
                  />
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-semibold mb-2 block">Height (cm)</label>
                  <input
                    type="number"
                    name="height"
                    value={healthData.height}
                    onChange={handleInputChange}
                    placeholder="170"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-gray-700 text-sm font-semibold mb-2 block">Activity Level</label>
                  <select
                    name="activityLevel"
                    value={healthData.activityLevel}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none bg-white"
                  >
                    <option value="sedentary">Sedentary</option>
                    <option value="light">Light Activity</option>
                    <option value="moderate">Moderate Activity</option>
                    <option value="active">Very Active</option>
                    <option value="extreme">Extremely Active</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-700 text-sm font-semibold mb-2 block">Dietary Preference</label>
                  <select
                    name="dietaryPreference"
                    value={healthData.dietaryPreference}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none bg-white"
                  >
                    <option value="none">No Preference</option>
                    <option value="vegetarian">Vegetarian</option>
                    <option value="vegan">Vegan</option>
                    <option value="keto">Keto</option>
                    <option value="paleo">Paleo</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-gray-700 text-sm font-semibold mb-2 block">Health Conditions & Allergies</label>
                <textarea
                  name="healthConditions"
                  value={healthData.healthConditions}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="e.g., Diabetes, High blood pressure, Lactose intolerance..."
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 transition-all outline-none resize-none"
                />
              </div>
            </div>
          )}

          {/* Progress Bar */}
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500">Analyzing report...</span>
                <span className="text-sm font-mono text-gray-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <motion.div
                  className="bg-gradient-to-r from-teal-500 to-cyan-500 h-2.5 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(progress, 10)}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2 text-center">
                OCR extraction and parameter analysis may take a few seconds...
              </p>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 flex items-start"
            >
              <XCircle className="h-5 w-5 text-red-500 mr-2.5 mt-0.5 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </motion.div>
          )}

          {/* Submit */}
          <motion.button
            type="button"
            disabled={(!file && !healthData.age) || loading}
            whileHover={!loading && (file || healthData.age) ? { scale: 1.02 } : {}}
            whileTap={!loading && (file || healthData.age) ? { scale: 0.98 } : {}}
            onClick={handleSubmit}
            className="mt-8 w-full bg-gradient-to-r from-teal-500 to-cyan-500 text-white px-6 py-4 rounded-xl font-semibold text-lg shadow-xl hover:shadow-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center font-bold tracking-tight"
          >
            {loading ? (
              <>
                <Loader className="animate-spin h-5 w-5 mr-2" />
                {file ? 'Analyzing Report...' : 'Generating Diet Plan...'}
              </>
            ) : (
              <>
                {file ? (
                  <>
                    <Microscope className="h-5 w-5 mr-2" />
                    Analyze Report
                  </>
                ) : (
                  <>
                    <Utensils className="h-5 w-5 mr-2" />
                    Generate Diet Plan
                  </>
                )}
              </>
            )}
          </motion.button>
        </GlassCard>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          {[
            {
              icon: <FileSearch className="h-6 w-6 text-teal-500" />,
              title: 'OCR Scanning',
              desc: 'Advanced text extraction from medical report images & PDFs',
            },
            {
              icon: <Microscope className="h-6 w-6 text-blue-500" />,
              title: 'Parameter Detection',
              desc: 'Identifies 35+ blood test parameters with abnormality flags',
            },
            {
              icon: <Apple className="h-6 w-6 text-green-500" />,
              title: 'Diet Recommendations',
              desc: 'Personalised nutrition plan based on your test results',
            },
          ].map((feat, idx) => (
            <GlassCard key={idx} className="p-5 text-center">
              <div className="flex justify-center mb-3">{feat.icon}</div>
              <h4 className="font-semibold text-gray-800 mb-1">{feat.title}</h4>
              <p className="text-gray-500 text-xs">{feat.desc}</p>
            </GlassCard>
          ))}
        </motion.div>
      </div>
    </div>
  );
};

export default ReportAnalyzer;
