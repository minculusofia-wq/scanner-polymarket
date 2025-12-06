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
    spread: number;
    hours_remaining: number;
    end_date: string;
    polymarket_url: string;
    created_at: string;
}

interface ScannerSettings {
    minWhaleCount: number;
    minVolumeUsd: number;
    minLiquidity: number;
    maxSpread: number; // Max spread allowed in cents
    maxTimeHours: number; // 0 = All time
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
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl w-full max-w-lg border border-white/10 shadow-2xl overflow-y-auto max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-sky-500/20 flex items-center justify-center">
                            <SlidersHorizontal className="w-5 h-5 text-sky-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Paramètres Avancés</h2>
                            <p className="text-sm text-gray-400">Qualité & Horizon</p>
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
                <div className="p-6 space-y-8">

                    {/* 1. QUALITY FILTERS (Spread) */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-2">
                            🛡️ Qualité (Spread Max)
                        </h3>
                        <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                            <div className="flex justify-between text-sm mb-2">
                                <span className="text-gray-300">Spread Maximum autorisé</span>
                                <span className="text-white font-mono font-bold">
                                    {localSettings.maxSpread >= 0.10 ? "Illimité" : `${(localSettings.maxSpread * 100).toFixed(1)} cts`}
                                </span>
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                step="0.5"
                                value={localSettings.maxSpread * 100}
                                onChange={(e) => setLocalSettings({ ...localSettings, maxSpread: Number(e.target.value) / 100 })}
                                className="w-full accent-rose-500"
                            />
                            <p className="text-xs text-gray-500 mt-2">
                                Exclut les marchés avec un écart Achat/Vente trop grand (pièges).
                            </p>
                        </div>
                    </div>

                    {/* 2. TIME HORIZON */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-sky-400 uppercase tracking-wider flex items-center gap-2">
                            ⏳ Horizon de Temps
                        </h3>
                        <div className="grid grid-cols-4 gap-2">
                            {[
                                { label: 'Tout', val: 0 },
                                { label: '24h', val: 24 },
                                { label: '3j', val: 72 },
                                { label: '1s', val: 168 },
                            ].map((opt) => (
                                <button
                                    key={opt.label}
                                    onClick={() => setLocalSettings(prev => ({ ...prev, maxTimeHours: opt.val }))}
                                    className={`py-2 rounded-lg text-sm font-medium border transition-all ${localSettings.maxTimeHours === opt.val
                                        ? 'bg-sky-500/20 border-sky-500 text-sky-400'
                                        : 'bg-white/5 border-white/5 text-gray-400 hover:bg-white/10'
                                        }`}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="border-t border-white/10 my-4"></div>

                    {/* Standard Filters (Condensed) */}
                    <div className="grid grid-cols-2 gap-4">
                        {/* Liquidity */}
                        <div className="space-y-2">
                            <label className="text-xs text-gray-400">Liquidité Min.</label>
                            <select
                                value={localSettings.minLiquidity}
                                onChange={(e) => setLocalSettings({ ...localSettings, minLiquidity: Number(e.target.value) })}
                                className="w-full bg-slate-900 border border-white/10 rounded-lg p-2 text-sm text-white"
                            >
                                <option value={0}>0$</option>
                                <option value={1000}>1k$</option>
                                <option value={10000}>10k$</option>
                                <option value={50000}>50k$</option>
                                <option value={100000}>100k$</option>
                            </select>
                        </div>

                        {/* Score */}
                        <div className="space-y-2">
                            <label className="text-xs text-gray-400">Score Min.</label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="number"
                                    value={localSettings.minScore}
                                    onChange={(e) => setLocalSettings({ ...localSettings, minScore: Number(e.target.value) })}
                                    className="w-full bg-slate-900 border border-white/10 rounded-lg p-2 text-sm text-white"
                                />
                                <span className="text-xs text-gray-500">/100</span>
                            </div>
                        </div>
                    </div>

                    {/* Toggles */}
                    <div className="pt-2">
                        <label className="flex items-center justify-between cursor-pointer group">
                            <span className="text-gray-300 group-hover:text-white transition-colors">Afficher 'Surveillance' (Watch)</span>
                            <input
                                type="checkbox"
                                checked={localSettings.showWatchLevel}
                                onChange={(e) => setLocalSettings({ ...localSettings, showWatchLevel: e.target.checked })}
                                className="w-5 h-5 rounded border-gray-600 bg-slate-800 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900"
                            />
                        </label>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-white/10 flex justify-end gap-3 sticky bottom-0 bg-slate-800/95 backdrop-blur">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                    >
                        Annuler
                    </button>
                    <button
                        onClick={handleSave}
                        className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white font-medium shadow-lg shadow-emerald-500/20 transition-all"
                    >
                        Sauvegarder
                    </button>
                </div>
            </div>
        </div>
    );
}

// ============ Signal Card ============
function SignalCard({ signal, showScore = true }: { signal: Signal; showScore?: boolean }) {
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
                    {showScore && (
                        <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-white/10">
                            <span className="text-lg font-bold text-white">{scoreOn10}</span>
                            <span className="text-xs text-gray-400">/10</span>
                        </div>
                    )}
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
                        href={signal.polymarket_url || `https://polymarket.com/event/${signal.slug}`}
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

    // Independent Settings States
    const [scannerSettings, setScannerSettings] = useState<ScannerSettings>({
        minWhaleCount: 0,
        minVolumeUsd: 0,
        minLiquidity: 0,
        maxSpread: 0.10, // Permissive for Scanner
        maxTimeHours: 0,
        minNewsCount: 0,
        minScore: 0,
        showWatchLevel: true // Show everything by default
    });

    const [proInsightSettings, setProInsightSettings] = useState<ScannerSettings>({
        minWhaleCount: 0,
        minVolumeUsd: 1000,
        minLiquidity: 1000,
        maxSpread: 0.05, // Stricter for Pro (5 cents)
        maxTimeHours: 0,
        minNewsCount: 0,
        minScore: 40, // Quality filter
        showWatchLevel: false // Hide noise by default
    });

    const [activeTab, setActiveTab] = useState<'scanner' | 'equilibrage' | 'hot'>('scanner');
    // Use strings to allow empty '' state
    const [hotSettings, setHotSettings] = useState({ amount: '', profit: '', strategy: 'whale' });

    // Computed Settings based on Tab
    const activeSettings = activeTab === 'hot' ? proInsightSettings : scannerSettings;

    // Update Handler
    const handleSettingsUpdate = (newSettings: ScannerSettings) => {
        if (activeTab === 'hot') {
            setProInsightSettings(newSettings);
        } else {
            setScannerSettings(newSettings);
        }
    };

    // WebSocket connection for real-time updates
    const onSignalsUpdate = useCallback((newSignals: any[], cached: boolean, cacheAge: number | null, wsError: string | null) => {
        // Only update signals from WS if we are in 'scanner' mode
        // (WS broadcasts default scanner results, not Equilibrage results)
        if (activeTab !== 'scanner') return;

        if (isLive && newSignals.length > 0) {
            setSignals(newSignals);
            setLastUpdate(new Date());
            if (wsError) {
                setError(wsError);
            }
        }
    }, [isLive, activeTab]);

    const onWhaleTrade = useCallback((trade: any) => {
        setWhaleTrades(prev => [trade, ...prev].slice(0, 20));
    }, []);

    const { isConnected } = useWebSocket({
        onSignalsUpdate,
        onWhaleTrade
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

            // PRO INSIGHTS LOGIC:
            // All strategies (whale, yield, scalp) are automatic scans.

            let endpoint = '/api/signals/';
            if (activeTab === 'equilibrage') {
                endpoint = '/api/signals/equilibrage';
            } else if (activeTab === 'hot') {
                endpoint = `/api/signals/hot?strategy=${hotSettings.strategy}`;
            }

            const response = await fetch(endpoint);

            if (!response.ok) {
                // Handle 404 (Endpoint not found - likely backend not updated/restarted)
                if (response.status === 404) {
                    throw new Error("Endpoint introuvable. Redémarrez le backend (LANCER.command).");
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Check for API error message
            if (data.error) {
                // Display specific backend error (e.g., CRASH details)
                setError(data.error);
                setSignals([]);
            } else if (data.signals && Array.isArray(data.signals)) {
                setSignals(data.signals);
                setLastUpdate(new Date());
            }
            setIsLoading(false);
        } catch (err: any) {
            console.error('Failed to fetch signals:', err);
            // Show specific error if we caught one, otherwise generic
            const msg = err.message || 'Erreur inconnue';
            if (msg.includes("Redémarrez") || msg.includes("Failed to fetch")) {
                setError('Backend non connecté ou obsolète. Lancez/Redémarrez avec LANCER.command');
            } else {
                setError(msg);
            }
            setIsLoading(false);
        }
    }, [activeTab, hotSettings]);

    // Initial fetch
    useEffect(() => {
        fetchSignals();
        fetchWhaleTrades();
    }, [fetchSignals, fetchWhaleTrades]);

    // Polling - Logic adapted for tabs
    useEffect(() => {
        // If Scanner Tab AND WS connected: NO Poll (WS handles it)
        if (activeTab === 'scanner' && isConnected && isLive) return;

        // If Equilibrage Tab: ALWAYS Poll (WS does not cover it)
        // If Scanner Tab AND Not Connected: Poll

        if (!isLive) return;

        console.log(`⏱️ Polling active (${activeTab})`);
        const interval = setInterval(() => {
            fetchSignals();
            fetchWhaleTrades();
        }, 30000);
        return () => clearInterval(interval);
    }, [isLive, isConnected, fetchSignals, fetchWhaleTrades, activeTab]);

    // Filter signals based on settings
    const filteredSignals = signals.filter(signal => {
        // Universal Filters (Apply to ALL tabs, including Pro Insights)
        // Uses activeSettings based on the current Tab

        // 1. Min Score
        if (signal.score < activeSettings.minScore) return false;

        // 2. Min Volume
        if (signal.volume_24h < activeSettings.minVolumeUsd) return false;

        // 3. Min Liquidity
        if (signal.liquidity < activeSettings.minLiquidity) return false;

        // 4. Min Whale Count (Added)
        if (signal.whale_count < activeSettings.minWhaleCount) return false;

        // 5. Max Spread (Advanced)
        if (activeSettings.maxSpread > 0 && signal.spread > activeSettings.maxSpread) return false;

        // 6. Time Horizon (Advanced)
        if (activeSettings.maxTimeHours > 0) {
            // If hours_remaining is 0 (or missing), we assume it fits unless it's strictly > maxTime
            if (signal.hours_remaining > activeSettings.maxTimeHours) return false;
        }

        // 6. Watch Level Toggle
        // If "Show Watch" is OFF, and signal is 'watch', hide it.
        if (!activeSettings.showWatchLevel && signal.level === 'watch') return false;

        return true;
    });

    // Stats
    const opportunityCount = signals.filter(s => s.level === 'opportunity').length;
    const strongCount = signals.filter(s => s.level === 'strong').length;

    return (
        <div className="min-h-screen bg-[#0B0E14] text-white p-6 font-sans">
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
                        <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4">
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Zap className="w-5 h-5 text-sky-400" />
                                {activeTab === 'scanner' && 'Signaux Scanner'}
                                {activeTab === 'equilibrage' ? 'Opportunités Équilibrage (45-55%)' : 'Signaux Scanner'}
                                {activeTab === 'hot' && '🔥 Action Scanner'}
                                <span className="ml-2 px-2 py-0.5 rounded-full bg-white/10 text-sm font-normal text-gray-400">
                                    {filteredSignals.length}
                                </span>
                            </h2>

                            {/* Tabs */}
                            <div className="flex p-1 bg-white/5 rounded-xl border border-white/5">
                                <button
                                    onClick={() => setActiveTab('scanner')}
                                    className={`
                                        px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                                        ${activeTab === 'scanner'
                                            ? 'bg-sky-500/20 text-sky-400 shadow-sm'
                                            : 'text-gray-400 hover:text-white hover:bg-white/5'}
                                    `}
                                >
                                    Scanner
                                </button>
                                <button
                                    onClick={() => setActiveTab('equilibrage')}
                                    className={`
                                        px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                                        ${activeTab === 'equilibrage'
                                            ? 'bg-purple-500/20 text-purple-400 shadow-sm'
                                            : 'text-gray-400 hover:text-white hover:bg-white/5'}
                                    `}
                                >
                                    Équilibrage (45-55%)
                                </button>
                                <button
                                    onClick={() => setActiveTab('hot')}
                                    className={`
                                        px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                                        ${activeTab === 'hot'
                                            ? 'bg-indigo-500/20 text-indigo-400 shadow-sm'
                                            : 'text-gray-400 hover:text-white hover:bg-white/5'}
                                    `}
                                >
                                    🔎 Pro Insights
                                </button>
                            </div>
                        </div>

                        {/* Pro Insights Cockpit */}
                        {activeTab === 'hot' && (
                            <div className="bg-[#151921] border border-indigo-500/20 rounded-xl p-4 animate-in fade-in slide-in-from-top-2">
                                <div className="flex flex-col gap-4">

                                    {/* 1. Strategy Selector */}
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            onClick={() => setHotSettings(prev => ({ ...prev, strategy: 'whale' }))}
                                            className={`px-4 py-3 text-sm font-bold rounded-lg transition-all flex items-center gap-2 ${hotSettings.strategy === 'whale' ? 'bg-indigo-600 text-white shadow-lg ring-1 ring-white/20' : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'}`}
                                        >
                                            🐋 Whale Copier <span className="text-[10px] font-normal opacity-70 ml-1">Volume &gt;25k</span>
                                        </button>
                                        <button
                                            onClick={() => setHotSettings(prev => ({ ...prev, strategy: 'yield' }))}
                                            className={`px-4 py-3 text-sm font-bold rounded-lg transition-all flex items-center gap-2 ${hotSettings.strategy === 'yield' ? 'bg-emerald-600 text-white shadow-lg ring-1 ring-white/20' : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'}`}
                                        >
                                            🛡️ Safe Yield <span className="text-[10px] font-normal opacity-70 ml-1">Hedge &lt;96%</span>
                                        </button>
                                        <button
                                            onClick={() => setHotSettings(prev => ({ ...prev, strategy: 'scalp' }))}
                                            className={`px-4 py-3 text-sm font-bold rounded-lg transition-all flex items-center gap-2 ${hotSettings.strategy === 'scalp' ? 'bg-orange-600 text-white shadow-lg ring-1 ring-white/20' : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'}`}
                                        >
                                            🦅 Scalp Pro <span className="text-[10px] font-normal opacity-70 ml-1">Spread &gt;3c</span>
                                        </button>
                                    </div>

                                    {/* 2. Dynamic Info Panel */}
                                    <div className="flex items-center gap-4 bg-black/20 p-3 rounded-lg border border-white/5 min-h-[50px]">
                                        {hotSettings.strategy === 'whale' && (
                                            <div className="flex items-center gap-2 text-indigo-400 animate-in fade-in">
                                                <span className="font-bold">CALL:</span>
                                                <span>Suivez la "Smart Money". Ces marchés ont des volumes massifs (&gt;25k$/24h) signalant une action imminente.</span>
                                            </div>
                                        )}
                                        {hotSettings.strategy === 'yield' && (
                                            <div className="flex items-center gap-2 text-emerald-400 animate-in fade-in">
                                                <span className="font-bold">CALL:</span>
                                                <span>Opportunité "Risk-Free". La somme des cotes est &lt; 98 cents. Achetez tout pour un profit garanti.</span>
                                            </div>
                                        )}
                                        {hotSettings.strategy === 'scalp' && (
                                            <div className="flex items-center gap-2 text-orange-400 animate-in fade-in">
                                                <span className="font-bold">CALL:</span>
                                                <span>Spread Inefficace (&gt;3 cts). Placez des ordres limites au milieu pour capturer la valeur.</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {filteredSignals.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-16 text-center">
                                <Filter className="w-12 h-12 text-gray-600 mb-4" />
                                <h3 className="text-lg font-medium text-gray-400 mb-2">Aucun signal trouvé</h3>
                                <p className="text-sm text-gray-500">
                                    {activeTab === 'equilibrage'
                                        ? "Aucun marché ne se trouve actuellement dans la zone 45-55%."
                                        : activeTab === 'hot'
                                            ? "Aucun signal ne correspond aux critères de 'Mouvement'. Le marché est calme."
                                            : "Ajustez les paramètres pour voir plus de résultats."}
                                </p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {filteredSignals.map((signal) => (
                                    <SignalCard
                                        key={signal.id}
                                        signal={signal}
                                        // Show score only in Scanner mode.
                                        // In Hot mode, we show ROI in the 'reason' field (handled by backend string),
                                        // so we might want to hide the standard score.
                                        showScore={activeTab === 'scanner'}
                                    />
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
                    settings={activeSettings}
                    onClose={() => setShowSettings(false)}
                    onUpdate={handleSettingsUpdate}
                />
            )}
        </div>
    );
}
