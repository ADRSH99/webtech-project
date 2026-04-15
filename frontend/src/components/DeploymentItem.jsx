import React from 'react';
import { Square, Trash2, Play, RotateCcw } from 'lucide-react';
import api from '../api';

export default function DeploymentItem({ deployment, onUpdate, onOpenModel, onRerun }) {
  const isRunning = deployment.state === 'running' || deployment.status === 'running';
  const statusColor = isRunning ? 'bg-green-500' : 'bg-slate-300';
  const statusBg = isRunning ? 'bg-green-50' : 'bg-slate-50';
  const statusText = isRunning ? 'text-green-700' : 'text-slate-600';
  const deploymentKey = deployment.container_id || deployment.id || '';

  const handleAction = async (action) => {
    try {
      if (action === 'stop') {
        if (!window.confirm('Stop container? You can rerun it later.')) return;
        await api.delete(`/containers/${deploymentKey}`);
      } else if (action === 'rerun') {
        const { data } = await api.post(`/containers/${deploymentKey}/rerun`);
        if (onRerun) {
          onRerun(data, deployment);
        }
      } else if (action === 'delete') {
        if (!window.confirm('Delete deployment and artifact files permanently?')) return;
        await api.delete(`/containers/${deploymentKey}/cleanup`);
      }
      await onUpdate();
    } catch (err) {
      console.error('Action failed:', err);
    }
  };

  const containerId = String(deployment.container_id || deployment.id || '');
  const displayName = deployment.model_name || deployment.name || (deployment.names && deployment.names[0] ? deployment.names[0].replace('/', '') : containerId.substring(0, 12));
  const hostPort = deployment.host_port || deployment.port || deployment.ports?.[0]?.PublicPort || 'N/A';

  return (
    <div className={`p-5 rounded-xl border border-slate-200 shadow-sm transition-all duration-200 hover:shadow-md ${statusBg}`}>
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="font-bold text-slate-900 text-lg">{displayName}</h3>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${statusText}`}>
              <span className={`w-2 h-2 rounded-full mr-1.5 ${statusColor}`}></span>
              {isRunning ? 'Running' : 'Stopped'}
            </span>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-200 text-slate-700 uppercase tracking-wider">
              {deployment.image?.split(':')[0] || 'Unknown'}
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-500 mt-3">
            <p>ID: <span className="font-mono text-slate-700">{containerId.substring(0, 12)}</span></p>
            <p>Port: <span className="font-mono text-slate-700">{hostPort}</span></p>
            <p>Created: <span className="text-slate-700">{deployment.created ? new Date(deployment.created * 1000).toLocaleDateString() : 'N/A'}</span></p>
          </div>
        </div>

        <div className="flex space-x-2 ml-4">
          {isRunning && (
            <button 
              onClick={() => onOpenModel && onOpenModel(deployment)}
              className="px-3 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 text-white hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm hover:shadow-md font-semibold flex items-center space-x-1 text-sm"
              title="Open Model Interface"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Open</span>
            </button>
          )}
          
          {isRunning && (
            <button 
              onClick={() => handleAction('stop')}
              className="p-2 rounded-lg bg-white border border-slate-200 text-amber-600 hover:bg-amber-50 hover:border-amber-300 transition-colors tooltip"
              title="Stop"
            >
              <Square className="w-5 h-5" />
            </button>
          )}

          {!isRunning && (
            <button
              onClick={() => handleAction('rerun')}
              className="p-2 rounded-lg bg-white border border-slate-200 text-blue-600 hover:bg-blue-50 hover:border-blue-300 transition-colors tooltip"
              title="Rerun"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
          )}
          
          <button 
            onClick={() => handleAction('delete')}
            className="p-2 rounded-lg bg-white border border-slate-200 text-red-600 hover:bg-red-50 hover:border-red-300 transition-colors tooltip"
            title="Delete"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
