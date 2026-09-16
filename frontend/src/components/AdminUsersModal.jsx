import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserCheck, 
  UserX, 
  Clock, 
  ShieldAlert, 
  ShieldCheck, 
  Plus, 
  X, 
  RefreshCw, 
  Mail, 
  CheckCircle2, 
  AlertCircle,
  Crown
} from 'lucide-react';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function AdminUsersModal({ isOpen, onClose }) {
  const { addToast } = useToast();
  const [data, setData] = useState({ admin_emails: [], whitelist: [], pending_requests: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('client');
  const [actionLoading, setActionLoading] = useState(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await api.getAdminUsers();
      if (res) setData(res);
    } catch (err) {
      addToast(err.message || 'Failed to load user whitelist', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleApprove = async (email, role = 'client') => {
    setActionLoading(email);
    try {
      await api.approveUser(email, role);
      addToast(`Approved ${email} as ${role}`, 'success');
      await loadData();
    } catch (err) {
      addToast(err.message || 'Failed to approve user', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevoke = async (email) => {
    if (!window.confirm(`Revoke access for ${email}?`)) return;
    setActionLoading(email);
    try {
      await api.revokeUser(email);
      addToast(`Revoked access for ${email}`, 'info');
      await loadData();
    } catch (err) {
      addToast(err.message || 'Failed to revoke user', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDirectAdd = async (e) => {
    e.preventDefault();
    if (!newEmail.trim()) return;
    setActionLoading('add');
    try {
      await api.approveUser(newEmail.trim(), newRole);
      addToast(`${newEmail.trim()} whitelisted successfully`, 'success');
      setNewEmail('');
      await loadData();
    } catch (err) {
      addToast(err.message || 'Failed to add user to whitelist', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-3xl w-full border border-brand-border shadow-warm-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-display flex items-center gap-2">
                <span>Client Whitelist & Access Manager</span>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 font-mono">
                  Admin Only
                </span>
              </h3>
              <p className="text-xs text-slate-500">
                Only whitelisted clients can extract PDFs, view records, and download reports.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          
          {/* Global PDF Scans Summary Banner */}
          <div className="p-4 bg-gradient-to-r from-amber-500/15 via-amber-400/10 to-amber-200/20 rounded-2xl border border-amber-300/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-amber-900 font-mono tracking-wider">
                System PDF Analytics (All Accounts)
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-extrabold text-amber-950 font-display">
                  {data.global_stats?.total_pdfs_scanned || 0}
                </span>
                <span className="text-xs font-bold text-amber-800 font-mono">Total PDFs Scanned</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="px-3 py-1.5 rounded-xl bg-white/90 border border-amber-200/80 text-xs text-slate-800 font-mono font-bold shadow-2xs">
                <span className="text-emerald-700">{data.global_stats?.total_pdfs_extracted || 0}</span> Extracted
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-white/90 border border-amber-200/80 text-xs text-slate-800 font-mono font-bold shadow-2xs">
                <span className="text-amber-800">{data.global_stats?.total_whitelisted_users || data.whitelist?.length || 0}</span> Clients
              </div>
            </div>
          </div>

          {/* Quick Whitelist Add Form */}
          <form onSubmit={handleDirectAdd} className="p-4 bg-amber-50/60 rounded-2xl border border-amber-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-950 font-display flex items-center gap-1.5">
                <Plus className="w-4 h-4 text-amber-600" /> Direct Whitelist Invitation
              </span>
              <span className="text-[11px] text-amber-800 font-medium">Whitelist a client before they register</span>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="email"
                required
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="client@clientcompany.com"
                className="flex-1 px-3.5 py-2 bg-white border border-amber-300 focus:border-amber-500 rounded-xl text-xs text-slate-900 placeholder-slate-400 font-mono"
              />
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-slate-800 font-semibold"
              >
                <option value="client">Role: Client</option>
                <option value="admin">Role: Admin</option>
              </select>
              <button
                type="submit"
                disabled={actionLoading === 'add'}
                className="btn-yellow text-xs px-4 py-2 font-bold whitespace-nowrap cursor-pointer disabled:opacity-50"
              >
                {actionLoading === 'add' ? 'Adding...' : 'Add to Whitelist'}
              </button>
            </div>
          </form>

          {/* Pending Approval Requests Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                  Pending Client Requests ({data.pending_requests?.length || 0})
                </h4>
              </div>
              <button
                onClick={loadData}
                disabled={isLoading}
                className="text-[11px] text-amber-800 font-semibold hover:underline flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} /> Refresh List
              </button>
            </div>

            {data.pending_requests?.length === 0 ? (
              <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50 text-center text-xs text-slate-400 font-mono">
                No pending approval requests.
              </div>
            ) : (
              <div className="space-y-2">
                {data.pending_requests.map((p) => (
                  <div 
                    key={p.email} 
                    className="p-3.5 bg-amber-50/50 rounded-xl border border-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-mono font-bold text-slate-900 flex items-center gap-1.5">
                        <Mail className="w-3.5 h-3.5 text-amber-600" />
                        <span>{p.email}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Requested: {new Date(p.requested_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => handleApprove(p.email, 'client')}
                        disabled={actionLoading === p.email}
                        className="flex-1 sm:flex-none btn-yellow text-xs px-3 py-1.5 font-bold cursor-pointer"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        <span>Approve Client</span>
                      </button>
                      <button
                        onClick={() => handleApprove(p.email, 'admin')}
                        disabled={actionLoading === p.email}
                        className="flex-1 sm:flex-none btn-white text-xs px-2.5 py-1.5 font-semibold text-slate-700 cursor-pointer"
                      >
                        <Crown className="w-3.5 h-3.5 text-amber-600" />
                        <span>Make Admin</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Whitelisted Active Users Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-emerald-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                Active Whitelisted Clients ({data.whitelist?.length || 0})
              </h4>
            </div>

            {data.whitelist?.length === 0 ? (
              <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50 text-center text-xs text-slate-400 font-mono">
                No whitelisted clients yet. Add one using the form above!
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-slate-200/80 rounded-2xl overflow-hidden bg-white">
                {data.whitelist.map((w) => (
                  <div key={w.email} className="p-3.5 flex items-center justify-between text-xs hover:bg-slate-50/60 transition-colors">
                    <div className="space-y-1">
                      <div className="font-mono font-bold text-slate-900 flex items-center gap-2">
                        <span>{w.email}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          w.role === 'admin' ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        }`}>
                          {w.role}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                        <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-bold">
                          {w.total_pdfs_scanned || 0} PDFs scanned
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-900 border border-emerald-200 font-bold">
                          {w.total_pdfs_extracted || 0} extracted
                        </span>
                        <span>
                          • Last active: {w.last_active_at ? new Date(w.last_active_at).toLocaleDateString() : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleRevoke(w.email)}
                      disabled={actionLoading === w.email}
                      className="text-xs text-rose-600 hover:text-rose-700 font-semibold px-2.5 py-1 rounded-lg hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-all cursor-pointer"
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Superadmin Emails Note */}
          {data.admin_emails?.length > 0 && (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-1 font-mono">
              <div className="font-bold text-slate-800 text-[11px] flex items-center gap-1.5">
                <Crown className="w-3.5 h-3.5 text-amber-600" /> Permanent Superadmins:
              </div>
              <div className="text-[11px] text-slate-500">
                {data.admin_emails.join(', ')}
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-end">
          <button
            onClick={onClose}
            className="btn-white text-xs px-4 py-1.5 font-semibold text-slate-700 cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
