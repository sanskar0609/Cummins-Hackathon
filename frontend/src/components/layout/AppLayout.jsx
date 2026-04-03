import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { ErrorBoundary } from '../ui/ErrorBoundary'

export function AppLayout() {
  return (
    <div className="flex h-screen w-screen bg-sc_bg overflow-hidden text-slate-300">
      <Sidebar />
      <div className="flex-1 flex flex-col relative w-full overflow-hidden">
        {/* Deep ambient background glows */}
        <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-sc_cyan/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-sc_purple/10 rounded-full blur-[150px] pointer-events-none" />

        <Topbar />

        <main className="flex-1 overflow-x-hidden overflow-y-auto w-full relative z-10 p-4 scroll-smooth">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
