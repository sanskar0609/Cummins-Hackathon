import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Activity, LayoutDashboard, Route, Map, TrendingUp, FlaskConical, Bot, Bell } from 'lucide-react'
import { motion } from 'framer-motion'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/suppliers', label: 'Suppliers', icon: Map },
  { path: '/demand', label: 'Demand', icon: TrendingUp },
  { path: '/simulator', label: 'Simulator', icon: FlaskConical },
  { path: '/copilot', label: 'Co-Pilot', icon: Bot },
  { path: '/alerts', label: 'Alerts & POs', icon: Bell }
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="w-64 h-full bg-sc_card/80 backdrop-blur-xl border-r border-white/5 flex flex-col p-4 shrink-0 relative z-50">
      <div className="flex items-center gap-3 px-3 py-6 mb-4">
        <Activity className="w-8 h-8 text-sc_cyan" />
        <h1 className="text-xl font-mono font-bold tracking-tight text-white leading-tight">
          SUPPLY<span className="text-sc_cyan">OS</span>
        </h1>
      </div>

      <nav className="flex-1 flex flex-col gap-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const Icon = item.icon
          
          return (
            <Link key={item.path} to={item.path} className="relative group">
              {isActive && (
                <motion.div 
                  layoutId="sidebar-active-pill"
                  className="absolute inset-0 bg-sc_cyan/10 border border-sc_cyan/20 rounded-xl"
                  initial={false}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              <div className={`relative flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                ${isActive ? 'text-sc_cyan shadow-[0_0_10px_rgba(0,212,255,0.2)]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}>
                <Icon className={`w-5 h-5 ${isActive ? 'drop-shadow-[0_0_8px_currentColor]' : ''}`} />
                <span className="font-medium tracking-wide">{item.label}</span>
              </div>
            </Link>
          )
        })}
      </nav>
      
      <div className="mt-auto pt-6 border-t border-white/5">
        <div className="px-4 py-3 rounded-xl bg-gradient-to-br from-sc_purple/20 to-transparent border border-sc_purple/20 flex flex-col gap-1">
          <span className="text-xs font-mono text-sc_purple uppercase tracking-widest">Enterprise API</span>
          <span className="text-sm font-semibold text-white">Status: Nominal</span>
        </div>
      </div>
    </div>
  )
}
