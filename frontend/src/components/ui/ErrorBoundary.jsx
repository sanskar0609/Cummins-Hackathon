import React from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Fatal UI Error Caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 w-full h-full min-h-[500px] flex flex-col items-center justify-center bg-transparent text-center p-6">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            className="max-w-md w-full bg-sc_card/80 backdrop-blur-2xl border border-sc_red/30 rounded-2xl p-8 shadow-2xl"
          >
            <div className="w-16 h-16 bg-sc_red/10 rounded-full flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(251,113,133,0.3)]">
              <AlertTriangle className="w-8 h-8 text-sc_red" />
            </div>
            
            <h1 className="text-2xl font-bold font-mono text-white mb-2 tracking-widest uppercase">
              System Fault
            </h1>
            
            <p className="text-sm font-mono text-slate-400 leading-relaxed mb-6">
              The intelligence interface encountered a fatal render exception and isolated the core to protect state stability.
            </p>
            
            <div className="bg-sc_elevated/50 border border-white/5 rounded-xl p-4 mb-8 text-left overflow-auto max-h-32 custom-scrollbar">
              <code className="text-[11px] font-mono text-sc_red/80 break-words">
                {this.state.error?.toString()}
              </code>
            </div>
            
            <button 
              onClick={() => window.location.reload()}
              className="w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 active:scale-95 text-white font-mono py-3 rounded-xl transition-all border border-white/10"
            >
              <RefreshCw className="w-4 h-4" />
              Reboot Interface
            </button>
          </motion.div>
        </div>
      )
    }

    return this.props.children
  }
}
