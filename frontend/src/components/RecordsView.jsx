import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Filter, 
  Download, 
  FolderOpen, 
  ChevronLeft, 
  ChevronRight, 
  CheckCircle2, 
  AlertTriangle, 
  FileSpreadsheet, 
  FileText, 
  ExternalLink,
  X,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { formatCurrency, formatNumber, truncate } from '../utils/formatters';

export default function RecordsView({
  records = [],
  totalMatched = 0,
  totalMaster = 0,
  passCount = 0,
  reviewCount = 0,
  isLoading,
  page,
  limit,
  searchQuery,
  statusFilter,
  onSearchChange,
  onStatusFilterChange,
  onPageChange,
  onLimitChange,
  onSelectRecord,
  onDownloadExcel,
  onDownloadMasterExcel,
  onResetBatch,
  onDownloadJson,
  onOpenFolder,
  onRefresh,
}) {
  const searchInputRef = useRef(null);
  const totalPages = Math.max(1, Math.ceil(totalMatched / limit));

  // Keyboard shortcut '/' to focus search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === '/' && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="space-y-5 animate-fade-in pb-12">
      
      {/* Top Filter and Search Control Card */}
      <div className="craft-card p-4 sm:p-5 bg-white space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          {/* Search Box */}
          <div className="relative flex-1 max-w-lg">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4 text-amber-600" />
            </div>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search by Contract No, Seller, GSTIN, Product, File..."
              className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-brand-border bg-brand-50/40 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:bg-white focus:border-amber-500 transition-all shadow-sm"
            />
            {searchQuery ? (
              <button
                onClick={() => onSearchChange('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            ) : (
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-white border border-slate-200 rounded">
                  /
                </kbd>
              </div>
            )}
          </div>

          {/* Quick Action Exports */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {records.length > 0 && onResetBatch && (
              <button
                onClick={onResetBatch}
                className="btn-white text-xs px-3 py-2 text-rose-700 hover:bg-rose-50 border-rose-200"
                title="Clear current batch records from UI view"
              >
                <X className="w-3.5 h-3.5" />
                <span>Clear UI</span>
              </button>
            )}
            {onDownloadMasterExcel && (
              <button
                onClick={onDownloadMasterExcel}
                className="btn-white text-xs px-3 py-2"
                title="Download Server Cumulative Master Excel Spreadsheet"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-slate-600" />
                <span>Server Master</span>
              </button>
            )}
            <button
              onClick={onDownloadExcel}
              className="btn-yellow text-xs px-3.5 py-2 font-bold"
              title="Download Current Batch Excel Spreadsheet"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Batch Excel</span>
            </button>
          </div>

        </div>

        {/* Filter Pills and Summary Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-brand-border">
          
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-500 mr-1 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5 text-amber-600" /> Filter:
            </span>

            {/* All Pill */}
            <button
              onClick={() => onStatusFilterChange('all')}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                statusFilter === 'all'
                  ? 'bg-amber-400 text-amber-950 shadow-xs border border-amber-500'
                  : 'bg-brand-50 text-slate-600 hover:bg-amber-50 border border-brand-border'
              }`}
            >
              All Records <span className="opacity-75 ml-1">({totalMaster})</span>
            </button>

            {/* Pass Pill */}
            <button
              onClick={() => onStatusFilterChange('PASS')}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'PASS'
                  ? 'bg-emerald-600 text-white shadow-xs border border-emerald-700'
                  : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200'
              }`}
            >
              <CheckCircle2 className="w-3 h-3" />
              <span>Passed</span>
              <span className="opacity-75">({passCount})</span>
            </button>

            {/* Review Pill */}
            <button
              onClick={() => onStatusFilterChange('REVIEW')}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'REVIEW'
                  ? 'bg-amber-500 text-amber-950 shadow-xs border border-amber-600'
                  : 'bg-amber-50 text-amber-900 hover:bg-amber-100 border border-amber-200'
              }`}
            >
              <AlertTriangle className="w-3 h-3" />
              <span>Review Needed</span>
              <span className="opacity-75">({reviewCount})</span>
            </button>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing <strong className="text-slate-800">{totalMatched}</strong> matching contracts
          </div>

        </div>
      </div>

      {/* Main Records Data Table Card */}
      <div className="craft-card overflow-hidden bg-white">
        <div className="overflow-x-auto min-h-[300px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-brand-50/70 border-b border-brand-border text-slate-600 font-bold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-3.5 w-12 text-center">#</th>
                <th className="py-3 px-3.5">Contract No</th>
                <th className="py-3 px-3.5">Date</th>
                <th className="py-3 px-3.5">Seller & GSTIN</th>
                <th className="py-3 px-3.5">Brand / Category</th>
                <th className="py-3 px-3.5 text-center">Qty</th>
                <th className="py-3 px-3.5 text-right">Unit Price</th>
                <th className="py-3 px-3.5 text-right">Order Value</th>
                <th className="py-3 px-3.5 text-center">Status</th>
                <th className="py-3 px-3.5">File Name</th>
                <th className="py-3 px-3.5 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-borderSubtle">
              {isLoading ? (
                <tr>
                  <td colSpan="11" className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <RefreshCw className="w-6 h-6 animate-spin text-amber-500" />
                      <span className="font-medium text-xs">Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan="11" className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center gap-2 max-w-sm mx-auto">
                      <FileSpreadsheet className="w-10 h-10 text-amber-300" />
                      <p className="font-bold text-slate-700 text-sm">No contracts found</p>
                      <p className="text-xs text-slate-500">
                        {searchQuery ? `No records match "${searchQuery}"` : 'No contracts extracted yet.'}
                      </p>
                      {searchQuery && (
                        <button
                          onClick={() => onSearchChange('')}
                          className="btn-white text-xs px-3 py-1.5 mt-2"
                        >
                          Clear Search
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                records.map((record, index) => {
                  const isPass = record.validation_status === 'PASS';
                  const rowNum = page * limit + index + 1;

                  return (
                    <tr
                      key={index}
                      onClick={() => onSelectRecord(record)}
                      className="table-row-hover cursor-pointer group transition-colors"
                    >
                      <td className="py-3.5 px-3.5 text-center text-slate-400 font-mono text-[11px]">
                        {rowNum}
                      </td>

                      <td className="py-3.5 px-3.5 font-mono font-bold text-slate-900 group-hover:text-amber-700">
                        {truncate(record.contract_no, 20)}
                      </td>

                      <td className="py-3.5 px-3.5 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                        {record.generated_date || '—'}
                      </td>

                      <td className="py-3.5 px-3.5">
                        <div className="font-semibold text-slate-800">
                          {truncate(record.seller_company_name, 22)}
                        </div>
                        {record.seller_gstin && record.seller_gstin !== 'NA' && (
                          <div className="font-mono text-[10px] text-slate-400 mt-0.5">
                            GSTIN: {record.seller_gstin}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-3.5 text-slate-600">
                        <div className="font-medium text-slate-800">{truncate(record.brand, 16)}</div>
                        <div className="text-[10px] text-slate-400 truncate max-w-[140px]">
                          {record.category_name_quadrant || '—'}
                        </div>
                      </td>

                      <td className="py-3.5 px-3.5 text-center font-mono font-semibold text-slate-800">
                        {record.ordered_quantity || '—'}
                      </td>

                      <td className="py-3.5 px-3.5 text-right font-mono text-slate-700">
                        {formatCurrency(record.unit_price)}
                      </td>

                      <td className="py-3.5 px-3.5 text-right font-mono font-bold text-slate-900">
                        {formatCurrency(record.total_order_value)}
                      </td>

                      <td className="py-3.5 px-3.5 text-center">
                        <span className={isPass ? 'badge-pass' : 'badge-review'}>
                          {isPass ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                          <span>{record.validation_status || 'REVIEW'}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-3.5 font-mono text-[11px] text-slate-400 truncate max-w-[130px]" title={record.file_name}>
                        {truncate(record.file_name, 18)}
                      </td>

                      <td className="py-3.5 px-3.5 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRecord(record);
                          }}
                          className="p-1.5 rounded-lg text-slate-400 group-hover:text-amber-700 hover:bg-amber-100 transition-colors"
                          title="Open Contract Details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination & Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-brand-50/60 border-t border-brand-border text-xs">
          
          {/* Limit selector */}
          <div className="flex items-center gap-2 text-slate-500">
            <span>Rows per page:</span>
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="px-2 py-1 rounded-md border border-brand-border bg-white text-xs font-semibold text-slate-700 focus:ring-1 focus:ring-amber-400 focus:outline-none"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          {/* Page indicator */}
          <div className="font-medium text-slate-600">
            Page <strong className="text-slate-900">{page + 1}</strong> of <strong className="text-slate-900">{totalPages}</strong> ({totalMatched} records)
          </div>

          {/* Prev / Next controls */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 0 || isLoading}
              className="btn-white text-xs px-2.5 py-1.5 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Prev</span>
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages - 1 || isLoading}
              className="btn-white text-xs px-2.5 py-1.5 disabled:opacity-40"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

        </div>

      </div>

    </div>
  );
}
