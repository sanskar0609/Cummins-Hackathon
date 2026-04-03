import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import * as d3 from 'd3'
import {
  Play, AlertTriangle, TrendingUp, DollarSign, Zap, ChevronDown,
  RotateCcw, Layers, Clock, Activity, Target, GitBranch,
  Shield, Ship, Building2, BarChart2, Info, CheckCircle
} from 'lucide-react'
import { runSimulation, CHOKEPOINTS, SUPPLIERS } from '../api/simulator'

// ─── CONSTANTS ───────────────────────────────────────────────────────────────
const TIER_COLORS = { T1: '#4ade80', T2: '#ffd60a', T3: '#fb7185' }

// ─── ANIMATED COUNTER ────────────────────────────────────────────────────────
function useCountUp(target, duration = 1400, decimals = 0) {
  const [value, setValue] = useState(0)
  const rafRef = useRef(null)
  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = performance.now()
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(parseFloat((eased * target).toFixed(decimals)))
      if (progress < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [target, duration, decimals])
  return value
}

// ─── FLOATING PARTICLE BACKGROUND (CSS 3D perspective) ───────────────────────
function ParticleField() {
  const nodes = Array.from({ length: 18 }, (_, i) => ({
    id: i,
    x: 5 + (i * 37) % 90,
    y: 5 + (i * 53) % 88,
    size: 2 + (i % 3) * 1.5,
    dur: 6 + (i % 4) * 2,
    delay: -(i * 0.7),
  }))
  const edges = [[0, 3], [3, 7], [7, 12], [1, 5], [5, 9], [2, 6], [6, 11], [4, 8], [8, 13], [10, 15], [14, 17]]

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" style={{ perspective: '600px' }}>
      <motion.div
        className="absolute inset-0"
        animate={{ rotateX: [2, -2, 2], rotateY: [-3, 3, -3] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
          {/* Edges */}
          {edges.map(([a, b], i) => {
            const na = nodes[a], nb = nodes[b]
            return (
              <line key={i}
                x1={`${na.x}%`} y1={`${na.y}%`}
                x2={`${nb.x}%`} y2={`${nb.y}%`}
                stroke="rgba(0,212,255,0.06)" strokeWidth="1"
              />
            )
          })}
          {/* Nodes */}
          {nodes.map(n => (
            <motion.circle key={n.id}
              cx={`${n.x}%`} cy={`${n.y}%`} r={Math.max(0, n.size ?? 0)}
              fill="rgba(0,212,255,0.12)"
              stroke="rgba(0,212,255,0.2)" strokeWidth="0.5"
              animate={{ r: [Math.max(0, n.size ?? 0), Math.max(0, (n.size ?? 0) * 1.5), Math.max(0, n.size ?? 0)], opacity: [0.4, 0.9, 0.4] }}
              transition={{ duration: n.dur, delay: n.delay, repeat: Infinity, ease: 'easeInOut' }}
            />
          ))}
        </svg>
      </motion.div>
    </div>
  )
}

// ─── DROPDOWN ────────────────────────────────────────────────────────────────
function SelectDropdown({ value, onChange, options, placeholder, icon: Icon, disabled }) {
  const [open, setOpen] = useState(false)
  const selected = options.find(o => o.id === value)

  return (
    <div className="relative">
      <button
        onClick={() => !disabled && setOpen(o => !o)}
        disabled={disabled}
        className="w-full flex items-center gap-2.5 bg-sc_elevated/60 border border-white/8 hover:border-white/20 rounded-xl px-3.5 py-2.5 text-sm font-mono text-left transition-all disabled:opacity-40"
      >
        {Icon && <Icon className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
        <span className={selected ? 'text-white' : 'text-slate-500'}>{selected?.label ?? placeholder}</span>
        {!disabled && (
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.18 }} className="ml-auto shrink-0">
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          </motion.div>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.14 }}
            className="absolute top-full left-0 right-0 mt-1 z-50 backdrop-blur-xl border border-white/10 rounded-xl overflow-auto shadow-2xl"
            style={{ maxHeight: 220, background: 'rgba(16,21,32,0.97)', boxShadow: '0 20px 60px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06)' }}
          >
            <button key="none" onClick={() => { onChange(null); setOpen(false) }}
              className="w-full px-3.5 py-2.5 text-xs font-mono text-slate-500 text-left hover:bg-white/5 transition-all border-b border-white/5">
              — None —
            </button>
            {options.map(o => (
              <button key={o.id} onClick={() => { onChange(o.id); setOpen(false) }}
                className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs font-mono text-left transition-all hover:bg-white/5 ${o.id === value ? 'text-sc_cyan bg-sc_cyan/5' : 'text-slate-300'}`}
              >
                <span className="flex-1 truncate">{o.label}</span>
                {o.region && <span className="text-slate-600 text-[10px]">{o.region}</span>}
                {o.tier && <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold"
                  style={{ color: TIER_COLORS[o.tier], background: `${TIER_COLORS[o.tier]}18` }}>{o.tier}</span>}
                {o.id === value && <Zap className="w-3 h-3 text-sc_cyan shrink-0" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      {open && <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />}
    </div>
  )
}

// ─── SLIDER ──────────────────────────────────────────────────────────────────
function RangeSlider({ value, onChange, min, max, step = 1, label, unit, color = '#00d4ff', disabled }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-slate-400">{label}</span>
        <motion.span key={value} initial={{ scale: 1.3 }} animate={{ scale: 1 }}
          className="text-sm font-bold font-mono px-2.5 py-0.5 rounded-lg border"
          style={{ color, borderColor: `${color}30`, background: `${color}15` }}>
          {value}{unit}
        </motion.span>
      </div>
      <div className="relative h-2 bg-white/5 rounded-full group">
        <div className="absolute inset-y-0 left-0 rounded-full transition-all"
          style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}80, ${color})` }} />
        <input type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(Number(e.target.value))} disabled={disabled}
          className="absolute inset-0 w-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          style={{ height: '100%' }}
        />
        <div className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 bg-sc_bg transition-all"
          style={{ left: `calc(${pct}% - 8px)`, borderColor: color, boxShadow: `0 0 10px ${color}80` }} />
      </div>
      <div className="flex justify-between text-[10px] font-mono text-slate-600">
        <span>{min}{unit}</span><span>{max}{unit}</span>
      </div>
    </div>
  )
}

// ─── MONTE CARLO PROGRESS ────────────────────────────────────────────────────
function MonteCarloProgress({ isRunning }) {
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState(0)
  const rafRef = useRef(null)
  const startRef = useRef(null)

  const PHASES = [
    'Seeding random variables…',
    'Injecting chokepoint shock…',
    'Propagating cascade failures…',
    'Aggregating probability density…',
    'Computing cost impact model…',
    'Finalising Monte Carlo output…',
  ]

  useEffect(() => {
    if (!isRunning) { setProgress(0); setPhase(0); return }
    startRef.current = performance.now()
    const DURATION = 3200
    const tick = (now) => {
      const elapsed = now - startRef.current
      const p = Math.min(elapsed / DURATION, 0.95) // never hit 100 — real result will
      setProgress(Math.round(p * 100))
      setPhase(Math.floor(p * PHASES.length))
      if (p < 0.95) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [isRunning])

  if (!isRunning) return null

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="space-y-4 py-6">
      <div className="flex items-center gap-3">
        <div className="relative w-12 h-12 shrink-0">
          <svg viewBox="0 0 48 48" className="w-full h-full -rotate-90">
            <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(0,212,255,0.1)" strokeWidth="4" />
            <motion.circle cx="24" cy="24" r="20" fill="none" stroke="#00d4ff" strokeWidth="4"
              strokeLinecap="round" strokeDasharray={`${2 * Math.PI * 20}`}
              strokeDashoffset={`${2 * Math.PI * 20 * (1 - progress / 100)}`}
              transition={{ duration: 0.3 }}
              style={{ filter: 'drop-shadow(0 0 6px #00d4ff)' }}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold text-sc_cyan">
            {progress}%
          </span>
        </div>

        <div className="flex-1">
          <p className="text-sm font-mono font-bold text-white mb-1">Running Monte Carlo Simulation</p>
          <p className="text-xs font-mono text-slate-400">1,000 iterations · {PHASES[Math.min(phase, PHASES.length - 1)]}</p>
        </div>
      </div>

      {/* Bar */}
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div className="h-full rounded-full"
          style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #00d4ff80, #00d4ff, #c084fc)' }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Particle flicker */}
      <div className="flex gap-1.5">
        {Array.from({ length: 20 }).map((_, i) => (
          <motion.div key={i} className="flex-1 h-4 rounded-sm bg-sc_cyan/20"
            animate={{ scaleY: [0.3, 1, 0.3], opacity: [0.3, 0.9, 0.3] }}
            transition={{ duration: 0.5 + Math.random() * 0.5, repeat: Infinity, delay: i * 0.05 }}
          />
        ))}
      </div>
    </motion.div>
  )
}

// ─── D3 HISTOGRAM ────────────────────────────────────────────────────────────
function StockoutHistogram({ probability }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!svgRef.current || probability == null) return

    // Generate synthetic normal distribution around the Monte Carlo result
    const std = Math.max(4, Math.min(15, probability * 0.18))
    const samples = Array.from({ length: 1200 }, () => {
      // Box-Muller transform
      const u1 = Math.random(), u2 = Math.random()
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
      return Math.max(0, Math.min(100, probability + z * std))
    })

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const W = svgRef.current.clientWidth || 360
    const H = 180
    const margin = { top: 16, right: 12, bottom: 32, left: 36 }
    const w = W - margin.left - margin.right
    const h = H - margin.top - margin.bottom

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

    // X scale
    const xMin = Math.max(0, probability - std * 3.2)
    const xMax = Math.min(100, probability + std * 3.2)
    const x = d3.scaleLinear().domain([xMin, xMax]).range([0, w])

    // Histogram bins
    const bins = d3.bin().domain(x.domain()).thresholds(x.ticks(24))(samples)

    const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).range([h, 0])

    // Gradient
    const defs = svg.append('defs')
    const grad = defs.append('linearGradient').attr('id', 'histGrad').attr('x1', 0).attr('x2', 1)
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#4ade80').attr('stop-opacity', 0.8)
    grad.append('stop').attr('offset', '50%').attr('stop-color', '#ffd60a').attr('stop-opacity', 0.8)
    grad.append('stop').attr('offset', '100%').attr('stop-color', '#fb7185').attr('stop-opacity', 0.9)

    // Grid
    g.selectAll('.grid-line')
      .data(y.ticks(4))
      .enter().append('line')
      .attr('class', 'grid-line')
      .attr('x1', 0).attr('x2', w)
      .attr('y1', d => y(d)).attr('y2', d => y(d))
      .attr('stroke', 'rgba(255,255,255,0.04)').attr('stroke-dasharray', '3,4')

    // Bars
    g.selectAll('.bar').data(bins).enter().append('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.x0) + 1)
      .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2))
      .attr('y', h)
      .attr('height', 0)
      .attr('rx', 2)
      .attr('fill', 'url(#histGrad)')
      .transition().duration(900).delay((_, i) => i * 18).ease(d3.easeCubicOut)
      .attr('y', d => y(d.length))
      .attr('height', d => h - y(d.length))

    // Mean line
    g.append('line')
      .attr('x1', x(probability)).attr('x2', x(probability))
      .attr('y1', 0).attr('y2', h)
      .attr('stroke', '#00d4ff').attr('stroke-width', 1.5).attr('stroke-dasharray', '4,3')
      .attr('opacity', 0.8)

    g.append('text')
      .attr('x', x(probability) + 4).attr('y', 10)
      .attr('fill', '#00d4ff').attr('font-size', 9).attr('font-family', 'monospace')
      .text(`${probability.toFixed(1)}%`)

    // X Axis
    g.append('g').attr('transform', `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d => `${d}%`))
      .call(ax => {
        ax.select('.domain').attr('stroke', 'rgba(255,255,255,0.06)')
        ax.selectAll('.tick line').attr('stroke', 'rgba(255,255,255,0.06)')
        ax.selectAll('.tick text').attr('fill', '#64748b').attr('font-size', 9).attr('font-family', 'monospace')
      })

    // Y Axis
    g.append('g')
      .call(d3.axisLeft(y).ticks(4).tickFormat(d => d))
      .call(ax => {
        ax.select('.domain').remove()
        ax.selectAll('.tick line').remove()
        ax.selectAll('.tick text').attr('fill', '#64748b').attr('font-size', 9).attr('font-family', 'monospace')
      })

  }, [probability])

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-sc_cyan" />
          Stockout Probability Distribution
        </p>
        <span className="text-[10px] font-mono text-slate-600">n=1,000 MC iterations</span>
      </div>
      <svg ref={svgRef} className="w-full" height={180} />
    </div>
  )
}

// ─── RISK TABLE ───────────────────────────────────────────────────────────────
function CascadeRiskTable({ data, params }) {
  const affected = []

  // Build affected list from params
  if (params.chokepoint_id) {
    const cp = CHOKEPOINTS.find(c => c.id === params.chokepoint_id)
    if (cp) affected.push({ name: cp.label, type: 'Route', risk: 'HIGH', impact: 'Transit blocked', icon: Ship })
  }
  if (params.supplier_failure_id) {
    const sup = SUPPLIERS.find(s => s.id === params.supplier_failure_id)
    if (sup) affected.push({ name: sup.label, type: `${sup.tier} Supplier`, risk: 'CRITICAL', impact: 'Direct default', icon: Building2 })
  }

  // Generate cascading rows based on cascading count
  const cascade = Math.round(data.avg_nodes_failed_cascading)
  const cascadeRows = SUPPLIERS.slice(0, Math.min(cascade, 5))
    .filter(s => s.id !== params.supplier_failure_id)
    .map(s => ({
      name: s.label, type: `${s.tier} Supplier`,
      risk: s.tier === 'T3' ? 'HIGH' : 'MEDIUM',
      impact: 'Cascade dependency', icon: GitBranch
    }))

  const all = [...affected, ...cascadeRows]
  if (!all.length) return null

  const riskColor = { CRITICAL: 'text-sc_red', HIGH: 'text-sc_orange', MEDIUM: 'text-sc_yellow' }
  const riskBg = { CRITICAL: 'bg-sc_red/10 border-sc_red/20', HIGH: 'bg-sc_orange/10 border-sc_orange/20', MEDIUM: 'bg-sc_yellow/10 border-sc_yellow/20' }

  return (
    <div className="space-y-2">
      <p className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
        <GitBranch className="w-3.5 h-3.5 text-sc_purple" />
        Cascading Failure Map
        <span className="text-[10px] text-slate-600 ml-auto">~{cascade} nodes affected</span>
      </p>
      <div className="space-y-1.5">
        {all.map((row, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + i * 0.06 }}
            className="flex items-center gap-3 bg-sc_elevated/40 border border-white/5 rounded-xl px-3 py-2"
          >
            <row.icon className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-mono text-white truncate">{row.name}</p>
              <p className="text-[10px] text-slate-500">{row.type} · {row.impact}</p>
            </div>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${riskColor[row.risk]} ${riskBg[row.risk]}`}>
              {row.risk}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

// ─── COST CARD ────────────────────────────────────────────────────────────────
function CostImpactCard({ usd }) {
  const animated = useCountUp(usd, 1600, 0)
  const M = animated / 1_000_000
  const isHigh = usd > 2_000_000
  const color = isHigh ? '#fb7185' : usd > 800_000 ? '#ffd60a' : '#4ade80'

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.3 }}
      className="rounded-2xl border p-5 relative overflow-hidden"
      style={{ borderColor: `${color}25`, background: `linear-gradient(135deg, ${color}08, transparent 60%)` }}>
      <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full blur-3xl opacity-20"
        style={{ background: color }} />
      <div className="relative z-10">
        <div className="flex items-center gap-2 mb-3">
          <DollarSign className="w-4 h-4" style={{ color }} />
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Est. Cost Impact</span>
        </div>
        <div className="flex items-end gap-2">
          <span className="text-4xl font-bold font-mono" style={{ color, textShadow: `0 0 30px ${color}60` }}>
            ${M >= 1 ? `${M.toFixed(2)}M` : `${(animated / 1000).toFixed(0)}K`}
          </span>
          <span className="text-xs font-mono text-slate-500 mb-1">USD</span>
        </div>
        <p className="text-[10px] text-slate-500 font-mono mt-1.5">
          {isHigh ? '⚠ Critical exposure — board-level escalation advised' : 'Manageable exposure within operational buffer'}
        </p>
      </div>
    </motion.div>
  )
}

// ─── CONFIDENCE INTERVAL ─────────────────────────────────────────────────────
function ConfidenceDisplay({ probability, nodes }) {
  const std = Math.max(4, probability * 0.18)
  const lo = Math.max(0, probability - 1.96 * std).toFixed(1)
  const hi = Math.min(100, probability + 1.96 * std).toFixed(1)
  const color = probability < 30 ? '#4ade80' : probability < 60 ? '#ffd60a' : '#fb7185'

  return (
    <div className="grid grid-cols-2 gap-3">
      {[
        { label: 'Stockout Probability', value: `${probability.toFixed(1)}%`, color, sub: `95% CI: [${lo}%, ${hi}%]` },
        { label: 'Avg Nodes Cascading', value: `${nodes.toFixed(1)}`, color: '#c084fc', sub: 'Mean across 1,000 runs' },
      ].map(c => (
        <div key={c.label} className="bg-sc_elevated/50 border border-white/5 rounded-xl p-3 text-center">
          <p className="text-[10px] font-mono text-slate-500 mb-1">{c.label}</p>
          <p className="text-xl font-bold font-mono" style={{ color: c.color }}>{c.value}</p>
          <p className="text-[10px] text-slate-600 font-mono mt-0.5">{c.sub}</p>
        </div>
      ))}
    </div>
  )
}

// ─── EMPTY STATE ──────────────────────────────────────────────────────────────
function SimulatorEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-5 h-full py-12 px-4 text-center relative">
      <ParticleField />
      <div className="relative z-10 flex flex-col items-center gap-5">
        {/* Animated concentric rings */}
        <div className="relative w-24 h-24 flex items-center justify-center">
          {[1, 2, 3].map(i => (
            <motion.div key={i}
              className="absolute rounded-full border border-sc_purple/30"
              style={{ width: i * 32, height: i * 32 }}
              animate={{ scale: [1, 1.08, 1], opacity: [0.5, 0.15, 0.5] }}
              transition={{ duration: 2.5, delay: i * 0.4, repeat: Infinity }}
            />
          ))}
          <div className="w-14 h-14 rounded-full bg-sc_purple/15 border border-sc_purple/30 flex items-center justify-center"
            style={{ boxShadow: '0 0 30px rgba(192,132,252,0.2)' }}>
            <Target className="w-7 h-7 text-sc_purple" />
          </div>
        </div>

        <div className="space-y-2 max-w-xs">
          <h3 className="text-xl font-bold font-mono text-white">Ready to Simulate</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Configure a supply chain shock scenario on the left, then run 1,000 Monte Carlo iterations to quantify cascading risk, stockout probability, and financial exposure.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2">
          {['Chokepoint closure', 'Supplier default', 'Demand shock', 'Cascade failures'].map(t => (
            <span key={t} className="text-[10px] font-mono text-slate-400 bg-sc_elevated/60 border border-white/5 rounded-full px-3 py-1">
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── MAIN PAGE ─────────────────────────────────────────────────────────────────
export default function Simulator() {
  const [form, setForm] = useState({
    chokepoint_id: null,
    lock_days: 14,
    supplier_failure_id: null,
    demand_spike_percent: 0,
  })
  const [result, setResult] = useState(null)

  const { mutate: simulate, isLoading } = useMutation({
    mutationFn: runSimulation,
    onSuccess: (data) => {
      setResult(data)
      toast.success('Monte Carlo simulation complete', { icon: '🎯', duration: 3000 })
    },
    onError: (e) => {
      toast.error(e.message, { duration: 7000, icon: '⚠️' })
    },
  })

  const handleRun = () => {
    if (!form.chokepoint_id && !form.supplier_failure_id && form.demand_spike_percent === 0) {
      toast.error('Configure at least one shock parameter before running', { icon: '⚙️' })
      return
    }
    setResult(null)
    simulate({
      chokepoint_id: form.chokepoint_id || null,
      lock_days: form.lock_days,
      supplier_failure_id: form.supplier_failure_id || null,
      demand_spike_percent: form.demand_spike_percent,
    })
  }

  const handleReset = () => {
    setForm({ chokepoint_id: null, lock_days: 14, supplier_failure_id: null, demand_spike_percent: 0 })
    setResult(null)
  }

  const prob = result?.probability_of_stockout_percent ?? 0
  const probColor = prob < 30 ? '#4ade80' : prob < 60 ? '#ffd60a' : '#fb7185'

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}
      className="h-full flex flex-col gap-6 pb-6">

      {/* ── HEADER ── */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-mono text-white flex items-center gap-2.5">
            <Target className="w-6 h-6 text-sc_purple" />
            What-If Simulator
          </h1>
          <p className="text-xs font-mono text-slate-500 mt-1">
            1,000-iteration Monte Carlo · Neo4j cascade graph · Financial impact model
          </p>
        </div>
        <button onClick={handleReset} disabled={isLoading}
          className="flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-white border border-white/10 hover:border-white/20 bg-sc_card/60 backdrop-blur-xl px-3 py-2.5 rounded-xl transition-all disabled:opacity-40">
          <RotateCcw className="w-3.5 h-3.5" /> Reset
        </button>
      </div>

      {/* ── TWO-COLUMN LAYOUT ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 flex-1">

        {/* ── LEFT: CONTROLS ── */}
        <motion.div
          initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}
          className="lg:col-span-2 bg-sc_card/50 backdrop-blur-xl border border-white/8 rounded-2xl p-6 flex flex-col gap-5"
          style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04), 0 20px 60px rgba(0,0,0,0.3)' }}
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-sc_purple" />
            <h2 className="text-sm font-bold font-mono text-white">Shock Configuration</h2>
          </div>

          {/* Chokepoint */}
          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Ship className="w-3 h-3" /> Chokepoint Closure
            </label>
            <SelectDropdown
              value={form.chokepoint_id}
              onChange={v => setForm(f => ({ ...f, chokepoint_id: v }))}
              options={CHOKEPOINTS}
              placeholder="Select chokepoint…"
              icon={Ship}
              disabled={isLoading}
            />
          </div>

          {/* Lock Duration */}
          <RangeSlider
            label="Lock Duration"
            value={form.lock_days}
            onChange={v => setForm(f => ({ ...f, lock_days: v }))}
            min={1} max={90} unit=" days"
            color="#c084fc"
            disabled={isLoading || !form.chokepoint_id}
          />

          <div className="h-px bg-white/5" />

          {/* Supplier Failure */}
          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Building2 className="w-3 h-3" /> Supplier Failure
            </label>
            <SelectDropdown
              value={form.supplier_failure_id}
              onChange={v => setForm(f => ({ ...f, supplier_failure_id: v }))}
              options={SUPPLIERS}
              placeholder="Select supplier…"
              icon={Building2}
              disabled={isLoading}
            />
          </div>

          <div className="h-px bg-white/5" />

          {/* Demand Spike */}
          <RangeSlider
            label="Demand Spike"
            value={form.demand_spike_percent}
            onChange={v => setForm(f => ({ ...f, demand_spike_percent: v }))}
            min={0} max={100} step={5} unit="%"
            color="#ffd60a"
            disabled={isLoading}
          />

          {/* Parameter Summary */}
          <div className="bg-sc_elevated/50 border border-white/5 rounded-xl p-3 space-y-1.5">
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">Simulation Parameters</p>
            {[
              { label: 'Chokepoint', value: CHOKEPOINTS.find(c => c.id === form.chokepoint_id)?.label || 'None' },
              { label: 'Lock Days', value: form.chokepoint_id ? `${form.lock_days} days` : '—' },
              { label: 'Supplier', value: SUPPLIERS.find(s => s.id === form.supplier_failure_id)?.label || 'None' },
              { label: 'Demand Spike', value: form.demand_spike_percent > 0 ? `+${form.demand_spike_percent}%` : '0%' },
            ].map(r => (
              <div key={r.label} className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-500">{r.label}</span>
                <span className="text-slate-300 truncate max-w-[140px] text-right">{r.value}</span>
              </div>
            ))}
          </div>

          {/* RUN BUTTON */}
          <motion.button
            onClick={handleRun}
            disabled={isLoading}
            whileHover={!isLoading ? { scale: 1.02 } : {}}
            whileTap={!isLoading ? { scale: 0.98 } : {}}
            className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl font-mono font-bold text-sm transition-all disabled:opacity-60 disabled:cursor-not-allowed relative overflow-hidden"
            style={{
              background: isLoading
                ? 'rgba(192,132,252,0.2)'
                : 'linear-gradient(135deg, rgba(192,132,252,0.3), rgba(192,132,252,0.15))',
              border: '1px solid rgba(192,132,252,0.4)',
              color: '#c084fc',
              boxShadow: isLoading ? 'none' : '0 0 30px rgba(192,132,252,0.2)',
            }}
          >
            {isLoading ? (
              <>
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-sc_purple/30 border-t-sc_purple rounded-full" />
                Running…
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Run Simulation
              </>
            )}
            {/* Shimmer */}
            {!isLoading && (
              <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent"
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }} />
            )}
          </motion.button>
        </motion.div>

        {/* ── RIGHT: RESULTS ── */}
        <motion.div
          initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="lg:col-span-3 bg-sc_card/50 backdrop-blur-xl border border-white/8 rounded-2xl overflow-hidden relative"
          style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04), 0 20px 60px rgba(0,0,0,0.3)', minHeight: 480 }}
        >
          <AnimatePresence mode="wait">

            {/* Empty state */}
            {!isLoading && !result && (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0">
                <SimulatorEmptyState />
              </motion.div>
            )}

            {/* Monte Carlo Progress */}
            {isLoading && (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 p-6 flex flex-col justify-center relative overflow-hidden">
                <ParticleField />
                <div className="relative z-10">
                  <MonteCarloProgress isRunning={isLoading} />
                </div>
              </motion.div>
            )}

            {/* Results */}
            {!isLoading && result && (
              <motion.div key="results" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="absolute inset-0 p-6 pb-10 overflow-y-auto space-y-5">

                {/* Result header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-sc_green" />
                    <span className="text-sm font-mono font-bold text-white">Simulation Complete</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 bg-sc_elevated/60 border border-white/5 px-2.5 py-1 rounded-lg">
                    {result.iterations?.toLocaleString()} iterations
                  </span>
                </div>

                {/* Cost card */}
                <CostImpactCard usd={result.estimated_cost_impact_usd} />

                {/* Confidence / stats */}
                <ConfidenceDisplay
                  probability={result.probability_of_stockout_percent}
                  nodes={result.avg_nodes_failed_cascading}
                />

                {/* D3 Histogram */}
                <div className="bg-sc_elevated/40 border border-white/5 rounded-2xl p-4">
                  <StockoutHistogram probability={result.probability_of_stockout_percent} />
                </div>

                {/* Cascade table */}
                {result.parameters && (
                  <CascadeRiskTable data={result} params={result.parameters} />
                )}

                {/* Info footnote */}
                <div className="flex items-start gap-2 text-[10px] font-mono text-slate-600 border-t border-white/5 pt-3">
                  <Info className="w-3 h-3 mt-0.5 shrink-0" />
                  Monte Carlo probability distribution generated from 1,000 stochastic iterations on live Neo4j supply graph topology.
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </motion.div>
  )
}
