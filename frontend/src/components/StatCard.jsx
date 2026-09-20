import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const colorMap = {
    blue: { bg: 'bg-blue-50 text-blue-600', ring: 'ring-blue-100' },
    amber: { bg: 'bg-amber-50 text-amber-600', ring: 'ring-amber-100' },
    rose: { bg: 'bg-rose-50 text-rose-600', ring: 'ring-rose-100' },
    emerald: { bg: 'bg-emerald-50 text-emerald-600', ring: 'ring-emerald-100' },
    purple: { bg: 'bg-purple-50 text-purple-600', ring: 'ring-purple-100' },
  };

  const scheme = colorMap[color] || colorMap.blue;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg ${scheme.bg} ring-4 ${scheme.ring}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  );
}
