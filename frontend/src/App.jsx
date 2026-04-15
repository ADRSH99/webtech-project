import React, { useState, useEffect } from 'react';
import api from './api';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import StatCard from './components/StatCard';
import DeployCard from './components/DeployCard';
import DeploymentItem from './components/DeploymentItem';
import LogsPanel from './components/LogsPanel';
import ModelsPanel from './components/ModelsPanel';
import SettingsPanel from './components/SettingsPanel';
import { Activity, Server, AlertCircle, LogIn, RefreshCw } from 'lucide-react';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('mf_token'));
  const [authMode, setAuthMode] = useState('login');
  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  const [activeTab, setActiveTab] = useState('dashboard');
  const [deployments, setDeployments] = useState([]);
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState(null);
  const [activeContainerId, setActiveContainerId] = useState(null);
  const [selectedDeployment, setSelectedDeployment] = useState(null);
  const [modelSearchTerm, setModelSearchTerm] = useState('');
  const [selectedModelInternalId, setSelectedModelInternalId] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('mf_settings');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (err) {
        console.warn('Invalid settings payload, using defaults', err);
      }
    }
    return {
      displayName: localStorage.getItem('mf_user') || 'User',
      autoRefresh: true,
      refreshIntervalSec: 15,
      compactMode: false,
    };
  });

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      const endpoint = authMode === 'register' ? '/auth/register' : '/auth/login';
      const { data } = await api.post(endpoint, authForm);
      localStorage.setItem('mf_token', data.token);
      localStorage.setItem('mf_user', data.username);
      setToken(data.token);
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
  };

  const updateSettings = (partial) => {
    setSettings((prev) => {
      const next = { ...prev, ...partial };
      localStorage.setItem('mf_settings', JSON.stringify(next));
      return next;
    });
  };

  const clearLocalPreferences = () => {
    localStorage.removeItem('mf_settings');
    setSettings({
      displayName: localStorage.getItem('mf_user') || 'User',
      autoRefresh: true,
      refreshIntervalSec: 15,
      compactMode: false,
    });
  };

  const runDiagnostics = async () => {
    const checkedAt = new Date().toLocaleTimeString([], { hour12: false });
    try {
      const { data } = await api.get('/health');
      setDiagnostics({
        apiOk: true,
        dockerOk: !!data?.docker_available,
        checkedAt,
      });
    } catch (err) {
      setDiagnostics({
        apiOk: false,
        dockerOk: false,
        checkedAt,
      });
    }
  };

  const fetchDeployments = async () => {
    if (!token) return;
    try {
      const { data } = await api.get('/containers');
      setDeployments(data);
      if (selectedDeployment) {
        const selectedId = selectedDeployment.container_id || selectedDeployment.id;
        const refreshedSelection = data.find((dep) => (dep.container_id || dep.id) === selectedId) || null;
        setSelectedDeployment(refreshedSelection);
      }
    } catch (err) {
      console.error('Failed to fetch deployments', err);
      if (err.response?.status === 401) handleLogout();
    }
  };

  const fetchModels = async () => {
    if (!token) return;
    setModelsLoading(true);
    try {
      const { data } = await api.get('/models');
      setModels(data.models || []);
    } catch (err) {
      console.error('Failed to fetch models', err);
    } finally {
      setModelsLoading(false);
    }
  };

  const handleRerunFromModel = async (model) => {
    try {
      const { data } = await api.post(`/containers/${model.container_id || model.internal_id}/rerun`);
      await fetchDeployments();
      await fetchModels();
      setActiveContainerId(data.container_id);
      setSelectedDeployment({
        container_id: data.container_id,
        internal_id: data.internal_id,
        model_name: model.model_name,
        url: data.url,
        status: 'running'
      });
      setActiveTab('dashboard');
    } catch (err) {
      console.error('Failed to rerun model', err);
      alert(err.response?.data?.detail || 'Failed to rerun model');
    }
  };

  const handleDeployNewFromModel = async (model) => {
    try {
      const { data } = await api.post(`/models/${model.internal_id}/deploy`);
      await fetchDeployments();
      await fetchModels();
      setActiveContainerId(data.container_id);
      setSelectedDeployment({
        container_id: data.container_id,
        internal_id: data.internal_id,
        model_name: model.model_name,
        url: data.url,
        status: 'running'
      });
      setActiveTab('dashboard');
    } catch (err) {
      console.error('Failed to create deployment from model', err);
      alert(err.response?.data?.detail || 'Failed to create deployment from model');
    }
  };

  const handleRerunFromDeployment = async (rerunResult, originalDeployment) => {
    await fetchDeployments();
    await fetchModels();

    const rerunContainerId = rerunResult?.container_id;
    const rerunUrl = rerunResult?.url;

    if (rerunContainerId) {
      setActiveContainerId(rerunContainerId);
      setSelectedDeployment({
        container_id: rerunContainerId,
        internal_id: rerunResult?.internal_id || originalDeployment?.internal_id,
        model_name: originalDeployment?.model_name,
        url: rerunUrl,
        status: 'running',
      });
    }
  };

  const checkHealth = async () => {
    try {
      const { data } = await api.get('/health');
      setHealthStatus(data);
    } catch (err) {
      setHealthStatus({ status: 'offline', docker_available: false });
    }
  };

  useEffect(() => {
    if (token) {
      fetchDeployments();
      fetchModels();
      checkHealth();
      if (settings.autoRefresh) {
        const interval = setInterval(fetchDeployments, settings.refreshIntervalSec * 1000);
        return () => clearInterval(interval);
      }
    }
  }, [token, settings.autoRefresh, settings.refreshIntervalSec]);

  useEffect(() => {
    if (token && activeTab === 'models') {
      fetchModels();
    }
  }, [activeTab, token]);

  const normalizedSearch = modelSearchTerm.trim().toLowerCase();
  const prefixMatches = normalizedSearch
    ? models
        .filter((m) => (m.model_name || '').toLowerCase().startsWith(normalizedSearch))
        .slice(0, 8)
    : [];

  const jumpToModel = (model) => {
    if (!model) return;
    setActiveTab('models');
    setSelectedModelInternalId(model.internal_id);
    setModelSearchTerm(model.model_name || '');
  };

  const handleSearchSubmit = () => {
    if (prefixMatches.length > 0) {
      jumpToModel(prefixMatches[0]);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4 font-sans">
        <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
          <div className="text-center mb-8">
            <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Server className="text-white w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">ModelForge</h1>
            <p className="text-slate-500 text-sm mt-1">Sign in to continue</p>
          </div>
          <div className="flex bg-slate-100 p-1 rounded-lg mb-6">
            <button onClick={() => { setAuthMode('login'); setAuthError(null); }} className={`flex-1 py-1.5 text-sm font-medium rounded-md ${authMode === 'login' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}>Login</button>
            <button onClick={() => { setAuthMode('register'); setAuthError(null); }} className={`flex-1 py-1.5 text-sm font-medium rounded-md ${authMode === 'register' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}>Register</button>
          </div>
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-slate-700 text-sm font-medium mb-1">Username</label>
              <input type="text" required value={authForm.username} onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-slate-700 text-sm font-medium mb-1">Password</label>
              <input type="password" required value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            {authError && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg flex items-center"><AlertCircle className="w-4 h-4 mr-2"/>{authError}</div>}
            <button type="submit" disabled={authLoading} className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center disabled:opacity-50">
              {authLoading ? <RefreshCw className="animate-spin w-4 h-4 mr-2" /> : <LogIn className="w-4 h-4 mr-2" />}
              {authMode === 'register' ? 'Create Account' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const dockerRunning = healthStatus?.docker_available || false;
  const runningCount = deployments.filter(d => d.status === 'running' || d.state === 'running').length;
  const errorCount = deployments.filter(d => d.status === 'exited' || d.state === 'exited').length;

  const showDashboard = activeTab === 'dashboard';

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans flex">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 ml-64 flex flex-col min-h-screen">
        <Topbar
          title={activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
          dockerRunning={dockerRunning}
          displayName={settings.displayName || localStorage.getItem('mf_user') || 'User'}
          searchTerm={modelSearchTerm}
          onSearchChange={setModelSearchTerm}
          searchSuggestions={prefixMatches}
          onSelectSuggestion={jumpToModel}
          onSearchSubmit={handleSearchSubmit}
        />
        <div className={`p-8 pb-16 flex-1 overflow-y-auto max-w-7xl mx-auto w-full ${settings.compactMode ? 'space-y-5' : 'space-y-8'}`}>
          {activeTab !== 'settings' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatCard label="Models Running" value={runningCount.toString()} icon={Activity} colorClass="bg-green-100 text-green-600" />
              <StatCard label="Total Deployments" value={deployments.length.toString()} icon={Server} colorClass="bg-blue-100 text-blue-600" />
              <StatCard label="Errors" value={errorCount.toString()} icon={AlertCircle} colorClass="bg-red-100 text-red-600" />
            </div>
          )}

          {activeTab === 'models' && (
            <ModelsPanel
              models={models}
              loading={modelsLoading}
              onRefresh={fetchModels}
              onRerun={handleRerunFromModel}
              onDeployNew={handleDeployNewFromModel}
              selectedModelInternalId={selectedModelInternalId}
              onSelectModel={setSelectedModelInternalId}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsPanel
              settings={settings}
              onSettingsChange={updateSettings}
              username={localStorage.getItem('mf_user') || 'User'}
              diagnostics={diagnostics}
              onRunDiagnostics={runDiagnostics}
              onLogout={handleLogout}
              onClearLocalData={clearLocalPreferences}
            />
          )}

          {showDashboard && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            <div className="xl:col-span-1 min-h-[460px]">
              <DeployCard onSuccess={async () => { await fetchDeployments(); await fetchModels(); }} />
            </div>
            <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col min-h-[460px]">
              <div className="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center"><Server className="w-5 h-5 mr-2 text-blue-600" /> Active Deployments</h2>
                <span className="text-xs font-semibold px-2 py-1 bg-slate-100 text-slate-600 rounded-md">{deployments.length}</span>
              </div>
              <div className="flex-1 space-y-4 overflow-y-auto pr-2">
                {deployments.length === 0 ? (
                  <div className="h-full flex flex-col justify-center items-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl p-8 bg-slate-50">
                    <Server className="w-12 h-12 mb-4 opacity-50" />
                    <p className="font-medium text-lg text-slate-600">No deployments yet</p>
                  </div>
                ) : (
                  deployments.map(dep => {
                    const depKey = dep.container_id || dep.id;
                    return (
                    <div key={depKey} onClick={() => setActiveContainerId(dep.container_id || dep.id)} className={`cursor-pointer rounded-xl transition-all ${activeContainerId === (dep.container_id || dep.id) ? 'ring-2 ring-blue-500 shadow-md transform scale-[1.01]' : 'hover:shadow-md'}`}>
                      <DeploymentItem
                        deployment={dep}
                        onUpdate={fetchDeployments}
                        onOpenModel={setSelectedDeployment}
                        onRerun={handleRerunFromDeployment}
                      />
                    </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
          )}

          {showDashboard && (
          <div className="w-full xl:col-span-3">
             <LogsPanel activeContainerId={activeContainerId} />
          </div>
          )}

          {showDashboard && selectedDeployment && (() => {
            const selectedId = selectedDeployment.container_id || selectedDeployment.id;
            const selected = deployments.find((d) => (d.container_id || d.id) === selectedId) || selectedDeployment;
            const port = selected?.host_port || selected?.port || selected?.ports?.[0]?.PublicPort || 7860;
            const iframeUrl = selected?.url || `http://localhost:${port}`;
            
            return (
              <div className="w-full bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="flex items-center justify-between p-6 bg-gradient-to-r from-blue-600 to-blue-700 text-white">
                  <div>
                    <h2 className="text-xl font-bold">Model Interface</h2>
                    <p className="text-blue-100 text-sm mt-1">{selected?.model_name || selected?.name || 'Deployed Model'}</p>
                    <p className="text-blue-200 text-xs mt-2 font-mono">{iframeUrl}</p>
                  </div>
                  <button
                    onClick={() => setSelectedDeployment(null)}
                    className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg font-medium transition-colors"
                  >
                    Close
                  </button>
                </div>
                <div className="relative bg-slate-50" style={{ height: '700px' }}>
                  <iframe
                    key={iframeUrl}
                    src={iframeUrl}
                    className="w-full h-full border-0"
                    title="Model Interface"
                    onError={() => console.error(`Failed to load iframe from ${iframeUrl}`)}
                  />
                </div>
              </div>
            );
          })()}
        </div>
      </main>
    </div>
  );
}
