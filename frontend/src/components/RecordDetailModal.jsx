import React, { useState, useEffect } from 'react';
import { 
  X, 
  Copy, 
  Check, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Building, 
  Mail, 
  Phone, 
  MapPin, 
  Package, 
  IndianRupee, 
  ShieldCheck,
  ExternalLink
} from 'lucide-react';
import { formatCurrency, formatNumber, copyToClipboard, cleanAddressDisplay } from '../utils/formatters';
import { useToast } from '../context/ToastContext';

export default function RecordDetailModal({ record, onClose }) {
  const { addToast } = useToast();
  const [copiedField, setCopiedField] = useState(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!record) return null;

  const handleCopy = async (fieldKey, value) => {
    if (!value || value === 'NA' || value === '—') return;
    const ok = await copyToClipboard(String(value));
    if (ok) {
      setCopiedField(fieldKey);
      addToast(`Copied "${fieldKey}" to clipboard`, 'info', 2000);
      setTimeout(() => setCopiedField(null), 1800);
    }
  };

  const isPass = record.validation_status === 'PASS';
  const cleanConsigneeAddress = cleanAddressDisplay(record.consignee_address);
  const cleanSellerAddress = cleanAddressDisplay(record.address);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
      <div 
        className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-2xl border border-brand-border shadow-warm-xl flex flex-col overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="flex items-start justify-between p-5 bg-gradient-to-r from-brand-50 to-amber-50/70 border-b border-brand-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-400 text-amber-950 flex items-center justify-center font-bold shadow-sm">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-display font-extrabold text-lg text-slate-900">
                  {record.contract_no || 'Unknown Contract'}
                </span>
                <span className={isPass ? 'badge-pass' : 'badge-review'}>
                  {isPass ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                  <span>{record.validation_status || 'REVIEW'}</span>
                  {record.validation_score ? ` (${record.validation_score}%)` : ''}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                File: {record.file_name || '—'} • Date: {record.generated_date || '—'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs flex-1">
          {/* Validation Warning Alert if Errors exist */}
          {record.validation_errors && record.validation_errors.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 space-y-1">
              <div className="flex items-center gap-2 font-bold text-amber-950">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Validation Flags Detected:</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800 pl-1 font-medium">
                {record.validation_errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 1: Seller Details */}
          <div className="space-y-3">
            <h4 className="font-display text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 border-b border-brand-border pb-1.5">
              <Building className="w-3.5 h-3.5 text-amber-600" />
              <span>Seller & Merchant Profile</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <FieldCard
                label="Seller Company Name"
                value={record.seller_company_name}
                onCopy={() => handleCopy('Seller Name', record.seller_company_name)}
                copied={copiedField === 'Seller Name'}
                colSpan="col-span-full"
              />
              <FieldCard
                label="GSTIN"
                value={record.seller_gstin}
                mono
                onCopy={() => handleCopy('GSTIN', record.seller_gstin)}
                copied={copiedField === 'GSTIN'}
              />
              <FieldCard
                label="Contact Phone"
                value={record.seller_contact_no}
                mono
                icon={Phone}
                onCopy={() => handleCopy('Phone', record.seller_contact_no)}
                copied={copiedField === 'Phone'}
              />
              <FieldCard
                label="Seller Email"
                value={record.seller_email}
                mono
                icon={Mail}
                onCopy={() => handleCopy('Seller Email', record.seller_email)}
                copied={copiedField === 'Seller Email'}
                colSpan="col-span-full"
              />
              {cleanSellerAddress && cleanSellerAddress !== '—' && (
                <FieldCard
                  label="Seller Address"
                  value={cleanSellerAddress}
                  colSpan="col-span-full"
                  onCopy={() => handleCopy('Seller Address', cleanSellerAddress)}
                  copied={copiedField === 'Seller Address'}
                />
              )}
            </div>
          </div>

          {/* Section 2: Financials & Product */}
          <div className="space-y-3">
            <h4 className="font-display text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 border-b border-brand-border pb-1.5">
              <Package className="w-3.5 h-3.5 text-amber-600" />
              <span>Product & Financial Breakdown</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              {record.product_name && record.product_name !== 'NA' && (
                <FieldCard
                  label="Product Name"
                  value={record.product_name}
                  colSpan="col-span-full"
                  onCopy={() => handleCopy('Product Name', record.product_name)}
                  copied={copiedField === 'Product Name'}
                />
              )}
              <FieldCard
                label="Category & Quadrant"
                value={record.category_name_quadrant}
                colSpan="col-span-full"
                onCopy={() => handleCopy('Category & Quadrant', record.category_name_quadrant)}
                copied={copiedField === 'Category & Quadrant'}
              />
              <FieldCard
                label="Brand / Make"
                value={record.brand}
                colSpan="sm:col-span-1"
                onCopy={() => handleCopy('Brand', record.brand)}
                copied={copiedField === 'Brand'}
              />
              <FieldCard
                label="Ordered Quantity"
                value={record.ordered_quantity}
                mono
              />
              <FieldCard
                label="Unit Price"
                value={formatCurrency(record.unit_price)}
                mono
              />
              <FieldCard
                label="Total Order Value (₹)"
                value={formatCurrency(record.total_order_value)}
                mono
                highlight
                colSpan="col-span-full"
              />
            </div>
          </div>

          {/* Section 3: Consignee & Buyer */}
          <div className="space-y-3">
            <h4 className="font-display text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5 border-b border-brand-border pb-1.5">
              <MapPin className="w-3.5 h-3.5 text-amber-600" />
              <span>Consignee & Delivery Destination</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <FieldCard
                label="Consignee Address"
                value={cleanConsigneeAddress}
                colSpan="col-span-full"
                onCopy={() => handleCopy('Consignee Address', cleanConsigneeAddress)}
                copied={copiedField === 'Consignee Address'}
              />
              <FieldCard
                label="Consignee Contact No"
                value={record.consignee_contact_no}
                mono
                icon={Phone}
                onCopy={() => handleCopy('Consignee Contact', record.consignee_contact_no)}
                copied={copiedField === 'Consignee Contact'}
              />
              <FieldCard
                label="Consignee Email"
                value={record.consignee_email}
                mono
                icon={Mail}
                onCopy={() => handleCopy('Consignee Email', record.consignee_email)}
                copied={copiedField === 'Consignee Email'}
              />
              <FieldCard
                label="Buyer Email"
                value={record.buyer_email}
                mono
                icon={Mail}
                onCopy={() => handleCopy('Buyer Email', record.buyer_email)}
                copied={copiedField === 'Buyer Email'}
              />
              <FieldCard
                label="Paying Authority Email"
                value={record.paying_authority_email}
                mono
                icon={Mail}
                onCopy={() => handleCopy('Paying Authority Email', record.paying_authority_email)}
                copied={copiedField === 'Paying Authority Email'}
                colSpan="col-span-full"
              />
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-brand-50/70 border-t border-brand-border flex items-center justify-between">
          <div className="text-[11px] text-slate-500 font-mono truncate max-w-xs">
            Source: <span className="text-slate-800">{record.file_name}</span>
          </div>
          <button
            onClick={onClose}
            className="btn-white text-xs px-4 py-1.5 font-semibold"
          >
            Close Window
          </button>
        </div>

      </div>
    </div>
  );
}

function FieldCard({ label, value, mono = false, highlight = false, icon: Icon, onCopy, copied, colSpan = '' }) {
  const displayVal = value || '—';
  const hasValue = value && value !== 'NA' && value !== '—';

  return (
    <div className={`p-3 rounded-xl border ${highlight ? 'bg-amber-50/60 border-amber-300' : 'bg-brand-50/40 border-brand-border'} ${colSpan}`}>
      <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
        <span className="flex items-center gap-1">
          {Icon && <Icon className="w-3 h-3 text-slate-400" />}
          {label}
        </span>
        {onCopy && hasValue && (
          <button
            onClick={onCopy}
            className="text-slate-400 hover:text-amber-700 p-0.5 rounded transition-colors"
            title="Copy value"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
          </button>
        )}
      </div>
      <div className={`text-xs font-semibold text-slate-800 ${mono ? 'font-mono text-[11px]' : ''} ${highlight ? 'text-amber-950 font-bold text-sm' : ''} break-words leading-relaxed`}>
        {displayVal}
      </div>
    </div>
  );
}
