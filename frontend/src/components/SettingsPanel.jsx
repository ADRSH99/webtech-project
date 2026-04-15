import React, { useState } from 'react';
import { Save, Wrench, LogOut, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';

export default function SettingsPanel({
  settings,
  onSettingsChange,
  username,
  diagnostics,
  onRunDiagnostics,
  onLogout,
  onClearLocalData,
}) {
  const [displayNameDraft, setDisplayNameDraft] = useState(settings.displayName || username || 'User');

  const handleSaveProfile = () => {
    onSettingsChange({ displayName: displayNameDraft.trim() || username || 'User' });
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      <section className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-8">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Profile</h2>
          <p className="text-sm text-slate-500 mt-1">Manage your basic account preferences for this workspace.</p>
          <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
              <input
                type="text"
                value={username || 'User'}
                disabled
                className="w-full px-3 py-2 border border-slate-200 bg-slate-50 text-slate-500 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Display Name</label>
              <input
                type="text"
                value={displayNameDraft}
                onChange={(e) => setDisplayNameDraft(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            onClick={handleSaveProfile}
            className="mt-4 inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            <Save className="w-4 h-4 mr-2" />
            Save Profile
          </button>
        </div>

        <div className="border-t border-slate-100 pt-8">
          <h2 className="text-lg font-bold text-slate-900">Preferences</h2>
          <p className="text-sm text-slate-500 mt-1">Control deployment polling and dashboard density.</p>

          <div className="mt-5 space-y-4">
            <label className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
              <span>
                <span className="text-sm font-medium text-slate-800 block">Auto-refresh deployments</span>
                <span className="text-xs text-slate-500">Keep deployments and model statuses synced in the background.</span>
              </span>
              <input
                type="checkbox"
                checked={settings.autoRefresh}
                onChange={(e) => onSettingsChange({ autoRefresh: e.target.checked })}
                className="h-4 w-4"
              />
            </label>

            <div className="rounded-lg border border-slate-200 p-4">
              <label className="text-sm font-medium text-slate-800 block mb-2">Refresh interval</label>
              <select
                value={settings.refreshIntervalSec}
                onChange={(e) => onSettingsChange({ refreshIntervalSec: Number(e.target.value) })}
                className="w-full md:w-64 px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={!settings.autoRefresh}
              >
                <option value={5}>Every 5 seconds</option>
                <option value={10}>Every 10 seconds</option>
                <option value={15}>Every 15 seconds</option>
                <option value={30}>Every 30 seconds</option>
                <option value={60}>Every 60 seconds</option>
              </select>
            </div>

            <label className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
              <span>
                <span className="text-sm font-medium text-slate-800 block">Compact dashboard cards</span>
                <span className="text-xs text-slate-500">Reduce spacing in dashboard sections for denser monitoring.</span>
              </span>
              <input
                type="checkbox"
                checked={settings.compactMode}
                onChange={(e) => onSettingsChange({ compactMode: e.target.checked })}
                className="h-4 w-4"
              />
            </label>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6 h-fit">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Troubleshoot</h2>
          <p className="text-sm text-slate-500 mt-1">Run quick environment checks.</p>
          <button
            onClick={onRunDiagnostics}
            className="mt-4 inline-flex items-center px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium"
          >
            <Wrench className="w-4 h-4 mr-2" />
            Run Diagnostics
          </button>

          <div className="mt-4 rounded-lg border border-slate-200 p-4 bg-slate-50 text-sm text-slate-700 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">API Health</span>
              <span className={diagnostics?.apiOk ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                {diagnostics ? (diagnostics.apiOk ? 'OK' : 'Failed') : 'Not checked'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Docker</span>
              <span className={diagnostics?.dockerOk ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                {diagnostics ? (diagnostics.dockerOk ? 'Running' : 'Unavailable') : 'Not checked'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Last check</span>
              <span className="font-medium text-slate-700">{diagnostics?.checkedAt || 'Never'}</span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-6 space-y-3">
          <h2 className="text-lg font-bold text-slate-900">Session</h2>
          <button
            onClick={onClearLocalData}
            className="w-full inline-flex items-center justify-center px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-sm font-medium"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear Local Preferences
          </button>
          <button
            onClick={onLogout}
            className="w-full inline-flex items-center justify-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Log Out
          </button>
        </div>

        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
          <div className="flex items-center font-semibold mb-1"><ShieldCheck className="w-4 h-4 mr-2" /> Security note</div>
          <p>Logging out removes your auth token from this browser session.</p>
        </div>
      </section>
    </div>
  );
}
