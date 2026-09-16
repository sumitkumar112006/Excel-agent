import React from 'react';

export default function StatsCard({
  title,
  value,
  subtext,
  icon: Icon,
  variant = 'default', // 'yellow', 'emerald', 'amber', 'slate'
}) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'yellow':
        return {
          bg: 'bg-gradient-to-br from-amber-50 to-amber-100/50 border-amber-200/80',
          iconBg: 'bg-amber-400/30 text-amber-800 border border-amber-300',
          valColor: 'text-amber-950',
          accent: 'border-l-4 border-l-amber-500',
        };
      case 'emerald':
        return {
          bg: 'bg-gradient-to-br from-emerald-50/70 to-white border-emerald-200/70',
          iconBg: 'bg-emerald-100 text-emerald-700 border border-emerald-300',
          valColor: 'text-emerald-950',
          accent: 'border-l-4 border-l-emerald-500',
        };
      case 'amber':
        return {
          bg: 'bg-gradient-to-br from-amber-50/40 to-white border-amber-200/60',
          iconBg: 'bg-amber-100 text-amber-700 border border-amber-200',
          valColor: 'text-amber-950',
          accent: 'border-l-4 border-l-amber-400',
        };
      default:
        return {
          bg: 'bg-white border-brand-border',
          iconBg: 'bg-slate-100 text-slate-700 border border-slate-200',
          valColor: 'text-slate-900',
          accent: 'border-l-4 border-l-brand-400',
        };
    }
  };

  const style = getVariantStyles();

  return (
    <div className={`craft-card p-5 ${style.bg} ${style.accent} flex flex-col justify-between transition-all duration-200 hover:-translate-y-0.5`}>
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </span>
          <div className={`text-2xl sm:text-3xl font-display font-extrabold mt-1 tracking-tight ${style.valColor}`}>
            {value}
          </div>
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-xl ${style.iconBg} shadow-sm shrink-0`}>
            <Icon className="w-5 h-5 stroke-[2]" />
          </div>
        )}
      </div>

      {subtext && (
        <div className="mt-3 pt-2.5 border-t border-slate-200/50 text-[11px] font-medium text-slate-500 flex items-center justify-between">
          <span>{subtext}</span>
        </div>
      )}
    </div>
  );
}
