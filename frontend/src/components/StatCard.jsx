import React from 'react';

export default function StatCard({ label, value, icon: Icon, colorClass, trend }) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-100 flex items-center justify-between hover:shadow-md transition-shadow duration-200">
      <div>
        <p className="text-sm font-medium text-slate-500 mb-1">{label}</p>
        <h3 className="text-3xl font-bold text-slate-900 tracking-tight">{value}</h3>
        {trend && (
          <p className="text-xs text-slate-400 mt-1">
            <span className="text-green-500 font-medium">{trend}</span> from last week
          </p>
        )}
      </div>
      <div className={`p-4 rounded-xl ${colorClass}`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
}
