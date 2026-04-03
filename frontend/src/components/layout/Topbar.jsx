import React, { useState, useEffect } from 'react'
import { Bell, Search, Settings } from 'lucide-react'
import { StatusPill } from '../ui/StatusPill'

export function Topbar() {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const formattedTime = time.toISOString().replace('T', ' ').split('.')[0] + ' UTC'

  return (
    <div className="h-16 border-b border-white/5 bg-sc_bg/80 backdrop-blur-xl flex items-center justify-between px-8 sticky top-0 z-40">
      
      {/* Search Bar - Aesthetic mock for $50k feeling */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white/5 border border-white/10 rounded-full w-96 text-slate-400 focus-within:border-sc_cyan/50 focus-within:bg-sc_cyan/5 transition-all duration-300">
        <Search className="w-4 h-4" />
        <input 
          type="text" 
          placeholder="Search SKUs, Routes, Suppliers..." 
          className="bg-transparent border-none outline-none text-sm w-full placeholder:text-slate-500 text-slate-200"
        />
        <div className="text-[10px] font-mono font-bold bg-white/10 px-2 py-0.5 rounded text-slate-400">⌘K</div>
      </div>

      <div className="flex items-center gap-8">
        {/* Live Clock */}
        <div className="font-mono text-sc_cyan text-sm tracking-widest hidden lg:block drop-shadow-[0_0_8px_rgba(0,212,255,0.5)]">
          {formattedTime}
        </div>

        {/* Global Connection Status */}
        <StatusPill status="HEALTHY" animated={true} />

        <div className="h-6 w-px bg-white/10 mx-2"></div>

        {/* Action Icons */}
        <div className="flex items-center gap-4 text-slate-400">
          <button className="hover:text-sc_orange transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sc_orange opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sc_orange"></span>
            </span>
          </button>
          <button className="hover:text-sc_cyan transition-colors">
            <Settings className="w-5 h-5" />
          </button>
          
          {/* User Avatar */}
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sc_cyan to-sc_purple p-[1px] cursor-pointer ml-2 shadow-[0_0_15px_rgba(192,132,252,0.3)] hover:shadow-[0_0_20px_rgba(0,212,255,0.5)] transition-shadow">
            <div className="w-full h-full bg-sc_bg rounded-full flex items-center justify-center">
              <span className="text-xs font-bold text-white">OP</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
