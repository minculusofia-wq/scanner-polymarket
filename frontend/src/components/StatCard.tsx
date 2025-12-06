import React from 'react';
import { DivideIcon as LucideIcon } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: string;
    icon: any;
    color: 'sky' | 'green' | 'purple' | 'orange' | 'yellow' | 'indigo' | 'rose' | 'fuchsia';
}

const colors = {
    sky: 'from-sky-500 to-blue-600',
    green: 'from-emerald-500 to-green-600',
    purple: 'from-purple-500 to-violet-600',
    orange: 'from-orange-500 to-red-500',
    yellow: 'from-yellow-400 to-amber-500',
    indigo: 'from-indigo-500 to-blue-600',
    rose: 'from-rose-500 to-pink-600',
    fuchsia: 'from-fuchsia-500 to-purple-600'
};

export function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
    return (
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 rounded-xl p-4 border border-white/5">
            <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${colors[color] || colors.sky} border flex items-center justify-center`}>
                    <Icon className="w-5 h-5 text-white" />
                </div>
                <div className="text-sm text-gray-400">{title}</div>
            </div>
            <div className="text-2xl font-bold text-white">{value}</div>
        </div>
    );
}
