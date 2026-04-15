import React, { useState, useEffect, useRef } from 'react';
import { Terminal, ScrollText, Filter, AlertCircle } from 'lucide-react';
import api from '../api';

export default function LogsPanel({ activeContainerId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const logsEndRef = useRef(null);

  useEffect(() => {
    if (!activeContainerId) {
      setLogs([]);
      return;
    }

    const fetchLogs = async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/containers/${activeContainerId}/logs`);
        const rawLogs = data.logs || "";
        
        // If the backend returns a string, parse it into the expected objects
        if (typeof rawLogs === 'string') {
          const lines = rawLogs.trim().split('\n').filter(line => line.trim() !== "");
          const formattedLogs = lines.map(line => {
            // Docker logs -t includes a timestamp at the start (e.g. 2024-04-15T12:00:00.000Z message)
            const parts = line.split(' ');
            const timestampStr = parts[0];
            const message = parts.slice(1).join(' ');
            
            return {
              timestamp: timestampStr,
              stream: 'stdout',
              message: message || line // fallback to full line if no space
            };
          });
          setLogs(formattedLogs);
        } else if (Array.isArray(rawLogs)) {
          setLogs(rawLogs);
        } else {
          setLogs([]);
        }
      } catch (err) {
        setLogs([{ timestamp: new Date().toISOString(), stream: 'stderr', message: `Failed to fetch logs: ${err.message}` }]);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [activeContainerId]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  return (
    <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 flex flex-col h-96 overflow-hidden">
      <div className="flex items-center justify-between p-4 bg-slate-800/80 border-b border-slate-700">
        <div className="flex items-center space-x-2 text-slate-100">
          <Terminal className="w-5 h-5 text-blue-400" />
          <h2 className="font-semibold tracking-wide flex items-center space-x-2">
            <span>Container Logs</span>
            {activeContainerId && (
              <span className="bg-slate-700 px-2 py-0.5 rounded font-mono text-xs font-normal text-slate-300 border border-slate-600">
                {String(activeContainerId).substring(0, 8)}
              </span>
            )}
          </h2>
        </div>
        
        <div className="flex items-center space-x-3 text-slate-400 text-sm">
          <button className="hover:text-blue-400 transition-colors tooltip" title="Filter logs">
            <Filter className="w-4 h-4" />
          </button>
          <button className="hover:text-blue-400 transition-colors tooltip" title="Follow scroll">
            <ScrollText className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto font-mono text-sm leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900">
        {!activeContainerId ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
            <Terminal className="w-12 h-12 opacity-50" />
            <p>Select a container to view logs</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-slate-500 italic flex items-center space-x-2">
            {loading ? <span className="animate-pulse">Waiting for logs...</span> : <span>No logs found for this container.</span>}
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div key={index} className={`flex space-x-4 ${log.stream === 'stderr' || log.message.toLowerCase().includes('error') ? 'text-red-400 bg-red-400/10 px-1 rounded -mx-1' : 'text-slate-300'}`}>
                 <span className="text-slate-500 shrink-0 w-24 tabular-nums">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) || '00:00:00'}
                 </span>
                 <span className="break-all flex-1 whitespace-pre-wrap font-medium">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
