import React from 'react';
import { NavLink } from 'react-router-dom';
import { Sparkles, Bell, Home, MessageSquare } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function Header({ isConnected, isChecking, appName }) {
  return (
    <header className="w-full border-b border-warm-200/80 bg-warm-50/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand identity */}
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-crimson-800 to-crimson-950 flex items-center justify-center text-white shadow-crimson-glow font-bold text-base tracking-wider">
              M
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-charcoal-900 tracking-tight">MAYA</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-crimson-100/70 text-crimson-900">
                  GGSIPU
                </span>
              </div>
            </div>
          </NavLink>

          {/* Navigation links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-crimson-50 text-crimson-900 font-bold'
                    : 'text-charcoal-600 hover:text-charcoal-900 hover:bg-warm-100'
                }`
              }
            >
              <Home className="w-3.5 h-3.5" />
              <span>Home</span>
            </NavLink>

            <NavLink
              to="/chat"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-crimson-50 text-crimson-900 font-bold'
                    : 'text-charcoal-600 hover:text-charcoal-900 hover:bg-warm-100'
                }`
              }
            >
              <Sparkles className="w-3.5 h-3.5 text-crimson-700" />
              <span>Ask MAYA</span>
            </NavLink>

            <NavLink
              to="/notices"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-crimson-50 text-crimson-900 font-bold'
                    : 'text-charcoal-600 hover:text-charcoal-900 hover:bg-warm-100'
                }`
              }
            >
              <Bell className="w-3.5 h-3.5" />
              <span>Notice Center</span>
            </NavLink>

            <NavLink
              to="/about"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-crimson-50 text-crimson-900 font-bold'
                    : 'text-charcoal-600 hover:text-charcoal-900 hover:bg-warm-100'
                }`
              }
            >
              <span>About</span>
            </NavLink>
          </nav>
        </div>

        {/* Live system state indicator */}
        <div className="flex items-center gap-3">
          <StatusBadge isConnected={isConnected} isChecking={isChecking} appName={appName} />
        </div>
      </div>
    </header>
  );
}
