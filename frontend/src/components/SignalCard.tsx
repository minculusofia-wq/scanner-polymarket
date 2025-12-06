import React from 'react';
import { ArrowUpRight, ArrowDownRight, ExternalLink, Activity, Info, TrendingUp, Fish, Newspaper, DollarSign, Users } from 'lucide-react';


interface Signal {
    id: string;
    score: number;
    level: 'opportunity' | 'strong' | 'interesting' | 'watch';
    direction: 'YES' | 'NO' | string; // Expanded for 'WHALE BUY: YES' etc
    market_question: string;
    whale_score: number;
    volume_score: number;
    news_score: number;
    whale_count: number;
    unique_whale_count: number;
    volume_24h: number;
    news_count: number;
    yes_price: number;
    no_price: number;
    price_movement: number;
    liquidity: number;
    spread: number;
    hours_remaining: number;
    end_date: string;
    polymarket_url: string;
}

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(value);
};

export function SignalCard({ signal }: { signal: Signal }) {
    // Dynamic color based on level
    const getLevelColor = (level: string) => {
        switch (level) {
            case 'opportunity': return 'border-green-500/50 bg-green-500/5 text-green-400';
            case 'strong': return 'border-sky-500/50 bg-sky-500/5 text-sky-400';
            case 'interesting': return 'border-indigo-500/50 bg-indigo-500/5 text-indigo-400';
            default: return 'border-gray-700 bg-gray-800/50 text-gray-400';
        }
    };

    const levelColor = getLevelColor(signal.level);

    // Direction logic
    const isYes = signal.direction && signal.direction.includes('YES');
    const isNo = signal.direction && signal.direction.includes('NO');
    const directionColor = isYes ? 'text-green-500' : isNo ? 'text-red-500' : 'text-gray-400';

    return (
        <div className={`rounded-xl border p-4 transition-all hover:bg-white/5 ${levelColor.split(' ')[0]} ${levelColor.split(' ')[1]}`}>
            <div className="flex flex-col gap-3">

                {/* Header */}
                <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-0.5 rounded textxs font-bold uppercase tracking-wider ${levelColor}`}>
                                {signal.level}
                            </span>
                            {/* Score Badge */}
                            <span className="bg-white/10 px-2 py-0.5 rounded text-xs font-mono text-gray-300">
                                {signal.score}/10
                            </span>
                            {/* Whale Badge if high */}
                            {signal.whale_count > 2 && (
                                <span className="bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded text-xs flex items-center gap-1">
                                    <Fish className="w-3 h-3" /> Whale
                                </span>
                            )}
                        </div>
                        <h3 className="font-medium text-white line-clamp-2 leading-snug">
                            {signal.market_question}
                        </h3>
                    </div>

                    {/* Action Button */}
                    <a
                        href={signal.polymarket_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors flex-shrink-0"
                    >
                        <ExternalLink className="w-5 h-5" />
                    </a>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-2 border-t border-white/5 border-b">
                    <div>
                        <div className="text-xs text-gray-500 mb-0.5">Prix</div>
                        <div className="text-sm font-bold text-white flex items-center gap-1">
                            {(signal.yes_price * 100).toFixed(1)}¢
                            <span className={`text-xs ${signal.price_movement >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {signal.price_movement >= 0 ? '+' : ''}{signal.price_movement.toFixed(1)}%
                            </span>
                        </div>
                    </div>
                    <div>
                        <div className="text-xs text-gray-500 mb-0.5">Volume 24h</div>
                        <div className="text-sm font-bold text-white max-w-[80px] truncate" title={formatCurrency(signal.volume_24h)}>
                            {formatCurrency(signal.volume_24h)}
                        </div>
                    </div>
                    <div>
                        <div className="text-xs text-gray-500 mb-0.5">Whales</div>
                        <div className="text-sm font-bold text-white flex items-center gap-1">
                            <Users className="w-3 h-3 text-indigo-400" />
                            {signal.unique_whale_count}
                        </div>
                    </div>
                    <div>
                        <div className="text-xs text-gray-500 mb-0.5">Liquidité</div>
                        <div className="text-sm font-bold text-white">
                            {formatCurrency(signal.liquidity)}
                        </div>
                    </div>
                </div>

                {/* Footer / Direction */}
                <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-500 flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        Fin: {new Date(signal.end_date).toLocaleDateString()}
                    </span>

                    <div className={`font-bold flex items-center gap-1 ${directionColor}`}>
                        {isYes ? <ArrowUpRight className="w-4 h-4" /> : isNo ? <ArrowDownRight className="w-4 h-4" /> : <Info className="w-4 h-4" />}
                        {signal.direction}
                    </div>
                </div>
            </div>
        </div>
    );
}
