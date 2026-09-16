import React from 'react';
import { 
  FileSpreadsheet, 
  LayoutDashboard, 
  Cpu, 
  Database, 
  FolderOpen, 
  Download, 
  RefreshCw, 
  Sparkles,
  User,
  LogOut,
  ShieldCheck,
  LogIn,
  Users,
  Crown
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({
  activeView,
  setActiveView,
  backendStatus,
  onRefresh,
  isRefreshing,
  onDownloadExcel,
  onDownloadJson,
  onOpenFolder,
  recordsCount = 0,
  onOpenJwtModal,
  onOpenLogin,
  onOpenAdminModal
}) {
  const { currentUser, logout, jwtToken, userRole } = useAuth();

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-brand-border shadow-warm-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 flex items-center justify-center text-amber-950 shadow-warm-sm ring-2 ring-amber-200/80">
              <FileSpreadsheet className="w-5 h-5 text-amber-950 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-extrabold text-lg tracking-tight text-slate-900">
                  GeM <span className="text-amber-600 font-bold">PDF Studio</span>
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                  <Sparkles className="w-2.5 h-2.5" /> v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-600 font-medium hidden sm:block">
                Contract Parser & Excel Pipeline
              </p>
            </div>
          </div>

          {/* Navigation Pills */}
          <nav className="flex items-center gap-1.5 p-1 bg-brand-50 border border-brand-200 rounded-xl">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                activeView === 'dashboard'
                  ? 'bg-amber-400 text-amber-950 shadow-warm-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-amber-100/60'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveView('extract')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                activeView === 'extract'
                  ? 'bg-amber-400 text-amber-950 shadow-warm-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-amber-100/60'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Extract PDFs</span>
            </button>

            <button
              onClick={() => setActiveView('records')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                activeView === 'records'
                  ? 'bg-amber-400 text-amber-950 shadow-warm-sm font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-amber-100/60'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Records</span>
              {recordsCount > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  activeView === 'records' ? 'bg-amber-950 text-amber-300' : 'bg-amber-200/80 text-amber-900'
                }`}>
                  {recordsCount}
                </span>
              )}
            </button>

            {/* Admin Console Pill */}
            {userRole === 'admin' && (
              <button
                onClick={() => setActiveView('admin')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeView === 'admin'
                    ? 'bg-amber-400 text-amber-950 shadow-warm-sm font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-amber-100/60'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Admin Console</span>
              </button>
            )}
          </nav>

          {/* Right Utilities & Quick Actions */}
          <div className="flex items-center gap-2.5">
            {/* Backend Health Badge */}
            <div 
              title={backendStatus.ok ? `FastAPI Online (${backendStatus.latency}ms)` : 'Backend Offline'}
              className={`hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                backendStatus.ok
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border-rose-200 animate-pulse'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${
                backendStatus.ok ? 'bg-emerald-500 dot-ping' : 'bg-rose-500'
              }`} />
              <span className="text-[11px] font-semibold">
                {backendStatus.ok ? `API ${backendStatus.latency || 0}ms` : 'API Offline'}
              </span>
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh Data & Connectivity (R)"
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-amber-50 border border-brand-border rounded-lg transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-amber-600' : ''}`} />
            </button>

            {/* Download Excel Quick Action */}
            <button
              onClick={onDownloadExcel}
              title="Download Master Excel Spreadsheet"
              className="hidden sm:inline-flex btn-yellow text-xs px-3 py-1.5 gap-1.5 font-bold"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Excel</span>
            </button>

            {/* JWT & User Section */}
            {currentUser ? (
              <div className="flex items-center gap-1.5 pl-2 border-l border-brand-border">
                
                {/* Admin Whitelist Manager Button (Only for Admins) */}
                {userRole === 'admin' && (
                  <button
                    onClick={onOpenAdminModal}
                    title="Manage Whitelisted Clients & Access Requests"
                    className="flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-lg bg-amber-100 hover:bg-amber-200/80 text-amber-950 border border-amber-300 transition-colors shadow-2xs"
                  >
                    <Users className="w-3.5 h-3.5 text-amber-700" />
                    <span className="hidden sm:inline">Clients</span>
                  </button>
                )}

                {/* JWT Inspector Trigger */}
                {jwtToken && (
                  <button
                    onClick={onOpenJwtModal}
                    title="Inspect Firebase JWT Token & Claims"
                    className="flex items-center gap-1 text-[11px] font-mono px-2 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 transition-colors"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="hidden xl:inline font-bold">JWT</span>
                  </button>
                )}

                {/* User Email Badge */}
                <div 
                  title={`Signed in as ${currentUser.email || currentUser.uid} (${userRole})`}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-medium text-slate-700 max-w-[140px] truncate"
                >
                  <User className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <span className="truncate text-[11px]">{currentUser.email || 'User'}</span>
                </div>

                {/* Sign Out Button */}
                <button
                  onClick={logout}
                  title="Sign out of Firebase"
                  className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenLogin}
                className="btn-white text-xs px-3 py-1.5 gap-1.5 font-semibold text-slate-700"
              >
                <LogIn className="w-3.5 h-3.5 text-amber-600" />
                <span>Sign In</span>
              </button>
            )}

          </div>

        </div>
      </div>
    </header>
  );
}
