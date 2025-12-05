'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Activity, TrendingUp, Fish, Newspaper, Zap, Wifi, WifiOff,
    ExternalLink, SlidersHorizontal, X, RefreshCw, Filter, ChevronDown,
    ArrowUpRight, ArrowDownRight, Eye, Clock, Loader2
} from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

// ============ Types ============
interface Signal {
    id: string;
    market_id: string;
    condition_id: string;
    slug: string;
    market_question: string;
    score: number;
    level: 'watch' | 'interesting' | 'strong' | 'opportunity';
    direction: 'YES' | 'NO';
    whale_score: number;
    volume_score: number;
    news_score: number;
    whale_count: number;
    volume_24h: number;
    news_count: number;
    yes_price: number;
    no_price: number;
    price_movement: number;
    liquidity: number;
    end_date: string;
    created_at: string;
}

interface ScannerSettings {
    minWhaleCount: number;
    minVolumeUsd: number;
    minNewsCount: number;
    minScore: number;
    showWatchLevel: boolean;
}

interface WhaleTrade {
    id: string;
    trader: string;
    market_id: string;
    market_question: string;
    slug: string;
    side: 'YES' | 'NO';
    size_usd: number;
    price: number;
    timestamp: string;
}

// ============ Utility Functions ============
function formatCurrency(value: number): string {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
}

function formatTimeAgo(timestamp: string): string {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function getPolymarketUrl(slug: string): string {
    return `https://polymarket.com/event/${slug}`;
}

// ============ Settings Panel ============
function SettingsPanel({
    settings,
    onClose,
    onUpdate
}: {
    settings: ScannerSettings;
    onClose: () => void;
    onUpdate: (settings: ScannerSettings) => void;
}) {
    const [localSettings, setLocalSettings] = useState(settings);

    const handleSave = () => {
        onUpdate(localSettings);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl w-full max-w-lg border border-white/10 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-sky-500/20 flex items-center justify-center">
                            <SlidersHorizontal className="w-5 h-5 text-sky-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Paramètres du Scanner</h2>
                            <p className="text-sm text-gray-400">Ajustez les seuils de détection</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                {/* Settings */}
                <div className="p-6 space-y-6">
                    {/* Whale Settings */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-sky-400 uppercase tracking-wider">
                            🐋 Détection Whales
                        </h3>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-300">Nombre min. de whales</span>
                                <span className="text-white font-mono">{localSettings.minWhaleCount}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="20"
                                step="1"
                                value={localSettings.minWhaleCount}
                                onChange={(e) => setLocalSettings({ ...localSettings, minWhaleCount: Number(e.target.value) })}
                                className="w-full accent-sky-500"
                            />
                        </div>
                    </div>

                    {/* Volume Settings */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-green-400 uppercase tracking-wider">
                            📈 Volume
                        </h3>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-300">Volume minimum (24h)</span>
                                <span className="text-white font-mono">{formatCurrency(localSettings.minVolumeUsd)}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="1000000"
                                step="10000"
                                value={localSettings.minVolumeUsd}
                                onChange={(e) => setLocalSettings({ ...localSettings, minVolumeUsd: Number(e.target.value) })}
                                className="w-full accent-green-500"
                            />
                        </div>
                    </div>

                    {/* News Settings */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider">
                            📰 Informations
                        </h3>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-300">Nombre min. de news</span>
                                <span className="text-white font-mono">{localSettings.minNewsCount}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="20"
                                step="1"
                                value={localSettings.minNewsCount}
                                onChange={(e) => setLocalSettings({ ...localSettings, minNewsCount: Number(e.target.value) })}
                                className="w-full accent-yellow-500"
                            />
                        </div>
                    </div>

                    {/* Score Settings */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-purple-400 uppercase tracking-wider">
                            🎯 Score Global
                        </h3>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-300">Score minimum</span>
                                <span className="text-white font-mono">{localSettings.minScore}/10</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                step="1"
                                value={localSettings.minScore}
                                onChange={(e) => setLocalSettings({ ...localSettings, minScore: Number(e.target.value) })}
                                className="w-full accent-purple-500"
                            />
                        </div>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={localSettings.showWatchLevel}
                                onChange={(e) => setLocalSettings({ ...localSettings, showWatchLevel: e.target.checked })}
                                className="w-4 h-4 rounded accent-sky-500"
                            />
                            <span className="text-sm text-gray-300">Afficher niveau &quot;Watch&quot;</span>
                        </label>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex gap-3 p-6 border-t border-white/10">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 font-medium transition-colors"
                    >
                        Annuler
                    </button>
                    <button
                        onClick={handleSave}
                        className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-sky-600 hover:from-sky-400 hover:to-sky-500 text-white font-medium transition-all shadow-lg shadow-sky-500/25"
                    >
                        Appliquer
                    </button>
                </div>
            </div>
        </div>
    );
}

// ============ Signal Card ============
function SignalCard({ signal }: { signal: Signal }) {
    const levelConfig = {
        watch: {
            border: 'border-gray-500/30',
            bg: 'bg-gray-500/5',
            badge: 'bg-gray-500/20 text-gray-400',
            emoji: '👁'
        },
        interesting: {
            border: 'border-yellow-500/30',
            bg: 'bg-yellow-500/5',
            badge: 'bg-yellow-500/20 text-yellow-400',
            emoji: '🟡'
        },
        strong: {
            border: 'border-orange-500/30',
            bg: 'bg-orange-500/5',
            badge: 'bg-orange-500/20 text-orange-400',
            emoji: '🔥'
        },
        opportunity: {
            border: 'border-green-500/30',
            bg: 'bg-green-500/5',
            badge: 'bg-green-500/20 text-green-400',
            emoji: '🚨'
        },
    };

    const config = levelConfig[signal.level] || levelConfig.watch;
    const scoreOn10 = Math.round(signal.score / 10);

    return (
        <div className={`
            relative rounded-2xl border ${config.border} ${config.bg}
            backdrop-blur-sm overflow-hidden transition-all duration-300
            hover:scale-[1.01] hover:shadow-xl group
        `}>
            <div className="p-5">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">{config.emoji}</span>
                        <span className={`px-2 py-1 rounded-lg text-xs font-semibold uppercase ${config.badge}`}>
                            {signal.level}
                        </span>
                    </div>

                    {/* Score */}
                    <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-white/10">
                        <span className="text-lg font-bold text-white">{scoreOn10}</span>
                        <span className="text-xs text-gray-400">/10</span>
                    </div>
                </div>

                {/* Question */}
                <h3 className="font-semibold text-white text-base mb-3 line-clamp-2 leading-snug">
                    {signal.market_question}
                </h3>

                {/* Direction & Price */}
                <div className="flex items-center gap-3 mb-4">
                    <div className={`
                        flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-sm
                        ${signal.direction === 'YES'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'}
                    `}>
                        {signal.direction === 'YES' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {signal.direction}
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-400">YES</span>
                        <span className="font-mono text-white">{(signal.yes_price * 100).toFixed(0)}¢</span>
                        <span className="text-gray-600">|</span>
                        <span className="text-gray-400">NO</span>
                        <span className="font-mono text-white">{(signal.no_price * 100).toFixed(0)}¢</span>
                    </div>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="bg-white/5 rounded-lg p-2 text-center">
                        <Fish className="w-3 h-3 mx-auto text-sky-400 mb-1" />
                        <div className="text-xs text-gray-500">Whales</div>
                        <div className="text-sm font-bold text-white">{signal.whale_count}</div>
                    </div>
                    <div className="bg-white/5 rounded-lg p-2 text-center">
                        <TrendingUp className="w-3 h-3 mx-auto text-green-400 mb-1" />
                        <div className="text-xs text-gray-500">Vol 24h</div>
                        <div className="text-sm font-bold text-white">{formatCurrency(signal.volume_24h)}</div>
                    </div>
                    <div className="bg-white/5 rounded-lg p-2 text-center">
                        <Activity className="w-3 h-3 mx-auto text-purple-400 mb-1" />
                        <div className="text-xs text-gray-500">Liquidité</div>
                        <div className="text-sm font-bold text-white">{formatCurrency(signal.liquidity)}</div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-white/5">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>Fin: {signal.end_date}</span>
                    </div>

                    {/* Open on Polymarket Button */}
                    <a
                        href={getPolymarketUrl(signal.slug)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="
                            flex items-center gap-2 px-3 py-1.5 rounded-lg
                            bg-sky-500/20 hover:bg-sky-500 
                            border border-sky-500/30 hover:border-sky-400
                            text-sky-400 hover:text-white
                            font-medium text-sm transition-all duration-200
                        "
                    >
                        <span>Ouvrir</span>
                        <ExternalLink className="w-3 h-3" />
                    </a>
                </div>
            </div>
        </div>
    );
}

// ============ Stat Card ============
function StatCard({
    title,
    value,
    icon: Icon,
    color = 'sky'
}: {
    title: string;
    value: string;
    icon: React.ElementType;
    color?: 'sky' | 'green' | 'yellow' | 'purple';
}) {
    const colors = {
        sky: 'from-sky-500/20 to-sky-600/10 border-sky-500/20 text-sky-400',
        green: 'from-green-500/20 to-green-600/10 border-green-500/20 text-green-400',
        yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/20 text-yellow-400',
        purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/20 text-purple-400',
    };

    return (
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 rounded-xl p-4 border border-white/5">
            <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${colors[color]} border flex items-center justify-center`}>
                    <Icon className="w-5 h-5" />
                </div>
                <div className="text-sm text-gray-400">{title}</div>
            </div>
            <div className="text-2xl font-bold text-white">{value}</div>
        </div>
    );
}

// ============ Main Dashboard ============
export default function Dashboard() {
    const [signals, setSignals] = useState<Signal[]>([]);
    const [isLive, setIsLive] = useState(true);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showSettings, setShowSettings] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [whaleTrades, setWhaleTrades] = useState<WhaleTrade[]>([]);
    const [settings, setSettings] = useState<ScannerSettings>({
        minWhaleCount: 0,
        minVolumeUsd: 0,
        minNewsCount: 0,
        minScore: 0,
        showWatchLevel: true,
    });

    // WebSocket connection for real-time updates
    const { isConnected } = useWebSocket({
        onSignalsUpdate: (newSignals, cached, cacheAge, wsError) => {
            if (isLive && newSignals.length > 0) {
                setSignals(newSignals);
                setLastUpdate(new Date());
                if (wsError) {
                    setError(wsError);
                }
            }
        },
        onWhaleTrade: (trade) => {
            setWhaleTrades(prev => [trade, ...prev].slice(0, 20));
        }
    });

    // Fetch whale trades
    const fetchWhaleTrades = useCallback(async () => {
        try {
            const response = await fetch('/api/whales/trades?limit=10');
            if (response.ok) {
                const data = await response.json();
                if (data.trades) {
                    setWhaleTrades(data.trades);
                }
            }
        } catch (err) {
            console.error('Failed to fetch whale trades:', err);
        }
    }, []);

    // Fetch signals from API
    const fetchSignals = useCallback(async () => {
        try {
            setError(null);
            const response = await fetch('/api/signals/');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Check for API error message
            if (data.error) {
                setError(data.error);
                setSignals([]);
            } else if (data.signals && Array.isArray(data.signals)) {
                setSignals(data.signals);
                setLastUpdate(new Date());
            }
            setIsLoading(false);
        } catch (err) {
            console.error('Failed to fetch signals:', err);
            setError('Backend non connecté. Lancez le backend avec LANCER.command');
            setIsLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchSignals();
        fetchWhaleTrades();
    }, [fetchSignals, fetchWhaleTrades]);

    // Polling
    useEffect(() => {
        if (!isLive) return;

        const interval = setInterval(() => {
            fetchSignals();
            fetchWhaleTrades();
        }, 30000);
        return () => clearInterval(interval);
    }, [isLive, fetchSignals, fetchWhaleTrades]);

    // Filter signals based on settings
    const filteredSignals = signals.filter(signal => {
        const scoreOn10 = Math.round(signal.score / 10);
        if (scoreOn10 < settings.minScore) return false;
        if (signal.whale_count < settings.minWhaleCount) return false;
        if ((signal.volume_24h || 0) < settings.minVolumeUsd) return false;
        if ((signal.news_count || 0) < settings.minNewsCount) return false;
        if (!settings.showWatchLevel && signal.level === 'watch') return false;
        return true;
    });

    // Stats
    const opportunityCount = signals.filter(s => s.level === 'opportunity').length;
    const strongCount = signals.filter(s => s.level === 'strong').length;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
            {/* Background */}
            <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sky-900/20 via-transparent to-transparent" />

            <div className="relative z-10 p-4 lg:p-6 max-w-[1600px] mx-auto">
                {/* Header */}
                <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-sky-500 to-sky-700 flex items-center justify-center shadow-lg shadow-sky-500/30">
                            <Zap className="w-7 h-7 text-white" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-white">Polymarket Scanner</h1>
                            <p className="text-sm text-gray-400">
                                {lastUpdate ? `Mis à jour ${formatTimeAgo(lastUpdate.toISOString())}` : 'Chargement...'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Live Status */}
                        <button
                            onClick={() => setIsLive(!isLive)}
                            className={`
                                flex items-center gap-2 px-3 py-2 rounded-lg border text-sm
                                ${isLive
                                    ? 'bg-green-500/10 border-green-500/30 text-green-400'
                                    : 'bg-gray-500/10 border-gray-500/30 text-gray-400'}
                            `}
                        >
                            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`} />
                            {isLive ? 'Live' : 'Pausé'}
                        </button>

                        {/* WebSocket Status */}
                        <div className={`flex items-center gap-1 px-2 py-2 rounded-lg text-xs ${isConnected
                                ? 'text-sky-400'
                                : 'text-gray-500'
                            }`} title={isConnected ? 'WebSocket connecté' : 'WebSocket déconnecté'}>
                            {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                        </div>

                        {/* Refresh */}
                        <button
                            onClick={fetchSignals}
                            disabled={isLoading}
                            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
                        >
                            <RefreshCw className={`w-5 h-5 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
                        </button>

                        {/* Settings */}
                        <button
                            onClick={() => setShowSettings(true)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
                        >
                            <SlidersHorizontal className="w-5 h-5 text-gray-400" />
                            <span className="text-gray-400 text-sm hidden sm:inline">Paramètres</span>
                        </button>
                    </div>
                </header>

                {/* Error Banner */}
                {error && (
                    <div className={`mb-6 p-4 rounded-xl ${error.includes('cache') || error.includes('Cache')
                        ? 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                        : 'bg-red-500/10 border border-red-500/30 text-red-400'
                        }`}>
                        {error}
                    </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                    <StatCard title="Total Signaux" value={signals.length.toString()} icon={Activity} color="sky" />
                    <StatCard title="Opportunités" value={opportunityCount.toString()} icon={Zap} color="green" />
                    <StatCard title="Whale Trades" value={whaleTrades.length.toString()} icon={Fish} color="yellow" />
                    <StatCard title="Filtrés" value={filteredSignals.length.toString()} icon={Filter} color="purple" />
                </div>

                {/* Whale Trades Section */}
                {whaleTrades.length > 0 && (
                    <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-sky-900/20 to-purple-900/20 border border-white/5">
                        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-3">
                            <Fish className="w-4 h-4 text-sky-400" />
                            Derniers Trades Whales
                        </h3>
                        <div className="space-y-2">
                            {whaleTrades.slice(0, 5).map((trade) => (
                                <div key={trade.id} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                    <div className="flex items-center gap-3">
                                        <span className="font-mono text-xs text-gray-400">{trade.trader}</span>
                                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${trade.side === 'YES'
                                            ? 'bg-green-500/20 text-green-400'
                                            : 'bg-red-500/20 text-red-400'
                                            }`}>
                                            {trade.side}
                                        </span>
                                        <span className="text-xs text-gray-500 truncate max-w-[200px]">{trade.market_question}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold text-white">{formatCurrency(trade.size_usd)}</span>
                                        <span className="text-xs text-gray-500">@ {(trade.price * 100).toFixed(0)}¢</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {isLoading && (
                    <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 className="w-10 h-10 text-sky-400 animate-spin mb-4" />
                        <p className="text-gray-400">Chargement des marchés Polymarket...</p>
                    </div>
                )}

                {/* Signals Grid */}
                {!isLoading && (
                    <>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Zap className="w-5 h-5 text-sky-400" />
                                Signaux ({filteredSignals.length})
                            </h2>
                        </div>

                        {filteredSignals.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-16 text-center">
                                <Filter className="w-12 h-12 text-gray-600 mb-4" />
                                <h3 className="text-lg font-medium text-gray-400 mb-2">Aucun signal</h3>
                                <p className="text-sm text-gray-500">Ajustez les paramètres pour voir plus de résultats</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {filteredSignals.map((signal) => (
                                    <SignalCard key={signal.id} signal={signal} />
                                ))}
                            </div>
                        )}
                    </>
                )}

                {/* Footer */}
                <footer className="mt-8 py-4 border-t border-white/5 text-center">
                    <p className="text-sm text-gray-500">
                        Polymarket Scanner • Données temps réel • Non conseil financier
                    </p>
                </footer>
            </div>

            {/* Settings Modal */}
            {showSettings && (
                <SettingsPanel
                    settings={settings}
                    onClose={() => setShowSettings(false)}
                    onUpdate={setSettings}
                />
            )}
        </div>
    );
}
