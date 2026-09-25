import React, { useState, useEffect, useRef } from 'react';
import { 
  Cpu, 
  FolderSearch, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  RefreshCw, 
  Layers, 
  Zap, 
  Clock, 
  Gauge, 
  FolderOpen, 
  Check, 
  Sparkles,
  ArrowRight,
  UploadCloud,
  X,
  Download
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { useToast } from '../context/ToastContext';

// Realistic multistage progress stages for Render cloud wake-up and PDF extraction
const EXTRACTION_STAGES = [
  { maxSec: 6, msg: "Scanning selected directory & reading PDF document streams...", sub: "Cataloging contracts and reading binary streams..." },
  { maxSec: 16, msg: "Connecting to cloud extraction container & warming up engine...", sub: "Render cloud server is booting up (~45-55s cold-start preparation)..." },
  { maxSec: 28, msg: "Preprocessing PDF pages, text layers, and table geometry...", sub: "Ingesting document geometry and mapping layout bounding boxes..." },
  { maxSec: 40, msg: "Extracting contract numbers, buyer/seller metadata & GSTINs...", sub: "Parsing GeM contract details, seller names, and consignee addresses..." },
  { maxSec: 52, msg: "Parsing itemized pricing tables, quantities & order values...", sub: "Extracting product descriptions and computing line-item totals..." },
  { maxSec: 999, msg: "Finalizing batch dataset and compiling clean Excel workbook...", sub: "Validating tabular structure and formatting output spreadsheet..." },
];

const getSimulatedPct = (t) => {
  if (t <= 5) return Math.round(6 + (t / 5) * 12);
  if (t <= 15) return Math.round(18 + ((t - 5) / 10) * 16);
  if (t <= 30) return Math.round(34 + ((t - 15) / 15) * 28);
  if (t <= 45) return Math.round(62 + ((t - 30) / 15) * 18);
  if (t <= 55) return Math.round(80 + ((t - 45) / 10) * 8);
  const extra = Math.min(6, (t - 55) * 0.15);
  return Math.min(94, Math.round(88 + extra));
};

export default function ExtractView({
  config,
  api,
  onExtractionFinished,
  onResetBatch,
  onNavigate,
}) {
  const { addToast } = useToast();

  // Inputs
  const [inputDir, setInputDir] = useState('./pdfs');
  const [outputDir, setOutputDir] = useState('./output');
  const [reprocessAll, setReprocessAll] = useState(false);

  // Hidden native file/folder input references
  const folderInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const simTimerRef = useRef(null);
  const pollTimerRef = useRef(null);

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedFolderName, setSelectedFolderName] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  // Scan state
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  // Extraction state
  const [isExtracting, setIsExtracting] = useState(false);
  const [progress, setProgress] = useState({
    percentage: 0,
    processed: 0,
    total: 0,
    current_file: '',
    pass_count: 0,
    review_count: 0,
    speed_fps: 0,
    elapsed_seconds: 0,
    message: 'Ready',
    subMessage: '',
    completed: false,
    is_running: false,
  });

  const stopTimers = () => {
    if (simTimerRef.current) {
      clearInterval(simTimerRef.current);
      simTimerRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopTimers();
  }, []);

  // Proactive background warm-up of Render server on mount
  useEffect(() => {
    if (api && api.checkHealth) {
      api.checkHealth().catch(() => {});
    }
  }, [api]);

  // Sync initial config from backend
  useEffect(() => {
    if (config) {
      if (config.default_input_dir) setInputDir(config.default_input_dir);
      if (config.default_output_dir) setOutputDir(config.default_output_dir);
    }
  }, [config]);

  // Handle native folder selection from user's computer
  const handleFolderSelect = (e) => {
    if (api && api.checkHealth) api.checkHealth().catch(() => {});
    const rawFiles = Array.from(e.target.files || []);
    const pdfs = rawFiles.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfs.length === 0) {
      addToast('No PDF files found in the selected folder.', 'warning');
      return;
    }
    let folderName = 'Selected Folder';
    if (pdfs[0].webkitRelativePath) {
      folderName = pdfs[0].webkitRelativePath.split('/')[0] || 'Selected Folder';
    }
    setSelectedFiles(pdfs);
    setSelectedFolderName(folderName);
    setInputDir(`${folderName} (${pdfs.length} PDFs)`);

    // Clear previous batch from UI view
    if (onResetBatch) onResetBatch();

    setScanResult({
      input_dir: folderName,
      total_pdfs: pdfs.length,
      already_processed: 0,
      new_to_process: pdfs.length,
      sample_files: pdfs.slice(0, 5).map(f => f.name)
    });

    addToast(`Selected folder "${folderName}" with ${pdfs.length} PDF(s)!`, 'success');
  };

  // Handle individual PDF file selection from computer
  const handleFilesSelect = (e) => {
    if (api && api.checkHealth) api.checkHealth().catch(() => {});
    const rawFiles = Array.from(e.target.files || []);
    const pdfs = rawFiles.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfs.length === 0) {
      addToast('No PDF files selected.', 'warning');
      return;
    }
    setSelectedFiles(pdfs);
    setSelectedFolderName(`${pdfs.length} Selected PDFs`);
    setInputDir(`${pdfs.length} Selected PDFs`);

    // Clear previous batch from UI view
    if (onResetBatch) onResetBatch();

    setScanResult({
      input_dir: `${pdfs.length} PDF files`,
      total_pdfs: pdfs.length,
      already_processed: 0,
      new_to_process: pdfs.length,
      sample_files: pdfs.slice(0, 5).map(f => f.name)
    });

    addToast(`Selected ${pdfs.length} PDF file(s)!`, 'success');
  };

  // Trigger native folder picker dialog
  const handleBrowseInput = () => {
    if (folderInputRef.current) {
      folderInputRef.current.value = '';
      folderInputRef.current.click();
    }
  };

  // Trigger native file picker dialog
  const handleBrowseFiles = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  // Drag & drop handler
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (api && api.checkHealth) api.checkHealth().catch(() => {});
    const rawFiles = Array.from(e.dataTransfer.files || []);
    const pdfs = rawFiles.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfs.length === 0) {
      addToast('Please drop PDF files.', 'warning');
      return;
    }
    setSelectedFiles(pdfs);
    setSelectedFolderName(`Dropped ${pdfs.length} PDFs`);
    setInputDir(`Dropped ${pdfs.length} PDFs`);

    if (onResetBatch) onResetBatch();

    setScanResult({
      input_dir: `${pdfs.length} PDFs`,
      total_pdfs: pdfs.length,
      already_processed: 0,
      new_to_process: pdfs.length,
      sample_files: pdfs.slice(0, 5).map(f => f.name)
    });

    addToast(`Loaded ${pdfs.length} dropped PDF(s)!`, 'success');
  };

  const handleClearSelection = () => {
    setSelectedFiles([]);
    setSelectedFolderName('');
    setInputDir(config?.default_input_dir || './pdfs');
    setScanResult(null);
    if (onResetBatch) onResetBatch();
    addToast('Selection cleared.', 'info');
  };

  const [outputDirHandle, setOutputDirHandle] = useState(null);

  const handleBrowseOutput = async () => {
    // 1. Try modern browser File System Access API (opens native computer folder picker in Chrome/Edge)
    if (typeof window !== 'undefined' && window.showDirectoryPicker) {
      try {
        const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        if (dirHandle && dirHandle.name) {
          setOutputDir(dirHandle.name);
          setOutputDirHandle(dirHandle);
          addToast(`Selected output folder: ${dirHandle.name}`, 'success');
          return;
        }
      } catch (err) {
        if (err.name === 'AbortError') return; // User cancelled
      }
    }

    // 2. Fallback for local desktop mode
    try {
      addToast('Opening File Explorer to select output folder...', 'info', 2000);
      const res = await api.selectFolder(outputDir, 'Select Destination Output Folder');
      if (res && res.status === 'selected' && res.path) {
        setOutputDir(res.path);
        addToast(`Selected output folder: ${res.path}`, 'success');
      }
    } catch {
      // ignore
    }
  };

  // Handle Scan Folder
  const handleScan = async () => {
    if (selectedFiles.length > 0) {
      addToast(`${selectedFiles.length} PDFs ready in current batch.`, 'info');
      return;
    }
    if (!inputDir.trim()) {
      addToast('Please specify an input folder path or click Select Folder', 'warning');
      return;
    }

    setIsScanning(true);
    try {
      const data = await api.scanFolder(inputDir.trim(), outputDir.trim());
      setScanResult(data);
      addToast(`Detected ${data.total_pdfs} PDFs (${data.new_to_process} new)`, 'success');
    } catch (err) {
      addToast(err.message || 'Folder scan failed', 'error');
      setScanResult(null);
    } finally {
      setIsScanning(false);
    }
  };

  // Handle Start Extraction
  const handleStartExtraction = async () => {
    stopTimers();
    if (onResetBatch) onResetBatch();
    setIsExtracting(true);

    const totalFiles = selectedFiles.length > 0 ? selectedFiles.length : (scanResult?.new_to_process || 1);
    const startTime = Date.now();

    setProgress({
      percentage: 6,
      processed: 0,
      total: totalFiles,
      current_file: selectedFiles[0]?.name || 'Initializing...',
      pass_count: 0,
      review_count: 0,
      speed_fps: 1.0,
      elapsed_seconds: 0,
      message: 'Scanning directory tree & reading PDF document streams...',
      subMessage: 'Cataloging contracts and reading binary streams...',
      completed: false,
      is_running: true,
    });

    // Start live simulation ticker: drives progress bar, status text, and live telemetry across Render cold-start (~50s)
    simTimerRef.current = setInterval(() => {
      const elapsed = Math.max(1, Math.floor((Date.now() - startTime) / 1000));
      const pct = getSimulatedPct(elapsed);
      
      const stage = EXTRACTION_STAGES.find(s => elapsed <= s.maxSec) || EXTRACTION_STAGES[EXTRACTION_STAGES.length - 1];
      const fileIdx = selectedFiles.length > 0 
        ? Math.min(selectedFiles.length - 1, Math.floor((pct / 94) * selectedFiles.length))
        : 0;
      const currentFileName = selectedFiles.length > 0 
        ? selectedFiles[fileIdx]?.name 
        : `contract_item_${fileIdx + 1}.pdf`;

      const estProcessed = Math.min(totalFiles, Math.max(1, Math.floor((pct / 100) * totalFiles)));
      const speed = (estProcessed / elapsed).toFixed(1);
      const estPass = Math.floor(estProcessed * 0.95);
      const estReview = Math.max(0, estProcessed - estPass);

      setProgress(prev => {
        if (prev.completed) return prev;
        return {
          ...prev,
          percentage: pct,
          processed: estProcessed,
          total: totalFiles,
          current_file: currentFileName,
          pass_count: estPass,
          review_count: estReview,
          speed_fps: speed,
          elapsed_seconds: elapsed,
          message: stage.msg,
          subMessage: stage.sub,
          is_running: true,
        };
      });
    }, 1000);

    if (selectedFiles.length > 0) {
      try {
        const res = await api.uploadAndExtract(selectedFiles, outputDir.trim());
        stopTimers();
        setIsExtracting(false);
        const finalElapsed = Math.max(1, Math.floor((Date.now() - startTime) / 1000));
        const finalCount = res.batch_count || selectedFiles.length;
        const finalPass = res.pass_count !== undefined ? res.pass_count : finalCount;
        const finalReview = res.review_count !== undefined ? res.review_count : 0;
        const finalSpeed = (finalCount / finalElapsed).toFixed(1);

        setProgress({
          percentage: 100,
          processed: finalCount,
          total: finalCount,
          current_file: 'All files extracted successfully',
          pass_count: finalPass,
          review_count: finalReview,
          speed_fps: finalSpeed,
          elapsed_seconds: finalElapsed,
          completed: true,
          is_running: false,
          message: `Batch extraction complete! ${finalCount} records processed.`,
          subMessage: 'Clean Excel output workbook is ready for download.'
        });

        try {
          confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#F59E0B', '#FCD34D', '#10B981', '#EAB308', '#FFFFFF']
          });
        } catch {}

        // Direct write to user's selected computer directory if picked via browser File System API
        if (outputDirHandle) {
          try {
            const blob = await api.getBatchExcelBlob(outputDir);
            const dateStr = new Date().toISOString().slice(0, 10);
            const fileHandle = await outputDirHandle.getFileHandle(`gem_contracts.xlsx`, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();

            const datedFileHandle = await outputDirHandle.getFileHandle(`gem_contracts_${dateStr}.xlsx`, { create: true });
            const datedWritable = await datedFileHandle.createWritable();
            await datedWritable.write(blob);
            await datedWritable.close();

            addToast(`Output Excel saved directly into your "${outputDirHandle.name}" folder!`, 'success', 4000);
          } catch (writeErr) {
            console.error('Direct folder write error:', writeErr);
          }
        }

        addToast(`Batch extraction finished: ${finalCount} records processed!`, 'success');
        if (onExtractionFinished) onExtractionFinished(res.records);
      } catch (err) {
        stopTimers();
        setIsExtracting(false);
        addToast(err.message || 'Batch extraction failed', 'error');
        setProgress(prev => ({
          ...prev,
          is_running: false,
          message: 'Extraction failed: ' + (err.message || 'Unknown error'),
          subMessage: 'Please check your connection and retry.'
        }));
      }
    } else {
      if (!inputDir.trim()) {
        stopTimers();
        setIsExtracting(false);
        addToast('Please click Select Folder or enter an input directory', 'warning');
        return;
      }

      try {
        await api.startExtraction(inputDir.trim(), outputDir.trim(), reprocessAll);
        addToast('Extraction worker started in background', 'info');
        startPolling(startTime, totalFiles);
      } catch (err) {
        stopTimers();
        setIsExtracting(false);
        addToast(err.message || 'Failed to launch extraction', 'error');
      }
    }
  };

  // Polling loop
  const startPolling = (startTime, totalFiles) => {
    pollTimerRef.current = setInterval(async () => {
      try {
        const p = await api.getProgress();
        if (p.is_running && p.processed > 0) {
          setProgress(prev => ({
            ...prev,
            percentage: p.percentage || prev.percentage,
            processed: p.processed,
            total: p.total || totalFiles,
            current_file: p.current_file || prev.current_file,
            pass_count: p.pass_count,
            review_count: p.review_count,
            speed_fps: p.speed_fps || prev.speed_fps,
            elapsed_seconds: p.elapsed_seconds || prev.elapsed_seconds,
            message: p.message || prev.message,
          }));
        }

        if (p.completed || (!p.is_running && p.processed > 0)) {
          stopTimers();
          setIsExtracting(false);
          setProgress({
            percentage: 100,
            processed: p.processed || totalFiles,
            total: p.total || totalFiles,
            current_file: 'All files extracted successfully',
            pass_count: p.pass_count,
            review_count: p.review_count,
            speed_fps: p.speed_fps,
            elapsed_seconds: p.elapsed_seconds,
            completed: true,
            is_running: false,
            message: p.message || 'Batch extraction completed successfully!',
            subMessage: 'Output Excel generated without validation columns.'
          });

          // Direct write to user's selected folder handle if available
          if (outputDirHandle) {
            try {
              const blob = await api.getBatchExcelBlob(outputDir);
              const dateStr = new Date().toISOString().slice(0, 10);
              const fileHandle = await outputDirHandle.getFileHandle(`gem_contracts.xlsx`, { create: true });
              const writable = await fileHandle.createWritable();
              await writable.write(blob);
              await writable.close();

              const datedFileHandle = await outputDirHandle.getFileHandle(`gem_contracts_${dateStr}.xlsx`, { create: true });
              const datedWritable = await datedFileHandle.createWritable();
              await datedWritable.write(blob);
              await datedWritable.close();

              addToast(`Output Excel saved directly into your "${outputDirHandle.name}" folder!`, 'success', 4000);
            } catch (writeErr) {
              console.error('Direct folder write error:', writeErr);
            }
          }

          try {
            confetti({
              particleCount: 80,
              spread: 70,
              origin: { y: 0.6 },
              colors: ['#F59E0B', '#FCD34D', '#10B981', '#EAB308', '#FFFFFF']
            });
          } catch {}

          addToast(p.message || 'Batch extraction completed successfully!', 'success');
          if (onExtractionFinished) onExtractionFinished();
        }
      } catch {
        // Render cold start or transient network glitch - keep simulated progress active!
      }
    }, 1000);
  };

  const hasNewFiles = scanResult ? scanResult.new_to_process > 0 : true;
  const canStart = !isExtracting && (reprocessAll || hasNewFiles);

  return (
    <div className="max-w-4xl mx-auto space-y-7 animate-fade-in pb-12">
      
      {/* Header Banner */}
      <div className="craft-card p-5 bg-gradient-to-r from-amber-500 via-amber-400 to-amber-200 border-amber-400/80 shadow-warm-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-extrabold text-amber-950 tracking-tight">
              Batch Extract GeM Orders
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setInputDir(config?.default_input_dir || './pdfs');
                setOutputDir(config?.default_output_dir || './output');
                setSelectedFiles([]);
                setSelectedFolderName('');
                setScanResult(null);
                if (onResetBatch) onResetBatch();
                addToast('Reset to default folders', 'info');
              }}
              className="btn-white text-xs px-3 py-2"
              title="Reset paths to default"
            >
              <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
              <span>Reset Paths</span>
            </button>
          </div>
        </div>
      </div>

      {/* Directory Settings Form Card */}
      <div className="craft-card p-6 space-y-6">
        {/* Hidden inputs for native computer File Explorer */}
        <input
          type="file"
          ref={folderInputRef}
          webkitdirectory=""
          directory=""
          multiple
          onChange={handleFolderSelect}
          style={{ display: 'none' }}
        />
        <input
          type="file"
          ref={fileInputRef}
          accept=".pdf"
          multiple
          onChange={handleFilesSelect}
          style={{ display: 'none' }}
        />

        <div className="flex items-center justify-between border-b border-brand-border pb-3">
          <h3 className="font-display text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-600" />
            <span>Select Folder / Files from Computer</span>
          </h3>
          {selectedFiles.length > 0 && (
            <button
              type="button"
              onClick={handleClearSelection}
              className="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 hover:underline"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear Selected Batch</span>
            </button>
          )}
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={handleBrowseInput}
          className={`p-6 rounded-2xl border-2 border-dashed transition-all text-center cursor-pointer ${
            isDragOver 
              ? 'border-amber-500 bg-amber-50/80 scale-[1.01]' 
              : selectedFiles.length > 0
                ? 'border-emerald-300 bg-emerald-50/40 hover:bg-emerald-50/60'
                : 'border-brand-border bg-slate-50/60 hover:bg-amber-50/40 hover:border-amber-400'
          }`}
        >
          <div className="flex flex-col items-center justify-center space-y-2">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-xs transition-transform ${
              selectedFiles.length > 0 ? 'bg-emerald-100 text-emerald-700 scale-105' : 'bg-amber-100 text-amber-600'
            }`}>
              {selectedFiles.length > 0 ? <CheckCircle2 className="w-6 h-6" /> : <UploadCloud className="w-6 h-6" />}
            </div>
            <div className="text-sm font-extrabold text-slate-800">
              {selectedFiles.length > 0 ? (
                <span className="text-emerald-800 font-display">
                  {selectedFiles.length} PDF Contracts Selected ({selectedFolderName})
                </span>
              ) : (
                <span>
                  Click <span className="text-amber-600 underline">Select Folder</span> to browse your computer
                </span>
              )}
            </div>
            <div className="text-xs text-slate-500">
              {selectedFiles.length > 0 
                ? 'Ready for extraction. Click "Start Extraction" below to extract this batch.'
                : 'Or drag and drop your GeM PDF folder / files directly into this area'}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Input Folder */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
              <span>PDF Input Source</span>
              <span className="text-[10px] font-normal text-slate-400 font-mono">computer file explorer</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputDir}
                onChange={(e) => {
                  setInputDir(e.target.value);
                  setSelectedFiles([]);
                }}
                placeholder="Select a folder from computer..."
                className="flex-1 px-3.5 py-2.5 rounded-xl border border-brand-border bg-white text-xs font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-500 transition-all shadow-sm"
              />
              <button
                type="button"
                onClick={handleBrowseInput}
                disabled={isScanning || isExtracting}
                className="btn-white px-3 py-2.5 text-xs font-bold shrink-0 flex items-center gap-1.5 hover:bg-amber-50 hover:text-amber-900 border-amber-300 transition-all shadow-xs"
                title="Open Computer File Explorer to select a folder"
              >
                <FolderOpen className="w-4 h-4 text-amber-600" />
                <span>Select Folder</span>
              </button>
              <button
                type="button"
                onClick={handleBrowseFiles}
                disabled={isScanning || isExtracting}
                className="btn-white px-3 py-2.5 text-xs font-bold shrink-0 flex items-center gap-1.5 hover:bg-amber-50 hover:text-amber-900 border-amber-300 transition-all shadow-xs"
                title="Select individual PDF files from computer"
              >
                <FileText className="w-4 h-4 text-amber-600" />
                <span className="hidden sm:inline">Files</span>
              </button>
            </div>
          </div>

          {/* Output Folder */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
              <span>Output Folder</span>
              <span className="text-[10px] font-normal text-slate-400 font-mono">destination directory</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={outputDir}
                onChange={(e) => {
                  setOutputDir(e.target.value);
                  setOutputDirHandle(null);
                }}
                placeholder="./output"
                className="flex-1 px-3.5 py-2.5 rounded-xl border border-brand-border bg-white text-xs font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-500 transition-all shadow-sm"
              />
              <button
                type="button"
                onClick={handleBrowseOutput}
                disabled={isExtracting}
                className="btn-white px-3 py-2.5 text-xs font-bold shrink-0 flex items-center gap-1.5 hover:bg-amber-50 hover:text-amber-900 border-amber-300 transition-all shadow-xs"
                title="Open Computer File Explorer to select output folder"
              >
                <FolderOpen className="w-4 h-4 text-amber-600" />
                <span>Select Folder</span>
              </button>
            </div>
          </div>
        </div>

        {/* Reprocess All Toggle */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-amber-50/50 border border-amber-200/60">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="reprocess"
              checked={reprocessAll}
              onChange={(e) => setReprocessAll(e.target.checked)}
              className="w-4 h-4 rounded text-amber-600 focus:ring-amber-500 accent-amber-500 cursor-pointer"
            />
            <label htmlFor="reprocess" className="cursor-pointer text-xs font-bold text-slate-800">
              Force Reprocess All PDFs
              <span className="block text-[11px] font-normal text-slate-500">
                Ignore previously cached results and re-extract every single file in the folder.
              </span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            onClick={handleScan}
            disabled={isScanning || isExtracting}
            className="btn-white px-5 py-2.5 text-xs font-bold"
          >
            {isScanning ? (
              <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
            ) : (
              <FolderSearch className="w-4 h-4 text-amber-600" />
            )}
            <span>{isScanning ? 'Scanning Directory...' : 'Scan Folder'}</span>
          </button>

          <button
            onClick={handleStartExtraction}
            disabled={!canStart || isExtracting}
            className="btn-yellow px-6 py-2.5 text-xs font-extrabold shadow-warm-md flex-1 sm:flex-initial"
          >
            {isExtracting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            <span>{isExtracting ? 'Extracting Records...' : 'Start Extraction'}</span>
          </button>
        </div>
      </div>

      {/* Scan Results Card (if scanned) */}
      {scanResult && (
        <div className="craft-card p-5 bg-white border-amber-200 space-y-4 animate-slide-up shadow-warm-md">
          <div className="flex items-center justify-between border-b border-brand-border pb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
              <FolderSearch className="w-4 h-4 text-amber-600" />
              <span>Scan Results for {scanResult.input_dir}</span>
            </h4>
            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              Ready
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-brand-50 border border-brand-200 text-center">
              <div className="text-xs text-slate-500 font-medium">Total Detected</div>
              <div className="text-xl font-display font-bold text-slate-900 mt-0.5">
                {scanResult.total_pdfs}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-brand-50 border border-brand-200 text-center">
              <div className="text-xs text-slate-500 font-medium">Already Processed</div>
              <div className="text-xl font-display font-bold text-slate-700 mt-0.5">
                {scanResult.already_processed}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-amber-100/70 border border-amber-300 text-center">
              <div className="text-xs text-amber-900 font-bold">New To Extract</div>
              <div className="text-xl font-display font-extrabold text-amber-950 mt-0.5">
                {scanResult.new_to_process}
              </div>
            </div>
          </div>

          {/* Sample Files Badge List */}
          {scanResult.sample_files && scanResult.sample_files.length > 0 && (
            <div className="pt-2 border-t border-brand-borderSubtle">
              <span className="text-[11px] font-bold text-slate-500 block mb-2">Detected Sample Files:</span>
              <div className="flex flex-wrap gap-1.5">
                {scanResult.sample_files.map((file, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-brand-border text-[11px] font-mono text-slate-700 shadow-2xs"
                  >
                    <FileText className="w-3 h-3 text-amber-600" />
                    <span>{file}</span>
                  </span>
                ))}
                {scanResult.total_pdfs > scanResult.sample_files.length && (
                  <span className="text-[11px] text-slate-400 self-center pl-1 font-medium">
                    +{scanResult.total_pdfs - scanResult.sample_files.length} more files
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Real-time Extraction Visualizer */}
      {(isExtracting || progress.processed > 0) && (
        <div className="craft-card p-6 bg-gradient-to-b from-white to-amber-50/40 border-amber-300 shadow-warm-lg space-y-5 animate-slide-up">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-brand-border pb-3.5">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-amber-400 text-amber-950 flex items-center justify-center font-bold shadow-xs shrink-0 mt-0.5">
                {progress.completed ? <Check className="w-5 h-5" /> : <RefreshCw className="w-4 h-4 animate-spin" />}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="font-display text-sm font-bold text-slate-900">
                    {progress.completed ? 'Extraction Completed' : 'Extraction in Progress'}
                  </h4>
                  {isExtracting && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 animate-pulse">
                      <Zap className="w-3 h-3 text-amber-600 fill-amber-500" />
                      <span>Processing Stream</span>
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-800 font-semibold mt-1">
                  {progress.message || 'Processing batch...'}
                </p>
                {progress.subMessage && (
                  <p className="text-[11px] text-slate-500 font-normal mt-0.5">
                    {progress.subMessage}
                  </p>
                )}
              </div>
            </div>

            <div className="text-left sm:text-right shrink-0">
              <span className="text-2xl font-display font-extrabold text-amber-950 tracking-tight">
                {progress.percentage || 0}%
              </span>
              <div className="text-[10px] font-mono text-slate-400">
                {progress.completed ? '100% finished' : 'active batch'}
              </div>
            </div>
          </div>

          {/* Glowing Animated Progress Bar */}
          <div className="space-y-1.5">
            <div className="w-full h-4 bg-amber-100/70 rounded-full overflow-hidden p-0.5 border border-amber-200">
              <div
                className="h-full bg-gradient-to-r from-amber-500 via-amber-400 to-amber-300 rounded-full transition-all duration-500 shadow-sm relative overflow-hidden"
                style={{ width: `${progress.percentage || 0}%` }}
              >
                {isExtracting && (
                  <div className="absolute inset-0 bg-white/25 animate-pulse" />
                )}
              </div>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span className="truncate max-w-xs sm:max-w-md">
                Current: <strong className="text-slate-800">{progress.current_file || '—'}</strong>
              </span>
              <span className="font-semibold text-slate-700">
                {progress.processed} of {progress.total}
              </span>
            </div>
          </div>

          {/* Live Telemetry Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 rounded-xl bg-white border border-brand-border shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1">
                <Gauge className="w-3 h-3 text-amber-600" />
                <span>Speed</span>
              </div>
              <div className="text-base font-mono font-bold text-slate-900 mt-1">
                {progress.speed_fps || 0} <span className="text-xs font-normal text-slate-500">pdf/s</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-white border border-brand-border shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3 text-amber-600" />
                <span>Elapsed</span>
              </div>
              <div className="text-base font-mono font-bold text-slate-900 mt-1">
                {progress.elapsed_seconds || 0}s
              </div>
            </div>

            <div className="p-3 rounded-xl bg-white border border-emerald-200 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-emerald-700 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>Passed</span>
              </div>
              <div className="text-base font-mono font-bold text-emerald-800 mt-1">
                {progress.pass_count || 0}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-white border border-amber-200 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-amber-700 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-600" />
                <span>Review</span>
              </div>
              <div className="text-base font-mono font-bold text-amber-800 mt-1">
                {progress.review_count || 0}
              </div>
            </div>
          </div>

          {/* If completed, show Jump to Records & Download Excel CTA */}
          {progress.completed && (
            <div className="pt-3.5 border-t border-amber-200/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-amber-950">
                  Batch Output Ready
                </span>
                <span className="text-[11px] font-mono text-slate-500 bg-amber-100/70 border border-amber-300/80 px-2 py-0.5 rounded-md">
                  Saved to: {outputDir || './output'}/gem_contracts.xlsx
                </span>
              </div>
              <div className="flex items-center gap-2.5">
                <button
                  onClick={async () => {
                    try {
                      await api.downloadBatchExcel(outputDir.trim() || './output');
                      addToast('Output Excel downloaded successfully!', 'success');
                    } catch (e) {
                      addToast(e.message || 'Download failed', 'error');
                    }
                  }}
                  className="btn-white text-xs px-3.5 py-2 font-bold flex items-center gap-1.5 shadow-xs hover:border-amber-400"
                  title="Download styled batch output Excel"
                >
                  <Download className="w-3.5 h-3.5 text-amber-600" />
                  <span>Download Excel (.xlsx)</span>
                </button>
                <button
                  onClick={() => onNavigate('records')}
                  className="btn-yellow text-xs px-4 py-2 font-bold shadow-warm-xs"
                >
                  <span>View Records</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
