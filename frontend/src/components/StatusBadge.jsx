import React from 'react';
import { Activity, CheckCircle2, AlertCircle } from 'lucide-react';

export default function StatusBadge({ isConnected, isChecking, appName }) {
  if (isChecking) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-warm-200/60 text-charcoal-700 border border-warm-300/40">
        <Activity className="w-3.5 h-3.5 animate-spin text-charcoal-500" />
        <span>Connecting to backend...</span>
      </div>
    );
  }

  if (isConnected) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200/60 shadow-sm">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span className="font-semibold">{appName || 'MAYA'} Core</span>
        <span className="text-emerald-600/70">| Connected (port 8000)</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200/60">
      <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
      <span>Backend Offline (run backend server)</span>
    </div>
  );
}
