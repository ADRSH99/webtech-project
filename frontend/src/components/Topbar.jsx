import React from 'react';
import { User, Search, Activity } from 'lucide-react';

export default function Topbar({
  title,
  dockerRunning,
  displayName = 'User',
  searchTerm = '',
  onSearchChange,
  searchSuggestions = [],
  onSelectSuggestion,
  onSearchSubmit,
}) {
  const initials = (displayName || 'User').trim().slice(0, 2).toUpperCase();
  const [showSuggestions, setShowSuggestions] = React.useState(false);

  const shouldShowSuggestions =
    showSuggestions && searchTerm.trim().length > 0 && searchSuggestions.length > 0;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSearchSubmit) {
      onSearchSubmit();
    }
    setShowSuggestions(false);
  };

  return (
    <header className="h-16 flex items-center justify-between px-8 bg-white border-b border-slate-200">
      <h1 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h1>

      <div className="flex items-center space-x-6">
        <div className="hidden md:block relative">
          <form
            onSubmit={handleSubmit}
            className="flex items-center bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 transition-shadow focus-within:ring-2 focus-within:ring-blue-100"
          >
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder="Search models by prefix..."
              className="bg-transparent border-none focus:outline-none focus:ring-0 text-sm ml-2 w-64 text-slate-700 placeholder-slate-400"
            />
          </form>

          {shouldShowSuggestions && (
            <div className="absolute z-30 mt-2 w-full bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
              {searchSuggestions.map((model) => (
                <button
                  key={model.internal_id}
                  type="button"
                  onMouseDown={() => {
                    if (onSelectSuggestion) {
                      onSelectSuggestion(model);
                    }
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-slate-50 border-b border-slate-100 last:border-b-0"
                >
                  <div className="text-sm font-medium text-slate-800">{model.model_name}</div>
                  <div className="text-xs text-slate-500 font-mono">{model.internal_id}</div>
                </button>
              ))}
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <Activity className={`w-4 h-4 ${dockerRunning ? 'text-green-500' : 'text-red-500'}`} />
          <span className="text-sm font-medium text-slate-600">Docker {dockerRunning ? 'Running' : 'Stopped'}</span>
        </div>

        <div className="flex items-center space-x-2 border-l border-slate-200 pl-6 cursor-pointer hover:opacity-80">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold shadow-sm">
            {initials}
          </div>
          <span className="text-sm font-medium text-slate-700 hidden sm:block">{displayName}</span>
        </div>
      </div>
    </header>
  );
}
