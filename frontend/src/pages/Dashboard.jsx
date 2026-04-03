import React, { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  AlertTriangle, Ship, Globe, Activity, Zap, TrendingUp,
  RefreshCw, Radio, Eye, BarChart3, Clock, X, WifiOff, Key
} from 'lucide-react'

// ─── CONSTANTS ───────────────────────────────────────────────────────────────
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''
const API_BASE     = import.meta.env.VITE_API_BASE_URL
const REFRESH_INTERVAL = 30000

const CHOKEPOINTS_STATIC = [
  { id: 'SUEZ',     name: 'Suez Canal',         coords: [32.55,  30.01],  region: 'Middle East' },
  { id: 'HORMUZ',   name: 'Strait of Hormuz',   coords: [56.4,   26.6],   region: 'Persian Gulf' },
  { id: 'MALACCA',  name: 'Strait of Malacca',  coords: [103.7,  1.25],   region: 'Southeast Asia' },
  { id: 'TAIWAN',   name: 'Taiwan Strait',       coords: [120.2,  24.0],   region: 'East Asia' },
  { id: 'PANAMA',   name: 'Panama Canal',        coords: [-79.9,  8.99],   region: 'Central America' },
  { id: 'BOSPORUS', name: 'Bosphorus Strait',    coords: [29.02,  41.1],   region: 'Turkey' },
  { id: 'DOVER',    name: 'Strait of Dover',     coords: [1.35,   51.05],  region: 'Northern Europe' },
  { id: 'BABELM',   name: 'Bab-el-Mandeb',       coords: [43.3,   12.58],  region: 'Red Sea' },
]

// Fallback risk data used when backend is offline
const FALLBACK_CHOKEPOINTS = CHOKEPOINTS_STATIC.map((c, i) => ({
  chokepoint_id: c.id,
  name: c.name,
  risk_score: [0.82, 0.44, 0.61, 0.55, 0.33, 0.29, 0.71, 0.67][i],
  vessel_count: [142, 98, 211, 87, 155, 44, 76, 103][i],
  avg_speed_knots: [8.2, 14.1, 12.4, 16.8, 11.3, 9.7, 18.2, 7.6][i],
  congestion_index: [0.84, 0.42, 0.63, 0.57, 0.31, 0.27, 0.74, 0.66][i],
  isOfflineFallback: true,
}))

const RISK_CONFIG = {
  LOW:      { color: '#4ade80', glow: 'rgba(74,222,128,0.8)',   size: 14, pulseSize: 38, label: 'Low Risk' },
  MEDIUM:   { color: '#ffd60a', glow: 'rgba(255,214,10,0.8)',   size: 16, pulseSize: 44, label: 'Medium Risk' },
  HIGH:     { color: '#ff6b35', glow: 'rgba(255,107,53,0.8)',   size: 18, pulseSize: 52, label: 'High Risk' },
  CRITICAL: { color: '#fb7185', glow: 'rgba(251,113,133,0.9)', size: 22, pulseSize: 64, label: 'Critical' },
}

const ALERTS_MOCK = [
  { id: 1, severity: 'CRITICAL', text: 'Suez Canal: Congestion Index >0.85', time: '0m ago' },
  { id: 2, severity: 'HIGH',     text: 'SKU-001 Demand Spike +38% detected', time: '3m ago' },
  { id: 3, severity: 'MEDIUM',   text: 'Taiwan Strait vessel density rising', time: '11m ago' },
  { id: 4, severity: 'LOW',      text: 'Auto-PO Approved by AI Agent', time: '28m ago' },
  { id: 5, severity: 'LOW',      text: 'Global Risk Index recomputed', time: '1h ago' },
]

function getRiskLevel(score) {
  if (score >= 0.75) return 'CRITICAL'
  if (score >= 0.5)  return 'HIGH'
  if (score >= 0.25) return 'MEDIUM'
  return 'LOW'
}

// ─── SAFE FETCH WRAPPER (never throws to React Query error boundary) ──────────
async function safeFetch(url, label) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (err) {
    // Return null — caller uses fallback data
    return null
  }
}

// ─── MISSING TOKEN BANNER ─────────────────────────────────────────────────────
function TokenMissingBanner() {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-sc_bg rounded-2xl">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4 text-center max-w-sm"
      >
        <div className="p-5 bg-sc_orange/10 rounded-full border border-sc_orange/20">
          <Key className="w-10 h-10 text-sc_orange" />
        </div>
        <h3 className="text-xl font-bold font-mono text-white">Mapbox Token Missing</h3>
        <p className="text-slate-400 text-sm leading-relaxed">
          Add <code className="text-sc_cyan bg-white/5 px-1 py-0.5 rounded">VITE_MAPBOX_TOKEN</code> to your{' '}
          <code className="text-sc_cyan bg-white/5 px-1 py-0.5 rounded">.env</code> file at the monorepo root,
          then restart the dev server.
        </p>
        <div className="text-xs font-mono text-slate-500 bg-sc_elevated border border-white/5 rounded-lg px-4 py-3 w-full text-left">
          # .env<br />
          VITE_MAPBOX_TOKEN=pk.eyJ1Ijoi...
        </div>
      </motion.div>
    </div>
  )
}

// ─── OFFLINE MODE BANNER ─────────────────────────────────────────────────────
function OfflineBanner() {
  return (
    <motion.div
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="absolute top-16 left-1/2 -translate-x-1/2 z-40 pointer-events-none"
    >
      <div className="flex items-center gap-2 bg-sc_orange/10 border border-sc_orange/30 rounded-full px-4 py-2 text-sc_orange text-xs font-mono backdrop-blur-xl">
        <WifiOff className="w-3.5 h-3.5 shrink-0" />
        <span>Backend offline — displaying static fallback data. Start FastAPI server on :8000 for live feed.</span>
      </div>
    </motion.div>
  )
}

// ─── RADIAL GAUGE ─────────────────────────────────────────────────────────────
function RadialGauge({ score = 0.62 }) {
  const clamped = Math.min(Math.max(score, 0), 1)
  const R = 54
  const circ = 2 * Math.PI * R
  const arcLen = circ * 0.75
  const dashOffset = arcLen * (1 - clamped)

  const color = clamped >= 0.75 ? '#fb7185' : clamped >= 0.5 ? '#ff6b35' : clamped >= 0.25 ? '#ffd60a' : '#4ade80'

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <svg className="w-full h-full" viewBox="0 0 120 120" style={{ transform: 'rotate(-225deg)' }}>
          <circle cx="60" cy="60" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8"
            strokeDasharray={`${arcLen} ${circ}`} strokeLinecap="round" />
          <motion.circle
            cx="60" cy="60" r={R} fill="none" stroke={color} strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${arcLen} ${circ}`}
            initial={{ strokeDashoffset: arcLen }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 2, ease: [0.22, 1, 0.36, 1] }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span className="text-3xl font-bold font-mono"
            style={{ color, textShadow: `0 0 20px ${color}80` }}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
            {Math.round(clamped * 100)}
          </motion.span>
          <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-0.5">/ 100</span>
        </div>
      </div>
      <span className="text-xs font-mono tracking-widest text-slate-400 uppercase mt-1">Global Risk Index</span>
    </div>
  )
}

// ─── COUNTDOWN TIMER ────────────────────────────────────────────────────────
function CountdownTimer({ seconds, total, onRefresh }) {
  const pct = seconds / total
  const r = 10
  const dashoffset = 2 * Math.PI * r * (1 - pct)
  return (
    <button onClick={onRefresh} className="flex items-center gap-2 text-slate-400 hover:text-sc_cyan transition-colors group" title="Refresh now">
      <div className="relative w-6 h-6">
        <svg className="w-6 h-6 -rotate-90" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" />
          <motion.circle cx="12" cy="12" r={r} fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * r}`} animate={{ strokeDashoffset: dashoffset }} transition={{ duration: 0.5 }} />
        </svg>
        <RefreshCw className="absolute inset-0 m-auto w-3 h-3 text-sc_cyan group-hover:rotate-180 transition-transform duration-500" />
      </div>
      <span className="text-xs font-mono text-sc_cyan">{seconds}s</span>
    </button>
  )
}

// ─── ALERT BADGE ─────────────────────────────────────────────────────────────
function AlertBadge({ severity }) {
  const cfg = {
    CRITICAL: 'bg-sc_red/20 text-sc_red border-sc_red/30',
    HIGH:     'bg-sc_orange/20 text-sc_orange border-sc_orange/30',
    MEDIUM:   'bg-sc_yellow/20 text-sc_yellow border-sc_yellow/30',
    LOW:      'bg-sc_green/15 text-sc_green border-sc_green/20',
  }[severity] || 'bg-slate-800 text-slate-300 border-white/10'
  return (
    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full uppercase tracking-widest border ${cfg}`}>
      {severity}
    </span>
  )
}

// ─── CHOKEPOINT POPUP ────────────────────────────────────────────────────────
function ChokepointPopup({ data, onClose }) {
  if (!data) return null
  const risk = data.risk_level || getRiskLevel(data.risk_score ?? 0.5)
  const cfg = RISK_CONFIG[risk]
  return (
    <motion.div
      key={data.chokepoint_id}
      initial={{ opacity: 0, scale: 0.85, y: 12 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.85, y: 12 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className="absolute z-50 w-72 pointer-events-auto"
      style={{ bottom: '38%', left: '42%', transform: 'translateX(-50%)' }}
    >
      <div className="bg-sc_card/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        style={{ boxShadow: `0 0 40px ${cfg.glow}30, 0 25px 60px rgba(0,0,0,0.5)` }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5"
          style={{ background: `linear-gradient(90deg, ${cfg.color}15, transparent)` }}>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ background: cfg.color, boxShadow: `0 0 8px ${cfg.color}` }} />
            <span className="font-bold text-white text-sm">{data.name || data.chokepoint_id}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full border"
              style={{ color: cfg.color, borderColor: `${cfg.color}40`, background: `${cfg.color}15` }}>
              {cfg.label}
            </span>
            <button onClick={onClose} className="text-slate-500 hover:text-slate-200 transition-colors ml-1">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-px bg-white/5">
          {[
            { label: 'Risk Score',    value: data.risk_score != null ? `${Math.round(data.risk_score * 100)}%` : '—', icon: '⚡' },
            { label: 'Vessels',       value: data.vessel_count ?? '—',                                               icon: '🚢' },
            { label: 'Avg Speed',     value: data.avg_speed_knots != null ? `${data.avg_speed_knots} kn` : '—',     icon: '💨' },
            { label: 'Cong. Index',   value: data.congestion_index != null ? data.congestion_index.toFixed(2) : '—',icon: '📊' },
          ].map(m => (
            <div key={m.label} className="bg-sc_card/80 px-4 py-3">
              <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">{m.icon} {m.label}</div>
              <div className="text-xl font-bold font-mono text-white">{m.value}</div>
            </div>
          ))}
        </div>
        <div className="px-4 py-2.5 text-[10px] text-slate-500 font-mono flex items-center gap-1.5">
          <Clock className="w-3 h-3" />
          <span>{data.isOfflineFallback ? 'Static fallback — start backend for live data' : `Updated: ${data.computed_at ? new Date(data.computed_at).toLocaleTimeString() : 'Just now'}`}</span>
        </div>
      </div>
    </motion.div>
  )
}

// ─── RIGHT PANEL ─────────────────────────────────────────────────────────────
function RightPanel({ chokepoints, vessels, isOffline, countdown, onRefresh }) {
  const vesselCount    = vessels?.features?.length ?? vessels?.length ?? 0
  const activeRoutes   = chokepoints?.length ?? 0
  const globalScore    = chokepoints?.length > 0
    ? chokepoints.reduce((acc, c) => acc + (c.risk_score ?? 0.5), 0) / chokepoints.length
    : 0.62
  const criticalCount  = chokepoints?.filter(c => getRiskLevel(c.risk_score ?? 0.5) === 'CRITICAL').length ?? 0

  return (
    <motion.div
      initial={{ x: 40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="absolute top-4 right-4 bottom-4 w-80 z-30 flex flex-col gap-3 pointer-events-none"
    >
      {/* Global Risk Gauge */}
      <div className="pointer-events-auto bg-sc_card/85 backdrop-blur-2xl border border-white/8 rounded-2xl p-5 shadow-2xl"
        style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04)' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-sc_cyan" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300">Global Risk</h3>
            {isOffline && (
              <span className="text-[9px] font-mono text-sc_orange border border-sc_orange/30 bg-sc_orange/10 px-1.5 py-0.5 rounded-full uppercase tracking-wider">offline</span>
            )}
          </div>
          <CountdownTimer seconds={countdown} total={REFRESH_INTERVAL / 1000} onRefresh={onRefresh} />
        </div>
        <div className="flex items-center justify-between">
          <RadialGauge score={globalScore} />
          <div className="flex flex-col gap-2 text-right">
            {criticalCount > 0 && (
              <div className="text-xs font-mono text-sc_red flex items-center gap-1 justify-end">
                <span className="w-1.5 h-1.5 rounded-full bg-sc_red animate-pulse" />
                {criticalCount} CRITICAL
              </div>
            )}
            <div className="text-xs font-mono text-slate-400">{activeRoutes} routes monitored</div>
            <div className="text-xs font-mono text-slate-400">
              <span className="text-sc_cyan font-bold">{isOffline ? '—' : vesselCount}</span> vessels
            </div>
          </div>
        </div>
      </div>

      {/* Metric tiles */}
      <div className="pointer-events-auto grid grid-cols-2 gap-2">
        {[
          { label: 'Active Routes',  value: activeRoutes,  icon: Activity,     color: 'text-sc_cyan' },
          { label: 'Live Vessels',   value: isOffline ? '—' : vesselCount, icon: Ship, color: 'text-sc_green' },
          { label: 'Critical Zones', value: criticalCount, icon: AlertTriangle, color: 'text-sc_red' },
          { label: 'D/S Alerts',     value: 2,             icon: Zap,          color: 'text-sc_orange' },
        ].map((m, i) => {
          const Icon = m.icon
          return (
            <motion.div key={m.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.08 }}
              className="bg-sc_card/80 backdrop-blur-xl border border-white/6 rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className={`w-3.5 h-3.5 ${m.color}`} />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{m.label}</span>
              </div>
              <span className={`text-2xl font-bold font-mono ${m.color}`}>{m.value}</span>
            </motion.div>
          )
        })}
      </div>

      {/* Alerts list */}
      <div className="pointer-events-auto flex-1 bg-sc_card/85 backdrop-blur-2xl border border-white/8 rounded-2xl overflow-hidden flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-sc_orange animate-pulse" />
            <h3 className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300">Live Alerts</h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">{ALERTS_MOCK.length} active</span>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/4">
          <AnimatePresence>
            {ALERTS_MOCK.map((alert, i) => (
              <motion.div key={alert.id}
                initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.8 + i * 0.08 }}
                className="px-4 py-3 hover:bg-white/3 transition-colors cursor-pointer group">
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <AlertBadge severity={alert.severity} />
                  <span className="text-[10px] font-mono text-slate-600 shrink-0">{alert.time}</span>
                </div>
                <p className="text-xs text-slate-300 group-hover:text-white transition-colors">{alert.text}</p>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Legend */}
      <div className="pointer-events-auto bg-sc_card/70 backdrop-blur-xl border border-white/6 rounded-xl px-4 py-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          {Object.entries(RISK_CONFIG).map(([level, cfg]) => (
            <div key={level} className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: cfg.color, boxShadow: `0 0 6px ${cfg.color}` }} />
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">{cfg.label}</span>
            </div>
          ))}
          <div className="flex items-center gap-2 col-span-2 pt-1.5 border-t border-white/5 mt-0.5">
            <div className="w-2.5 h-2.5 rounded-full bg-sc_cyan/60 shrink-0" />
            <span className="text-[10px] font-mono text-slate-400">AIS vessel position</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── HEADER STRIP ─────────────────────────────────────────────────────────────
function DashboardHeader({ isOffline }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="absolute top-4 left-4 z-30 pointer-events-none">
      <div className="bg-sc_card/85 backdrop-blur-2xl border border-white/8 rounded-2xl px-5 py-3 shadow-2xl"
        style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <Eye className="w-3.5 h-3.5 text-sc_cyan" />
              <span className="text-xs font-mono font-bold uppercase tracking-widest text-sc_cyan">Live Situational Awareness</span>
            </div>
            <p className="text-[10px] text-slate-500 font-mono">
              {now.toISOString().replace('T', ' ').split('.')[0]} UTC
            </p>
          </div>
          <div className="h-8 w-px bg-white/8" />
          <div className="flex items-center gap-1.5">
            {isOffline ? (
              <>
                <WifiOff className="w-3 h-3 text-sc_orange" />
                <span className="text-[10px] font-mono text-sc_orange font-bold uppercase tracking-wider">Offline Mode</span>
              </>
            ) : (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sc_green opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-sc_green" />
                </span>
                <span className="text-[10px] font-mono text-sc_green font-bold uppercase tracking-wider">Live</span>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── MAIN DASHBOARD ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const mapContainerRef  = useRef(null)
  const mapRef           = useRef(null)
  const markersRef       = useRef([])
  const vesselMarkersRef = useRef([])
  const offlineToastShown = useRef(false)

  const [mapReady, setMapReady]                 = useState(false)
  const [selectedChokepoint, setSelectedChokepoint] = useState(null)
  const [countdown, setCountdown]               = useState(REFRESH_INTERVAL / 1000)
  const [isOffline, setIsOffline]               = useState(false)

  // ── DATA FETCHING ──────────────────────────────────────────────────────────
  const {
    data: rawChokepoints,
    refetch: refetchCp,
  } = useQuery({
    queryKey: ['chokepoints'],
    queryFn: () => safeFetch(`${API_BASE}/risk/chokepoints`, 'chokepoints'),
    refetchInterval: REFRESH_INTERVAL,
    retry: false,
    onSuccess: (data) => {
      if (!data) {
        setIsOffline(true)
        if (!offlineToastShown.current) {
          toast('Backend offline — running in offline mode. Displaying static fallback data.', {
            icon: '📡',
            duration: 6000,
            style: { background: '#0b0f17', color: '#ff6b35', border: '1px solid rgba(255,107,53,0.3)' }
          })
          offlineToastShown.current = true
        }
      } else {
        setIsOffline(false)
        offlineToastShown.current = false
      }
    },
  })

  const { data: rawVessels, refetch: refetchVessels } = useQuery({
    queryKey: ['ais-live'],
    queryFn: () => safeFetch(`${API_BASE}/ais/live`, 'AIS feed'),
    refetchInterval: REFRESH_INTERVAL,
    retry: false,
  })

  // Use live data or fallback — never undefined
  const chokepoints = rawChokepoints || FALLBACK_CHOKEPOINTS
  const vessels     = rawVessels    || { features: [] }

  const handleRefresh = useCallback(() => {
    refetchCp()
    refetchVessels()
    setCountdown(REFRESH_INTERVAL / 1000)
    toast.success('Refreshed', { duration: 2000, icon: '🔄' })
  }, [refetchCp, refetchVessels])

  // ── COUNTDOWN ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setInterval(() => {
      setCountdown(prev => prev <= 1 ? REFRESH_INTERVAL / 1000 : prev - 1)
    }, 1000)
    return () => clearInterval(t)
  }, [])

  // ── CSS KEYFRAMES INJECTION ───────────────────────────────────────────────
  useEffect(() => {
    if (document.getElementById('cp-anim')) return
    const style = document.createElement('style')
    style.id = 'cp-anim'
    style.textContent = `
      @keyframes cpPulse {
        0%   { transform: scale(1);   opacity: 0.55; }
        60%  { transform: scale(1.4); opacity: 0.18; }
        100% { transform: scale(1.8); opacity: 0; }
      }
    `
    document.head.appendChild(style)
    return () => document.getElementById('cp-anim')?.remove()
  }, [])

  // ── MAP INITIALIZATION ────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return
    if (!MAPBOX_TOKEN) { setMapReady(true); return } // show token error UI

    mapboxgl.accessToken = MAPBOX_TOKEN

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [20, 18],
      zoom: 1.9,
      projection: 'globe',
      antialias: true,
      maxZoom: 12,
      minZoom: 1,
    })

    map.addControl(new mapboxgl.NavigationControl({ showCompass: true, visualizePitch: true }), 'bottom-left')

    map.on('load', () => {
      map.setFog({
        color: 'rgb(4, 6, 14)',
        'high-color': 'rgb(6, 10, 24)',
        'horizon-blend': 0.07,
        'space-color': 'rgb(1, 2, 8)',
        'star-intensity': 0.75,
      })
      try { map.setPaintProperty('water', 'fill-color', '#050e20') } catch (_) {}
      try { map.setPaintProperty('admin-0-boundary', 'line-color', 'rgba(0, 212, 255, 0.12)') } catch (_) {}
      setMapReady(true)
    })

    map.on('error', (e) => {
      // Suppress Mapbox tile errors from appearing as red in console
      // (tile 404s are network-level and expected in local dev)
      if (e?.error?.status === 404) return
    })

    mapRef.current = map

    return () => {
      markersRef.current.forEach(m => m.remove())
      vesselMarkersRef.current.forEach(m => m.remove())
      map.remove()
      mapRef.current = null
      setMapReady(false)
    }
  }, [])

  // ── CHOKEPOINT MARKERS ────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current || !MAPBOX_TOKEN) return

    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    const map = mapRef.current
    const riskMap = {}
    chokepoints.forEach(c => { riskMap[c.chokepoint_id] = c })

    CHOKEPOINTS_STATIC.forEach((cp) => {
      const riskData = riskMap[cp.id] || {}
      const score    = riskData.risk_score ?? 0.5
      const risk     = getRiskLevel(score)
      const cfg      = RISK_CONFIG[risk]

      const el = document.createElement('div')
      el.style.cssText = `position:relative;width:${cfg.pulseSize}px;height:${cfg.pulseSize}px;cursor:pointer;`

      const ring = (delay) => {
        const r = document.createElement('div')
        r.style.cssText = `
          position:absolute;inset:0;border-radius:50%;
          border:1.5px solid ${cfg.color};
          animation:cpPulse 2.6s ease-out ${delay}s infinite;
        `
        return r
      }

      const dot = document.createElement('div')
      const ds  = cfg.size
      dot.style.cssText = `
        position:absolute;top:50%;left:50%;
        width:${ds}px;height:${ds}px;
        margin:${-ds / 2}px 0 0 ${-ds / 2}px;
        border-radius:50%;
        background:${cfg.color};
        box-shadow:0 0 ${ds * 1.8}px ${cfg.color},0 0 ${ds * 3}px ${cfg.color}55;
      `

      el.appendChild(ring(0))
      el.appendChild(ring(0.9))
      el.appendChild(dot)

      const merged = { ...cp, ...riskData, chokepoint_id: cp.id, name: cp.name, risk_level: risk }
      el.addEventListener('click', () => setSelectedChokepoint(merged))

      const marker = new mapboxgl.Marker({ element: el, anchor: 'center' })
        .setLngLat(cp.coords)
        .addTo(map)

      markersRef.current.push(marker)
    })
  }, [mapReady, chokepoints])

  // ── VESSEL DOTS ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current || !MAPBOX_TOKEN) return

    vesselMarkersRef.current.forEach(m => m.remove())
    vesselMarkersRef.current = []

    const features = vessels?.features || []

    features.slice(0, 600).forEach((f) => {
      const coords = f.geometry?.coordinates || [f.longitude, f.latitude]
      if (!coords || coords[0] == null) return

      const el = document.createElement('div')
      el.style.cssText = 'width:5px;height:5px;border-radius:50%;background:rgba(0,212,255,0.6);box-shadow:0 0 5px rgba(0,212,255,0.4);'

      new mapboxgl.Marker({ element: el, anchor: 'center' })
        .setLngLat(coords)
        .addTo(mapRef.current)

      vesselMarkersRef.current.push(el)
    })
  }, [mapReady, vessels])

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <motion.div
      className="relative w-full"
      style={{ height: 'calc(100vh - 64px - 32px)', minHeight: '600px' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
    >
      {/* Map container */}
      <div
        ref={mapContainerRef}
        className="absolute inset-0 rounded-2xl overflow-hidden"
        style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 30px 80px rgba(0,0,0,0.7)' }}
      />

      {/* Missing token error overlay */}
      {!MAPBOX_TOKEN && <TokenMissingBanner />}

      {/* Map loading overlay */}
      <AnimatePresence>
        {MAPBOX_TOKEN && !mapReady && (
          <motion.div className="absolute inset-0 bg-sc_bg z-50 rounded-2xl flex items-center justify-center"
            exit={{ opacity: 0 }} transition={{ duration: 0.8 }}>
            <div className="flex flex-col items-center gap-4">
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                className="w-16 h-16 border-2 border-sc_cyan/20 border-t-sc_cyan rounded-full"
                style={{ boxShadow: '0 0 30px rgba(0,212,255,0.25)' }} />
              <div className="text-center">
                <p className="font-mono text-sc_cyan text-sm tracking-widest uppercase">Initializing Radar</p>
                <p className="font-mono text-slate-500 text-xs mt-1">Connecting to AIS Feed...</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Offline banner */}
      <AnimatePresence>{isOffline && <OfflineBanner />}</AnimatePresence>

      {/* Header */}
      <DashboardHeader isOffline={isOffline} />

      {/* Chokepoint popup */}
      <AnimatePresence>
        {selectedChokepoint && (
          <ChokepointPopup data={selectedChokepoint} onClose={() => setSelectedChokepoint(null)} />
        )}
      </AnimatePresence>

      {/* Right overlay panel */}
      <RightPanel
        chokepoints={chokepoints}
        vessels={vessels}
        isOffline={isOffline}
        countdown={countdown}
        onRefresh={handleRefresh}
      />

      {/* Bottom status bar */}
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 1.0 }}
        className="absolute bottom-4 left-4 z-30">
        <div className="bg-sc_card/80 backdrop-blur-xl border border-white/8 rounded-xl px-4 py-2 flex items-center gap-4 text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <BarChart3 className="w-3.5 h-3.5 text-sc_purple" />
            <span className="text-sc_purple font-bold">Gemini 2.5 Flash</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-sc_cyan" />
            <span>{CHOKEPOINTS_STATIC.length} chokepoints monitored</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${isOffline ? 'bg-sc_orange' : 'bg-sc_green animate-pulse'}`} />
            <span className={isOffline ? 'text-sc_orange' : 'text-sc_green'}>
              {isOffline ? 'Offline — Start :8000' : 'API Connected'}
            </span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
