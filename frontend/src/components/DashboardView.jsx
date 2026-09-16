import React from 'react';
import { 
  FileSpreadsheet, 
  IndianRupee, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  Sparkles, 
  FolderOpen, 
  Download, 
  Cpu, 
  FileText, 
  ExternalLink,
  ShieldCheck,
  Zap,
  Clock
} from 'lucide-react';
import StatsCard from './StatsCard';
import { formatCurrency, formatNumber, truncate } from '../utils/formatters';

export default function DashboardView({
  stats,
  recentRecords = [],
  onSelectRecord,
  onNavigate,
  onDownloadExcel,
  onDownloadJson,
  onOpenFolder,
  config,
}) {
  const passRate = stats.totalMaster > 0 
    ? Math.round((stats.passCount / stats.totalMaster) * 100) 
    : 100;

  return (
    <div className="space-y-7 animate-fade-in pb-12">
      
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-400 via-amber-300 to-amber-100 p-5 sm:p-6 border border-amber-400/60 shadow-warm-md">
        {/* Decorative background craft pattern */}
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 rounded-full bg-amber-400/40 blur-2xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 -mb-10 w-48 h-48 rounded-full bg-white/30 blur-xl pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-extrabold text-amber-950 tracking-tight">
              GeM PDF to Excel Studio
            </h1>
          </div>

          {/* Quick Action CTA Buttons */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigate('extract')}
              className="btn-yellow px-4 py-2.5 text-xs sm:text-sm font-bold shadow-warm-md"
            >
              <Cpu className="w-4 h-4" />
              <span>Start Extraction</span>
              <ArrowRight className="w-4 h-4 ml-0.5" />
            </button>
            <button
              onClick={() => onNavigate('records')}
              className="btn-white px-3.5 py-2.5 text-xs sm:text-sm font-semibold"
            >
              <FileText className="w-4 h-4 text-amber-700" />
              <span>View Records</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatsCard
          title="Master Contracts"
          value={formatNumber(stats.totalMaster)}
          subtext={`Saved in master database`}
          icon={FileSpreadsheet}
          variant="yellow"
        />

        <StatsCard
          title="Total Order Value"
          value={formatCurrency(stats.totalValue)}
          subtext="Cumulative INR order volume"
          icon={IndianRupee}
          variant="slate"
        />

        <StatsCard
          title="Validation Pass Rate"
          value={`${passRate}%`}
          subtext={`${formatNumber(stats.passCount)} verified contracts`}
          icon={CheckCircle2}
          variant="emerald"
        />

        <StatsCard
          title="Needs Review"
          value={formatNumber(stats.reviewCount)}
          subtext={stats.reviewCount > 0 ? "Requires manual spot-check" : "All contracts verified"}
          icon={AlertTriangle}
          variant="amber"
        />
      </div>

      {/* Quick Launch & Output Management Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Recent Parsed Contracts */}
        <div className="lg:col-span-2 craft-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-brand-border">
              <div>
                <h3 className="font-display text-base font-bold text-slate-900">
                  Recent Contract Extractions
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Latest Government e-Marketplace contracts processed
                </p>
              </div>
              <button
                onClick={() => onNavigate('records')}
                className="text-xs font-bold text-amber-700 hover:text-amber-800 flex items-center gap-1 hover:underline"
              >
                <span>View All</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Table */}
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-brand-border text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-2.5 px-3">Contract No</th>
                    <th className="py-2.5 px-3">Seller Name</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Order Value</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-borderSubtle">
                  {recentRecords.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="py-8 text-center text-slate-400">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <FileSpreadsheet className="w-8 h-8 text-amber-300" />
                          <p className="font-medium">No extracted contracts yet.</p>
                          <button
                            onClick={() => onNavigate('extract')}
                            className="btn-yellow text-xs px-3 py-1.5 mt-1"
                          >
                            Run PDF Extractor
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    recentRecords.map((r, idx) => {
                      const isPass = r.validation_status === 'PASS';
                      return (
                        <tr
                          key={idx}
                          onClick={() => onSelectRecord(r)}
                          className="table-row-hover cursor-pointer group"
                        >
                          <td className="py-3 px-3 font-mono font-semibold text-slate-900 group-hover:text-amber-700">
                            {truncate(r.contract_no, 20)}
                          </td>
                          <td className="py-3 px-3 text-slate-700 font-medium">
                            {truncate(r.seller_company_name, 22)}
                          </td>
                          <td className="py-3 px-3">
                            <span className={isPass ? 'badge-pass' : 'badge-review'}>
                              {isPass ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                              {r.validation_status || 'REVIEW'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right font-mono font-semibold text-slate-900">
                            {formatCurrency(r.total_order_value)}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectRecord(r);
                              }}
                              className="text-slate-400 group-hover:text-amber-600 p-1 rounded hover:bg-amber-100 transition-colors"
                              title="Inspect Details"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Quick Export & Folder Hub */}
        <div className="craft-card p-6 flex flex-col justify-between space-y-5 bg-gradient-to-b from-white to-brand-50/50">
          <div>
            <h3 className="font-display text-base font-bold text-slate-900 flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-amber-600" />
              <span>Master Output Hub</span>
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-1">
              Direct exports and local file management
            </p>

            <div className="mt-5 space-y-3">
              {/* Excel Download Card */}
              <div className="p-3.5 rounded-xl bg-white border border-emerald-200/80 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">gem_contracts.xlsx</h4>
                    <p className="text-[11px] text-slate-500">Multi-tab formatted Excel sheet</p>
                  </div>
                </div>
                <button
                  onClick={onDownloadExcel}
                  className="p-2 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                  title="Download Excel"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>

              {/* Records Explorer Shortcut Card */}
              <div className="p-3.5 rounded-xl bg-white border border-amber-200/80 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">Contract Records Explorer</h4>
                    <p className="text-[11px] text-slate-500">Search, filter & review contracts</p>
                  </div>
                </div>
                <button
                  onClick={() => onNavigate('records')}
                  className="p-2 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 transition-colors"
                  title="View Records"
                >
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {/* Explorer Button */}
              <button
                onClick={onOpenFolder}
                className="w-full btn-white py-2.5 text-xs font-semibold"
              >
                <FolderOpen className="w-4 h-4 text-amber-600" />
                <span>Open Output Folder in Explorer</span>
              </button>
            </div>
          </div>

          {/* Engine Feature Highlights */}
          <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/70 text-[11px] space-y-1.5 text-amber-900">
            <div className="flex items-center gap-1.5 font-bold text-amber-950">
              <Zap className="w-3.5 h-3.5 text-amber-600" />
              <span>Engine Features:</span>
            </div>
            <p className="text-amber-900/90 leading-relaxed">
              • PyMuPDF High-Speed Engine (~50 PDFs/sec)<br />
              • Auto Mathematical Validation & GSTIN Check<br />
              • Incremental Delta Updates & Safe Appending
            </p>
          </div>
        </div>

      </div>

    </div>
  );
}
