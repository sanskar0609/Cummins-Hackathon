import React, { useState, useEffect, useRef, useCallback, useLayoutEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, User, Send, Copy, AlertCircle, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

// ─── UTILS ────────────────────────────────────────────────────────────────
const WS_BASE_URL = import.meta.env.VITE_WS_URL

function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'sess-' + Math.random().toString(36).substring(2, 10)
}

function getTimeString() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

// ─── PROMPT CHIPS ────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What is my biggest risk today?",
  "Simulate Suez closure for 7 days",
  "Draft CFO email for SKU-007 shortage",
  "Which supplier is most at risk?"
]

// ─── TYPEWRITER HOOK ─────────────────────────────────────────────────────
function useTypewriter(text = '', isActive, speedMs = 18) {
  const [displayed, setDisplayed] = useState('')
  const [isDone, setIsDone] = useState(false)
  
  useEffect(() => {
    const safeText = text || ''
    if (!isActive) {
      setDisplayed(safeText)
      setIsDone(true)
      return
    }
    setDisplayed('')
    setIsDone(false)
    let curIndex = 0
    
    const interval = setInterval(() => {
      curIndex++
      setDisplayed(safeText.slice(0, curIndex))
      if (curIndex >= safeText.length) {
        clearInterval(interval)
        setIsDone(true)
      }
    }, speedMs)
    
    return () => clearInterval(interval)
  }, [text, isActive, speedMs])
  
  return { displayed, isDone }
}

// ─── MESSAGE BUBBLE ──────────────────────────────────────────────────────
function MessageBubble({ msg, isLatestAI }) {
  const isUser = msg.role === 'user'
  const { displayed, isDone } = useTypewriter(msg.content, isLatestAI && !isUser)
  
  const textBody = isLatestAI && !isUser ? displayed : msg.content

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.content)
      toast.success('Copied!', { icon: '📋', style: { background: '#0b0f17', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' } })
    } catch {
      toast.error('Failed to copy')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 15, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      <div className={`flex items-center justify-center shrink-0 w-8 h-8 rounded-lg border ${
        isUser ? 'bg-sc_cyan/20 border-sc_cyan/30 text-sc_cyan' : 'bg-sc_purple/20 border-sc_purple/30 text-sc_purple'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`relative px-4 py-3 text-sm leading-relaxed rounded-2xl whitespace-pre-wrap font-mono ${
          isUser 
            ? 'bg-sc_cyan/10 border border-sc_cyan/20 text-white rounded-br-sm'
            : 'bg-[#0b0f17] border border-white/10 text-slate-300 rounded-bl-sm'
        }`}>
          {textBody}
          {!isUser && !isDone && (
            <motion.span 
              animate={{ opacity: [1, 0] }}
              transition={{ repeat: Infinity, duration: 0.6 }}
              className="inline-block w-1.5 h-3.5 bg-sc_purple ml-1 align-middle"
            />
          )}
        </div>
        
        <div className={`flex items-center gap-2 px-1 text-[10px] text-slate-600 font-mono ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <span>{msg.timestamp}</span>
          {!isUser && (
            <button onClick={handleCopy} className="hover:text-white transition-colors p-1" title="Copy to clipboard">
              <Copy className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────
export default function Copilot() {
  const [sessionId] = useState(() => generateSessionId())
  
  const [messages, setMessages] = useState([])
  const [inputVal, setInputVal] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [latestAIId, setLatestAIId] = useState(null)
  
  const [wsState, setWsState] = useState('connecting') // connected, retrying, disconnected
  const retries = useRef(0)
  const wsRef = useRef(null)
  const scrollContainerRef = useRef(null)
  const connectTimer = useRef(null)

  // Auto-scroll fix: use scrollTo on the container to prevent scrolling the whole document body
  useLayoutEffect(() => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, isTyping])

  // WebSocket connect
  const connectWS = useCallback(() => {
    // Add 500ms delay to ensure UI is ready before connecting
    connectTimer.current = setTimeout(() => {
      if (retries.current >= 5) {
        setWsState('disconnected')
        return
      }

      try {
        const url = `${WS_BASE_URL}/copilot/chat/${sessionId}`.replace('http', 'ws')
        const ws = new WebSocket(url)

        ws.onopen = () => {
          setWsState('connected')
          retries.current = 0
        }

        ws.onmessage = (event) => {
          setIsTyping(false)
          const msgId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString()
          setLatestAIId(msgId)
          setMessages(prev => [...prev, {
            id: msgId,
            role: 'ai',
            content: event.data,
            timestamp: getTimeString()
          }])
        }

        ws.onclose = (event) => {
          setIsTyping(false)
          wsRef.current = null
          if (event.code !== 1000 && retries.current < 5) {
            retries.current += 1
            setWsState('retrying')
            toast('Co-Pilot disconnected — reconnecting...', { icon: '🔄', id: 'ws-reconnect' })
            connectTimer.current = setTimeout(connectWS, 3000)
          } else if (retries.current >= 5) {
            setWsState('disconnected')
          }
        }

        ws.onerror = () => {
          setWsState('disconnected')
          retries.current = 999 // Stop retrying immediately if it's a hard error (like Gemini quota)
          toast('Co-Pilot offline — Gemini API quota reached. Try again tomorrow.', { 
            icon: '⚠️', 
            duration: 5000,
            id: 'ws-error',
            style: { background: 'rgba(234, 88, 12, 0.15)', color: '#fb923c', border: '1px solid rgba(234, 88, 12, 0.4)' }
          })
        }

        wsRef.current = ws
      } catch (e) {
        setWsState('disconnected')
      }
    }, 500)
  }, [sessionId])

  useEffect(() => {
    connectWS()
    return () => {
      clearTimeout(connectTimer.current)
      if (wsRef.current) {
        wsRef.current.close(1000)
      }
    }
  }, [connectWS])

  const handleSend = () => {
    const text = inputVal.trim()
    if (!text || wsState !== 'connected' || isTyping) return
    
    setInputVal('')
    setIsTyping(true)
    
    setMessages(prev => [...prev, {
      id: crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: getTimeString()
    }])

    wsRef.current.send(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-sc_bg rounded-2xl border border-white/10 relative shadow-2xl">
      
      {/* Background Particles */}
      <div className="absolute inset-0 pointer-events-none opacity-20" style={{ background: 'radial-gradient(circle at center, rgba(168,85,247,0.15) 0%, transparent 60%)' }} />

      {/* ── HEADER ── */}
      <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/5 bg-gradient-to-r from-[rgba(168,85,247,0.1)] to-transparent backdrop-blur-md relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sc_purple/20 border border-sc_purple/40 flex items-center justify-center shadow-[0_0_15px_rgba(168,85,247,0.3)]">
            <Bot className="w-5 h-5 text-sc_purple" />
          </div>
          <div>
            <h1 className="text-white font-mono font-bold">Supply Chain Co-Pilot</h1>
            <p className="text-[10px] font-mono text-slate-400">Powered by Gemini 2.5 Flash</p>
          </div>
        </div>
        
        {/* Status Indicator */}
        <div className="flex items-center gap-2 bg-black/20 px-3 py-1.5 rounded-full border border-white/5">
          {wsState === 'connected' && (
            <>
              <span className="w-2 h-2 rounded-full bg-sc_green shadow-[0_0_8px_#4ade80] animate-pulse" />
              <span className="text-[10px] font-mono font-bold text-sc_green">Connected</span>
            </>
          )}
          {wsState === 'retrying' && (
            <>
              <span className="w-2 h-2 rounded-full bg-sc_yellow shadow-[0_0_8px_#ffd60a]" />
              <span className="text-[10px] font-mono font-bold text-sc_yellow">Reconnecting...</span>
            </>
          )}
          {wsState === 'disconnected' && (
            <>
              <span className="w-2 h-2 rounded-full bg-sc_red shadow-[0_0_8px_#fb7185]" />
              <span className="text-[10px] font-mono font-bold text-sc_red">Disconnected</span>
            </>
          )}
        </div>
      </header>

      {/* ── MESSAGES DIV ── */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto px-6 py-6 space-y-6 relative z-10" 
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.1) transparent' }}
      >
        
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center gap-6">
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="w-16 h-16 rounded-2xl bg-sc_purple/10 border border-sc_purple/30 flex items-center justify-center shadow-[0_0_40px_rgba(168,85,247,0.2)]"
            >
              <Bot className="w-8 h-8 text-sc_purple" />
            </motion.div>
            
            <div className="text-center space-y-1">
              <h2 className="text-xl font-mono font-bold text-white">Supply Chain Co-Pilot</h2>
              <p className="text-sm font-mono text-slate-500">Powered by Gemini 2.5 Flash</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 max-w-xl w-full">
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  onClick={() => {
                    setInputVal(s)
                    setTimeout(() => handleSend(), 50)
                  }}
                  className="bg-sc_elevated/50 hover:bg-sc_purple/10 border border-white/5 hover:border-sc_purple/40 text-left px-4 py-3 rounded-xl text-xs font-mono text-slate-300 hover:text-white transition-all duration-200"
                >
                  {s}
                </motion.button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} isLatestAI={msg.id === latestAIId} />
        ))}
        
        {isTyping && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-sc_purple">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span className="text-xs font-mono">Agent reasoning...</span>
          </motion.div>
        )}
      </div>

      {wsState === 'disconnected' && (
        <div className="px-6 py-2 bg-sc_red/10 border-t border-b border-sc_red/20 text-center relative z-10">
          <p className="text-xs font-mono font-bold text-sc_red flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Backend offline. Please restart the simulation server.
          </p>
        </div>
      )}

      {/* ── INPUT ── */}
      <div className="flex-shrink-0 p-4 border-t border-white/5 bg-[rgba(6,8,13,0.8)] backdrop-blur-md relative z-10">
        <div className="flex items-end gap-3 bg-[rgba(16,21,32,0.9)] border border-white/10 focus-within:border-sc_purple/50 focus-within:shadow-[0_0_15px_rgba(168,85,247,0.15)] rounded-2xl p-2 transition-all duration-300">
          <textarea
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={wsState !== 'connected' || isTyping}
            placeholder={wsState === 'connected' ? "Ask about supply chain risk..." : "Connecting..."}
            className="flex-1 max-h-[100px] bg-transparent border-none outline-none resize-none text-sm font-mono text-white placeholder-slate-600 px-3 py-2 disabled:opacity-50"
            rows={Math.min(4, Math.max(1, inputVal.split('\n').length))}
          />
          <button
            onClick={handleSend}
            disabled={!inputVal.trim() || wsState !== 'connected' || isTyping}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-sc_purple text-white flex items-center justify-center hover:bg-purple-600 disabled:opacity-30 disabled:hover:bg-sc_purple transition-all mb-0.5 mr-0.5 shadow-[0_0_15px_rgba(168,85,247,0.4)] disabled:shadow-none"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-[10px] font-mono text-slate-500 mt-3 select-none">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
      
    </div>
  )
}
