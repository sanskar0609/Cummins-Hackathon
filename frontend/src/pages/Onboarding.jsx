import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, Sparkles, PackagePlus, FileSpreadsheet, CheckCircle2, ChevronRight, Loader2, ArrowRight, Lock, LogOut, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';

// ─── PROFILE ALREADY EXISTS — show locked view ────────────────────────────────
function ProfileLockedView({ companyName, industry, onLogout }) {
  return (
    <div className="min-h-screen bg-[#050B14] flex flex-col items-center justify-center font-sans text-slate-300 relative overflow-hidden">
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-900/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-blue-900/20 rounded-full blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full mx-auto px-6 relative z-10"
      >
        <div className="bg-[#0B1221]/80 backdrop-blur-xl border border-cyan-700/30 p-8 rounded-2xl shadow-2xl text-center space-y-6">
          <div className="w-20 h-20 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto">
            <ShieldCheck className="w-10 h-10 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Profile Active</h2>
            <p className="text-slate-400 text-sm">Your workspace is scoped to this company profile. Log out to switch profiles.</p>
          </div>

          <div className="bg-[#131E32] border border-slate-700 rounded-xl p-5 text-left space-y-3">
            <div className="flex items-center gap-3">
              <Building2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Company Name</p>
                <p className="text-white font-semibold">{companyName}</p>
              </div>
            </div>
            {industry && (
              <div className="flex items-center gap-3 border-t border-slate-700/50 pt-3">
                <Sparkles className="w-4 h-4 text-purple-400 shrink-0" />
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Industry / Sector</p>
                  <p className="text-white font-semibold">{industry}</p>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-700/50">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              <p className="text-[10px] text-slate-500 font-mono">All intelligence data is isolated to this workspace</p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => window.location.href = '/demand'}
              className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-3 rounded-lg transition-all flex items-center justify-center gap-2"
            >
              Go to Dashboard <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={onLogout}
              className="px-4 py-3 border border-slate-600 hover:border-red-500/50 hover:bg-red-900/20 text-slate-400 hover:text-red-400 rounded-lg transition-all flex items-center gap-2 text-sm"
            >
              <LogOut className="w-4 h-4" /> Log out
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [companyData, setCompanyData] = useState({ name: '', industry: '' });
  const [importMethod, setImportMethod] = useState('');
  const [aiDescription, setAiDescription] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [skus, setSkus] = useState([]);
  const [csvPath, setCsvPath] = useState('');

  // Check if profile already exists in localStorage
  const existingId   = localStorage.getItem('company_id');
  const existingName = localStorage.getItem('company_name');
  const existingIndustry = localStorage.getItem('company_industry');

  const handleLogout = () => {
    localStorage.removeItem('company_id');
    localStorage.removeItem('company_name');
    localStorage.removeItem('company_industry');
    toast.success('Logged out. You can now create a new profile.');
    window.location.reload();
  };

  // If profile is already set, show locked view
  if (existingId && existingName) {
    return <ProfileLockedView companyName={existingName} industry={existingIndustry} onLogout={handleLogout} />;
  }

  const handleCsvUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsExtracting(true);
    const toastId = toast.loading("Processing CSV...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("https://cummins-hackathon.onrender.com/api/v1/onboarding/upload-csv", { method: "POST", body: formData });
      const data = await res.json();
      if (data.skus && data.skus.length > 0) {
        setSkus(data.skus);
        if (data.csv_path) setCsvPath(data.csv_path);
        toast.success(`Imported ${data.skus.length} products from CSV!`, { id: toastId });
        setStep(3);
      } else {
        toast.error(data.detail || "Failed to process CSV.", { id: toastId });
      }
    } catch (err) {
      toast.error("Upload failed.", { id: toastId });
    } finally {
      setIsExtracting(false);
    }
  };

  const handleAiExtraction = async () => {
    if (!aiDescription) return toast.error("Please describe your products first!");
    setIsExtracting(true);
    const toastId = toast.loading("AI is mapping your categories...");
    try {
      const res = await fetch("https://cummins-hackathon.onrender.com/api/v1/onboarding/extract-skus", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: aiDescription })
      });
      const data = await res.json();
      if (data.skus && data.skus.length > 0) {
        setSkus(data.skus);
        if (data.csv_path) setCsvPath(data.csv_path);
        toast.success(`Extracted ${data.skus.length} products!`, { id: toastId });
        setStep(3);
      } else {
        toast.error("No clear products found, please try again.", { id: toastId });
      }
    } catch (err) {
      toast.error("Extraction failed.", { id: toastId });
    } finally {
      setIsExtracting(false);
    }
  };

  const handleFinish = async () => {
    const toastId = toast.loading("Saving workspace configuration...");
    try {
      const res = await fetch("https://cummins-hackathon.onrender.com/api/v1/onboarding/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: companyData.name, industry: companyData.industry, skus, csv_path: csvPath })
      });
      const data = await res.json();
      if (data.company_id) localStorage.setItem('company_id', data.company_id);
      localStorage.setItem('company_name', companyData.name);
      localStorage.setItem('company_industry', companyData.industry);
      toast.success("Workspace setup complete!", { id: toastId });
      setTimeout(() => { window.location.href = '/demand'; }, 1500);
    } catch (err) {
      toast.error("Failed to save.", { id: toastId });
    }
  };

  return (
    <div className="min-h-screen bg-[#050B14] flex flex-col pt-16 font-sans text-slate-300 relative overflow-hidden">
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-900/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-blue-900/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="max-w-4xl mx-auto w-full px-6 relative z-10">

        {/* Header Steps */}
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-500 ${step >= 1 ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' : 'bg-slate-800 text-slate-500'}`}>1</div>
            <span className={step >= 1 ? 'text-cyan-300 font-medium tracking-wide' : 'text-slate-500'}>Company Profile</span>
          </div>
          <div className={`h-px flex-1 mx-4 ${step >= 2 ? 'bg-cyan-500/50' : 'bg-slate-800 transition-colors duration-700'}`} />
          <div className="flex items-center gap-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-500 ${step >= 2 ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' : 'bg-slate-800 text-slate-500'}`}>2</div>
            <span className={step >= 2 ? 'text-cyan-300 font-medium tracking-wide' : 'text-slate-500'}>SKU Catalog</span>
          </div>
          <div className={`h-px flex-1 mx-4 ${step >= 3 ? 'bg-cyan-500/50' : 'bg-slate-800 transition-colors duration-700'}`} />
          <div className="flex items-center gap-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-500 ${step >= 3 ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' : 'bg-slate-800 text-slate-500'}`}>3</div>
            <span className={step >= 3 ? 'text-cyan-300 font-medium tracking-wide' : 'text-slate-500'}>Finalize</span>
          </div>
        </div>

        <div className="bg-[#0B1221]/80 backdrop-blur-xl border border-slate-700/50 p-8 rounded-2xl shadow-2xl min-h-[500px] flex flex-col justify-center">
          <AnimatePresence mode="wait">

            {/* STEP 1 */}
            {step === 1 && (
              <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-white mb-2">Welcome to SupplyOS</h2>
                  <p className="text-slate-400">Let's scope the intelligence engine to your business footprint.</p>
                </div>
                <div className="space-y-4 max-w-md mx-auto">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">Company Name</label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <input
                        type="text" value={companyData.name}
                        onChange={e => setCompanyData({...companyData, name: e.target.value})}
                        className="w-full bg-[#131E32] border border-slate-700 rounded-lg py-3 pl-10 pr-4 text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
                        placeholder="e.g. Acme Appliances"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">Industry / Sector</label>
                    <input
                      type="text" value={companyData.industry}
                      onChange={e => setCompanyData({...companyData, industry: e.target.value})}
                      className="w-full bg-[#131E32] border border-slate-700 rounded-lg py-3 px-4 text-white focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
                      placeholder="e.g. Consumer Electronics"
                    />
                  </div>
                  <button
                    onClick={() => {
                      if(!companyData.name || !companyData.industry) return toast.error("Please fill in both fields");
                      setStep(2);
                    }}
                    className="w-full mt-8 bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-all group"
                  >
                    Continue to Catalog <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 2 */}
            {step === 2 && (
              <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6 flex flex-col h-full">
                <div className="text-center mb-4">
                  <h2 className="text-3xl font-bold text-white mb-2">Initialize Product Catalog</h2>
                  <p className="text-slate-400">How would you like to import the SKUs we should monitor?</p>
                </div>
                {!importMethod ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                    <div onClick={() => setImportMethod('ai')} className="cursor-pointer bg-[#131E32] hover:bg-[#1C2A44] border border-cyan-800/30 hover:border-cyan-500/50 group p-6 rounded-xl transition-all flex flex-col items-center text-center">
                      <div className="w-16 h-16 rounded-full bg-cyan-900/30 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <Sparkles className="w-8 h-8" />
                      </div>
                      <h3 className="text-lg font-medium text-white mb-2">Describe with AI</h3>
                      <p className="text-sm text-slate-400">Just type what you sell in plain English. AI will automatically map it to structured SKUs.</p>
                      <span className="mt-4 text-xs font-semibold uppercase tracking-wider text-cyan-500 bg-cyan-500/10 px-3 py-1 rounded-full">Recommended</span>
                    </div>
                    <div className="relative cursor-pointer bg-[#131E32] hover:bg-[#1C2A44] border border-slate-700 hover:border-slate-500 p-6 rounded-xl transition-all flex flex-col items-center text-center opacity-80 hover:opacity-100">
                      <input type="file" accept=".csv" disabled={isExtracting} onChange={handleCsvUpload} className="absolute inset-0 opacity-0 cursor-pointer z-10" />
                      <div className="w-16 h-16 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mb-4">
                        <FileSpreadsheet className="w-8 h-8" />
                      </div>
                      <h3 className="text-lg font-medium text-white mb-2">Paste / CSV Upload</h3>
                      <p className="text-sm text-slate-400">Drop your Tally or Zoho export file directly. We'll map the columns automatically.</p>
                      {isExtracting && (
                        <div className="absolute inset-0 bg-slate-900/60 flex items-center justify-center rounded-xl z-20">
                          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col h-full items-center">
                    <div className="w-full max-w-2xl bg-[#131E32] border border-slate-700 rounded-xl p-6 relative">
                      <button onClick={() => setImportMethod('')} className="absolute top-4 right-4 text-xs text-slate-500 hover:text-white">Change Method</button>
                      <h3 className="text-cyan-400 font-medium flex items-center gap-2 mb-4"><Sparkles className="w-4 h-4"/> AI Catalog Extraction</h3>
                      <textarea
                        value={aiDescription} onChange={e => setAiDescription(e.target.value)}
                        placeholder="Example: We sell home appliances like Induction Stoves, Pressure Cookers (3L and 5L), and 750W Mixer Grinders..."
                        className="w-full h-32 bg-[#0B1221] border border-slate-700/50 rounded-lg p-4 text-white focus:outline-none focus:border-cyan-500 resize-none mb-4"
                      />
                      <button onClick={handleAiExtraction} disabled={isExtracting}
                        className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-all"
                      >
                        {isExtracting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                        {isExtracting ? "Analyzing & Mapping..." : "Extract SKUs"}
                      </button>
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {/* STEP 3 */}
            {step === 3 && (
              <motion.div key="step3" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6 text-center flex flex-col items-center">
                <div className="w-20 h-20 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-2">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
                <h2 className="text-3xl font-bold text-white">Catalog Initialized</h2>
                <p className="text-slate-400 max-w-md">Successfully mapped <strong className="text-white">{skus.length}</strong> products for {companyData.name}. All live signal tracking will now be contextualized to these items.</p>
                {csvPath && (
                  <div className="mt-4 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-2 text-emerald-400 text-xs font-mono">
                    <FileSpreadsheet className="w-4 h-4" />
                    Generated Master Catalog CSV: {csvPath.split(/[\\\/]/).pop()}
                  </div>
                )}
                <div className="w-full max-w-2xl bg-[#131E32] border border-slate-700 rounded-xl overflow-hidden mt-6 text-left">
                  <table className="w-full text-sm">
                    <thead className="bg-[#1C2A44] border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3 text-slate-400 font-medium">SKU ID</th>
                        <th className="px-4 py-3 text-slate-400 font-medium">Product Name</th>
                        <th className="px-4 py-3 text-slate-400 font-medium">Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {skus.map((s, i) => (
                        <tr key={i} className="border-b border-slate-800/50 hover:bg-[#1C2A44]/50">
                          <td className="px-4 py-3 text-cyan-400 font-mono text-xs">{s.sku}</td>
                          <td className="px-4 py-3 text-white">{s.name}</td>
                          <td className="px-4 py-3 text-slate-400">{s.category}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button onClick={handleFinish}
                  className="mt-8 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-lg shadow-cyan-900/20 text-white font-medium py-3 px-12 rounded-lg flex items-center justify-center gap-2 transition-all hover:scale-105"
                >
                  <PackagePlus className="w-5 h-5" /> Launch Dashboard Environment
                </button>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
