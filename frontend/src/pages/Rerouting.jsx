import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { 
  ArrowRightLeft, MapPin, Package, AlertTriangle, 
  CheckCircle2, Upload, Database, Info, Navigation, Bot, X,
  Clock, Cloud, Zap, Wind, Maximize2, Layers
} from 'lucide-react'
import toast from 'react-hot-toast'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''
const API_BASE = import.meta.env.VITE_API_BASE_URL

export default function Rerouting() {
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  
  const [jsonInput, setJsonInput] = useState(JSON.stringify({
    "warehouses": [
      {"name": "Pune", "stock": 12000, "lat": 18.52, "lon": 73.85},
      {"name": "Mumbai", "stock": 8000, "lat": 19.07, "lon": 72.87},
      {"name": "Delhi", "stock": 5000, "lat": 28.61, "lon": 77.20},
      {"name": "Bangalore", "stock": 1500, "lat": 12.97, "lon": 77.59},
      {"name": "Chennai", "stock": 4000, "lat": 13.08, "lon": 80.27},
      {"name": "Kolkata", "stock": 6000, "lat": 22.57, "lon": 88.36}
    ],
    "main_warehouse": "Pune"
  }, null, 2))
  
  const [isCalculating, setIsCalculating] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current || !MAPBOX_TOKEN) return
    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [78.9, 20.5],
      zoom: 3.5,
      projection: 'globe',
      antialias: true
    })
    map.on('style.load', () => {
      map.setFog({ color: 'rgb(4, 6, 14)', 'high-color': 'rgb(10, 15, 30)', 'space-color': 'rgb(1, 2, 8)', 'star-intensity': 0.8 })
      try {
        map.addSource('mapbox-traffic', { type: 'vector', url: 'mapbox://mapbox.mapbox-traffic-v1' });
        map.addLayer({
          'id': 'traffic',
          'type': 'line',
          'source': 'mapbox-traffic',
          'source-layer': 'traffic',
          'paint': {
            'line-color': [
              'interpolate', ['linear'], ['get', 'congestion'],
              0, '#4ade80',
              0.5, '#ffd60a',
              1, '#fb7185'
            ],
            'line-width': 1.5,
            'line-opacity': 0.4
          }
        });
      } catch (e) { console.error(e); }
    })
    mapRef.current = map
    return () => {
      if (markersRef.current) markersRef.current.forEach(m => m.remove())
      if (map) map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapRef.current || !result) return;
    const map = mapRef.current;

    const drawNetwork = () => {
      if (!map.isStyleLoaded()) return;
      
      console.log("EXEC: drawNetwork with result:", result);

      // 1. CLEAR OLD LAYERS/SOURCES
      ['node-layer', 'transfer-layer', 'node-pulse-layer', 'node-labels', 'diagnostic-layer'].forEach(l => {
        if (map.getLayer(l)) map.removeLayer(l);
      });
      ['nodes-source', 'transfers-source'].forEach(s => {
        if (map.getSource(s)) map.removeSource(s);
      });

      // 2. PREPARE DATA
      const nodes = (result?.visualization || []);
      const nodesData = {
        type: 'FeatureCollection',
        features: [
          // Hardcoded Diagnostic Node to verify drawing is active
          { type: 'Feature', geometry: { type: 'Point', coordinates: [-100, 80] }, properties: { name: 'DIAGNOSTIC-NODE', color: 'red', stock: 0, demand: 0, net: 0, status: 'OK' } },
          ...nodes.map(n => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [parseFloat(n.lon), parseFloat(n.lat)] },
            properties: { ...n }
          }))
        ]
      };

      const transfers = (result?.suggestions || []);
      const transfersData = {
        type: 'FeatureCollection',
        features: transfers.map(t => {
          const from = nodes.find(n => n.name === t.from);
          const to = nodes.find(n => n.name === t.to);
          if (!from || !to) return null;
          return { type: 'Feature', geometry: { type: 'LineString', coordinates: [[parseFloat(from.lon), parseFloat(from.lat)], [parseFloat(to.lon), parseFloat(to.lat)]] }, properties: { ...t } };
        }).filter(Boolean)
      };

      // 3. ADD SOURCES
      map.addSource('nodes-source', { type: 'geojson', data: nodesData });
      map.addSource('transfers-source', { type: 'geojson', data: transfersData });

      // 4. ADD LAYERS
      map.addLayer({
        id: 'transfer-layer', type: 'line', source: 'transfers-source',
        paint: { 'line-color': '#00D4FF', 'line-width': 2, 'line-dasharray': [2, 1], 'line-opacity': 0.6 }
      });

      map.addLayer({
        id: 'node-pulse-layer', type: 'circle', source: 'nodes-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 12, 10, 35],
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.25,
          'circle-blur': 0.8
        }
      });

      map.addLayer({
        id: 'node-layer', type: 'circle', source: 'nodes-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 6, 10, 12],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff'
        }
      });

      map.addLayer({
        id: 'node-labels', type: 'symbol', source: 'nodes-source',
        layout: { 
          'text-field': ['get', 'name'],
          'text-size': 11, 'text-offset': [0, 1.8], 'text-anchor': 'top' 
        },
        paint: { 'text-color': '#adb5bd', 'text-halo-color': '#000', 'text-halo-width': 1 }
      });

      // 5. FIT BOUNDS
      const bounds = new mapboxgl.LngLatBounds();
      nodes.forEach(n => bounds.extend([parseFloat(n.lon), parseFloat(n.lat)]));
      if (!bounds.isEmpty()) {
        console.log("Adjusting Map Bounds...");
        map.fitBounds(bounds, { padding: 120, duration: 1500 });
      }
    };

    if (map.isStyleLoaded()) {
      drawNetwork();
    } else {
      map.once('style.load', drawNetwork);
    }
  }, [result]);

  const handleCalculate = async () => {
    setIsCalculating(true)
    try {
      console.log("POSTING to redistribute:", jsonInput);
      const res = await fetch(`${API_BASE}/rerouting/calculate`, {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: jsonInput
      })
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Server synchronization failed.");
      }
      const data = await res.json()
      console.log("API Response Data:", data);
      setResult(data)
      toast.success("Network redistribution synced!")
    } catch (err) { 
      console.error("Calculation Error:", err);
      toast.error(err.message || "System synchronization failed.") 
    }
    setIsCalculating(false)
  }

  return (
    <div className="h-full flex flex-col bg-[#06080d] overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
      
      {/* ── HEADER ── */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-white/5 bg-[rgba(6,8,13,0.8)] backdrop-blur-3xl sticky top-0 z-50">
        <div className="flex items-center justify-between">
           <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-sc_cyan/10 border border-sc_cyan/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,212,255,0.1)]">
               <ArrowRightLeft className="w-5 h-5 text-sc_cyan" />
             </div>
             <div>
               <h1 className="text-lg font-mono font-black text-white tracking-tight uppercase">Supply Chain Rerouting Hub</h1>
               <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-sc_green animate-pulse" />
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Real-Time Logistics Engine Operational</span>
               </div>
             </div>
           </div>
           {result?.suggestions && (
              <div className="flex items-center gap-3 px-4 py-2 bg-sc_cyan/10 border border-sc_cyan/20 rounded-xl">
                 <div className="flex flex-col items-end">
                    <span className="text-[10px] font-mono text-sc_cyan uppercase">Network Status</span>
                    <span className="text-xs font-bold text-white uppercase">{(result?.suggestions || []).length} Operations Pending</span>
                 </div>
              </div>
           )}
        </div>
      </header>

      {/* ── MAP HERO SECTION (LARGE) ── */}
      <section className="w-full h-[650px] relative shrink-0 border-b border-white/5 group">
         <div ref={mapContainerRef} className="w-full h-full" />
         
         {/* Map Overlay Tools */}
         <div className="absolute top-6 left-6 z-10 flex flex-col gap-3">
            <div className="bg-sc_card/95 backdrop-blur-2xl px-4 py-3 rounded-2xl border border-white/10 shadow-2xl flex flex-col gap-4">
               <h3 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2"><Layers className="w-3 h-3"/> Node Legend</h3>
               <div className="flex flex-col gap-3">
                  <LegendItem color="bg-sc_red" label="Deficit Area" count={(Array.isArray(result?.visualization) ? result.visualization : []).filter(n=>n.status==='DEFICIT').length} />
                  <LegendItem color="bg-sc_cyan" label="Surplus Stash" count={(Array.isArray(result?.visualization) ? result.visualization : []).filter(n=>n.status==='SURPLUS').length} />
                  <LegendItem color="bg-sc_green" label="Balanced Stock" count={(Array.isArray(result?.visualization) ? result.visualization : []).filter(n=>n.status==='OK').length} />
               </div>
            </div>
            
            <div className="bg-sc_card/95 backdrop-blur-2xl px-4 py-2.5 rounded-2xl border border-white/10 shadow-2xl flex items-center gap-3">
               <div className="flex items-center gap-2">
                  <div className="w-3 h-0.5 bg-sc_orange opacity-60" />
                  <span className="text-[10px] font-mono text-sc_orange font-bold uppercase tracking-wider">Live Traffic Radar</span>
               </div>
               <div className="h-3 w-px bg-white/10" />
               <div className="flex items-center gap-2">
                  <Cloud className="w-3 h-3 text-sc_cyan opacity-60" />
                  <span className="text-[10px] font-mono text-sc_cyan font-bold uppercase tracking-wider">Weather Shield</span>
               </div>
            </div>
         </div>

         {!MAPBOX_TOKEN && (
            <div className="absolute inset-0 bg-sc_bg z-20 flex items-center justify-center p-10 text-center">
               <div className="max-w-xs flex flex-col items-center gap-4">
                  <AlertTriangle className="w-12 h-12 text-sc_orange" />
                  <p className="font-mono text-xs text-slate-400">Add <span className="text-white">VITE_MAPBOX_TOKEN</span> to your environment to activate the global situational hub.</p>
               </div>
            </div>
         )}
      </section>

      {/* ── LOWER OPS CENTER (SCROLLABLE) ── */}
      <section className="flex-1 flex flex-col lg:flex-row gap-8 p-8 min-h-screen content-start">
         
         {/* INGESTION BLOCK */}
         <div className="lg:w-[450px] shrink-0 sticky top-28 self-start flex flex-col gap-6">
            <div className="bg-sc_card border border-white/10 rounded-3xl p-6 relative overflow-hidden group shadow-2xl">
               <div className="absolute inset-0 bg-gradient-to-br from-sc_cyan/5 via-transparent to-transparent opacity-50" />
               <div className="relative z-10">
                  <div className="flex items-center justify-between mb-6">
                     <h2 className="text-xs font-mono font-bold text-sc_cyan uppercase tracking-[0.2em] flex items-center gap-2">
                        <Upload className="w-4 h-4"/> Supply Ingestion
                     </h2>
                     <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-500 hover:text-white transition-all"><Maximize2 className="w-3.5 h-3.5"/></button>
                  </div>
                  
                  <textarea 
                     className="w-full h-80 bg-black/60 border border-white/10 rounded-2xl p-5 text-xs font-mono text-sc_cyan placeholder-slate-700 focus:ring-1 focus:ring-sc_cyan focus:border-sc_cyan/50 transition-all resize-none mb-6 shadow-inner" 
                     value={jsonInput} 
                     onChange={e=>setJsonInput(e.target.value)} 
                  />
                  
                  <button 
                     onClick={handleCalculate} 
                     disabled={isCalculating} 
                     className="w-full py-5 bg-sc_cyan text-[#06080d] font-black font-mono text-sm rounded-2xl hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-3 shadow-[0_12px_40px_rgba(0,212,255,0.25)]"
                  >
                     {isCalculating ? (
                        <div className="w-6 h-6 border-3 border-[#06080d] border-t-transparent rounded-full animate-spin" />
                     ) : (
                        <><Navigation className="w-5 h-5" /> RECOMPUTE OPERATIONS</>
                     )}
                  </button>
               </div>
            </div>
            
            <div className="p-5 bg-sc_card/40 border border-white/5 rounded-2xl italic text-[11px] text-slate-400 leading-relaxed font-mono">
               <Info className="w-4 h-4 text-sc_cyan mb-2" />
               Decision parameters are infused with real-time semantic trending from YouTube, Google News, and Shipping APIs. The rerouting algorithm prioritizes deficit clearing over distance minimizing.
            </div>
         </div>

         {/* INSIGHTS BLOCK */}
         <div className="flex-1 flex flex-col gap-6">
            <div className="bg-sc_card border border-white/10 rounded-3xl overflow-hidden flex flex-col shadow-2xl min-h-[600px]">
               <div className="px-6 py-5 border-b border-white/5 bg-white/[0.03] flex items-center justify-between">
                  <div>
                     <h3 className="text-xs font-mono font-bold text-white flex items-center gap-2 uppercase tracking-widest pb-1 underline decoration-sc_purple decoration-2 underline-offset-4">
                        <Bot className="w-5 h-5 text-sc_purple" /> AI Deployment Strategy
                     </h3>
                     <p className="text-[10px] font-mono text-slate-500 mt-1 uppercase">Automated Stock Redistribution Protocol</p>
                  </div>
                  {result && (
                     <div className="flex gap-2">
                        <div className="px-3 py-1 rounded-full bg-sc_cyan/10 border border-sc_cyan/20 text-sc_cyan text-[10px] font-mono font-bold">OPTIMIZED</div>
                     </div>
                  )}
               </div>
               
               <div className="p-6 space-y-4">
                  <AnimatePresence mode="popLayout">
                     {!result ? (
                        <div className="flex flex-col items-center justify-center py-40 gap-4 opacity-50 grayscale transition-all text-center">
                           <Database className="w-16 h-16 text-sc_cyan animate-pulse" />
                           <div className="flex flex-col gap-1">
                              <p className="text-sm font-mono text-white font-bold">READY FOR DEPLOYMENT</p>
                              <p className="text-xs font-mono text-slate-500 italic max-w-xs">Upload your regional supply configuration to trigger the proximity-aware decision matrix.</p>
                           </div>
                        </div>
                     ) : (result?.suggestions || []).length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-40 gap-4 bg-sc_green/5 border border-sc_green/10 rounded-2xl">
                           <CheckCircle2 className="w-12 h-12 text-sc_green" />
                           <p className="text-sm font-mono text-sc_green font-bold uppercase tracking-widest">Network Synchronized</p>
                           <p className="text-xs font-mono text-slate-400 text-center max-w-xs px-6">Current regional demand is perfectly aligned with on-hand supply across all monitored nodes.</p>
                        </div>
                     ) : (
                        (result?.suggestions || []).map((s,i)=>(
                           <motion.div 
                              key={i} 
                              initial={{opacity:0, y:20}} 
                              animate={{opacity:1, y:0}} 
                              transition={{delay:i*0.1}} 
                              className="bg-white/[0.03] border border-white/5 hover:border-sc_cyan/30 hover:bg-white/[0.06] rounded-2xl p-6 flex items-center gap-6 group transition-all"
                           >
                              <div className="w-14 h-14 rounded-2xl bg-sc_cyan/5 border border-sc_cyan/20 flex flex-col items-center justify-center text-sc_cyan shrink-0 transition-transform group-hover:scale-105">
                                 <Package className="w-6 h-6 mb-1 opacity-80" />
                                 <span className="text-[9px] font-black font-mono">OP-{i+100}</span>
                              </div>
                              
                              <div className="flex-1 min-w-0">
                                 <div className="flex items-center gap-3 mb-3">
                                    <span className="text-lg font-black text-white group-hover:text-sc_cyan transition-colors">{s.from}</span> 
                                    <ArrowRightLeft className="w-4 h-4 text-slate-600 animate-pulse" /> 
                                    <span className="text-lg font-black text-white">{s.to}</span>
                                 </div>
                                 <div className="flex flex-wrap items-center gap-4">
                                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sc_purple/10 border border-sc_purple/20 text-sc_purple">
                                       <Clock className="w-3.5 h-3.5"/><span className="text-[10px] font-mono font-bold">{s.eta} ETA</span>
                                    </div>
                                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-[10px] font-bold ${s.weather === 'Heavy Rain' ? 'bg-sc_orange/10 border-sc_orange/20 text-sc_orange' : 'bg-white/5 border-white/10 text-slate-400'}`}>
                                       {s.weather === 'Clear' ? <Zap className="w-3 h-3"/> : <Cloud className="w-3 h-3"/>} {s.weather.toUpperCase()}
                                    </div>
                                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-500 text-[10px] font-mono">
                                       <Wind className="w-3 h-3"/> {s.distance_km} KM
                                    </div>
                                 </div>
                                 <p className="mt-4 text-xs text-slate-500 leading-relaxed italic border-l-2 border-sc_cyan/20 pl-4">"{s.reason}"</p>
                              </div>
                              
                              <div className="text-right flex flex-col items-end shrink-0">
                                 <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">Transfer Unit</span>
                                 <div className="text-4xl font-black font-mono text-sc_cyan leading-none">+{s.quantity}</div>
                                 <span className="text-[10px] font-mono text-sc_cyan/60 font-bold uppercase mt-1">Confirmed Allocation</span>
                              </div>
                           </motion.div>
                        ))
                     )}
                  </AnimatePresence>
               </div>
            </div>
         </div>
         
      </section>

      {/* ── FOOTER STATUS ── */}
      <footer className="shrink-0 px-8 py-5 border-t border-white/5 bg-sc_card/20 flex justify-between items-center text-[10px] font-mono text-slate-500">
         <div className="flex gap-6">
            <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-sc_cyan animate-pulse" /> NETWORK ACTIVE</span>
            <span className="flex items-center gap-2 uppercase tracking-widest">Model: Gemini 2.0 Situational Engine</span>
         </div>
         <div className="flex gap-4">
            <span className="hover:text-sc_cyan cursor-pointer transition-colors">HELP CENTER</span>
            <span className="hover:text-sc_cyan cursor-pointer transition-colors">API DOCS</span>
         </div>
      </footer>

    </div>
  )
}

function LegendItem({ color, label, count }) {
  return (
    <div className="flex items-center justify-between gap-4 min-w-[160px]">
       <div className="flex items-center gap-2.5">
          <div className={`w-3 h-3 rounded-md ${color} shadow-[0_0_10px_currentColor] border border-white/20`} />
          <span className="text-[11px] font-mono font-bold text-slate-300 uppercase leading-none tracking-tight">{label}</span>
       </div>
       <span className="text-[10px] font-mono text-slate-500 font-bold">{count ?? '—'}</span>
    </div>
  )
}
