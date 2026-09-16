import React, { useState } from 'react';
import { ShieldCheck, Copy, Check, X, Key, Calendar, User, Clock, Terminal } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function JwtTokenModal({ isOpen, onClose }) {
  const { jwtToken, tokenClaims, currentUser, getFreshToken } = useAuth();
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  if (!isOpen || !jwtToken) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(jwtToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    addToast('JWT ID Token copied to clipboard', 'success');
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await getFreshToken();
      addToast('JWT ID token refreshed with Firebase', 'info');
    } catch {
      addToast('Failed to refresh token', 'error');
    } finally {
      setIsRefreshing(false);
    }
  };

  const expDate = tokenClaims?.exp ? new Date(tokenClaims.exp * 1000).toLocaleTimeString() : 'N/A';
  const authTime = tokenClaims?.auth_time ? new Date(tokenClaims.auth_time * 1000).toLocaleTimeString() : 'N/A';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-2xl w-full border border-brand-border shadow-warm-xl overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 font-display">Firebase JWT Session Inspector</h3>
              <p className="text-[11px] text-slate-500 font-mono">RS256 Signed JSON Web Token</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          
          {/* Claims Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="text-[10px] text-slate-400 uppercase font-mono font-semibold flex items-center gap-1 mb-1">
                <User className="w-3 h-3 text-slate-500" /> User UID
              </div>
              <div className="font-mono text-[11px] text-slate-800 font-medium truncate" title={currentUser?.uid}>
                {currentUser?.uid?.slice(0, 10)}...
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="text-[10px] text-slate-400 uppercase font-mono font-semibold flex items-center gap-1 mb-1">
                <Clock className="w-3 h-3 text-slate-500" /> Issued At
              </div>
              <div className="font-mono text-[11px] text-slate-800 font-medium truncate">
                {authTime}
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="text-[10px] text-slate-400 uppercase font-mono font-semibold flex items-center gap-1 mb-1">
                <Calendar className="w-3 h-3 text-slate-500" /> Expires At
              </div>
              <div className="font-mono text-[11px] text-slate-800 font-medium truncate">
                {expDate}
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="text-[10px] text-slate-400 uppercase font-mono font-semibold flex items-center gap-1 mb-1">
                <Key className="w-3 h-3 text-slate-500" /> Auth Provider
              </div>
              <div className="font-mono text-[11px] text-slate-800 font-medium capitalize truncate">
                {tokenClaims?.firebase?.sign_in_provider || 'password'}
              </div>
            </div>
          </div>

          {/* Raw Token Box */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 font-mono flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-amber-600" /> Raw ID Token (Bearer Token)
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className="text-[11px] font-semibold text-amber-700 hover:text-amber-800 underline"
                >
                  {isRefreshing ? 'Refreshing...' : 'Force Refresh'}
                </button>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-900 hover:bg-slate-800 text-white transition-all shadow-2xs"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy JWT'}
                </button>
              </div>
            </div>

            <div className="p-3.5 bg-slate-900 text-slate-200 rounded-xl font-mono text-[10.5px] leading-relaxed break-all border border-slate-800 max-h-36 overflow-y-auto selection:bg-amber-500 selection:text-slate-900">
              {jwtToken}
            </div>
          </div>

          {/* FastAPI backend verify snippet */}
          <div className="p-3.5 bg-amber-50/80 rounded-xl border border-amber-200 text-xs text-amber-950 space-y-1.5">
            <p className="font-bold text-[11px] text-amber-900 flex items-center gap-1.5">
              <span>💡 How Backend Receives This Token:</span>
            </p>
            <p className="text-[11px] text-amber-800 font-mono">
              Headers: <span className="font-bold text-amber-950">Authorization: Bearer &lt;token&gt;</span>
            </p>
            <p className="text-[10.5px] text-amber-800 leading-relaxed font-sans">
              Every request from the React frontend now automatically attaches this header to all FastAPI endpoints!
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end">
          <button
            onClick={onClose}
            className="btn-white text-xs px-4 py-1.5"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
