import React from 'react'
import { ServerCrash } from 'lucide-react'
import { Card } from './Card'

export function EmptyState({ title = "Data Unavailable", message = "The OSINT feeds have not generated output for this module.", icon: Icon = ServerCrash }) {
  return (
    <Card className="flex flex-col items-center justify-center p-12 text-center border-dashed border-white/10 bg-transparent">
      <div className="p-4 bg-white/5 rounded-full mb-4">
        <Icon className="w-10 h-10 text-slate-500" />
      </div>
      <h3 className="text-xl font-medium text-slate-300 mb-2 font-mono tracking-tight">{title}</h3>
      <p className="text-slate-500 max-w-sm mx-auto">{message}</p>
    </Card>
  )
}
