/**
 * API client for interacting with the FastAPI backend
 */

const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const { protocol, port, hostname } = window.location;
    if (protocol.startsWith('http')) {
      // If running on typical vite/webpack/live-server ports
      if (port === '3000' || port === '5173' || port === '5500') {
        // Use proxy or direct
        return '';
      }
      return window.location.origin;
    }
  }
  return 'http://127.0.0.1:8000';
};

const BASE_URL = getApiBase();

let currentAuthToken = null;

const getHeaders = (extra = {}) => {
  const headers = { ...extra };
  if (currentAuthToken) {
    headers['Authorization'] = `Bearer ${currentAuthToken}`;
  }
  return headers;
};

async function handleResponse(response) {
  if (!response.ok) {
    let errorMsg = `Server error (${response.status})`;
    try {
      const data = await response.json();
      if (data && (data.error || data.detail || data.message)) {
        errorMsg = data.error || data.detail || data.message;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export const api = {
  setAuthToken(token) {
    currentAuthToken = token;
  },

  getAuthToken() {
    return currentAuthToken;
  },

  async getAuthStatus() {
    const res = await fetch(`${BASE_URL}/api/auth/status`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  async getAdminUsers() {
    const res = await fetch(`${BASE_URL}/api/admin/users`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  async getAdminStats() {
    const res = await fetch(`${BASE_URL}/api/admin/stats`, {
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  async approveUser(email, role = 'client') {
    const res = await fetch(`${BASE_URL}/api/admin/approve`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ email, role }),
    });
    return handleResponse(res);
  },

  async revokeUser(email) {
    const res = await fetch(`${BASE_URL}/api/admin/revoke`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ email }),
    });
    return handleResponse(res);
  },

  async checkHealth() {
    const start = performance.now();
    try {
      const res = await fetch(`${BASE_URL}/api/health`, { 
        cache: 'no-store',
        headers: getHeaders()
      });
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        const data = await res.json();
        return { ok: true, data, latency };
      }
      return { ok: false, latency };
    } catch {
      return { ok: false, latency: null };
    }
  },

  async getConfig() {
    const res = await fetch(`${BASE_URL}/api/config`, {
      headers: getHeaders()
    });
    return handleResponse(res);
  },

  async scanFolder(inputDir, outputDir) {
    const res = await fetch(`${BASE_URL}/api/scan`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ input_dir: inputDir, output_dir: outputDir }),
    });
    return handleResponse(res);
  },

  async startExtraction(inputDir, outputDir, reprocessAll = false) {
    const res = await fetch(`${BASE_URL}/api/extract`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        input_dir: inputDir,
        output_dir: outputDir,
        reprocess_all: Boolean(reprocessAll),
      }),
    });
    return handleResponse(res);
  },

  async getProgress() {
    const res = await fetch(`${BASE_URL}/api/progress`, { 
      cache: 'no-store',
      headers: getHeaders()
    });
    return handleResponse(res);
  },

  async uploadAndExtract(files, outputDir = './output') {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    const headers = {};
    if (currentAuthToken) {
      headers['Authorization'] = `Bearer ${currentAuthToken}`;
    }
    const res = await fetch(`${BASE_URL}/api/upload-and-extract?output_dir=${encodeURIComponent(outputDir)}`, {
      method: 'POST',
      headers,
      body: formData,
    });
    return handleResponse(res);
  },

  async clearBatch(outputDir = './output') {
    const res = await fetch(`${BASE_URL}/api/clear-batch?output_dir=${encodeURIComponent(outputDir)}`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  async getRecords({ outputDir = './output', status = null, search = null, limit = 50, offset = 0, batchOnly = true } = {}) {
    let url = `${BASE_URL}/api/records?limit=${limit}&offset=${offset}&output_dir=${encodeURIComponent(outputDir)}&batch_only=${batchOnly}`;
    if (status && status !== 'all') {
      url += `&status=${encodeURIComponent(status.toUpperCase())}`;
    }
    if (search && search.trim()) {
      url += `&search=${encodeURIComponent(search.trim())}`;
    }
    const res = await fetch(url, {
      headers: getHeaders()
    });
    return handleResponse(res);
  },

  async getBatchExcelBlob(outputDir = './output') {
    const url = `${BASE_URL}/api/download/batch-excel?output_dir=${encodeURIComponent(outputDir)}`;
    const res = await fetch(url, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to download batch Excel spreadsheet');
    }
    return await res.blob();
  },

  async downloadBatchExcel(outputDir = './output') {
    const blob = await this.getBatchExcelBlob(outputDir);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `gem_contracts_${new Date().toISOString().slice(0, 10)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      try {
        link.remove();
        window.URL.revokeObjectURL(downloadUrl);
      } catch {}
    }, 15000);
    return blob;
  },

  async downloadExcel(outputDir = './output') {
    const url = `${BASE_URL}/api/download/excel?output_dir=${encodeURIComponent(outputDir)}`;
    const res = await fetch(url, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to download Excel spreadsheet');
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', `gem_contracts_${new Date().toISOString().slice(0, 10)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      try {
        link.remove();
        window.URL.revokeObjectURL(downloadUrl);
      } catch {}
    }, 15000);
    return true;
  },

  async downloadJson(outputDir = './output') {
    const url = `${BASE_URL}/api/download/json?output_dir=${encodeURIComponent(outputDir)}`;
    const res = await fetch(url, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to download JSON master');
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `gem_contracts_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
    return true;
  },

  async openFolder(folderPath = './output') {
    const res = await fetch(`${BASE_URL}/api/open-folder`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ folder_path: folderPath }),
    });
    return handleResponse(res);
  },

  async selectFolder(initialDir = '', title = 'Select Folder') {
    const res = await fetch(`${BASE_URL}/api/select-folder`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ initial_dir: initialDir, title }),
    });
    return handleResponse(res);
  },
};
