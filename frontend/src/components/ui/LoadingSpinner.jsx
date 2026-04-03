import React from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ size = 'md', text = 'Stabilizing Core Metrics...' }) {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  }[size]

  return (
    <div className="flex flex-col items-center justify-center p-8 text-sc_cyan">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      >
        <Loader2 className={`${sizeClass} opacity-80 drop-shadow-[0_0_15px_rgba(0,212,255,0.8)]`} />
      </motion.div>
      {text && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="mt-4 text-sm font-mono tracking-widest uppercase text-sc_cyan/80"
        >
          {text}
        </motion.p>
      )}
    </div>
  )
}
