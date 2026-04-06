import React, { useState, useMemo, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
  ReferenceArea, Label
} from 'recharts'
import {
  TrendingUp, TrendingDown, Package, Truck, BarChart3,
  AlertTriangle, Clock, ChevronDown, RefreshCw, Activity,
  Zap, BarChart2, Info, Bot, Sparkles, Loader,
  Youtube, Globe, Newspaper, Share2, Compass, ArrowRightLeft,
  Calendar, CheckCircle2, Search, Database
} from 'lucide-react'
import { fetchForecast, fetchDSRatio, fetchAgentSense, fetchCompanyProfile, ROUTE_MAP } from '../api/demand'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const GAUGE_THRESHOLDS = { green: 1.5, yellow: 2.0 }

function gaugeColor(ratio) {
  if (ratio < GAUGE_THRESHOLDS.green)  return { stroke: '#4ade80', glow: '#4ade8055', label: 'HEALTHY',  text: 'text-sc_green' }
  if (ratio < GAUGE_THRESHOLDS.yellow) return { stroke: '#ffd60a', glow: '#ffd60a55', label: 'WARNING',  text: 'text-sc_yellow' }
  return                                       { stroke: '#fb7185', glow: '#fb718555', label: 'CRITICAL', text: 'text-sc_red' }
}

function stockoutEstimate(ratio, supplyQty) {
  if (!ratio || ratio === 0) return 'NO DATA'
  if (ratio < 1.0) return '> 90 days'
  const est = Math.max(0, Math.round(90 / ratio))
  if (est > 90) return '> 90 days'
  return `~${est} days`
}

// ─── COMPONENT: RADIAL GAUGE ──────────────────────────────────────────────────
function RadialGauge({ ratio, isLoading }) {
  const maxRatio = 3.5; const cRatio = Math.min(ratio ?? 0, maxRatio); const pct = cRatio / maxRatio; const color = gaugeColor(ratio ?? 0); const SIZE = 220; const CX = SIZE / 2; const CY = SIZE / 2; const R = 88; const S_DEG = 150; const SW_DEG = 240; const eDeg = S_DEG + SW_DEG * pct; const toRad = (d) => (d * Math.PI) / 180; const arcP = (deg, r = R) => [CX + r * Math.cos(toRad(deg)), CY + r * Math.sin(toRad(deg))]; const [sx, sy] = arcP(S_DEG); const [ex, ey] = arcP(eDeg); const lArc = SW_DEG * pct > 180 ? 1 : 0
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={SIZE} height={SIZE * 0.78} viewBox={`0 0 ${SIZE} ${SIZE * 0.78}`} style={{ overflow: 'visible' }}>
        <defs><filter id="gglow"><feGaussianBlur stdDeviation="4" result="cb"/><feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
        <path d={`M ${arcP(S_DEG)[0]} ${arcP(S_DEG)[1]} A ${R} ${R} 0 1 1 ${arcP(S_DEG + SW_DEG - 0.01)[0]} ${arcP(S_DEG + SW_DEG - 0.01)[1]}`} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={12} strokeLinecap="round" />
        {!isLoading && cRatio > 0 && <motion.path d={`M ${sx} ${sy} A ${R} ${R} 0 ${lArc} 1 ${ex} ${ey}`} fill="none" stroke={color.stroke} strokeWidth={12} strokeLinecap="round" filter="url(#gglow)" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, ease: 'easeOut' }} />}
        {[0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5].map((t) => { const tD = S_DEG + SW_DEG * (t / maxRatio); const [ix, iy] = arcP(tD, R - 16); const [ox, oy] = arcP(tD, R + 4); return <line key={t} x1={ix} y1={iy} x2={ox} y2={oy} stroke={[1.5, 2.0].includes(t) ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.12)'} strokeWidth={1} /> })}
        <motion.text x={CX} y={CY - 6} textAnchor="middle" fill={color.stroke} fontSize="34" fontWeight="700" fontFamily="Space Grotesk">{(ratio ?? 0).toFixed(2)}</motion.text>
        <text x={CX} y={CY + 22} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" fontFamily="monospace" letterSpacing="2">D/S RATIO</text>
      </svg>
      <div className="flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-mono font-bold tracking-widest" style={{ color: color.stroke, borderColor: `${color.stroke}40`, background: `${color.glow}` }}>
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: color.stroke }} />
        {isLoading ? 'SYNCING…' : (ratio > 0 ? color.label : 'NO DATA')}
      </div>
    </div>
  )
}

// ─── COMPONENT: FORECAST CHART ────────────────────────────────────────────────
function ForecastChart({ data, sku }) {
  if (!data?.length) return (
     <div className="flex flex-col items-center justify-center p-20 gap-4 opacity-40">
        <Database className="w-12 h-12 text-slate-500" />
        <div className="text-center font-mono text-xs uppercase tracking-widest leading-loose">Waintg to Supply Updates... <br/> Run Forecaster Pipeline to Sync.</div>
     </div>
  )
  const chartData = data.map((row) => ({ date: row.forecast_date.slice(5), demand: row.predicted_demand, upper: row.upper_bound, lower: row.lower_bound }))
  return (
    <div className="w-full h-full flex flex-col pt-4">
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 20, right: 10, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="dg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3}/><stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/></linearGradient>
            <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ffd60a" stopOpacity={0.1}/><stop offset="95%" stopColor="#ffd60a" stopOpacity={0}/></linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
          <ReferenceArea x1={chartData[0]?.date} x2={chartData[29]?.date} fill="rgba(0,212,255,0.02)" strokeOpacity={0}><Label value="MONTH 1" position="top" fill="#00d4ff" fontSize={10} fontFamily="monospace" opacity={0.6} /></ReferenceArea>
          <ReferenceArea x1={chartData[30]?.date} x2={chartData[59]?.date} fill="rgba(255,214,10,0.01)" strokeOpacity={0}><Label value="MONTH 2" position="top" fill="#ffd60a" fontSize={10} fontFamily="monospace" opacity={0.6} /></ReferenceArea>
          <ReferenceArea x1={chartData[60]?.date} x2={chartData[89]?.date} fill="rgba(0,212,255,0.02)" strokeOpacity={0}><Label value="MONTH 3" position="top" fill="#00d4ff" fontSize={10} fontFamily="monospace" opacity={0.6} /></ReferenceArea>
          <XAxis dataKey="date" tick={{fill:'#475569', fontSize:10}} axisLine={false} tickLine={false} interval={Math.max(1, Math.floor(chartData.length / 6))} />
          <YAxis tick={{fill:'#475569', fontSize:10}} axisLine={false} tickLine={false} hide />
          <Tooltip content={({active, payload}) => active && payload ? (
            <div className="bg-sc_card border border-white/10 p-3 rounded-xl font-mono text-[10px]">
              <div className="text-sc_cyan mb-1">{payload[0].payload.date}</div>
              <div className="text-white font-bold text-xs">{Math.round(payload[0].value)} units</div>
            </div>
          ) : null} />
          <Area type="monotone" dataKey="upper" stroke="none" fill="url(#cg)" />
          <Area type="monotone" dataKey="demand" stroke="#00d4ff" strokeWidth={2} fill="url(#dg)" animationDuration={2000} />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex justify-around border-t border-white/5 py-4 mt-2">
        {[0, 1, 2].map(i => {
           const s = chartData.slice(i*30, (i+1)*30); const t = s.reduce((sum,d)=>sum+d.demand,0); const pT = i>0?chartData.slice((i-1)*30,i*30).reduce((sum,d)=>sum+d.demand,0):0; const tr = pT?(t-pT)/pT*100:0
           return <div key={i} className="text-center"><p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Month {i+1}</p><div className="text-sm font-black text-white">{Math.round(t/1000)}K</div><div className={`text-[9px] font-bold ${tr>=0?'text-sc_green':'text-sc_red'}`}>{i>0?(tr>=0?'↗':'↘'):'•'} {i>0?`${Math.abs(Math.round(tr))}%`:'BASE'}</div></div>
        })}
      </div>
    </div>
  )
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function Demand() {
  const [sku, setSku] = useState('SKU-001')
  const [agentQuery, setAgentQuery] = useState('')
  const [agentResult, setAgentResult] = useState(null)
  const [isSensing, setIsSensing] = useState(false)
  const [autoSensedProfile, setAutoSensedProfile] = useState(null)

  const { data: profile } = useQuery({ queryKey:['profile'], queryFn: fetchCompanyProfile })
  const { data: forecast, isLoading: fLoading } = useQuery({ queryKey:['forecast', sku], queryFn: () => fetchForecast(sku) })
  const { data: dsData, isLoading: dsLoading } = useQuery({ queryKey:['ds', sku], queryFn: () => fetchDSRatio(sku) })

  useEffect(() => {
    if (profile?.name && profile.name !== autoSensedProfile) {
      const q = `${profile.name} ${profile.industry || ''} market demand disruptions`.trim()
      setAgentQuery(q); handleAgentSense(null, q); setAutoSensedProfile(profile.name)
    }
  }, [profile?.name])

  const ratio = dsData?.ds_ratio ?? 0
  const supply = dsData?.in_transit_supply ?? 0
  const demand30 = dsData?.['30_day_demand'] ?? 0

  const handleAgentSense = async (e, qO) => {
    if (e) e.preventDefault(); const q = qO || agentQuery; if (!q) return
    setIsSensing(true); try { const res = await fetchAgentSense(q); setAgentResult(res) } catch(err) { toast.error("Offline") } setIsSensing(false)
  }

  return (
    <div className="space-y-10 pb-32">
      
      {/* ── HEADER ── */}
      <header className="flex justify-between items-center bg-sc_card/60 p-6 rounded-2xl border border-white/5 backdrop-blur-xl sticky top-0 z-50">
        <div>
          <h1 className="text-2xl font-black font-mono text-white flex items-center gap-3"><Sparkles className="text-sc_cyan" /> Predictive Demand Intelligence</h1>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest leading-none">Autonomous Market Sensing & Forecasting</p>
        </div>
        <div className="flex gap-4 items-center">
           <div className={`px-4 py-2 rounded-xl bg-sc_green/5 border border-sc_green/20 text-sc_green font-mono text-[10px] font-bold`}>
             <CheckCircle2 className="w-3 h-3 inline mr-2"/> PROFILE SYNCED
           </div>
           <SKUSelector value={sku} onChange={setSku} skuList={['SKU-001', 'SKU-002', 'SKU-003']} />
        </div>
      </header>

      {/* ── SECTION 1: MULTI-SOURCE SIGNAL INTELLIGENCE (TOP) ── */}
      <section className="bg-sc_card border border-white/5 rounded-3xl p-8 space-y-8 shadow-2xl relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-sc_purple/10 via-transparent to-transparent pointer-events-none" />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
           <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-sc_purple/10 border border-sc_purple/20 flex items-center justify-center text-sc_purple shadow-[0_0_30px_rgba(168,85,247,0.15)]"><Bot className="w-7 h-7" /></div>
              <div>
                 <h2 className="text-xl font-black font-mono text-white uppercase tracking-widest leading-none mb-1 text-premium">Multi-Source Signal Intelligence</h2>
                 <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-bold">Automated Semantic Analysis Across 6 Hubs</p>
              </div>
           </div>
           <div className="flex flex-wrap gap-2.5">
              <SourceBadge icon={Youtube} label="Youtube" /><SourceBadge icon={Share2} label="Reddit" /><SourceBadge icon={Globe} label="Trends" /><SourceBadge icon={Newspaper} label="NewsAPI" />
           </div>
        </div>

        <form onSubmit={handleAgentSense} className="flex gap-4 relative z-10 bg-black/40 p-2.5 rounded-2xl border border-white/10 shadow-inner group">
           <div className="px-5 flex items-center border-r border-white/5"><Search className="w-4 h-4 text-slate-500 group-focus-within:text-sc_cyan transition-colors"/></div>
           <input className="flex-1 bg-transparent py-4 text-sm font-mono text-sc_cyan focus:outline-none placeholder-slate-600" value={agentQuery} onChange={e=>setAgentQuery(e.target.value)} placeholder="Query agent: e.g. 'Unilever demand disruptions'..." />
           <button className="bg-sc_cyan text-black px-12 py-4 rounded-xl font-mono font-black text-xs flex items-center gap-3 hover:brightness-110 active:scale-95 transition-all shadow-lg">{isSensing ? <Loader className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />} SENSE MARKET</button>
        </form>

        <AnimatePresence mode="popLayout">
           {!agentResult ? (
             <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-50 select-none">
                <Activity className="w-14 h-14 text-sc_purple animate-pulse" />
                <div className="text-center">
                   <p className="text-base font-mono font-black text-white uppercase tracking-[0.2em] mb-1">WAINTG TO SUPPLY UPDATES</p>
                   <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-bold">Waiting for rerouting ingestion or manual sensor trigger</p>
                </div>
             </div>
           ) : (
             <motion.div initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
                <InsightCard icon={Share2} label="Social Sentiment" title={agentResult.product_in_demand} sub={`Trend: ${agentResult.demand_trend_pct}%`} content={agentResult.query_context} accent="cyan" />
                <InsightCard icon={AlertTriangle} label="Supply Disruptions" title={agentResult.disruption_flag ? "Risk Detected" : "Stable Stock"} sub="Global Trade News" content={agentResult.disruption_summary || "No immediate supply disruptions identified in global news feeds."} accent={agentResult.disruption_flag ? "red" : "green"} />
                <InsightCard icon={Compass} label="Search Volume" title="Consumer Intent" sub="Trends / Reddit" content={`AI detected a ${agentResult.trend_direction} pattern in consumer search signals over the last 90 days.`} accent="yellow" />
                <div className="md:col-span-2 lg:col-span-1 bg-sc_purple/5 border border-sc_purple/20 rounded-2xl p-7 flex flex-col justify-between border-dashed relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity"><Bot className="w-20 h-20" /></div>
                    <div>
                       <div className="flex items-center gap-2.5 mb-6"><Zap className="w-4 h-4 text-sc_purple" /><span className="text-[10px] font-mono text-sc_purple font-black uppercase tracking-widest">Final Recommendation</span></div>
                       <p className="text-[13px] text-white font-mono leading-relaxed italic text-premium">"Based on signal fusion, we recommend increasing safety stock by {agentResult.demand_trend_pct}% across coastal zones."</p>
                    </div>
                    <div className="mt-8 flex items-center justify-between border-t border-sc_purple/10 pt-4">
                       <div className={`px-5 py-2 rounded-full text-[10px] font-black tracking-[0.2em] ${agentResult.trend_direction==='rising'?'bg-sc_green/10 text-sc_green border border-sc_green/30':'bg-sc_yellow/10 text-sc_yellow border border-sc_yellow/30'}`}>{agentResult.trend_direction?.toUpperCase() || 'STABLE'} SIGNAL</div>
                       <div className="flex flex-col items-end"><span className="text-[9px] font-mono text-slate-500 uppercase font-black">Confidence</span><span className="text-lg font-black text-white font-mono">{agentResult.confidence_percentage}</span></div>
                    </div>
                </div>
             </motion.div>
           )}
        </AnimatePresence>
      </section>

      {/* ── SECTION 2: METRICS TILES (NOW BELOW SENSING) ── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <InfoTile icon={TrendingUp} label="Predicted 30d" value={demand30 > 0 ? `${(demand30/1000).toFixed(1)}K` : 'NO DATA'} sub="90d Prophet Window" color="cyan" />
        <InfoTile icon={Truck} label="Global Stock" value={supply > 0 ? `${(supply/1000).toFixed(1)}K` : 'NO DATA'} sub="Ingested manifest supply" color="green" />
        <InfoTile icon={BarChart2} label="Overall D/S" value={ratio > 0 ? `${ratio.toFixed(2)}x` : 'NO DATA'} sub={ratio > 1.5 ? 'Threshold Breached' : 'Optimal Balance'} color={ratio > 1.5 ? 'yellow' : 'cyan'} />
        <InfoTile icon={Clock} label="Stockout Risk" value={stockoutEstimate(ratio, supply)} sub="Coverage Horizon" color="orange" />
      </div>

      {/* ── SECTION 3: FORECASTING & DSR GAUGE (BOTTOM) ── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        <div className="lg:col-span-2 bg-sc_card border border-white/5 rounded-3xl p-10 relative overflow-hidden shadow-2xl">
           <div className="flex items-center justify-between mb-2">
              <h3 className="text-[11px] font-mono font-black text-white uppercase tracking-[0.2em] flex items-center gap-3"><BarChart3 className="w-5 h-5 text-sc_cyan" /> Proximity Forecasting</h3>
              <div className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-[9px] font-mono text-slate-500 uppercase font-bold tracking-widest">v2.1 Synchronized</div>
           </div>
           <ForecastChart data={forecast} sku={sku} />
        </div>
        <div className="bg-sc_card border border-white/5 rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl">
           <div className="absolute top-10 left-10 text-[11px] font-mono font-black text-white uppercase tracking-[0.2em] flex items-center gap-3"><Activity className="w-5 h-5 text-sc_purple"/> Overall D/S Ratio</div>
           <RadialGauge ratio={ratio} isLoading={dsLoading} />
           <div className="mt-12 p-6 bg-white/[0.02] rounded-2xl border border-white/5 text-center max-w-[240px]">
              <p className="text-[10px] font-mono text-slate-500 leading-relaxed uppercase tracking-widest italic font-bold">"Updated automatically after entering rerouting data ingestion."</p>
           </div>
        </div>
      </section>

    </div>
  )
}

function InsightCard({ icon: Icon, label, title, sub, content, accent }) {
  const ac = { cyan: 'text-sc_cyan border-sc_cyan/30 bg-sc_cyan/5', red: 'text-sc_red border-sc_red/30 bg-sc_red/5', green: 'text-sc_green border-sc_green/30 bg-sc_green/5', yellow: 'text-sc_yellow border-sc_yellow/30 bg-sc_yellow/5' }[accent]
  return (
    <div className={`border-l-4 rounded-2xl p-7 flex flex-col gap-4 shadow-xl shadow-black/20 backdrop-blur-sm ${ac}`}>
       <div className="flex items-center gap-2.5 opacity-70 border-b border-white/5 pb-2"><Icon className="w-4 h-4" /><span className="text-[10px] font-mono font-black uppercase tracking-[0.2em]">{label}</span></div>
       <div><h4 className="text-base font-black text-white mb-0.5 leading-tight tracking-tight">{title}</h4><p className="text-[11px] font-bold uppercase opacity-90 tracking-widest">{sub}</p></div>
       <p className="text-xs text-slate-400 font-mono leading-relaxed line-clamp-4">{content}</p>
    </div>
  )
}

function SourceBadge({ icon: Icon, label }) {
  return <div className="flex items-center gap-2.5 bg-white/5 border border-white/10 px-4 py-2 rounded-xl transition-all hover:bg-white/10"><Icon className="w-3.5 h-3.5 text-slate-500" /><span className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-tighter">{label}</span><div className="w-1.5 h-1.5 rounded-full bg-sc_green shadow-[0_0_10px_rgba(74,222,128,0.6)]" /></div>
}

function InfoTile({ icon: Icon, label, value, sub, color }) {
  const c = { cyan: 'text-sc_cyan border-sc_cyan/20 bg-sc_cyan/5', green: 'text-sc_green border-sc_green/20 bg-sc_green/5', yellow: 'text-sc_yellow border-sc_yellow/20 bg-sc_yellow/5', orange: 'text-sc_orange border-sc_orange/20 bg-sc_orange/5' }[color]
  return (
    <div className={`border p-7 rounded-3xl relative overflow-hidden transition-all hover:scale-[1.02] shadow-xl ${c}`}>
       <div className={`absolute -top-10 -right-10 w-24 h-24 blur-3xl opacity-10 ${c.replace('text', 'bg')}`} />
       <div className="flex items-center gap-3.5 mb-5"><div className="p-2.5 rounded-xl bg-white/10"><Icon className="w-4 h-4 shadow-sm" /></div><span className="text-[11px] font-mono text-slate-500 font-black uppercase tracking-[0.2em]">{label}</span></div>
       <div className="text-4xl font-black font-mono leading-none text-white tracking-tighter mb-2">{value}</div>
       <div className="text-[10px] font-mono text-slate-500 uppercase font-black tracking-widest">{sub}</div>
    </div>
  )
}

function SKUSelector({ value, onChange, skuList }) {
  return (
    <div className="bg-sc_card/80 border border-white/10 rounded-2xl px-5 py-2.5 text-xs font-mono text-white flex items-center gap-4 shadow-lg focus-within:border-sc_cyan/50 transition-all">
       <Package className="w-5 h-5 text-sc_cyan" />
       <select className="bg-transparent focus:outline-none font-black text-sm" value={value} onChange={e=>onChange(e.target.value)}>
         {skuList.map(s => <option key={s} value={s} className="bg-sc_card">{s}</option>)}
       </select>
    </div>
  )
}
