import React, { useState } from 'react';
import { 
  ShieldAlert, 
  RefreshCw, 
  LogOut, 
  Copy, 
  Check, 
  Mail, 
  Clock, 
  Sparkles,
  ShieldCheck,
  Building2,
  Lock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import confetti from 'canvas-confetti';

export default function PendingApprovalView() {
  const { currentUser, refreshApprovalStatus, logout, isCheckingApproval } = useAuth();
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const email = currentUser?.email || 'Your account';

  const handleCopy = () => {
    if (currentUser?.email) {
      navigator.clipboard.writeText(currentUser.email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      addToast('Email copied to clipboard. Send it to your admin.', 'info');
    }
  };

  const handleCheckStatus = async () => {
    setIsRefreshing(true);
    try {
      const res = await refreshApprovalStatus();
      if (res?.status === 'approved') {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 }
        });
        addToast('Access Granted! Welcome to GeM PDF Studio.', 'success');
      } else {
        addToast('Still pending approval. Please contact the administrator.', 'info');
      }
    } catch {
      addToast('Failed to check status. Ensure backend is running.', 'error');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4 sm:p-6">
      <div className="max-w-lg w-full bg-white/95 backdrop-blur-sm border border-brand-border rounded-3xl p-6 sm:p-9 shadow-warm-xl text-center space-y-7 relative overflow-hidden">
        
        {/* Subtle Top Amber Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-1 bg-amber-500/80 rounded-full" />

        {/* Icon & Status Pill */}
        <div className="space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200/80 text-amber-600 shadow-warm-xs">
            <Clock className="w-8 h-8 text-amber-600 animate-pulse" />
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100/70 border border-amber-300/80 text-amber-900 text-xs font-bold font-mono">
            <span className="w-2 h-2 rounded-full bg-amber-500 dot-ping" />
            <span>PENDING APPROVAL</span>
          </div>
        </div>

        {/* Main Headings */}
        <div className="space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-display">
            Access Approval Required
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed max-w-md mx-auto">
            Your account is authenticated via Firebase, but this extraction suite is restricted to 
            <strong className="text-slate-800 font-semibold"> whitelisted clients only</strong>.
          </p>
        </div>

        {/* Account Details Box */}
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 text-left space-y-3 text-xs">
          <div className="flex items-center justify-between text-slate-500 font-mono text-[11px]">
            <span>Registered Email</span>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" /> Firebase Verified
            </span>
          </div>

          <div className="flex items-center justify-between gap-2 p-2.5 bg-white rounded-xl border border-slate-200 font-mono text-slate-900">
            <div className="flex items-center gap-2 truncate">
              <Mail className="w-4 h-4 text-slate-400 shrink-0" />
              <span className="truncate font-semibold">{email}</span>
            </div>
            <button
              type="button"
              onClick={handleCopy}
              title="Copy email to send to admin"
              className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors shrink-0"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <p className="text-[11px] text-slate-500 leading-relaxed font-sans">
            Please ask your system administrator or team lead to approve <strong className="text-slate-700">{email}</strong> in the backend whitelist.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3 pt-2">
          <button
            type="button"
            onClick={handleCheckStatus}
            disabled={isRefreshing || isCheckingApproval}
            className="w-full btn-yellow py-3 px-4 font-bold text-sm text-amber-950 flex items-center justify-center gap-2 cursor-pointer shadow-warm-sm"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing || isCheckingApproval ? 'animate-spin' : ''}`} />
            <span>{isRefreshing || isCheckingApproval ? 'Checking Approval...' : 'Check Approval Status'}</span>
          </button>

          <button
            type="button"
            onClick={logout}
            className="w-full btn-white py-2.5 px-4 text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center justify-center gap-2 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out / Switch Account</span>
          </button>
        </div>

        {/* Subtle Footer Note */}
        <div className="pt-2 text-[11px] text-slate-400 font-mono flex items-center justify-center gap-1.5">
          <Lock className="w-3 h-3 text-slate-400" />
          <span>Backend Zero-Trust Whitelist Protected</span>
        </div>

      </div>
    </div>
  );
}
