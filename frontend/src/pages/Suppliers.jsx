import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import cytoscape from 'cytoscape'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  X, MapPin, Layers, Zap, RefreshCw, Maximize2, ZoomIn, ZoomOut,
  ChevronRight, AlertTriangle, Brain, Share2, Loader2
} from 'lucide-react'
import { fetchSupplierGraph, fetchSupplierNarrative } from '../api/suppliers'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const TIER_CONFIG = {
  T0: { color: '#00d4ff', label: 'OEM (T0)',    size: 78 },
  T1: { color: '#4ade80', label: 'Tier 1',       size: 56 },
  T2: { color: '#ffd60a', label: 'Tier 2',       size: 42 },
  T3: { color: '#fb7185', label: 'Tier 3 (Raw)', size: 32 },
}

const HEALTH_COLOR = {
  GOOD:     '#4ade80',
  WARNING:  '#ffd60a',
  CRITICAL: '#fb7185',
}

const EDGE_COLOR = {
  SUPPLIES_TO: '#00d4ff',
  DEPENDS_ON:  '#c084fc',
  SHIPS_VIA:   '#ff6b35',
}

const TYPE_ICON = { Company: '🏭', Supplier: '🔩', Product: '📦', Route: '🚢' }

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function resolveNodeColor(data) {
  if (data.health && HEALTH_COLOR[data.health]) return HEALTH_COLOR[data.health]
  if (data.type === 'Product') return '#c084fc'
  if (data.type === 'Route')   return '#ff6b35'
  return TIER_CONFIG[data.tier]?.color ?? '#64748b'
}

function resolveNodeSize(data) {
  if (data.type === 'Product') return 30
  if (data.type === 'Route')   return 28
  return TIER_CONFIG[data.tier]?.size ?? 36
}

function resolveEdgeColor(label) {
  return EDGE_COLOR[label] ?? '#475569'
}

// ─── BUILD CYTOSCAPE ELEMENTS ─────────────────────────────────────────────────
function buildElements(graphData) {
  const elements = []

  for (const n of (graphData?.nodes ?? [])) {
    const d = n.data ?? {}
    const color = resolveNodeColor(d)
    const size  = resolveNodeSize(d)
    const name  = d.name || d.id || ''
    elements.push({
      data: {
        ...d,
        cyColor:    color,
        cySize:     size,
        shortName:  name.length > 14 ? name.slice(0, 13) + '…' : name,
      }
    })
  }

  for (const e of (graphData?.edges ?? [])) {
    const d = e.data ?? {}
    elements.push({
      data: {
        ...d,
        cyEdgeColor: resolveEdgeColor(d.label),
      }
    })
  }

  return elements
}

// ─── CYTOSCAPE STYLESHEET ─────────────────────────────────────────────────────
// NOTE: shadow-blur / shadow-opacity are NOT valid Cytoscape CSS properties and
// cause warnings. edge:hover is also invalid — we use mouseover events instead.
function buildStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'background-color':    'data(cyColor)',
        'width':               'data(cySize)',
        'height':              'data(cySize)',
        'label':               'data(shortName)',
        'color':               '#e2e8f0',
        'font-size':           '10px',
        'font-family':         'Space Grotesk, monospace',
        'font-weight':         '600',
        'text-valign':         'bottom',
        'text-margin-y':       6,
        'text-outline-color':  '#06080d',
        'text-outline-width':  3,
        'border-width':        2,
        'border-color':        'data(cyColor)',
        'border-opacity':      0.7,
        'transition-property': 'border-width, border-opacity, width, height, background-opacity',
        'transition-duration': '180ms',
        'z-index':             10,
      }
    },
    {
      selector: 'node[type = "Product"]',
      style: {
        'shape':            'diamond',
        'background-color': '#c084fc',
        'border-color':     '#c084fc',
      }
    },
    {
      selector: 'node[type = "Route"]',
      style: {
        'shape':            'hexagon',
        'background-color': '#ff6b35',
        'border-color':     '#ff6b35',
      }
    },
    // Selected state (applied via .addClass in tap handler)
    {
      selector: 'node.selected',
      style: {
        'border-width':   5,
        'border-color':   '#ffffff',
        'border-opacity': 1,
        'z-index':        100,
      }
    },
    // Faded (non-neighbourhood nodes after selection)
    {
      selector: '.faded',
      style: {
        'opacity': 0.12,
      }
    },
    // Hovered — set/removed via mouseover/mouseout events
    {
      selector: 'node.hovered',
      style: {
        'border-width':   4,
        'border-opacity': 1,
        'z-index':        80,
      }
    },
    {
      selector: 'edge',
      style: {
        'width':              2,
        'line-color':         'data(cyEdgeColor)',
        'target-arrow-color': 'data(cyEdgeColor)',
        'target-arrow-shape': 'triangle',
        'curve-style':        'bezier',
        'arrow-scale':        1.1,
        'opacity':            0.55,
        'transition-property':'opacity, width',
        'transition-duration':'150ms',
      }
    },
    {
      selector: 'edge.highlighted',
      style: {
        'opacity': 1,
        'width':   3,
      }
    },
  ]
}

// ─── LOADING SKELETON ─────────────────────────────────────────────────────────
function GraphSkeleton() {
  return (
    <div className="absolute inset-0 rounded-2xl overflow-hidden bg-sc_card/40 flex items-center justify-center"
      style={{ boxShadow: '0 0 0 1px rgba(255,255,255,0.05)' }}>
      {/* Animated node placeholders */}
      {[
        { cx: '50%', cy: '42%', r: 39, delay: 0 },
        { cx: '25%', cy: '28%', r: 27, delay: 0.15 },
        { cx: '70%', cy: '28%', r: 27, delay: 0.25 },
        { cx: '18%', cy: '60%', r: 20, delay: 0.35 },
        { cx: '38%', cy: '62%', r: 20, delay: 0.4 },
        { cx: '62%', cy: '62%', r: 20, delay: 0.45 },
        { cx: '82%', cy: '60%', r: 20, delay: 0.5 },
      ].map((n, i) => (
        <motion.div key={i}
          className="absolute rounded-full bg-white/5 border border-white/8"
          style={{ left: n.cx, top: n.cy, width: n.r * 2, height: n.r * 2, transform: 'translate(-50%, -50%)' }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, delay: n.delay, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}
      <div className="flex flex-col items-center gap-4 z-10">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-2 border-sc_cyan/20 border-t-sc_cyan rounded-full"
          style={{ boxShadow: '0 0 20px rgba(0,212,255,0.2)' }} />
        <p className="font-mono text-sc_cyan text-sm tracking-widest uppercase">Loading Supply Graph</p>
        <p className="font-mono text-slate-500 text-xs">Querying Neo4j Knowledge Graph...</p>
      </div>
    </div>
  )
}

// ─── NODE DETAIL PANEL ────────────────────────────────────────────────────────
function NodeDetailPanel({ node, onClose }) {
  const [narrativeText, setNarrativeText] = useState('')
  const [isTyping, setIsTyping]           = useState(false)
  const typingRef = useRef(null)

  // Clean up typewriter on unmount
  useEffect(() => () => { if (typingRef.current) clearInterval(typingRef.current) }, [])

  const { mutate: generateNarrative, isLoading: narrativeLoading } = useMutation({
    mutationFn: () => fetchSupplierNarrative(node.data.id, node.data.name),
    onSuccess: (data) => startTypewriter(data?.narrative ?? 'No narrative generated.'),
    onError: (e) => {
      toast.error(e.message, { duration: 5000, icon: '🤖' })
      setNarrativeText('Health signals not yet gathered. Use the /health endpoint first to collect OSINT data.')
    }
  })

  function startTypewriter(text) {
    if (typingRef.current) clearInterval(typingRef.current)
    setNarrativeText('')
    setIsTyping(true)
    let i = 0
    typingRef.current = setInterval(() => {
      i++
      setNarrativeText(text.slice(0, i))
      if (i >= text.length) {
        clearInterval(typingRef.current)
        typingRef.current = null
        setIsTyping(false)
      }
    }, 18)
  }

  const d       = node.data ?? {}
  const hColor  = d.health ? (HEALTH_COLOR[d.health] ?? '#64748b') : (TIER_CONFIG[d.tier]?.color ?? '#00d4ff')
  const typeIcon = TYPE_ICON[d.type] ?? '⬡'
  const isSupplierLike = d.type === 'Supplier' || d.type === 'Company'

  return (
    <motion.div
      initial={{ x: 48, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 48, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="absolute top-4 right-4 bottom-4 w-80 z-30 flex flex-col pointer-events-auto"
    >
      <div className="flex-1 flex flex-col bg-sc_card/90 backdrop-blur-2xl border border-white/8 rounded-2xl overflow-hidden shadow-2xl"
        style={{ boxShadow: `0 0 40px ${hColor}12, 0 25px 60px rgba(0,0,0,0.5)` }}>

        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-white/5"
          style={{ background: `linear-gradient(135deg, ${hColor}15, transparent 70%)` }}>
          <div className="flex items-start gap-3">
            <span className="text-3xl mt-0.5 leading-none">{typeIcon}</span>
            <div>
              <h3 className="text-white font-bold text-sm leading-snug">{d.name ?? d.id}</h3>
              <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                {d.tier && (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border"
                    style={{ color: hColor, borderColor: `${hColor}40`, background: `${hColor}15` }}>
                    {d.tier}
                  </span>
                )}
                {d.health && (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border"
                    style={{ color: hColor, borderColor: `${hColor}30`, background: `${hColor}10` }}>
                    {d.health}
                  </span>
                )}
                {!d.tier && !d.health && (
                  <span className="text-[10px] font-mono text-slate-400">{d.type}</span>
                )}
              </div>
            </div>
          </div>
          <button onClick={onClose}
            className="text-slate-500 hover:text-white p-1.5 hover:bg-white/10 rounded-lg transition-all shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Properties */}
        <div className="p-4 space-y-2 border-b border-white/5">
          {[
            { label: 'ID',       value: d.id,       Icon: Zap },
            { label: 'Location', value: d.location,  Icon: MapPin },
            { label: 'Type',     value: d.type,      Icon: Layers },
          ].filter(r => r.value).map(row => (
            <div key={row.label} className="flex items-center gap-2.5 text-xs">
              <row.Icon className="w-3 h-3 text-slate-500 shrink-0" />
              <span className="text-slate-500 w-14 shrink-0">{row.label}</span>
              <span className="text-slate-200 font-mono truncate">{row.value}</span>
            </div>
          ))}
        </div>

        {/* AI Narrative */}
        {isSupplierLike && (
          <div className="p-4 flex flex-col gap-3 flex-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-sc_purple" />
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">AI Narrative</span>
              </div>
              <button
                onClick={() => generateNarrative()}
                disabled={narrativeLoading}
                className="flex items-center gap-1.5 text-[10px] font-mono text-sc_purple border border-sc_purple/30 bg-sc_purple/10 hover:bg-sc_purple/20 px-2 py-1 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {narrativeLoading
                  ? <><Loader2 className="w-3 h-3 animate-spin" />Generating…</>
                  : <><Brain className="w-3 h-3" />Generate</>
                }
              </button>
            </div>
            <div className="flex-1 bg-sc_elevated/50 rounded-xl p-3 border border-white/5 min-h-[90px] overflow-y-auto">
              {narrativeText
                ? <p className="text-xs text-slate-300 leading-relaxed">
                    {narrativeText}
                    {isTyping && <span className="inline-block w-[2px] h-3 bg-sc_purple ml-0.5 animate-pulse rounded-sm align-middle" />}
                  </p>
                : <p className="text-xs text-slate-600 italic">
                    Click 'Generate' to produce an AI risk narrative using OSINT signals.
                  </p>
              }
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-white/5">
          <p className="text-[10px] font-mono text-slate-600 flex items-center gap-1.5">
            <Share2 className="w-3 h-3" />
            Neo4j Knowledge Graph
          </p>
        </div>
      </div>
    </motion.div>
  )
}

// ─── LEGEND ───────────────────────────────────────────────────────────────────
function Legend() {
  return (
    <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.9 }}
      className="absolute bottom-4 left-4 z-30 bg-sc_card/85 backdrop-blur-xl border border-white/8 rounded-2xl px-4 py-3.5">
      <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-2.5">Tier Legend</p>
      <div className="grid grid-cols-2 gap-x-5 gap-y-1.5 mb-3">
        {Object.entries(TIER_CONFIG).map(([tier, cfg]) => (
          <div key={tier} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: cfg.color }} />
            <span className="text-[10px] font-mono text-slate-400">{cfg.label}</span>
          </div>
        ))}
        {[
          { color: '#c084fc', label: 'Product' },
          { color: '#ff6b35', label: 'Route' },
        ].map(t => (
          <div key={t.label} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: t.color }} />
            <span className="text-[10px] font-mono text-slate-400">{t.label}</span>
          </div>
        ))}
      </div>
      <div className="border-t border-white/5 pt-2.5 space-y-1.5">
        <p className="text-[10px] font-mono text-slate-500 mb-1.5">Edge types</p>
        {Object.entries(EDGE_COLOR).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div className="w-5 h-0.5 rounded shrink-0" style={{ background: color }} />
            <span className="text-[10px] font-mono text-slate-400">{type.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// ─── ZOOM CONTROLS ────────────────────────────────────────────────────────────
function ZoomControls({ onZoomIn, onZoomOut, onFit }) {
  return (
    <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.6 }}
      className="absolute bottom-4 right-4 z-30 flex flex-col gap-1.5">
      {[
        { icon: <ZoomIn   className="w-4 h-4" />, fn: onZoomIn,  title: 'Zoom in' },
        { icon: <ZoomOut  className="w-4 h-4" />, fn: onZoomOut, title: 'Zoom out' },
        { icon: <Maximize2 className="w-4 h-4" />, fn: onFit,   title: 'Fit to screen' },
      ].map((btn, i) => (
        <button key={i} title={btn.title} onClick={btn.fn}
          className="w-9 h-9 bg-sc_card/90 border border-white/10 rounded-xl flex items-center justify-center text-slate-400 hover:text-sc_cyan hover:border-sc_cyan/40 hover:bg-sc_cyan/10 backdrop-blur-xl transition-all">
          {btn.icon}
        </button>
      ))}
    </motion.div>
  )
}

// ─── STATS BAR ────────────────────────────────────────────────────────────────
function StatsBar({ nodes, edges }) {
  const suppliers = nodes.filter(n => n.data?.type === 'Supplier')
  const critical  = suppliers.filter(n => n.data?.health === 'CRITICAL').length
  const warning   = suppliers.filter(n => n.data?.health === 'WARNING').length
  const good      = suppliers.filter(n => n.data?.health === 'GOOD').length

  return (
    <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }}
      className="absolute top-4 left-4 z-30">
      <div className="bg-sc_card/85 backdrop-blur-2xl border border-white/8 rounded-2xl px-5 py-3 shadow-2xl"
        style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2">
            <Share2 className="w-4 h-4 text-sc_cyan" />
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Supplier Graph</span>
          </div>
          <div className="w-px h-5 bg-white/10" />
          <div className="flex items-center gap-4">
            {[
              { label: 'Nodes',    value: nodes.length,  color: 'text-sc_cyan' },
              { label: 'Edges',    value: edges.length,  color: 'text-slate-300' },
              { label: 'Critical', value: critical,      color: 'text-sc_red' },
              { label: 'Warning',  value: warning,       color: 'text-sc_yellow' },
              { label: 'Healthy',  value: good,          color: 'text-sc_green' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className={`text-base font-bold font-mono ${s.color}`}>{s.value}</div>
                <div className="text-[9px] text-slate-500 uppercase tracking-wider">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function Suppliers() {
  const containerRef  = useRef(null)
  const cyRef         = useRef(null)
  const [selectedNode, setSelectedNode] = useState(null)

  // ── DATA FETCH ──────────────────────────────────────────────────────────────
  const { data: rawGraph, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['supplier-graph'],
    queryFn: fetchSupplierGraph,
    staleTime: 5 * 60 * 1000,
    retry: 1,
    onError: (e) => toast.error(e.message, { duration: 6000, icon: '🕸️' }),
  })

  // ── CYTOSCAPE INIT ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!rawGraph) return

    const elements = buildElements(rawGraph)
    if (elements.filter(e => !e.data.source).length === 0) return

    // isMounted guards every async/deferred callback so stale closures
    // cannot touch state or a destroyed Cytoscape instance.
    let isMounted = true
    let rafId = null

    // Destroy any previous instance BEFORE scheduling the new one
    if (cyRef.current) {
      try {
        cyRef.current.removeAllListeners()
        cyRef.current.destroy()
      } catch (_) {}
      cyRef.current = null
    }

    // Defer init to next animation frame so React has fully committed the
    // container div to the real DOM before Cytoscape reads its dimensions.
    rafId = requestAnimationFrame(() => {
      // By the time the frame fires, isMounted may already be false if the
      // component unmounted before the frame ran — bail immediately.
      if (!isMounted || !containerRef.current) return

      let cy
      try {
        cy = cytoscape({
          container: containerRef.current,
          elements,
          style: buildStylesheet(),
          layout: {
            name:              'cose',
            animate:           true,
            animationDuration: 1000,
            fit:               true,
            padding:           70,
            nodeRepulsion:     () => 14000,
            nodeOverlap:       24,
            idealEdgeLength:   () => 130,
            edgeElasticity:    () => 100,
            gravity:           80,
            numIter:           1000,
            coolingFactor:     0.99,
            minTemp:           1.0,
            randomize:         false,
          },
          userZoomingEnabled: true,
          userPanningEnabled: true,
          wheelSensitivity:   0.35,
        })
      } catch (err) {
        console.error('[Suppliers] Cytoscape init failed:', err)
        return
      }

      // Double-check: component might have unmounted while cytoscape() was running
      if (!isMounted) {
        try { cy.destroy() } catch (_) {}
        return
      }

      cyRef.current = cy

      // ── EVENT HANDLERS ──────────────────────────────────────────────────
      cy.on('tap', 'node', (evt) => {
        if (!isMounted) return
        try {
          const node = evt.target
          cy.elements().removeClass('selected faded highlighted hovered')
          node.addClass('selected')
          const hood = node.closedNeighborhood()
          cy.elements().not(hood).addClass('faded')
          hood.edges().addClass('highlighted')
          setSelectedNode({ data: node.data() })
        } catch (e) {
          console.warn('[Suppliers] node tap error:', e)
        }
      })

      cy.on('tap', (evt) => {
        if (!isMounted) return
        try {
          if (evt.target === cy) {
            cy.elements().removeClass('selected faded highlighted hovered')
            setSelectedNode(null)
          }
        } catch (e) {
          console.warn('[Suppliers] bg tap error:', e)
        }
      })

      cy.on('mouseover', 'node', (evt) => {
        if (!isMounted) return
        try { evt.target.addClass('hovered') } catch (_) {}
      })
      cy.on('mouseout', 'node', (evt) => {
        if (!isMounted) return
        try { evt.target.removeClass('hovered') } catch (_) {}
      })
      cy.on('mouseover', 'edge', (evt) => {
        if (!isMounted) return
        try { evt.target.style({ opacity: 1, width: 3 }) } catch (_) {}
      })
      cy.on('mouseout', 'edge', (evt) => {
        if (!isMounted) return
        try { evt.target.style({ opacity: 0.55, width: 2 }) } catch (_) {}
      })
    }) // end requestAnimationFrame

    // ── CLEANUP — runs when component unmounts OR rawGraph changes ──────────
    return () => {
      isMounted = false                        // stop all in-flight callbacks first
      if (rafId != null) cancelAnimationFrame(rafId)   // cancel pending init frame
      try {
        if (cyRef.current) {
          cyRef.current.removeAllListeners()   // detach all events before destroy
          cyRef.current.destroy()
          cyRef.current = null
        }
      } catch (e) {
        console.warn('[Suppliers] Cytoscape cleanup error:', e)
      }
      setSelectedNode(null)
    }
  }, [rawGraph])

  // ── CONTROL CALLBACKS ────────────────────────────────────────────────────
  const handleZoomIn  = useCallback(() => { try { cyRef.current?.zoom({ level: (cyRef.current.zoom() * 1.3), renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 } }) } catch (_) {} }, [])
  const handleZoomOut = useCallback(() => { try { cyRef.current?.zoom({ level: (cyRef.current.zoom() * 0.77), renderedPosition: { x: cyRef.current.width() / 2, y: cyRef.current.height() / 2 } }) } catch (_) {} }, [])
  const handleFit     = useCallback(() => { try { cyRef.current?.fit(60) } catch (_) {} }, [])

  const handleSeedGraph = useCallback(async () => {
    const apiBase = import.meta.env.VITE_API_BASE_URL
    try {
      await fetch(`${apiBase}/admin/seed-graph`)
      toast.success('Graph seeded! Reloading…', { icon: '🌱' })
      refetch()
    } catch {
      toast.error('Seed request failed — check Neo4j connection')
    }
  }, [refetch])

  const nodes    = rawGraph?.nodes ?? []
  const edges    = rawGraph?.edges ?? []
  const hasNodes = nodes.length > 0

  const location = useLocation()

  return (
    <motion.div
      key={location.pathname}  // force full remount on route change so Cytoscape never touches a stale DOM node
      className="relative w-full"
      style={{ height: 'calc(100vh - 64px - 32px)', minHeight: '600px' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* ── GRAPH CANVAS — always rendered so ref is stable ── */}
      <div
        ref={containerRef}
        className="absolute inset-0 rounded-2xl overflow-hidden"
        style={{
          background: 'radial-gradient(ellipse at 50% 35%, #06101e 0%, #06080d 70%)',
          boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 30px 80px rgba(0,0,0,0.7)',
          // Hide canvas until data is loaded to prevent a flash of empty Cytoscape
          opacity: isLoading || !hasNodes ? 0 : 1,
          transition: 'opacity 0.6s ease',
        }}
      />

      {/* ── LOADING SKELETON ── */}
      <AnimatePresence>
        {isLoading && (
          <motion.div className="absolute inset-0 z-20" exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
            <GraphSkeleton />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── ERROR ── */}
      <AnimatePresence>
        {isError && !isLoading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-20 flex items-center justify-center bg-sc_bg/95 rounded-2xl">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <div className="p-5 bg-sc_red/10 rounded-full border border-sc_red/20">
                <AlertTriangle className="w-10 h-10 text-sc_red" />
              </div>
              <h3 className="text-xl font-bold font-mono text-white">Graph Unavailable</h3>
              <p className="text-slate-400 text-sm">{error?.message}</p>
              <button onClick={() => refetch()} className="btn-primary flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── EMPTY STATE — graph loaded but no nodes ── */}
      <AnimatePresence>
        {!isLoading && !isError && !hasNodes && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-20 flex items-center justify-center">
            <div className="flex flex-col items-center gap-4 text-center max-w-sm">
              <div className="p-5 bg-sc_purple/10 rounded-full border border-sc_purple/20">
                <Share2 className="w-10 h-10 text-sc_purple" />
              </div>
              <h3 className="text-xl font-bold font-mono text-white">Graph Not Seeded</h3>
              <p className="text-slate-400 text-sm">No supplier nodes found in Neo4j. Seed the graph to visualise the supply network.</p>
              <button onClick={handleSeedGraph} className="btn-primary flex items-center gap-2">
                <Zap className="w-4 h-4" /> Seed Graph Now
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── OVERLAYS (only when graph is visible) ── */}
      {!isLoading && !isError && hasNodes && (
        <>
          <StatsBar nodes={nodes} edges={edges} />

          <motion.button
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
            onClick={() => { refetch(); toast('Refreshing graph…', { icon: '🔄', duration: 1500 }) }}
            className="absolute top-4 z-30 flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-sc_cyan border border-white/10 hover:border-sc_cyan/30 bg-sc_card/80 backdrop-blur-xl px-3 py-2 rounded-xl transition-all"
            style={{ right: selectedNode ? '340px' : '56px' }}
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </motion.button>

          <Legend />
          <ZoomControls onZoomIn={handleZoomIn} onZoomOut={handleZoomOut} onFit={handleFit} />

          {/* Hint — only when nothing selected */}
          {!selectedNode && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.8 }}
              className="absolute bottom-16 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
              <div className="bg-sc_card/70 backdrop-blur-xl border border-white/8 rounded-full px-4 py-2 text-xs font-mono text-slate-500 flex items-center gap-2">
                <ChevronRight className="w-3 h-3" />
                Click any node to inspect details and generate an AI narrative
              </div>
            </motion.div>
          )}
        </>
      )}

      {/* ── NODE DETAIL PANEL ── */}
      <AnimatePresence>
        {selectedNode && (
          <NodeDetailPanel
            node={selectedNode}
            onClose={() => {
              setSelectedNode(null)
              try { cyRef.current?.elements().removeClass('selected faded highlighted hovered') } catch (_) {}
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}
