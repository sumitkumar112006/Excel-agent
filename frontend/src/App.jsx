import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import DashboardView from './components/DashboardView';
import ExtractView from './components/ExtractView';
import RecordsView from './components/RecordsView';
import RecordDetailModal from './components/RecordDetailModal';
import LoginPage from './components/LoginPage';
import JwtTokenModal from './components/JwtTokenModal';
import PendingApprovalView from './components/PendingApprovalView';
import AdminUsersModal from './components/AdminUsersModal';
import AdminView from './components/AdminView';
import { api } from './api/client';
import { useToast } from './context/ToastContext';
import { useAuth } from './context/AuthContext';
import { exportRecordsToExcel } from './utils/excelExporter';

export default function App() {
  const { addToast } = useToast();
  const { currentUser, loading: isAuthLoading, approvalStatus, userRole } = useAuth();

  // Navigation
  const [activeView, setActiveView] = useState('dashboard');
  const [isJwtModalOpen, setIsJwtModalOpen] = useState(false);
  const [isAdminModalOpen, setIsAdminModalOpen] = useState(false);
  const [guestMode, setGuestMode] = useState(false);
  const [forceLoginView, setForceLoginView] = useState(false);

  // Backend state
  const [backendStatus, setBackendStatus] = useState({ ok: false, latency: null });
  const [config, setConfig] = useState({
    default_input_dir: './pdfs',
    default_output_dir: './output',
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Stats
  const [stats, setStats] = useState({
    totalMaster: 0,
    totalValue: 0,
    passCount: 0,
    reviewCount: 0,
  });

  // Recent Records (for Dashboard)
  const [recentRecords, setRecentRecords] = useState([]);

  // Full Records Explorer State
  const [records, setRecords] = useState([]);
  const [totalMatched, setTotalMatched] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(50);
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);

  // Selected Record for Modal Detail
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Check Backend Connectivity
  const checkHealth = useCallback(async () => {
    const health = await api.checkHealth();
    setBackendStatus(health);
    return health.ok;
  }, []);

  // Load Config
  const loadConfig = useCallback(async () => {
    try {
      const cfg = await api.getConfig();
      if (cfg) setConfig(cfg);
    } catch {
      // ignore
    }
  }, []);

  // Load Dashboard Data
  const loadDashboardData = useCallback(async () => {
    try {
      const data = await api.getRecords({ limit: 6, offset: 0 });
      setStats({
        totalMaster: data.total_master || 0,
        totalValue: data.total_value_inr || 0,
        passCount: data.pass_count || 0,
        reviewCount: data.review_count || 0,
      });
      setRecentRecords(data.records || []);
    } catch {
      // ignore
    }
  }, []);

  // Load Records for Explorer View
  const loadRecords = useCallback(async () => {
    setIsLoadingRecords(true);
    try {
      const data = await api.getRecords({
        status: statusFilter,
        search: searchQuery,
        limit,
        offset: page * limit,
      });

      setRecords(data.records || []);
      setTotalMatched(data.total || 0);
      setStats({
        totalMaster: data.total_master || 0,
        totalValue: data.total_value_inr || 0,
        passCount: data.pass_count || 0,
        reviewCount: data.review_count || 0,
      });
    } catch (err) {
      console.error('Failed to load records:', err);
    } finally {
      setIsLoadingRecords(false);
    }
  }, [statusFilter, searchQuery, page, limit]);

  // Combined Refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    const isOnline = await checkHealth();
    if (isOnline) {
      await Promise.all([loadConfig(), loadDashboardData()]);
      if (activeView === 'records') {
        await loadRecords();
      }
      addToast('Data synchronized with backend', 'info', 2000);
    } else {
      addToast('Cannot connect to FastAPI backend', 'error', 3000);
    }
    setIsRefreshing(false);
  };

  // Initial Load
  useEffect(() => {
    checkHealth().then((online) => {
      if (online) {
        loadConfig();
      }
    });

    // Polling heartbeat every 5s
    const heartbeat = setInterval(async () => {
      await checkHealth();
    }, 5000);

    return () => clearInterval(heartbeat);
  }, [checkHealth, loadConfig]);

  // Trigger loadRecords when navigating to records or changing query
  useEffect(() => {
    if (activeView === 'records') {
      loadRecords();
    }
  }, [activeView, loadRecords]);

  // Keyboard shortcut 'r' for refresh
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.key === 'r' || e.key === 'R') && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
        e.preventDefault();
        handleRefresh();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleRefresh]);

  // Download Handlers
  const handleDownloadExcel = async () => {
    // 1. If we have records in memory in React state, export immediately via SheetJS!
    if (records && records.length > 0) {
      try {
        exportRecordsToExcel(records);
        addToast(`Downloaded Excel spreadsheet with ${records.length} records!`, 'success');
        return;
      } catch (clientErr) {
        console.warn('Client export fallback to API:', clientErr);
      }
    }

    // 2. Try fetching from backend batch endpoint
    try {
      addToast('Preparing Excel workbook...', 'info', 2000);
      await api.downloadBatchExcel(config?.default_output_dir || './output');
      addToast('Excel spreadsheet downloaded successfully!', 'success');
    } catch (err) {
      try {
        // 3. Fallback: try fetching latest records from backend to export
        const data = await api.getRecords({ limit: 1000, batchOnly: true });
        if (data && data.records && data.records.length > 0) {
          exportRecordsToExcel(data.records);
          addToast(`Downloaded Excel spreadsheet with ${data.records.length} records!`, 'success');
          return;
        }
        await api.downloadExcel(config?.default_output_dir || './output');
        addToast('Excel spreadsheet downloaded successfully!', 'success');
      } catch (masterErr) {
        addToast('No extracted records found to download. Please extract PDFs first.', 'warning');
      }
    }
  };

  const handleDownloadMasterExcel = async () => {
    try {
      addToast('Preparing Server Master Excel workbook...', 'info', 2000);
      await api.downloadExcel(config.default_output_dir || './output');
      addToast('Server Master Excel downloaded successfully!', 'success');
    } catch (err) {
      addToast(err.message || 'Master Excel download failed', 'error');
    }
  };

  const handleDownloadJson = async () => {
    try {
      addToast('Preparing JSON data...', 'info', 2000);
      await api.downloadJson(config.default_output_dir || './output');
      addToast('JSON file downloaded successfully!', 'success');
    } catch (err) {
      addToast(err.message || 'JSON download failed', 'error');
    }
  };

  const handleResetBatch = async () => {
    try {
      await api.clearBatch(config?.default_output_dir || './output');
    } catch {
      // ignore
    }
    setRecords([]);
    setRecentRecords([]);
    setTotalMatched(0);
    setStats({
      totalMaster: 0,
      totalValue: 0,
      passCount: 0,
      reviewCount: 0,
    });
    setSelectedRecord(null);
    addToast('Previous batch records cleared from UI view.', 'info');
  };

  const handleOpenFolder = async () => {
    const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    if (isLocalhost) {
      try {
        await api.openFolder(config.default_output_dir || './output');
        addToast('Output folder opened in Explorer', 'success');
        return;
      } catch {
        // fallback to view records
      }
    }
    setActiveView('records');
    addToast('Viewing batch records. Use "Export Excel" to save file.', 'info', 3000);
  };

  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-warm-canvas">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-amber-500/30 border-t-amber-500 rounded-full animate-spin mx-auto" />
          <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">Loading Firebase Session...</p>
        </div>
      </div>
    );
  }

  // Show clean minimal login page if not logged in and not in guest preview mode
  if (!currentUser && !guestMode || forceLoginView) {
    return (
      <div className="min-h-screen flex flex-col bg-brand-warm-canvas">
        <header className="py-4 border-b border-brand-border bg-white/60 backdrop-blur-xs">
          <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
            <div className="flex items-center gap-2 font-display font-bold text-slate-900 text-sm">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>GeM PDF Studio</span>
            </div>
            {forceLoginView && (
              <button
                onClick={() => setForceLoginView(false)}
                className="text-xs text-slate-500 hover:text-slate-800 underline font-medium"
              >
                ← Back to Workspace
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center">
          <LoginPage 
            onBypassDemo={() => {
              setGuestMode(true);
              setForceLoginView(false);
            }} 
          />
        </main>

        <footer className="py-4 text-center text-xs text-slate-400 font-mono">
          Firebase Auth v10 + JWT Session Architecture
        </footer>
      </div>
    );
  }

  // Show Pending Approval view if logged in but pending whitelist approval
  if (currentUser && approvalStatus === 'pending' && !guestMode) {
    return (
      <div className="min-h-screen flex flex-col bg-brand-warm-canvas">
        <header className="py-4 border-b border-brand-border bg-white/60 backdrop-blur-xs">
          <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
            <div className="flex items-center gap-2 font-display font-bold text-slate-900 text-sm">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>GeM PDF Studio</span>
            </div>
            <div className="text-xs text-amber-800 font-mono font-bold px-2.5 py-0.5 rounded-full bg-amber-100 border border-amber-300">
              Zero-Trust Access Control
            </div>
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center">
          <PendingApprovalView />
        </main>

        <footer className="py-4 text-center text-xs text-slate-400 font-mono">
          Backend Whitelist Enforcement Active
        </footer>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <Navbar
        activeView={activeView}
        setActiveView={setActiveView}
        backendStatus={backendStatus}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        onDownloadExcel={handleDownloadExcel}
        onDownloadJson={handleDownloadJson}
        onOpenFolder={handleOpenFolder}
        recordsCount={stats.totalMaster}
        onOpenJwtModal={() => setIsJwtModalOpen(true)}
        onOpenAdminModal={() => setIsAdminModalOpen(true)}
        onOpenLogin={() => {
          setGuestMode(false);
          setForceLoginView(true);
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-7">
        {activeView === 'dashboard' && (
          <DashboardView
            stats={stats}
            recentRecords={recentRecords}
            onSelectRecord={(r) => setSelectedRecord(r)}
            onNavigate={(view) => setActiveView(view)}
            onDownloadExcel={handleDownloadExcel}
            onDownloadJson={handleDownloadJson}
            onOpenFolder={handleOpenFolder}
            config={config}
          />
        )}

        {activeView === 'extract' && (
          <ExtractView
            config={config}
            api={api}
            onResetBatch={handleResetBatch}
            onExtractionFinished={async (batchRecords) => {
              if (batchRecords && batchRecords.length > 0) {
                setRecords(batchRecords);
                setRecentRecords(batchRecords.slice(0, 6));
                setTotalMatched(batchRecords.length);
                const val = batchRecords.reduce((sum, r) => sum + (typeof r.total_order_value === 'number' ? r.total_order_value : 0), 0);
                const passes = batchRecords.filter(r => r.validation_status === 'PASS').length;
                setStats({
                  totalMaster: batchRecords.length,
                  totalValue: Math.round(val * 100) / 100,
                  passCount: passes,
                  reviewCount: batchRecords.length - passes,
                });
              } else {
                await loadDashboardData();
                await loadRecords();
              }
              setActiveView('records');
            }}
            onNavigate={(view) => setActiveView(view)}
          />
        )}

        {activeView === 'records' && (
          <RecordsView
            records={records}
            totalMatched={totalMatched}
            totalMaster={stats.totalMaster}
            passCount={stats.passCount}
            reviewCount={stats.reviewCount}
            isLoading={isLoadingRecords}
            page={page}
            limit={limit}
            searchQuery={searchQuery}
            statusFilter={statusFilter}
            onSearchChange={(q) => {
              setSearchQuery(q);
              setPage(0);
            }}
            onStatusFilterChange={(f) => {
              setStatusFilter(f);
              setPage(0);
            }}
            onPageChange={(p) => setPage(p)}
            onLimitChange={(l) => {
              setLimit(l);
              setPage(0);
            }}
            onSelectRecord={(r) => setSelectedRecord(r)}
            onDownloadExcel={handleDownloadExcel}
            onDownloadMasterExcel={handleDownloadMasterExcel}
            onResetBatch={handleResetBatch}
            onDownloadJson={handleDownloadJson}
            onOpenFolder={handleOpenFolder}
            onRefresh={loadRecords}
          />
        )}

        {activeView === 'admin' && (
          <AdminView />
        )}
      </main>

      {/* Record Detail Modal */}
      {selectedRecord && (
        <RecordDetailModal
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}

      {/* JWT Token Inspector Modal */}
      <JwtTokenModal
        isOpen={isJwtModalOpen}
        onClose={() => setIsJwtModalOpen(false)}
      />

      {/* Admin Whitelist & User Manager Modal */}
      <AdminUsersModal
        isOpen={isAdminModalOpen}
        onClose={() => setIsAdminModalOpen(false)}
      />

      {/* Subtle Footer */}
      <footer className="mt-auto py-5 border-t border-brand-border bg-white/70 backdrop-blur-xs text-center text-xs text-slate-500 font-medium">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-slate-600 font-semibold">
            <span>GeM Contract Extraction Suite</span>
            <span className="text-slate-300">•</span>
            <span className="text-amber-700">Non-LLM Deterministic Pipeline</span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            FastAPI + PyMuPDF + Firebase JWT Auth
          </div>
        </div>
      </footer>
    </div>
  );
}
