import React from 'react';
import { Archive, Play, Rocket, RefreshCw } from 'lucide-react';

export default function ModelsPanel({
  models,
  loading,
  onRefresh,
  onRerun,
  onDeployNew,
  selectedModelInternalId,
  onSelectModel,
}) {
  const rowRefs = React.useRef({});

  React.useEffect(() => {
    if (!selectedModelInternalId) return;
    const row = rowRefs.current[selectedModelInternalId];
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [selectedModelInternalId]);

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center">
          <Archive className="w-5 h-5 mr-2 text-blue-600" />
          Models Library
        </h2>
        <button
          onClick={onRefresh}
          className="inline-flex items-center px-3 py-2 text-sm rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {models.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50">
          <Archive className="w-10 h-10 mx-auto text-slate-400 mb-3" />
          <p className="text-slate-700 font-medium">No model artifacts found</p>
          <p className="text-sm text-slate-500 mt-1">Deploy a model once to save reusable artifacts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {models.map((model) => {
            const running = model.status === 'running';
            const isSelected = selectedModelInternalId === model.internal_id;
            return (
              <div
                key={model.internal_id}
                ref={(el) => {
                  rowRefs.current[model.internal_id] = el;
                }}
                onClick={() => onSelectModel && onSelectModel(model.internal_id)}
                className={`rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
                  isSelected
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-base font-semibold text-slate-900 truncate">{model.model_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">{model.internal_id}</p>
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase font-semibold">{model.framework || 'unknown'}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 uppercase font-semibold">{model.task || 'unknown'}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-semibold ${running ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                        {model.status || 'archived'}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">{model.host_port ? `:${model.host_port}` : '-'}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRerun(model);
                      }}
                      className="inline-flex items-center px-3 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium"
                    >
                      <Play className="w-4 h-4 mr-1" />
                      Rerun
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeployNew(model);
                      }}
                      className="inline-flex items-center px-3 py-2 text-sm rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium"
                    >
                      <Rocket className="w-4 h-4 mr-1" />
                      New Deployment
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
