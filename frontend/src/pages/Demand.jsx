import React, { useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts'
import {
  TrendingUp, TrendingDown, Package, Truck, BarChart3,
  AlertTriangle, Clock, ChevronDown, RefreshCw, Activity,
  Zap, BarChart2, Info
} from 'lucide-react'
import { fetchForecast, fetchDSRatio, SKU_LIST, ROUTE_MAP } from '../api/demand'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const GAUGE_THRESHOLDS = { green: 1.5, yellow: 2.0 }

function gaugeColor(ratio) {
  if (ratio < GAUGE_THRESHOLDS.green)  return { stroke: '#4ade80', glow: '#4ade8055', label: 'HEALTHY',  text: 'text-sc_green' }
  if (ratio < GAUGE_THRESHOLDS.yellow) return { stroke: '#ffd60a', glow: '#ffd60a55', label: 'WARNING',  text: 'text-sc_yellow' }
  return                                       { stroke: '#fb7185', glow: '#fb718555', label: 'CRITICAL', text: 'text-sc_red' }
}

function stockoutEstimate(ratio, supplyQty) {
  if (!ratio || ratio === 0) return '∞'
  if (ratio < 1.0) return '> 90 days'
  // Rough: supply lasts supply/daily_demand days. daily_demand ≈ 30day_demand/30
  const days = Math.round(supplyQty / (supplyQty * (ratio / 30)))
  const est = Math.max(0, Math.round(90 / ratio))
  if (est > 90) return '> 90 days'
  return `~${est} days`
}

// ─── RADIAL GAUGE ─────────────────────────────────────────────────────────────
function RadialGauge({ ratio, isLoading }) {
  const maxRatio = 3.5
  const clampedRatio = Math.min(ratio ?? 0, maxRatio)
  const pct = clampedRatio / maxRatio           // 0→1
  const color = gaugeColor(ratio ?? 0)

  // Arc math: sweep = 240°, starts at 150° (bottom-left), ends at 390° (bottom-right)
  const SIZE = 220
  const CX = SIZE / 2
  const CY = SIZE / 2
  const R = 88
  const START_DEG = 150
  const SWEEP_DEG = 240
  const endDeg = START_DEG + SWEEP_DEG * pct
  const toRad = (d) => (d * Math.PI) / 180
  const arcPoint = (deg, r = R) => [
    CX + r * Math.cos(toRad(deg)),
    CY + r * Math.sin(toRad(deg)),
  ]
  const [sx, sy] = arcPoint(START_DEG)
  const [ex, ey] = arcPoint(endDeg)
  const largeArc = SWEEP_DEG * pct > 180 ? 1 : 0

  // Tick marks at 1.0, 1.5, 2.0, 2.5, 3.0
  const ticks = [0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={SIZE} height={SIZE * 0.78} viewBox={`0 0 ${SIZE} ${SIZE * 0.78}`} style={{ overflow: 'visible' }}>
        <defs>
          <filter id="gaugeGlow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <linearGradient id="gaugeTrack" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#4ade80" stopOpacity="0.3" />
            <stop offset="43%"  stopColor="#ffd60a" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#fb7185" stopOpacity="0.3" />
          </linearGradient>
        </defs>

        {/* Track (full 240° arc) */}
        <path
          d={`M ${arcPoint(START_DEG)[0]} ${arcPoint(START_DEG)[1]} A ${R} ${R} 0 1 1 ${arcPoint(START_DEG + SWEEP_DEG - 0.01)[0]} ${arcPoint(START_DEG + SWEEP_DEG - 0.01)[1]}`}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={12} strokeLinecap="round"
        />

        {/* Value arc */}
        {!isLoading && clampedRatio > 0 && (
          <motion.path
            d={`M ${sx} ${sy} A ${R} ${R} 0 ${largeArc} 1 ${ex} ${ey}`}
            fill="none"
            stroke={color.stroke}
            strokeWidth={12}
            strokeLinecap="round"
            filter="url(#gaugeGlow)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
            style={{ pathLength: 1 }}
          />
        )}

        {/* Tick marks */}
        {ticks.map((t) => {
          const tDeg = START_DEG + SWEEP_DEG * (t / maxRatio)
          const [ix, iy] = arcPoint(tDeg, R - 16)
          const [ox, oy] = arcPoint(tDeg, R + 4)
          const isKey = [1.5, 2.0].includes(t)
          return (
            <line key={t} x1={ix} y1={iy} x2={ox} y2={oy}
              stroke={isKey ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.12)'}
              strokeWidth={isKey ? 2 : 1} />
          )
        })}

        {/* Threshold labels */}
        {[{ v: 1.5, label: '1.5' }, { v: 2.0, label: '2.0' }].map(({ v, label }) => {
          const deg = START_DEG + SWEEP_DEG * (v / maxRatio)
          const [lx, ly] = arcPoint(deg, R + 20)
          return (
            <text key={v} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              fill="rgba(255,255,255,0.3)" fontSize="9" fontFamily="monospace">
              {label}
            </text>
          )
        })}

        {/* Center value */}
        {isLoading ? (
          <rect x={CX - 28} y={CY - 16} width={56} height={32} rx={6}
            fill="rgba(255,255,255,0.05)" />
        ) : (
          <>
            <motion.text
              x={CX} y={CY - 6}
              textAnchor="middle" dominantBaseline="middle"
              fill={color.stroke}
              fontSize="34"
              fontWeight="700"
              fontFamily="Space Grotesk, monospace"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
            >
              {(ratio ?? 0).toFixed(2)}
            </motion.text>
            <text x={CX} y={CY + 22} textAnchor="middle" fill="rgba(255,255,255,0.4)"
              fontSize="10" fontFamily="monospace" letterSpacing="2">
              D/S RATIO
            </text>
          </>
        )}

        {/* Needle dot */}
        {!isLoading && (
          <motion.circle
            cx={ex} cy={ey} r={6}
            fill={color.stroke}
            filter="url(#gaugeGlow)"
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            transition={{ delay: 1.4, type: 'spring', stiffness: 300 }}
          />
        )}
      </svg>

      {/* Status badge */}
      <motion.div
        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}
        className="flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-mono font-bold tracking-widest"
        style={{ color: color.stroke, borderColor: `${color.stroke}40`, background: `${color.glow}` }}
      >
        <motion.div className="w-1.5 h-1.5 rounded-full" style={{ background: color.stroke }}
          animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.4, repeat: Infinity }} />
        {isLoading ? 'LOADING…' : color.label}
      </motion.div>
    </div>
  )
}

// ─── SKELETON ────────────────────────────────────────────────────────────────
function SkeletonBlock({ className = '' }) {
  return (
    <motion.div
      className={`bg-white/5 rounded-xl ${className}`}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <SkeletonBlock key={i} className="h-28" />)}
      </div>
      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2"><SkeletonBlock className="h-80" /></div>
        <SkeletonBlock className="h-80" />
      </div>
    </div>
  )
}

// ─── ALERT BANNER ────────────────────────────────────────────────────────────
function AlertBanner({ sku, ratio, status }) {
  const color = gaugeColor(ratio)
  const isCritical = status === 'CRITICAL' || ratio >= GAUGE_THRESHOLDS.yellow
  return (
    <motion.div
      initial={{ y: -48, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: -48, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 28 }}
      className="rounded-2xl border p-4 flex items-start gap-4"
      style={{
        background: `linear-gradient(135deg, ${color.glow}, transparent 60%)`,
        borderColor: `${color.stroke}30`,
        boxShadow: `0 0 30px ${color.glow}`,
      }}
    >
      <div className="p-2 rounded-xl border flex-shrink-0"
        style={{ borderColor: `${color.stroke}30`, background: `${color.stroke}15` }}>
        <AlertTriangle className="w-5 h-5" style={{ color: color.stroke }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-bold font-mono text-sm" style={{ color: color.stroke }}>
            {isCritical ? 'CRITICAL SUPPLY SHORTAGE' : 'SUPPLY WARNING'}
          </span>
          <span className="text-xs font-mono text-slate-500">• {sku}</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          {isCritical
            ? `Demand is outpacing supply by ${ratio.toFixed(2)}×. Immediate procurement action required — route exposure on ${ROUTE_MAP[sku]}.`
            : `D/S ratio has crossed the 1.5× warning threshold. Monitor closely and consider pre-emptive PO creation.`
          }
        </p>
      </div>
      <div className="text-right flex-shrink-0">
        <div className="text-2xl font-bold font-mono" style={{ color: color.stroke }}>{ratio.toFixed(2)}×</div>
        <div className="text-[10px] text-slate-500 font-mono">D/S RATIO</div>
      </div>
    </motion.div>
  )
}

// ─── EMPTY STATE ─────────────────────────────────────────────────────────────
function ForecastEmptyState({ sku }) {
  return (
    <div className="flex flex-col items-center justify-center gap-5 py-16 px-4 text-center">
      {/* Animated bars */}
      <div className="flex items-end gap-2 h-16">
        {[0.4, 0.7, 0.5, 0.9, 0.6, 0.8, 0.4, 0.75, 0.55, 0.65].map((h, i) => (
          <motion.div key={i}
            className="w-4 rounded-t-sm"
            style={{ background: `rgba(0,212,255,${h * 0.4})`, height: `${h * 100}%` }}
            animate={{ scaleY: [1, h * 0.4 + 0.6, 1] }}
            transition={{ duration: 2 + i * 0.15, repeat: Infinity, ease: 'easeInOut', delay: i * 0.1 }}
          />
        ))}
        {/* Forecast dashed extension */}
        {[0.7, 0.85, 0.9, 0.6, 0.4].map((h, i) => (
          <motion.div key={`f${i}`}
            className="w-4 rounded-t-sm border-2 border-dashed"
            style={{ borderColor: `rgba(255,214,10,0.4)`, height: `${h * 100}%`, background: 'transparent' }}
            animate={{ opacity: [0.4, 0.9, 0.4] }}
            transition={{ duration: 2, repeat: Infinity, delay: 0.5 + i * 0.1 }}
          />
        ))}
      </div>

      <div className="space-y-2">
        <h3 className="text-xl font-bold font-mono text-white">No Forecast Data Yet</h3>
        <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
          No demand forecast has been ingested for <span className="text-sc_cyan font-mono">{sku}</span> yet.
          Run the Prophet model pipeline to generate a 90-day forecast.
        </p>
      </div>

      <div className="flex items-center gap-3 text-xs font-mono text-slate-500 bg-sc_elevated/60 border border-white/5 rounded-xl px-4 py-3">
        <Activity className="w-4 h-4 text-sc_purple" />
        <span>D/S Ratio gauge is live — forecast chart populates after first ingestion run</span>
      </div>
    </div>
  )
}

// ─── CUSTOM TOOLTIP ──────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const isForecast = payload[0]?.payload?.isForecast

  return (
    <div className="bg-sc_card/95 backdrop-blur-xl border border-white/10 rounded-xl p-3 shadow-2xl min-w-[160px]">
      <p className="text-[10px] font-mono text-slate-400 mb-2 flex items-center gap-1.5">
        {isForecast
          ? <><span className="w-1.5 h-1.5 rounded-full bg-sc_yellow inline-block" />FORECAST</>
          : <><span className="w-1.5 h-1.5 rounded-full bg-sc_cyan inline-block" />HISTORICAL</>
        }
        <span className="ml-auto">{label}</span>
      </p>
      {payload.map((p) => (
        p.name !== 'band' && (
          <div key={p.name} className="flex items-center justify-between gap-4 text-xs">
            <span className="text-slate-400 capitalize">{p.name}</span>
            <span className="font-mono font-bold" style={{ color: p.color }}>
              {typeof p.value === 'number' ? p.value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : p.value}
            </span>
          </div>
        )
      ))}
    </div>
  )
}

// ─── SKU SELECTOR ─────────────────────────────────────────────────────────────
function SKUSelector({ value, onChange, isLoading }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        disabled={isLoading}
        className="flex items-center gap-3 bg-sc_card/80 backdrop-blur-xl border border-white/10 hover:border-sc_cyan/40 rounded-xl px-4 py-2.5 text-sm font-mono transition-all disabled:opacity-50"
        style={{ minWidth: 160 }}
      >
        <Package className="w-4 h-4 text-sc_cyan" />
        <span className="text-white font-bold">{value}</span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }} className="ml-auto">
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </motion.div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-2 z-50 bg-sc_card/95 backdrop-blur-2xl border border-white/10 rounded-xl overflow-hidden shadow-2xl"
            style={{ minWidth: 160, boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}
          >
            {SKU_LIST.map((sku) => (
              <button key={sku} onClick={() => { onChange(sku); setOpen(false) }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-mono text-left transition-all hover:bg-white/5 ${sku === value ? 'text-sc_cyan bg-sc_cyan/5' : 'text-slate-300'}`}
              >
                <Package className="w-3.5 h-3.5" />
                {sku}
                {sku === value && <Zap className="w-3 h-3 ml-auto text-sc_cyan" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {open && <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />}
    </div>
  )
}

// ─── FORECAST CHART ──────────────────────────────────────────────────────────
function ForecastChart({ data, sku }) {
  if (!data?.length) return <ForecastEmptyState sku={sku} />

  // Separate historical vs forecast. If no model_used tag, treat all as forecast.
  // Prepare chart data: add a 'confidence band' area.
  const chartData = data.map((row, i) => ({
    date:     row.forecast_date.slice(5),   // MM-DD
    demand:   row.predicted_demand,
    upper:    row.upper_bound,
    lower:    row.lower_bound,
    band:     [row.lower_bound, row.upper_bound],
    isForecast: true,
  }))

  // Reference line at the median forecast
  const medianDemand = Math.round(
    chartData.reduce((s, d) => s + d.demand, 0) / chartData.length
  )

  return (
    <div className="w-full h-full min-h-[280px]">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 12, right: 16, bottom: 4, left: 8 }}>
          <defs>
            <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#ffd60a" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#ffd60a" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 6" stroke="rgba(255,255,255,0.04)" />

          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
            axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
            tickLine={false}
            interval={Math.floor(chartData.length / 8)}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}
          />

          <Tooltip content={<ChartTooltip />} />

          {/* Confidence band: upper bound fill - lower bound fill */}
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#confidenceGradient)"
            name="band"
            animationDuration={1200}
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="#06080d"
            name="band"
            animationDuration={1200}
          />

          {/* Main forecast line */}
          <Area
            type="monotone"
            dataKey="demand"
            stroke="#00d4ff"
            strokeWidth={2.5}
            fill="url(#demandGradient)"
            name="demand"
            dot={false}
            activeDot={{ r: 5, fill: '#00d4ff', stroke: '#06080d', strokeWidth: 2 }}
            animationDuration={1400}
            animationEasing="ease-out"
          />

          <ReferenceLine
            y={medianDemand}
            stroke="rgba(255,107,53,0.4)"
            strokeDasharray="4 4"
            label={{ value: `Avg ${medianDemand.toLocaleString()}`, fill: '#ff6b35', fontSize: 10, fontFamily: 'monospace', position: 'insideTopRight' }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-2 px-2">
        {[
          { color: '#00d4ff', label: '90-Day Forecast' },
          { color: '#ffd60a', label: 'Confidence Band', dashed: true },
          { color: '#ff6b35', label: 'Avg Demand', dashed: true },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-2">
            <div className={`h-0.5 w-5 rounded ${l.dashed ? 'border-t-2 border-dashed bg-transparent' : ''}`}
              style={l.dashed ? { borderColor: l.color } : { background: l.color }} />
            <span className="text-[10px] font-mono text-slate-400">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── METRIC TILES ─────────────────────────────────────────────────────────────
function InfoTile({ icon: Icon, label, value, sub, color, delay }) {
  const colors = {
    cyan:   { bg: 'bg-sc_cyan/10',   border: 'border-sc_cyan/20',   text: 'text-sc_cyan',   icon: 'text-sc_cyan' },
    yellow: { bg: 'bg-sc_yellow/10', border: 'border-sc_yellow/20', text: 'text-sc_yellow', icon: 'text-sc_yellow' },
    red:    { bg: 'bg-sc_red/10',    border: 'border-sc_red/20',    text: 'text-sc_red',    icon: 'text-sc_red' },
    green:  { bg: 'bg-sc_green/10',  border: 'border-sc_green/20',  text: 'text-sc_green',  icon: 'text-sc_green' },
    orange: { bg: 'bg-sc_orange/10', border: 'border-sc_orange/20', text: 'text-sc_orange', icon: 'text-sc_orange' },
  }[color] || {}

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className={`relative rounded-2xl border p-5 flex flex-col gap-3 overflow-hidden ${colors.bg} ${colors.border}`}
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)' }}
    >
      {/* Background glow dot */}
      <div className="absolute -top-4 -right-4 w-16 h-16 rounded-full blur-2xl opacity-30"
        style={{ background: { cyan: '#00d4ff', yellow: '#ffd60a', red: '#fb7185', green: '#4ade80', orange: '#ff6b35' }[color] }} />

      <div className={`p-2 rounded-xl w-fit ${colors.bg} border ${colors.border}`}>
        <Icon className={`w-4 h-4 ${colors.icon}`} />
      </div>
      <div>
        <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-2xl font-bold font-mono ${colors.text} leading-none`}
          style={{ textShadow: `0 0 20px currentColor` }}>
          {value}
        </p>
        {sub && <p className="text-[10px] text-slate-500 font-mono mt-1">{sub}</p>}
      </div>
    </motion.div>
  )
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function Demand() {
  const [sku, setSku] = useState('SKU-001')

  const {
    data: forecast,
    isLoading: forecastLoading,
    isError: forecastError,
    error: forecastErr,
    refetch: refetchForecast,
  } = useQuery({
    queryKey: ['demand-forecast', sku],
    queryFn: () => fetchForecast(sku),
    staleTime: 2 * 60 * 1000,
    retry: 1,
    onError: (e) => toast.error(e.message, { duration: 6000, icon: '📉' }),
  })

  const {
    data: dsData,
    isLoading: dsLoading,
    isError: dsError,
    error: dsErr,
    refetch: refetchDS,
  } = useQuery({
    queryKey: ['ds-ratio', sku],
    queryFn: () => fetchDSRatio(sku),
    staleTime: 2 * 60 * 1000,
    retry: 1,
    onError: (e) => toast.error(e.message, { duration: 6000, icon: '⚖️' }),
  })

  const isLoading = forecastLoading || dsLoading
  const ratio     = dsData?.ds_ratio ?? 0
  const showAlert = ratio >= GAUGE_THRESHOLDS.green && !isLoading

  // Derived metric values
  const predictedDemand = useMemo(() => {
    if (!forecast?.length) return dsData?.['30_day_demand'] ?? null
    const next30 = forecast.slice(0, 30)
    return Math.round(next30.reduce((s, r) => s + r.predicted_demand, 0))
  }, [forecast, dsData])

  const handleSkuChange = useCallback((newSku) => {
    setSku(newSku)
  }, [])

  const handleRefresh = useCallback(() => {
    refetchForecast()
    refetchDS()
    toast('Refreshing demand intelligence…', { icon: '🔄', duration: 1500 })
  }, [refetchForecast, refetchDS])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-6"
    >
      {/* ── HEADER ROW ── */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-mono text-white flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-sc_yellow" />
            Demand Intelligence
          </h1>
          <p className="text-xs font-mono text-slate-500 mt-1">
            90-day Prophet forecast + real-time D/S ratio analysis
          </p>
        </div>

        <div className="flex items-center gap-3">
          <SKUSelector value={sku} onChange={handleSkuChange} isLoading={isLoading} />
          <button onClick={handleRefresh} disabled={isLoading}
            className="flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-sc_cyan border border-white/10 hover:border-sc_cyan/30 bg-sc_card/60 backdrop-blur-xl px-3 py-2.5 rounded-xl transition-all disabled:opacity-40">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── ALERT BANNER ── */}
      <AnimatePresence>
        {showAlert && dsData && (
          <AlertBanner sku={sku} ratio={ratio} status={dsData.status} />
        )}
      </AnimatePresence>

      {/* ── LOADING SKELETON ── */}
      <AnimatePresence>
        {isLoading && (
          <motion.div exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <PageSkeleton />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── MAIN CONTENT ── */}
      {!isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6"
        >
          {/* ── METRIC TILES ── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <InfoTile
              icon={TrendingUp}
              label="30-Day Demand"
              value={predictedDemand != null
                ? predictedDemand >= 1000
                  ? `${(predictedDemand / 1000).toFixed(1)}k`
                  : predictedDemand.toLocaleString()
                : '—'}
              sub={forecast?.length ? 'Prophet forecast' : 'From D/S model'}
              color="cyan"
              delay={0.05}
            />
            <InfoTile
              icon={Truck}
              label="In-Transit Supply"
              value={dsData?.in_transit_supply != null
                ? dsData.in_transit_supply >= 1000
                  ? `${(dsData.in_transit_supply / 1000).toFixed(1)}k`
                  : dsData.in_transit_supply.toFixed(0)
                : '—'}
              sub={`Route: ${ROUTE_MAP[sku]}`}
              color={ratio < 1.5 ? 'green' : ratio < 2.0 ? 'yellow' : 'red'}
              delay={0.1}
            />
            <InfoTile
              icon={BarChart2}
              label="D/S Ratio"
              value={ratio > 0 ? `${ratio.toFixed(2)}×` : '—'}
              sub={dsData?.status ?? 'Calculating…'}
              color={ratio < 1.5 ? 'green' : ratio < 2.0 ? 'yellow' : 'red'}
              delay={0.15}
            />
            <InfoTile
              icon={Clock}
              label="Est. Stockout"
              value={dsData ? stockoutEstimate(ratio, dsData.in_transit_supply) : '—'}
              sub="At current demand rate"
              color={ratio < 1.5 ? 'green' : ratio < 2.0 ? 'orange' : 'red'}
              delay={0.2}
            />
          </div>

          {/* ── CHART + GAUGE ROW ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Forecast chart — 2/3 width */}
            <motion.div
              className="lg:col-span-2 bg-sc_card/50 backdrop-blur-xl border border-white/8 rounded-2xl p-6"
              style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04), 0 20px 60px rgba(0,0,0,0.3)' }}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="font-bold font-mono text-white text-sm flex items-center gap-2">
                    <Activity className="w-4 h-4 text-sc_cyan" />
                    90-Day Demand Forecast
                  </h2>
                  <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                    {sku} · Prophet model · Confidence band shown
                  </p>
                </div>
                {forecast?.length > 0 && (
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 bg-sc_elevated/60 border border-white/5 rounded-lg px-2.5 py-1.5">
                    <Info className="w-3 h-3" />
                    {forecast.length} data points
                  </div>
                )}
              </div>

              {forecastError ? (
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <AlertTriangle className="w-8 h-8 text-sc_red" />
                  <p className="text-sm text-slate-400">{forecastErr?.message}</p>
                  <button onClick={() => refetchForecast()}
                    className="text-xs font-mono text-sc_cyan border border-sc_cyan/30 bg-sc_cyan/10 px-3 py-1.5 rounded-lg hover:bg-sc_cyan/20 transition-all flex items-center gap-1.5">
                    <RefreshCw className="w-3 h-3" /> Retry
                  </button>
                </div>
              ) : (
                <ForecastChart data={forecast} sku={sku} />
              )}
            </motion.div>

            {/* D/S Gauge — 1/3 width */}
            <motion.div
              className="bg-sc_card/50 backdrop-blur-xl border border-white/8 rounded-2xl p-6 flex flex-col items-center gap-4"
              style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04), 0 20px 60px rgba(0,0,0,0.3)' }}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.15 }}
            >
              <div className="w-full">
                <h2 className="font-bold font-mono text-white text-sm flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-sc_yellow" />
                  D/S Ratio Gauge
                </h2>
                <p className="text-[10px] font-mono text-slate-500 mt-0.5">Demand vs Supply · {sku}</p>
              </div>

              {dsError ? (
                <div className="flex flex-col items-center gap-3 py-8 text-center">
                  <AlertTriangle className="w-7 h-7 text-sc_red" />
                  <p className="text-xs text-slate-400">{dsErr?.message}</p>
                  <button onClick={() => refetchDS()}
                    className="text-xs font-mono text-sc_cyan border border-sc_cyan/30 bg-sc_cyan/10 px-3 py-1.5 rounded-lg hover:bg-sc_cyan/20 transition-all flex items-center gap-1.5">
                    <RefreshCw className="w-3 h-3" /> Retry
                  </button>
                </div>
              ) : (
                <RadialGauge ratio={ratio} isLoading={dsLoading} />
              )}

              {/* Threshold guide */}
              <div className="w-full space-y-2 border-t border-white/5 pt-4">
                {[
                  { label: 'Healthy',  range: '< 1.5×',  color: '#4ade80' },
                  { label: 'Warning',  range: '1.5–2.0×', color: '#ffd60a' },
                  { label: 'Critical', range: '> 2.0×',  color: '#fb7185' },
                ].map(t => (
                  <div key={t.label} className="flex items-center justify-between text-[10px] font-mono">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: t.color }} />
                      <span className="text-slate-400">{t.label}</span>
                    </div>
                    <span style={{ color: t.color }}>{t.range}</span>
                  </div>
                ))}
              </div>

              {dsData && (
                <div className="w-full bg-sc_elevated/50 rounded-xl p-3 border border-white/5 space-y-1.5">
                  {[
                    { label: 'SKU',          value: dsData.sku },
                    { label: 'Route',        value: dsData.route_id },
                    { label: '30d Demand',   value: dsData['30_day_demand']?.toLocaleString() },
                    { label: 'In-Transit',   value: dsData.in_transit_supply?.toLocaleString() },
                  ].map(r => (
                    <div key={r.label} className="flex items-center justify-between text-[10px] font-mono">
                      <span className="text-slate-500">{r.label}</span>
                      <span className="text-slate-300">{r.value ?? '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
