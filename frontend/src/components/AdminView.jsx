import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserCheck, 
  UserX, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  Plus, 
  Search, 
  RefreshCw, 
  Mail, 
  Crown, 
  CheckCircle2, 
  AlertCircle, 
  Trash2, 
  Copy, 
  Check,
  UserPlus,
  Lock,
  Sparkles,
  ArrowRight,
  Filter,
  FileSpreadsheet,
  FileText,
  Cpu,
  Activity,
  IndianRupee,
  Layers,
  FolderSearch
} from 'lucide-react';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { formatNumber, formatCurrency } from '../utils/formatters';
import confetti from 'canvas-confetti';

export default function AdminView() {
  const { addToast } = useToast();
  const { currentUser } = useAuth();

  const [data, setData] = useState({ 
    admin_emails: [], 
    whitelist: [], 
    pending_requests: [],
    global_stats: {},
    activity_log: [],
    user_stats: {}
  });
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all'); // 'all' | 'client' | 'admin'

  // Add Form State
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('client');
  const [isSubmittingAdd, setIsSubmittingAdd] = useState(false);

  // Action Loading State
  const [actionLoading, setActionLoading] = useState(null);
  const [copiedEmail, setCopiedEmail] = useState(null);

  // Fetch Whitelist & Global Stats Data from Backend
  const loadData = async () => {
    setIsLoading(true);
    try {
      const res = await api.getAdminUsers();
      if (res) setData(res);
    } catch (err) {
      addToast(err.message || 'Failed to load user whitelist & stats', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCopy = (email) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
    addToast(`Copied ${email}`, 'info', 1500);
  };

  // 1-Click Approval
  const handleApprove = async (email, role = 'client') => {
    setActionLoading(email);
    try {
      await api.approveUser(email, role);
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 }
      });
      addToast(`Approved ${email} as ${role.toUpperCase()}`, 'success');
      await loadData();
    } catch (err) {
      addToast(err.message || 'Failed to approve user', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  // Revoke Access
  const handleRevoke = async (email) => {
    if (!window.confirm(`Are you sure you want to revoke access for ${email}? They will no longer be able to use the studio.`)) {
      return;
    }
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

  // Direct Whitelist Add
  const handleDirectAdd = async (e) => {
    e.preventDefault();
    if (!newEmail.trim()) return;

    const emails = newEmail.split(',').map(e => e.trim()).filter(Boolean);
    if (!emails.length) return;

    setIsSubmittingAdd(true);
    try {
      for (const email of emails) {
        await api.approveUser(email, newRole);
      }
      addToast(`Successfully whitelisted ${emails.length} user(s)`, 'success');
      setNewEmail('');
      await loadData();
    } catch (err) {
      addToast(err.message || 'Failed to whitelist user', 'error');
    } finally {
      setIsSubmittingAdd(false);
    }
  };

  // Filter Whitelist entries
  const filteredWhitelist = (data.whitelist || []).filter((w) => {
    const matchesSearch = w.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || w.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const globalStats = data.global_stats || {};
  const totalPdfsScanned = globalStats.total_pdfs_scanned || 0;
  const totalPdfsExtracted = globalStats.total_pdfs_extracted || 0;
  const totalMasterRecords = globalStats.total_master_records || 0;
  const passCount = globalStats.pass_count || 0;
  const reviewCount = globalStats.review_count || 0;
  const totalValueInr = globalStats.total_value_inr || 0;

  const pendingCount = data.pending_requests?.length || 0;
  const approvedCount = data.whitelist?.length || 0;
  const adminCount = data.admin_emails?.length || 0;
  const activityLog = data.activity_log || [];

  return (
    <div className="space-y-7 pb-16">
      
      {/* Page Title & Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/80 backdrop-blur-xs p-6 rounded-3xl border border-brand-border shadow-warm-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 flex items-center justify-center text-amber-950 shadow-warm-sm ring-2 ring-amber-200/80">
            <Users className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 font-display">
                Admin Console & PDF Scan Analytics
              </h1>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 font-mono">
                Admin Panel
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Track real-time PDF processing across all client & admin accounts, manage whitelists, and review system logs.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="btn-white text-xs px-3.5 py-2 gap-2 font-semibold text-slate-700 cursor-pointer shadow-2xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-amber-600 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh All Stats</span>
          </button>
        </div>
      </div>

      {/* Hero Analytics Banner: Total PDFs Scanned by All Accounts */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-500 via-amber-400 to-amber-200 p-6 sm:p-7 border border-amber-400 shadow-warm-lg">
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-80 h-80 rounded-full bg-white/20 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-12 w-64 h-64 rounded-full bg-amber-600/20 blur-2xl pointer-events-none" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          
          {/* Main Hero Number */}
          <div className="lg:col-span-6 space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/10 border border-amber-950/15 text-amber-950 font-mono font-bold text-xs">
              <Layers className="w-3.5 h-3.5 text-amber-900" />
              <span>System-Wide Aggregate Metric</span>
            </div>
            <h2 className="text-xs sm:text-sm uppercase tracking-wider font-bold text-amber-950/80 font-mono">
              Total PDFs Scanned Across All Users & Accounts
            </h2>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-amber-950 font-display tracking-tight drop-shadow-2xs">
                {formatNumber(totalPdfsScanned)}
              </span>
              <span className="text-sm sm:text-base font-bold text-amber-900/90 font-mono">
                PDF Documents
              </span>
            </div>
            <p className="text-xs text-amber-950/80 font-medium max-w-lg leading-relaxed pt-1">
              Includes all batch scans, multi-folder explorations, and extraction jobs executed by all whitelisted operators and system admins.
            </p>
          </div>

          {/* Quick Metrics Columns */}
          <div className="lg:col-span-6 grid grid-cols-2 sm:grid-cols-3 gap-3">
            
            <div className="bg-white/85 backdrop-blur-xs p-4 rounded-2xl border border-white/60 shadow-warm-xs space-y-1">
              <div className="flex items-center gap-1.5 text-slate-500 text-[11px] font-mono uppercase font-bold">
                <FileSpreadsheet className="w-3.5 h-3.5 text-amber-700" />
                <span>Extracted</span>
              </div>
              <div className="text-xl sm:text-2xl font-bold text-slate-900 font-display">
                {formatNumber(totalPdfsExtracted)}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">Processed to Excel</div>
            </div>

            <div className="bg-white/85 backdrop-blur-xs p-4 rounded-2xl border border-white/60 shadow-warm-xs space-y-1">
              <div className="flex items-center gap-1.5 text-slate-500 text-[11px] font-mono uppercase font-bold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Pass Rate</span>
              </div>
              <div className="text-xl sm:text-2xl font-bold text-emerald-700 font-display">
                {totalMasterRecords > 0 ? Math.round((passCount / totalMasterRecords) * 100) : 100}%
              </div>
              <div className="text-[10px] text-slate-500 font-mono">{formatNumber(passCount)} valid records</div>
            </div>

            <div className="col-span-2 sm:col-span-1 bg-white/85 backdrop-blur-xs p-4 rounded-2xl border border-white/60 shadow-warm-xs space-y-1">
              <div className="flex items-center gap-1.5 text-slate-500 text-[11px] font-mono uppercase font-bold">
                <IndianRupee className="w-3.5 h-3.5 text-slate-700" />
                <span>Total Value</span>
              </div>
              <div className="text-xl sm:text-2xl font-bold text-slate-900 font-display truncate">
                {formatCurrency(totalValueInr)}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">Combined GeM Volume</div>
            </div>

          </div>

        </div>
      </div>

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Active Whitelist */}
        <div className="craft-card p-5 space-y-2 bg-white">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider font-mono">Approved Clients</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-slate-900 font-display">
            {approvedCount}
          </div>
          <p className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Full Studio Access Granted
          </p>
        </div>

        {/* Card 2: Pending Requests */}
        <div className={`craft-card p-5 space-y-2 transition-all ${
          pendingCount > 0 ? 'bg-amber-50/70 border-amber-300 shadow-warm-md' : 'bg-white'
        }`}>
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider font-mono text-amber-950">Pending Requests</span>
            <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center border border-amber-300">
              <Clock className={`w-4 h-4 ${pendingCount > 0 ? 'animate-pulse text-amber-700' : ''}`} />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-amber-950 font-display">
            {pendingCount}
          </div>
          <p className="text-[11px] text-amber-800 font-medium">
            {pendingCount > 0 ? 'Action required: Clients waiting for approval' : 'Queue clean (0 pending)'}
          </p>
        </div>

        {/* Card 3: Superadmins */}
        <div className="craft-card p-5 space-y-2 bg-white">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider font-mono">System Admins</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200">
              <Crown className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-slate-900 font-display">
            {adminCount}
          </div>
          <p className="text-[11px] text-slate-500 font-medium">
            Permanent Superadmin Privileges
          </p>
        </div>

        {/* Card 4: Backend Security Engine */}
        <div className="craft-card p-5 space-y-2 bg-white">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider font-mono">Security Layer</span>
            <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center border border-slate-200">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            </div>
          </div>
          <div className="text-base font-bold text-slate-900 font-display flex items-center gap-1.5 mt-1">
            <span>Firebase RS256</span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Zero-Trust Whitelist Active
          </p>
        </div>

      </div>

      {/* Main Grid: Pending Queue (Left) & Direct Add Form (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Pending Approval Requests */}
        <div className="lg:col-span-2 craft-card p-6 space-y-4 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-xs">
                {pendingCount}
              </div>
              <h3 className="text-sm font-bold text-slate-900 font-display">
                Pending Client Approvals
              </h3>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">
              Auto-registered on sign-in
            </span>
          </div>

          {data.pending_requests?.length === 0 ? (
            <div className="py-10 text-center space-y-2 text-slate-400">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-400 stroke-[1.5]" />
              <p className="text-xs font-semibold text-slate-600">All Client Requests Handled</p>
              <p className="text-[11px] text-slate-400">When new clients log in with their Google/Email account, their requests will appear here for 1-click approval.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.pending_requests.map((p) => (
                <div 
                  key={p.email}
                  className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200/90 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition-all hover:bg-amber-50"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-amber-600 shrink-0" />
                      <span className="font-mono font-bold text-sm text-slate-900 truncate">
                        {p.email}
                      </span>
                      <button
                        onClick={() => handleCopy(p.email)}
                        className="text-slate-400 hover:text-slate-700 transition-colors"
                        title="Copy email"
                      >
                        {copiedEmail === p.email ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
                      <span>Requested: {new Date(p.requested_at).toLocaleString()}</span>
                      {p.name && <span>• Name: {p.name}</span>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
                    <button
                      onClick={() => handleApprove(p.email, 'client')}
                      disabled={actionLoading === p.email}
                      className="btn-yellow text-xs px-3.5 py-1.5 font-bold cursor-pointer flex-1 sm:flex-none shadow-2xs"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>{actionLoading === p.email ? 'Approving...' : 'Approve Client'}</span>
                    </button>

                    <button
                      onClick={() => handleApprove(p.email, 'admin')}
                      disabled={actionLoading === p.email}
                      className="btn-white text-xs px-3 py-1.5 font-semibold text-slate-700 cursor-pointer flex-1 sm:flex-none"
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

        {/* Right Col: Direct Pre-Whitelist Invitation Form */}
        <div className="craft-card p-6 space-y-4 bg-white flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <div className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-700 flex items-center justify-center font-bold text-xs">
                <UserPlus className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 font-display">
                Pre-Whitelist Client
              </h3>
            </div>
            
            <p className="text-xs text-slate-500 leading-relaxed">
              Add a client’s email in advance so they can log in instantly without waiting for approval.
            </p>

            <form onSubmit={handleDirectAdd} className="space-y-3.5 pt-1">
              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-slate-700 font-mono uppercase">
                  Client Email Address(es)
                </label>
                <input
                  type="text"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="client@company.com (or comma-separated)"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-amber-500 rounded-xl text-xs text-slate-900 font-mono"
                />
                <span className="text-[10px] text-slate-400">Multiple emails supported via commas</span>
              </div>

              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-slate-700 font-mono uppercase">
                  Assign Access Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-semibold"
                >
                  <option value="client">Client (Standard Extraction & Records Access)</option>
                  <option value="admin">Admin (Full Whitelist & System Access)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isSubmittingAdd}
                className="w-full btn-yellow py-2.5 px-4 text-xs font-bold cursor-pointer flex items-center justify-center gap-2 shadow-warm-xs disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                <span>{isSubmittingAdd ? 'Whitelisting...' : 'Add to Whitelist'}</span>
              </button>
            </form>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-500 font-mono space-y-1">
            <div className="flex items-center gap-1 font-bold text-slate-700">
              <Lock className="w-3 h-3 text-slate-500" /> Persistent Storage
            </div>
            <div>Saved in <code className="bg-slate-200/70 px-1 py-0.5 rounded text-[10px]">backend/users_whitelist.json</code></div>
          </div>
        </div>

      </div>

      {/* Whitelisted Users Explorer Table with Per-User PDF Scans Breakdown */}
      <div className="craft-card p-6 space-y-5 bg-white">
        
        {/* Table Top Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2.5">
            <UserCheck className="w-5 h-5 text-emerald-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900 font-display">
                Active Whitelisted Accounts & Per-User PDF Counts ({filteredWhitelist.length})
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">
                Individual document scanning & extraction breakdown per account
              </p>
            </div>
          </div>

          {/* Search & Filter */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search email..."
                className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-amber-500 rounded-xl text-xs text-slate-900 font-mono w-44 sm:w-56"
              />
            </div>

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 font-semibold"
            >
              <option value="all">All Roles</option>
              <option value="client">Clients Only</option>
              <option value="admin">Admins Only</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-200/80">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/90 text-slate-600 font-mono text-[11px] border-b border-slate-200 uppercase">
                <th className="py-3 px-4 font-bold">Email Address</th>
                <th className="py-3 px-4 font-bold">Role</th>
                <th className="py-3 px-4 font-bold">PDFs Scanned</th>
                <th className="py-3 px-4 font-bold">PDFs Extracted</th>
                <th className="py-3 px-4 font-bold">Last Activity</th>
                <th className="py-3 px-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans">
              {filteredWhitelist.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400 font-mono text-xs">
                    {searchQuery ? `No users match "${searchQuery}"` : 'No whitelisted clients yet. Add one above!'}
                  </td>
                </tr>
              ) : (
                filteredWhitelist.map((w) => (
                  <tr key={w.email} className="hover:bg-slate-50/60 transition-colors">
                    
                    {/* Email Column */}
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <span>{w.email}</span>
                        <button
                          onClick={() => handleCopy(w.email)}
                          className="text-slate-300 hover:text-slate-600 transition-colors"
                          title="Copy email"
                        >
                          {copiedEmail === w.email ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>

                    {/* Role Badge */}
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase font-mono ${
                        w.role === 'admin' 
                          ? 'bg-amber-100 text-amber-900 border border-amber-300' 
                          : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      }`}>
                        {w.role === 'admin' ? <Crown className="w-3 h-3 text-amber-700" /> : <UserCheck className="w-3 h-3 text-emerald-600" />}
                        <span>{w.role}</span>
                      </span>
                    </td>

                    {/* PDFs Scanned Count */}
                    <td className="py-3.5 px-4 font-mono font-semibold">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-amber-50 text-amber-900 border border-amber-200 text-xs">
                        <FolderSearch className="w-3 h-3 text-amber-700" />
                        <span>{formatNumber(w.total_pdfs_scanned || 0)}</span>
                      </span>
                    </td>

                    {/* PDFs Extracted Count */}
                    <td className="py-3.5 px-4 font-mono font-semibold">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-900 border border-emerald-200 text-xs">
                        <FileSpreadsheet className="w-3 h-3 text-emerald-600" />
                        <span>{formatNumber(w.total_pdfs_extracted || 0)}</span>
                      </span>
                    </td>

                    {/* Last Activity */}
                    <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                      {w.last_active_at ? new Date(w.last_active_at).toLocaleDateString() : 'Inactive'}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRevoke(w.email)}
                        disabled={actionLoading === w.email}
                        className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-700 font-semibold px-2.5 py-1 rounded-lg hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-all cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Revoke</span>
                      </button>
                    </td>

                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

      </div>

      {/* Real-Time System Activity Stream / Audit Log */}
      <div className="craft-card p-6 space-y-4 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-amber-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900 font-display">
                Real-Time PDF Scan & Extraction Activity Stream
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">
                Chronological record of scans and extraction runs across all user accounts
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {activityLog.length} recent events
          </span>
        </div>

        {activityLog.length === 0 ? (
          <div className="py-8 text-center text-slate-400 font-mono text-xs bg-slate-50 rounded-2xl border border-slate-200/70">
            No recent scan activities logged yet. New scans will stream here automatically.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto pr-1">
            {activityLog.map((log) => (
              <div key={log.id} className="py-3 flex items-start justify-between gap-4 text-xs">
                <div className="flex items-start gap-3 min-w-0">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    log.action === 'extract' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {log.action === 'extract' ? <FileSpreadsheet className="w-3.5 h-3.5" /> : <FolderSearch className="w-3.5 h-3.5" />}
                  </div>
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-900 truncate">
                        {log.user_email}
                      </span>
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.2 rounded font-mono ${
                        log.action === 'extract' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}>
                        {log.action}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-600 font-medium">
                      {log.description}
                    </div>
                  </div>
                </div>

                <div className="text-[10px] text-slate-400 font-mono shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()} • {new Date(log.timestamp).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Permanent Superadmin List Card */}
      {data.admin_emails?.length > 0 && (
        <div className="craft-card p-5 bg-slate-900 text-slate-200 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs font-mono uppercase">
            <Crown className="w-4 h-4" /> Permanent Superadmins
          </div>
          <p className="text-xs text-slate-400">
            These accounts have permanent unrevokable administrative rights defined in <code className="text-amber-300 font-mono text-[10.5px]">backend/users_whitelist.json</code>:
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {data.admin_emails.map((adminEmail) => (
              <span key={adminEmail} className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 font-mono text-xs border border-slate-700 flex items-center gap-1.5">
                <Crown className="w-3 h-3 text-amber-400" />
                {adminEmail}
              </span>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
