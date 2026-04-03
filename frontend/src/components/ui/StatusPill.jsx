import React from 'react'

export function StatusPill({ status, animated = false }) {
  const getStyle = () => {
    switch (status?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return { bg: 'bg-sc_red', text: 'text-sc_red', glow: 'shadow-[0_0_10px_rgba(251,113,133,0.5)]' }
      case 'WARNING':
      case 'MEDIUM':
        return { bg: 'bg-sc_yellow', text: 'text-sc_yellow', glow: 'shadow-[0_0_10px_rgba(255,214,10,0.5)]' }
      case 'HEALTHY':
      case 'LOW':
      case 'NORMAL':
        return { bg: 'bg-sc_green', text: 'text-sc_green', glow: 'shadow-[0_0_10px_rgba(74,222,128,0.5)]' }
      case 'AI':
      case 'ACTIVE':
        return { bg: 'bg-sc_purple', text: 'text-sc_purple', glow: 'shadow-[0_0_10px_rgba(192,132,252,0.5)]' }
      default:
        return { bg: 'bg-sc_cyan', text: 'text-sc_cyan', glow: 'shadow-[0_0_10px_rgba(0,212,255,0.5)]' }
    }
  }

  const style = getStyle()

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex h-2.5 w-2.5">
        {animated && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${style.bg}`}></span>
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${style.bg} ${style.glow}`}></span>
      </div>
      <span className={`text-xs font-mono uppercase tracking-wider font-semibold ${style.text}`}>
        {status}
      </span>
    </div>
  )
}
