import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Upload,
  RefreshCw,
  Trash2,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Activity,
  Clock,
  LogOut,
  LogIn,
  X
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const API_BASE = 'http://localhost:8000';

/* ── Axios helper that attaches the JWT token ── */
const authHeaders = () => {
  const token = localStorage.getItem('mf_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const App = () => {
  /* ── Auth state ── */
  const [token, setToken] = useState(localStorage.getItem('mf_token'));
  const [username, setUsername] = useState(localStorage.getItem('mf_user') || '');
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  /* ── App state ── */
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState(null);
  const [selectedModelUrl, setSelectedModelUrl] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  /* ── Auth handlers ── */
  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      const endpoint = authMode === 'register' ? '/auth/register' : '/auth/login';
      const resp = await axios.post(`${API_BASE}${endpoint}`, authForm);
      const { token: jwt, username: user } = resp.data;
      localStorage.setItem('mf_token', jwt);
      localStorage.setItem('mf_user', user);
      setToken(jwt);
      setUsername(user);
      setAuthForm({ username: '', password: '' });
    } catch (err) {
      setAuthError(err.response?.data?.detail || err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('mf_token');
    localStorage.removeItem('mf_user');
    setToken(null);
    setUsername('');
    setSelectedModelUrl(null);
  };

  /* ── Data fetchers ── */
  const fetchDeployments = async () => {
    setRefreshing(true);
    try {
      const resp = await axios.get(`${API_BASE}/containers`);
      setDeployments(resp.data);
    } catch (err) {
      console.error('Failed to fetch deployments', err);
    } finally {
      setRefreshing(false);
    }
  };

  const checkHealth = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/health`);
      setHealthStatus(resp.data);
    } catch (err) {
      setHealthStatus({ status: 'offline', docker_available: false });
    }
  };

  useEffect(() => {
    fetchDeployments();
    checkHealth();
  }, []);

  /* ── Protected actions (use auth headers) ── */
  const handleDeploy = async (e) => {
    e.preventDefault();
    const modelFile = e.target.modelFile.files[0];
    const configFile = e.target.configFile.files[0];

    if (!modelFile || !configFile) {
      setMessage({ type: 'error', text: 'Please select both model and config files.' });
      return;
    }

    setLoading(true);
    setMessage({ type: 'info', text: 'Deploying model... This may take a minute.' });

    const formData = new FormData();
    formData.append('model_file', modelFile);
    formData.append('config_file', configFile);

    try {
      const resp = await axios.post(`${API_BASE}/deploy-model`, formData, {
        headers: authHeaders(),
      });
      setMessage({ type: 'success', text: `Deployed successfully! ID: ${resp.data.container_id}` });
      fetchDeployments();
      e.target.reset();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      setMessage({ type: 'error', text: `Deployment failed: ${errorMsg}` });
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async (containerId) => {
    if (!window.confirm(`Stop container ${containerId}?`)) return;
    try {
      await axios.delete(`${API_BASE}/containers/${containerId}`, {
        headers: authHeaders(),
      });
      fetchDeployments();
      if (selectedModelUrl?.includes(containerId)) setSelectedModelUrl(null);
    } catch (err) {
      alert('Failed to stop container');
    }
  };

  const handleStopAll = async () => {
    if (!window.confirm('Stop ALL containers?')) return;
    try {
      await axios.delete(`${API_BASE}/containers/cleanup-all`, {
        headers: authHeaders(),
      });
      fetchDeployments();
      setSelectedModelUrl(null);
    } catch (err) {
      alert('Failed to cleanup all');
    }
  };

  /* ── Login / Register screen ── */
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary-500/30">
              <Activity className="text-white w-8 h-8" />
            </div>
            <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">ModelForge</h1>
            <p className="text-slate-500 text-sm mt-1">ML Model Deployment Platform</p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 ring-1 ring-slate-900/5">
            <div className="flex rounded-xl bg-slate-100 p-1 mb-6">
              <button
                onClick={() => { setAuthMode('login'); setAuthError(null); }}
                className={cn(
                  "flex-1 py-2 text-sm font-semibold rounded-lg transition-all",
                  authMode === 'login'
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                )}
              >
                Login
              </button>
              <button
                onClick={() => { setAuthMode('register'); setAuthError(null); }}
                className={cn(
                  "flex-1 py-2 text-sm font-semibold rounded-lg transition-all",
                  authMode === 'register'
                    ? "bg-white text-slate-800 shadow-sm"
                    : "text-slate-500 hover:text-slate-700"
                )}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleAuth} className="space-y-4">
              <div>
                <label className="block text-slate-600 mb-1.5 text-sm font-medium">Username</label>
                <input
                  type="text"
                  value={authForm.username}
                  onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="Enter username"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1.5 text-sm font-medium">Password</label>
                <input
                  type="password"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="Enter password"
                  required
                />
              </div>

              {authError && (
                <div className="p-3 rounded-xl bg-red-50 text-red-700 text-sm flex items-center space-x-2 border border-red-100">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-xl font-bold transition-all shadow-lg shadow-primary-500/30 disabled:opacity-50 flex items-center justify-center"
              >
                {authLoading ? (
                  <RefreshCw className="animate-spin w-5 h-5 mr-2" />
                ) : (
                  <LogIn className="w-5 h-5 mr-2" />
                )}
                {authMode === 'register' ? 'Create Account' : 'Sign In'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  /* ── Main dashboard (authenticated) ── */
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Activity className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-800">ModelForge</h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className={cn(
              "flex items-center px-3 py-1 rounded-full text-xs font-medium border",
              healthStatus?.docker_available
                ? "bg-green-50 text-green-700 border-green-200"
                : "bg-red-50 text-red-700 border-red-200"
            )}>
              <span className={cn(
                "w-2 h-2 rounded-full mr-2",
                healthStatus?.docker_available ? "bg-green-500 animate-pulse" : "bg-red-500"
              )} />
              {healthStatus?.docker_available ? "Docker Connected" : "Docker Offline"}
            </div>
            <div className="flex items-center space-x-2 pl-4 border-l border-slate-200">
              <span className="text-sm text-slate-600 font-medium">{username}</span>
              <button
                onClick={handleLogout}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Sidebar / Forms */}
          <div className="space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 ring-1 ring-slate-900/5">
              <h2 className="text-lg font-semibold mb-4 flex items-center">
                <Upload className="w-5 h-5 mr-4 text-primary-600" />
                Deploy New Model
              </h2>
              <form onSubmit={handleDeploy} className="space-y-4 font-normal text-sm">
                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Model File (.pkl, .pt, .onnx)</label>
                  <input
                    name="modelFile"
                    type="file"
                    className="block w-full text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 transition-all border border-slate-200 p-1 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-600 mb-1 font-medium">Config File (config.json)</label>
                  <input
                    name="configFile"
                    type="file"
                    className="block w-full text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 transition-all border border-slate-200 p-1 rounded-lg"
                    required
                  />
                </div>
                <button
                  disabled={loading}
                  className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-xl font-bold transition-all shadow-lg shadow-primary-500/30 disabled:opacity-50 flex items-center justify-center"
                >
                  {loading ? <RefreshCw className="animate-spin w-5 h-5 mr-2" /> : <Upload className="w-5 h-5 mr-2" />}
                  {loading ? 'Deploying...' : 'Deploy to Container'}
                </button>
              </form>

              {message && (
                <div className={cn(
                  "mt-4 p-4 rounded-xl flex items-start space-x-3 text-sm",
                  message.type === 'error' ? "bg-red-50 text-red-700 border border-red-100" :
                    message.type === 'success' ? "bg-green-50 text-green-700 border border-green-100" :
                      "bg-blue-50 text-blue-700 border border-blue-100"
                )}>
                  {message.type === 'error' ? <AlertCircle className="w-5 h-5 flex-shrink-0" /> : <CheckCircle2 className="w-5 h-5 flex-shrink-0" />}
                  <span>{message.text}</span>
                </div>
              )}
            </section>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">Active Deployments</h2>
                  <p className="text-sm text-slate-500">Managed via SQLite & Docker</p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={fetchDeployments}
                    className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Refresh List"
                  >
                    <RefreshCw className={cn("w-5 h-5", refreshing && "animate-spin")} />
                  </button>
                  {deployments.length > 0 && (
                    <button
                      onClick={handleStopAll}
                      className="px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 text-sm font-semibold rounded-lg transition-colors border border-red-100"
                    >
                      Clear All
                    </button>
                  )}
                </div>
              </div>

              {deployments.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-slate-100 rounded-2xl">
                  <div className="bg-slate-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Activity className="text-slate-300 w-8 h-8" />
                  </div>
                  <h3 className="text-slate-900 font-semibold italic">No active deployments</h3>
                  <p className="text-slate-400 text-sm">Upload a model to get started</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {deployments.map((deployment) => (
                    <div
                      key={deployment.container_id}
                      className={cn(
                        "group p-4 rounded-xl border transition-all cursor-pointer",
                        selectedModelUrl === deployment.url
                          ? "border-primary-500 bg-primary-50/50 ring-1 ring-primary-500"
                          : "border-slate-200 hover:border-primary-300 hover:shadow-md"
                      )}
                      onClick={() => setSelectedModelUrl(deployment.url)}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="bg-white w-10 h-10 rounded-lg border border-slate-100 shadow-sm flex items-center justify-center text-primary-600">
                          <Activity className="w-6 h-6" />
                        </div>
                        <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => { e.stopPropagation(); window.open(deployment.url, '_blank'); }}
                            className="p-1.5 text-slate-400 hover:text-primary-600"
                            title="Open in new tab"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStop(deployment.container_id); }}
                            className="p-1.5 text-slate-400 hover:text-red-600"
                            title="Remove"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <h4 className="font-bold text-slate-800 truncate" title={deployment.model_name}>
                        {deployment.model_name}
                      </h4>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 py-0.5 bg-slate-100 rounded">
                          {deployment.framework}
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary-600 px-2 py-0.5 bg-primary-50 rounded">
                          {deployment.task}
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-green-600 px-2 py-0.5 bg-green-50 rounded">
                          {deployment.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-3 text-[10px] text-slate-400 font-mono">
                        <span>ID: {deployment.container_id}</span>
                        {deployment.host_port && <span>Port: {deployment.host_port}</span>}
                      </div>
                      {deployment.created_at && (
                        <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(deployment.created_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Iframe Viewport */}
        {selectedModelUrl && (
          <section className="bg-white rounded-3xl shadow-2xl border border-primary-100 overflow-hidden ring-1 ring-slate-900/5">
            <div className="bg-primary-600 px-6 py-4 flex items-center justify-between text-white">
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-bold">Interactive Interface</h2>
                  <p className="text-[10px] text-primary-100 font-medium tracking-wide">MODEL RUNNING IN ISOLATED DOCKER CONTAINER</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => window.open(selectedModelUrl, '_blank')}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  title="Full screen"
                >
                  <ExternalLink className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setSelectedModelUrl(null)}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors border-l border-white/20 pl-4"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="bg-slate-50 flex items-center justify-center" style={{ height: '700px' }}>
              <iframe
                src={selectedModelUrl}
                className="w-full h-full border-0"
                title="Model Interface"
              />
            </div>
          </section>
        )}
      </main>

      <footer className="max-w-7xl mx-auto px-4 py-8 mt-8 border-t border-slate-200">
        <p className="text-center text-slate-400 text-sm">
          ModelForge • Web Technologies and Applications Project
        </p>
      </footer>
    </div>
  );
};

export default App;
