import React from 'react'

export function Badge({ children, variant = 'cyan', size = 'sm', className = '' }) {
  const colors = {
    cyan: 'bg-sc_cyan/10 text-sc_cyan border-sc_cyan/20',
    orange: 'bg-sc_orange/10 text-sc_orange border-sc_orange/20',
    green: 'bg-sc_green/10 text-sc_green border-sc_green/20',
    yellow: 'bg-sc_yellow/10 text-sc_yellow border-sc_yellow/20',
    purple: 'bg-sc_purple/10 text-sc_purple border-sc_purple/20',
    red: 'bg-sc_red/10 text-sc_red border-sc_red/20',
    gray: 'bg-slate-800/50 text-slate-300 border-white/5'
  }

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  }

  return (
    <span 
      className={`inline-flex items-center font-medium border rounded-full ${colors[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  )
}
