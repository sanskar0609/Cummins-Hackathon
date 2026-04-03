import { motion } from 'framer-motion'
import React from 'react'

export function Card({ children, className = '', noPadding = false, delay = 0, hoverGlow = false, ...props }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay, ease: [0.25, 0.4, 0.25, 1] }}
      className={`glass-panel border-white/5 bg-sc_card/60 backdrop-blur-xl ${noPadding ? '' : 'p-6'} 
        ${hoverGlow ? 'hover:border-sc_cyan/30 transition-colors duration-500' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}
