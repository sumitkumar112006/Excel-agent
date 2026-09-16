/**
 * Formatting and helper utilities for GeM Extractor
 */

export function formatCurrency(val) {
  if (val === null || val === undefined || val === 'NA' || val === '—' || val === '') {
    return '—';
  }
  const num = Number(val);
  if (isNaN(num)) return String(val);

  if (num >= 10000000) {
    return `₹${(num / 10000000).toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    return `₹${(num / 100000).toFixed(2)} L`;
  }
  if (num >= 10000) {
    return `₹${(num / 1000).toFixed(1)}k`;
  }
  return `₹${num.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

export function formatNumber(val) {
  if (val === null || val === undefined || val === 'NA' || val === '—' || val === '') {
    return '—';
  }
  const num = Number(val);
  if (isNaN(num)) return String(val);
  return num.toLocaleString('en-IN');
}

export function truncate(str, maxLen = 30) {
  if (!str || str === 'NA') return '—';
  return str.length > maxLen ? str.substring(0, maxLen) + '…' : str;
}

export function cleanAddressDisplay(text) {
  if (!text || text === 'NA' || text === '—') return '—';
  let val = String(text).trim();
  const prefixRegex = /^(?:address|pataa|ptaa|pata|पता)\b\s*(?:[/|\\–\-])?\s*(?:address|pataa|ptaa|pata|पता)?\s*[:.\-–=;]*\s*/i;
  for (let i = 0; i < 5; i++) {
    const prev = val;
    val = val.replace(prefixRegex, '').trim();
    val = val.replace(/^(?:address|pataa|ptaa|pata|पता)\b[:.\s\-–;=]*/i, '').trim();
    val = val.replace(/^[:|\-–;,\s]+/, '').trim();
    if (val === prev) break;
  }
  val = val.replace(/\s+/g, ' ').trim();
  val = val.replace(/^[:|\-–;,\s]+|[:|\-–;\s]+$/, '').trim();
  return val || '—';
}

export async function copyToClipboard(text) {
  if (!text || text === '—') return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand('copy');
      textArea.remove();
      return successful;
    }
  } catch (err) {
    console.error('Failed to copy', err);
    return false;
  }
}


