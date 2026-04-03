import React from 'react'
import { Card } from './Card'

export function MetricTile({ title, value, icon: Icon, trend, trendLabel, color = 'cyan', delay }) {
  const textColor = {
    cyan: 'text-sc_cyan',
    orange: 'text-sc_orange',
    green: 'text-sc_green',
    purple: 'text-sc_purple',
    yellow: 'text-sc_yellow',
    red: 'text-sc_red'
  }[color]

  return (
    <Card hoverGlow delay={delay} className="flex flex-col gap-2">
      <div className="flex justify-between items-center text-slate-400">
        <h3 className="font-mono text-xs uppercase tracking-wider">{title}</h3>
        {Icon && <Icon className={`w-4 h-4 ${textColor} opacity-80`} />}
      </div>
      <div className="flex items-end gap-3">
        <div className={`text-4xl font-semibold tracking-tight ${textColor} drop-shadow-[0_0_15px_currentColor]`}>
          {value}
        </div>
        {trend && (
          <div className={`text-sm mb-1 ${trend > 0 ? 'text-sc_green' : trend < 0 ? 'text-sc_red' : 'text-slate-400'}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </div>
        )}
      </div>
      {trendLabel && <div className="text-xs text-slate-500">{trendLabel}</div>}
    </Card>
  )
}
