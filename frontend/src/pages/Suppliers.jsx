import React, { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import cytoscape from 'cytoscape'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Zap, RefreshCw, Maximize2, X, Activity, Upload, ShieldCheck, AlertTriangle, Loader2
} from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = 'https://cummins-hackathon.onrender.com/api'

export default function Suppliers() {
  const containerRef = useRef(null)
  const cyRef = useRef(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [simulationData, setSimulationData] = useState(null)
  const [localNodes, setLocalNodes] = useState([])

  useEffect(() => {
    if (!containerRef.current) return
    if (cyRef.current) cyRef.current.destroy()

    // THE ABSOLUTE DEFINITIVE NEO4J CIRCULAR FIX (V5)
    cyRef.current = cytoscape({
      container: containerRef.current,
      boxSelectionEnabled: false,
      autounselectify: true,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      minZoom: 0.1,
      maxZoom: 3,
      style: [
        {
          selector: 'node',
          style: {
            'shape': 'circle', // THE GOLD STANDARD
            'width': 40, // FIXED AT 40px
            'height': 40, // FIXED AT 40px
            'background-color': 'data(color)',
            'label': 'data(name)',
            'color': '#fff',
            'font-size': '8px',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-outline-color': 'data(color)',
            'text-outline-width': '2px',
            'border-width': '2px',
            'border-color': '#fff'
          }
        },
        {
          selector: 'node[id = "YOU"]',
          style: {
            'width': 60,
            'height': 60,
            'background-color': '#6366f1',
            'font-size': '10px'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#475569',
            'curve-style': 'bezier',
            'opacity': 0.4
          }
        }
      ]
    })

    cyRef.current.on('tap', 'node', (e) => setSelectedNode(e.target.data()))

    // Forced Initial State
    const init = [
        { data: { id: 'YOU', name: 'HQ', color: '#6366f1' } },
        { data: { id: 's1', name: 'Foxconn', color: '#10b981', parent: 'YOU' } },
        { data: { id: 'e1', source: 's1', target: 'YOU' } }
    ]
    cyRef.current.add(init)
    cyRef.current.layout({ name: 'cose', padding: 100, animate: false }).run()
    cyRef.current.fit()

    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [])

  const handleCSVUpload = (data) => {
    if (!cyRef.current) return
    setLocalNodes(data)
    
    const elements = []
    const ids = new Set(['YOU'])
    elements.push({ data: { id: 'YOU', name: 'HQ', color: '#6366f1' } })

    data.forEach(row => {
        const name = row.supplier_name || row.id || 'Node'
        const s_id = row.supplier_id || row.id || name
        const parent = row.parent_supplier || row.parent || 'YOU'
        elements.push({ data: { id: s_id, name: name.substring(0,6), color: '#10b981' } })
        ids.add(s_id)
        if (ids.has(parent)) {
            elements.push({ data: { id: `e_${s_id}`, source: s_id, target: parent } })
        }
    })

    cyRef.current.elements().remove()
    cyRef.current.add(elements)
    cyRef.current.layout({ name: 'cose', componentSpacing: 100 }).run()
    cyRef.current.fit()
    toast.success('Digital Twin Reconstructed')
  }

  return (
    <div className="relative w-full h-[800px] bg-[#020617] rounded-[3rem] overflow-hidden border-4 border-white/5">
      <div 
        ref={containerRef} 
        style={{ width: '100%', height: '100%', position: 'absolute' }}
      />

      <div className="absolute top-10 left-10 z-50 pointer-events-none">
        <div className="flex items-center gap-6 bg-slate-900/60 backdrop-blur-3xl p-6 rounded-[2rem] border border-white/10 pointer-events-auto">
          <div className="p-4 bg-indigo-600 rounded-3xl"><Activity className="w-8 h-8 text-white" /></div>
          <div><h1 className="text-white font-black text-2xl uppercase tracking-tighter">Circular Twin Explorer</h1></div>
        </div>
      </div>

      <SimulationPanel onUpload={handleCSVUpload} onRun={() => {}} isLoading={false} canRun={localNodes.length > 0} />

      <div className="absolute bottom-10 right-10 z-50 flex flex-col gap-4">
        <button onClick={() => cyRef.current?.fit()} className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center text-white"><Maximize2 className="w-8 h-8" /></button>
        <button onClick={() => window.location.reload()} className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center text-white"><RefreshCw className="w-8 h-8" /></button>
      </div>
    </div>
  )
}

function SimulationPanel({ onUpload, onRun, isLoading, canRun }) {
  const [hasFile, setHasFile] = useState(false)
  const inputRef = useRef(null)

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      onUpload(evt.target.result.trim().split('\n').slice(1).map(l => {
        const p = l.split(',')
        return { tier: p[0], id: p[1], name: p[2], parent: p[5] }
      }))
      setHasFile(true)
    }
    reader.readAsText(file)
  }

  return (
    <div className="absolute top-44 left-10 z-50 w-80 bg-slate-900/80 backdrop-blur-3xl border border-white/10 rounded-[2.5rem] p-8 shadow-3xl">
      <div onClick={() => inputRef.current.click()} className="w-full h-40 border-2 border-dashed rounded-[2rem] flex flex-col items-center justify-center cursor-pointer mb-6 border-white/10">
        <input type="file" ref={inputRef} className="hidden" accept=".csv" onChange={handleFile} />
        <Upload className="w-12 h-12 text-slate-700" />
      </div>
      <button onClick={onRun} disabled={!canRun} className="w-full py-5 bg-indigo-600 text-white rounded-[2rem] font-black uppercase text-xs">Run Propagation</button>
    </div>
  )
}
