import React, { useState } from 'react';
import { UploadCloud, FileJson, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import api from '../api';

export default function DeployCard({ onSuccess }) {
  const [modelFile, setModelFile] = useState(null);
  const [configFile, setConfigFile] = useState(null);
  const [status, setStatus] = useState(null); // { type, text }
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.json')) {
        setConfigFile(file);
      } else {
        setModelFile(file);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!modelFile || !configFile) {
      setStatus({ type: 'error', text: 'Select BOTH Model (.pkl, .onnx, .pt) and Config (.json)' });
      return;
    }

    setLoading(true);
    setStatus({ type: 'info', text: 'Compiling + Containerizing...' });

    const formData = new FormData();
    formData.append('model_file', modelFile);
    formData.append('config_file', configFile);

    try {
      const { data } = await api.post('/deploy-model', formData);
      setStatus({ type: 'success', text: `Deployed: ${data.container_id}` });
      if (onSuccess) onSuccess();
      setModelFile(null);
      setConfigFile(null);
    } catch (err) {
      setStatus({ type: 'error', text: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col h-full hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center">
          <UploadCloud className="w-5 h-5 mr-2 text-blue-600" />
          Deploy New Model
        </h2>
        <span className="text-xs font-semibold px-2 py-1 bg-blue-50 text-blue-700 rounded-md uppercase tracking-wider">Drag & Drop</span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 flex-1 flex flex-col justify-between">
        <div 
          className="grid grid-cols-1 sm:grid-cols-2 gap-4 h-full"
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <label className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 block h-full min-h-[160px]
            ${dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400 bg-slate-50 hover:bg-slate-100/50'}`}
          >
            <UploadCloud className={`w-8 h-8 mb-3 transition-colors ${modelFile ? 'text-blue-600' : 'text-slate-400 group-hover:text-blue-500'}`} />
            <span className="text-sm font-semibold uppercase text-slate-700 mb-1">Model Artifact</span>
            <span className="text-xs text-slate-500">{modelFile ? modelFile.name : '.pkl, .onnx, .pt'}</span>
            <input 
              type="file" 
              className="opacity-0 absolute inset-0 cursor-pointer" 
              onChange={(e) => setModelFile(e.target.files[0])}
            />
            {modelFile && <div className="absolute top-2 right-2 bg-green-100 text-green-700 rounded-full p-1"><CheckCircle className="w-4 h-4" /></div>}
          </label>

          <label className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 block h-full min-h-[160px]
            ${dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400 bg-slate-50 hover:bg-slate-100/50'}`}
          >
            <FileJson className={`w-8 h-8 mb-3 transition-colors ${configFile ? 'text-blue-600' : 'text-slate-400 group-hover:text-blue-500'}`} />
            <span className="text-sm font-semibold uppercase text-slate-700 mb-1">Config JSON</span>
            <span className="text-xs text-slate-500">{configFile ? configFile.name : 'Select or drop .json'}</span>
            <input 
              type="file" 
              accept=".json"
              className="opacity-0 absolute inset-0 cursor-pointer" 
              onChange={(e) => setConfigFile(e.target.files[0])}
            />
            {configFile && <div className="absolute top-2 right-2 bg-green-100 text-green-700 rounded-full p-1"><CheckCircle className="w-4 h-4" /></div>}
          </label>
        </div>

        {status && (
          <div className={`p-4 rounded-lg border text-sm font-medium flex items-center space-x-3
            ${status.type === 'error' ? 'bg-red-50 border-red-200 text-red-700' : ''}
            ${status.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : ''}
            ${status.type === 'info' ? 'bg-blue-50 border-blue-200 text-blue-700' : ''}
          `}>
            {status.type === 'error' && <AlertCircle className="w-5 h-5 shrink-0" />}
            {status.type === 'success' && <CheckCircle className="w-5 h-5 shrink-0" />}
            {status.type === 'info' && <Loader2 className="w-5 h-5 shrink-0 animate-spin" />}
            <span>{status.text}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !modelFile || !configFile}
          className="w-full py-3 bg-blue-600 border border-transparent text-white font-bold rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {loading ? 'Processing...' : 'Deploy Model'}
        </button>
      </form>
    </div>
  );
}
