import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertTriangle, ShieldAlert, CheckCircle2, 
  FileText, ArrowRight, Activity, DollarSign, Package, Bot, RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'

// ─── UTILS ─────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_BASE_URL

// ─── COMPONENT ────────────────────────────────────────────────────────
export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(true)
  const [alertsError, setAlertsError] = useState(null)

  const [activeDraft, setActiveDraft] = useState(null)
  const [isGeneratingPO, setIsGeneratingPO] = useState(false)
  const [draftErrorAlert, setDraftErrorAlert] = useState(null)
  
  const [isProcessingAlert, setIsProcessingAlert] = useState(null)

  // Fetch real alerts
  const fetchAlerts = async () => {
    setIsLoadingAlerts(true)
    setAlertsError(null)
    try {
      const res = await fetch(`${API_BASE}/alerts`)
      if (!res.ok) throw new Error('API unreachable')
      const data = await res.json()
      setAlerts(Array.isArray(data) ? data : (data.alerts || []))
    } catch (error) {
      setAlertsError(error.message)
    } finally {
      setIsLoadingAlerts(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
  }, [])

  const getSeverityStyle = (sev) => {
    switch (sev?.toLowerCase()) {
      case 'critical': return 'bg-sc_red/20 text-sc_red border-sc_red/40 shadow-[0_0_15px_rgba(251,113,133,0.3)]'
      case 'high': return 'bg-sc_orange/20 text-sc_orange border-sc_orange/40 shadow-[0_0_15px_rgba(249,115,22,0.2)]'
      case 'medium': return 'bg-sc_yellow/20 text-sc_yellow border-sc_yellow/40'
      default: return 'bg-sc_cyan/20 text-sc_cyan border-sc_cyan/40'
    }
  }

  const getSeverityIcon = (sev) => {
    switch (sev?.toLowerCase()) {
      case 'critical': return <ShieldAlert className="w-4 h-4" />
      case 'high': return <AlertTriangle className="w-4 h-4" />
      case 'medium': return <Activity className="w-4 h-4" />
      default: return <AlertTriangle className="w-4 h-4" />
    }
  }

  // 1. Alert Action: Approve & Trigger Agent
  const handleApproveAlert = async (alert) => {
    setIsProcessingAlert(alert.id || alert._id || 'unknown')
    setDraftErrorAlert(null)
    try {
      const alertSource = alert.rawSource || alert.source || alert.type || 'SYSTEM_ALERT'
      const alertId = alert.id || alert._id || 'unknown'
      const alertSum = alert.summary || alert.description || ''

      const res = await fetch(`${API_BASE}/agents/alerts/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alert_source: alertSource,
          raw_context: { internal_id: alertId, summary: alertSum }
        })
      })
      
      if (!res.ok) throw new Error('Failed to trigger LangGraph agent')
      const data = await res.json()

      toast.success(
        <div>
          <p className="font-bold">Agent Triggered</p>
          <p className="text-xs text-slate-300">{data.recommended_action || 'Slack integration deployed.'}</p>
        </div>,
        { icon: '🤖', style: { background: '#0b0f17', color: '#fff', border: '1px solid #4ade80' } }
      )
      
      // Attempt to generate PO Draft
      generatePODraft(alert)

      // Remove from timeline
      setAlerts(prev => prev.filter(a => (a.id || a._id) !== alertId))
    } catch (error) {
      toast.error('Failed to trigger LangGraph agent.', { style: { background: '#0b0f17', color: '#fff' } })
    } finally {
      setIsProcessingAlert(null)
    }
  }

  const handleDismissAlert = (alert) => {
    const alertId = alert.id || alert._id
    setAlerts(prev => prev.filter(a => (a.id || a._id) !== alertId))
    toast('Alert dismissed.', { icon: '🧹', style: { background: '#0b0f17', color: '#fff' } })
  }

  // 2. PO Agent Generator
  const generatePODraft = async (alert) => {
    setIsGeneratingPO(true)
    setActiveDraft(null)
    setDraftErrorAlert(null)
    try {
      const res = await fetch(`${API_BASE}/agents/po/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ds_ratio: alert.ds_ratio || 2.5,
          sku: alert.sku || alert.affected || "SKU-UNKNOWN",
          current_supply: alert.current_supply || 1000
        })
      })
      if (!res.ok) throw new Error('API Error')
      const data = await res.json()
      
      setActiveDraft({
        sku: data.po_draft?.sku || data.sku || alert.sku || alert.affected || "SKU-UNKNOWN",
        supplier: data.po_draft?.supplier || data.supplier || "Auto-selected Alternative Supplier",
        qty: data.po_draft?.qty || data.qty || "Determined by logic model",
        estimatedCost: data.po_draft?.estimatedCost || data.estimatedCost || "Calculated at Execution",
        justification: data.po_draft?.justification || data.po_draft || data.justification || "LangGraph reasoning applied to mitigate disruption.",
      })
      
    } catch (err) {
      // Step 6g: Show error state in right panel instead of fallback block
      setDraftErrorAlert(alert)
    } finally {
      setIsGeneratingPO(false)
    }
  }

  const handleExecutePO = () => {
    toast.success('Autonomous PO Approved & Executed!', { 
      icon: '✅', 
      style: { background: '#0b0f17', color: '#4ade80', border: '1px solid #4ade80' } 
    })
    setActiveDraft(null)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      
      {/* ── HEADER ── */}
      <header className="flex-shrink-0 px-6 py-5 border-b border-white/5 bg-[rgba(6,8,13,0.6)] backdrop-blur-xl relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sc_orange/10 border border-sc_orange/30 flex items-center justify-center shadow-[0_0_20px_rgba(249,115,22,0.15)]">
            <Bot className="w-5 h-5 text-sc_orange" />
          </div>
          <div>
            <h1 className="text-xl font-mono font-bold text-white tracking-tight">Enterprise Alerts &amp; Autonomous Agents</h1>
            <p className="text-xs font-mono text-slate-400">Review LangGraph agent intercept recommendations &amp; execute smart contracts</p>
          </div>
        </div>
      </header>

      {/* ── TWO COLUMN LAYOUT ── */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6 p-6 overflow-hidden">
        
        {/* LEFT COLUMN: ALERT TIMELINE */}
        <div className="flex-1 flex flex-col min-h-0 bg-sc_card border border-white/5 rounded-2xl shadow-xl overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-br from-sc_orange/5 to-transparent pointer-events-none" />
          
          <div className="flex-shrink-0 px-5 py-4 border-b border-white/5 bg-sc_elevated/30 flex items-center justify-between z-10">
            <h2 className="text-sm font-bold font-mono text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-sc_orange" />
              Intelligence Timeline
            </h2>
            <span className="text-xs font-mono text-slate-500 bg-white/5 px-2 py-1 rounded border border-white/10">
              {alerts.length} Active
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4 relative z-10" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(249,115,22,0.2) transparent' }}>
            
            {/* Loading Skeleton */}
            {isLoadingAlerts && (
              <div className="space-y-4">
                {[1,2,3].map(i => (
                  <div key={i} className="bg-sc_elevated/50 border border-white/5 rounded-xl p-4 h-40 animate-pulse flex flex-col justify-between">
                    <div className="flex justify-between w-full"><div className="w-24 h-5 bg-white/10 rounded" /><div className="w-16 h-3 bg-white/5 rounded" /></div>
                    <div className="w-3/4 h-3 bg-white/10 rounded" />
                    <div className="w-full h-12 bg-white/5 rounded" />
                    <div className="flex gap-2"><div className="w-1/2 h-8 bg-white/10 rounded" /><div className="w-1/4 h-8 bg-white/5 rounded" /></div>
                  </div>
                ))}
              </div>
            )}

            {/* Error Banner */}
            {!isLoadingAlerts && alertsError && (
              <div className="h-full flex flex-col items-center justify-center text-center gap-4">
                <AlertTriangle className="w-12 h-12 text-sc_red bg-sc_red/10 p-2 rounded-full border border-sc_red/20 shadow-[0_0_20px_rgba(251,113,133,0.15)]" />
                <div>
                  <p className="text-sm font-mono text-sc_red font-bold">⚠ Unable to reach Alert Intelligence Service.</p>
                  <p className="text-xs font-mono text-slate-400 mt-1">Backend connection refused or quota exhausted.</p>
                </div>
                <button 
                  onClick={fetchAlerts}
                  className="px-4 py-2 mt-2 bg-sc_red/20 hover:bg-sc_red/30 border border-sc_red/40 text-sc_red rounded text-xs font-mono transition-colors flex items-center gap-2"
                >
                  <RefreshCw className="w-3 h-3" /> Retry Connection
                </button>
              </div>
            )}

            {/* Empty State */}
            {!isLoadingAlerts && !alertsError && alerts.length === 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full flex flex-col items-center justify-center text-slate-500 space-y-3">
                <CheckCircle2 className="w-10 h-10 text-sc_green/40 shadow-[0_0_20px_rgba(74,222,128,0.1)] rounded-full" />
                <p className="text-sm font-mono">No active threats. System nominal.</p>
              </motion.div>
            )}
            
            <AnimatePresence>
              {!isLoadingAlerts && !alertsError && alerts.map((alert) => {
                const alertId = alert.id || alert._id || Math.random().toString()
                const sev = alert.severity || 'medium'
                const type = alert.type || alert.alert_type || 'System Alert'
                const timestamp = alert.timestamp || new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'})
                const affected = alert.affected || alert.target_node || alert.sku || 'Unknown Impact Area'
                const summary = alert.summary || alert.description || 'No detailed scenario generated.'
                const recAction = alert.recommendedAction || alert.recommended_action || 'Review dependencies manually.'

                return (
                  <motion.div
                    key={alertId}
                    initial={{ opacity: 0, scale: 0.98, x: -10 }}
                    animate={{ opacity: 1, scale: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.95, height: 0, marginBottom: 0 }}
                    transition={{ duration: 0.3 }}
                    className="bg-sc_elevated/60 backdrop-blur-md border border-white/10 rounded-xl p-4 flex flex-col gap-3 group hover:border-sc_orange/30 transition-all shadow-lg relative z-10"
                  >
                    {/* Alert Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase tracking-wider border flex items-center gap-1.5 ${getSeverityStyle(sev)}`}>
                          {getSeverityIcon(sev)}
                          {sev}
                        </span>
                        <span className="text-xs font-mono font-bold text-white">{type}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">{timestamp}</span>
                    </div>

                    {/* Body */}
                    <div>
                      <p className="text-xs font-mono text-sc_orange mb-1 font-semibold">{affected}</p>
                      <p className="text-sm text-slate-300 leading-relaxed mb-3">{summary}</p>
                      <div className="bg-[#06080d] rounded-lg p-3 border border-white/5 flex items-start gap-2">
                        <Bot className="w-4 h-4 text-sc_purple shrink-0 mt-0.5" />
                        <div>
                          <p className="text-[10px] font-mono text-sc_purple uppercase tracking-widest mb-1">Agent Recommendation</p>
                          <p className="text-xs text-slate-400">{recAction}</p>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 mt-1">
                      <button
                        onClick={() => handleApproveAlert(alert)}
                        disabled={isProcessingAlert === alertId}
                        className="flex-1 bg-sc_orange text-white hover:bg-orange-500 py-2 rounded-lg text-xs font-mono font-bold transition-all shadow-[0_0_15px_rgba(249,115,22,0.2)] hover:shadow-[0_0_20px_rgba(249,115,22,0.4)] disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {isProcessingAlert === alertId ? <Bot className="w-4 h-4 animate-bounce" /> : <CheckCircle2 className="w-4 h-4" />}
                        {isProcessingAlert === alertId ? 'Deploying...' : 'Approve Execution'}
                      </button>
                      <button
                        onClick={() => handleDismissAlert(alert)}
                        disabled={isProcessingAlert === alertId}
                        className="px-4 py-2 border border-white/10 hover:border-sc_red/50 hover:text-sc_red hover:bg-sc_red/10 text-slate-400 rounded-lg text-xs font-mono font-bold transition-all disabled:opacity-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        </div>

        {/* RIGHT COLUMN: PO DRAFT PANEL */}
        <div className="w-full lg:w-[420px] flex-shrink-0 flex flex-col min-h-0 bg-sc_card border border-white/5 rounded-2xl shadow-xl overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-t from-[#0b0f17] to-transparent pointer-events-none" />
          
          <div className="flex-shrink-0 px-5 py-4 border-b border-white/5 bg-[rgba(168,85,247,0.05)] flex items-center gap-2 z-10">
            <FileText className="w-4 h-4 text-sc_purple" />
            <h2 className="text-sm font-bold font-mono text-white">Autonomous PO Draft</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-5 flex flex-col relative z-10" style={{ scrollbarWidth: 'none' }}>
            
            {isGeneratingPO && (
              <div className="absolute inset-0 z-20 bg-sc_card/80 backdrop-blur-sm flex flex-col items-center justify-center">
                <Bot className="w-10 h-10 text-sc_purple animate-pulse mb-3" />
                <p className="text-sm font-mono text-sc_purple">Agent drafting procurement contract...</p>
                <div className="w-32 h-1 bg-white/10 rounded-full mt-4 overflow-hidden">
                  <motion.div className="h-full bg-sc_purple" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }} />
                </div>
              </div>
            )}

            {!activeDraft && !isGeneratingPO && !draftErrorAlert && (
              <div className="flex-1 flex flex-col items-center justify-center text-center opacity-40">
                <Package className="w-12 h-12 text-slate-500 mb-3" />
                <p className="text-sm font-mono text-slate-400">No active PO drafts.<br/>Approve an alert to invoke agent.</p>
              </div>
            )}

            {/* Error State for PO Generation */}
            {draftErrorAlert && !isGeneratingPO && (
              <div className="flex-1 flex flex-col items-center justify-center text-center gap-3">
                <AlertTriangle className="w-12 h-12 text-sc_orange bg-sc_orange/10 p-2 rounded-full border border-sc_orange/20 shadow-[0_0_20px_rgba(249,115,22,0.15)]" />
                <div>
                  <p className="text-sm font-mono text-sc_orange font-bold">Agent unavailable.</p>
                  <p className="text-xs font-mono text-slate-400 mt-1 max-w-[250px]">PO draft could not be generated. Please retry or escalate manually.</p>
                </div>
                <button 
                  onClick={() => generatePODraft(draftErrorAlert)}
                  className="px-4 py-2 mt-3 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 rounded text-xs font-mono transition-colors flex items-center gap-2"
                >
                  <RefreshCw className="w-3 h-3" /> Retry Generation
                </button>
              </div>
            )}

            {activeDraft && !isGeneratingPO && !draftErrorAlert && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col h-full">
                
                {/* Meta block */}
                <div className="bg-sc_elevated/50 border border-white/5 rounded-xl p-4 space-y-4 mb-4">
                  <div className="flex justify-between items-center border-b border-white/5 pb-3">
                    <span className="text-xs font-mono text-slate-500">Target Object</span>
                    <span className="text-sm font-mono font-bold text-sc_cyan">{activeDraft.sku}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-white/5 pb-3">
                    <span className="text-xs font-mono text-slate-500">Vendor Node</span>
                    <span className="text-sm font-mono font-bold text-white">{activeDraft.supplier}</span>
                  </div>
                  <div className="flex justify-between items-center bg-white/5 p-2 rounded">
                    <span className="text-xs font-mono text-slate-400">Procurement Vol</span>
                    <span className="text-sm font-mono font-bold text-white tracking-widest">{activeDraft.qty}</span>
                  </div>
                </div>

                {/* AI Context */}
                <div className="mb-4">
                  <p className="text-[10px] font-mono text-sc_purple uppercase tracking-widest mb-2 flex items-center gap-1">
                    <Bot className="w-3 h-3" /> LangGraph Reasoning Context
                  </p>
                  <p className="text-xs text-slate-300 leading-relaxed bg-[rgba(168,85,247,0.08)] border border-sc_purple/20 p-3 rounded-lg border-l-2 border-l-sc_purple">
                    {activeDraft.justification}
                  </p>
                </div>

                {/* Fiscal Impact */}
                <div className="mb-auto">
                  <div className="flex items-center justify-between p-4 rounded-xl border border-sc_green/20 bg-sc_green/5">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-5 h-5 text-sc_green" />
                      <span className="text-sm font-mono text-slate-300">Total Liability</span>
                    </div>
                    <span className="text-lg font-mono font-bold text-sc_green">{activeDraft.estimatedCost}</span>
                  </div>
                </div>

                {/* Exec Actions */}
                <div className="mt-6 flex flex-col gap-2">
                  <button onClick={handleExecutePO} className="w-full py-3 bg-sc_green hover:bg-green-500 text-black rounded-lg text-sm font-mono font-bold transition-all shadow-[0_0_20px_rgba(74,222,128,0.2)] hover:shadow-[0_0_30px_rgba(74,222,128,0.4)] flex items-center justify-center gap-2 group">
                    Approve &amp; Execute PO
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <button onClick={() => setActiveDraft(null)} className="w-full py-2.5 border border-white/10 hover:border-sc_red/50 hover:bg-sc_red/10 hover:text-red-400 text-slate-400 rounded-lg text-sm font-mono transition-all">
                    Reject Override
                  </button>
                </div>
              </motion.div>
            )}

          </div>
        </div>
      </div>
    </div>
  )
}
