'use client';

import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, Loader2, RefreshCw, ExternalLink, BarChart3 } from 'lucide-react';
import { EdgeOpportunity, EdgeResponse } from '@/types';
import { formatPrice } from '@/utils/formatting';

function EdgeCard({ opportunity }: { opportunity: EdgeOpportunity }) {
    const isPositiveEdge = opportunity.edge > 0;
    const isBuyYes = opportunity.recommendation === 'BUY_YES';
    const isBuyNo = opportunity.recommendation === 'BUY_NO';
    const isHold = opportunity.recommendation === 'HOLD';

    return (
        <div className={`
            relative p-4 rounded-xl border transition-all duration-300
            ${isBuyYes ? 'border-green-500/40 bg-green-500/5' : ''}
            ${isBuyNo ? 'border-red-500/40 bg-red-500/5' : ''}
            ${isHold ? 'border-gray-500/30 bg-gray-500/5' : ''}
            hover:scale-[1.01]
        `}>
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-500/20 text-blue-400">
                        {opportunity.asset}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium
                        ${opportunity.confidence === 'HIGH' ? 'bg-yellow-500/20 text-yellow-400' : ''}
                        ${opportunity.confidence === 'MEDIUM' ? 'bg-orange-500/20 text-orange-400' : ''}
                        ${opportunity.confidence === 'LOW' ? 'bg-gray-500/20 text-gray-400' : ''}
                    `}>
                        {opportunity.confidence}
                    </span>
                </div>
                <a
                    href={`https://polymarket.com/event/${opportunity.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-white"
                >
                    <ExternalLink className="w-4 h-4" />
                </a>
            </div>

            {/* Question */}
            <h3 className="text-sm font-medium text-white mb-3 line-clamp-2">
                {opportunity.market_question}
            </h3>

            {/* Probabilities Comparison */}
            <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="p-2 rounded-lg bg-white/5">
                    <div className="text-xs text-gray-400 mb-1">Polymarket</div>
                    <div className="text-lg font-bold text-white">
                        {(opportunity.polymarket_yes_price * 100).toFixed(1)}%
                    </div>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                    <div className="text-xs text-gray-400 mb-1">Monte Carlo</div>
                    <div className="text-lg font-bold text-purple-400">
                        {(opportunity.mc_probability * 100).toFixed(1)}%
                    </div>
                </div>
            </div>

            {/* Edge Display */}
            <div className={`
                flex items-center justify-between p-3 rounded-lg mb-3
                ${isPositiveEdge ? 'bg-green-500/10' : 'bg-red-500/10'}
            `}>
                <div className="flex items-center gap-2">
                    {isPositiveEdge ? (
                        <TrendingUp className="w-5 h-5 text-green-400" />
                    ) : (
                        <TrendingDown className="w-5 h-5 text-red-400" />
                    )}
                    <span className={`text-lg font-bold ${isPositiveEdge ? 'text-green-400' : 'text-red-400'}`}>
                        {isPositiveEdge ? '+' : ''}{opportunity.edge_percent.toFixed(1)}%
                    </span>
                </div>
                <span className="text-sm text-gray-400">Edge</span>
            </div>

            {/* Recommendation */}
            {!isHold && (
                <div className={`
                    text-center py-2 px-4 rounded-lg font-bold text-sm
                    ${isBuyYes ? 'bg-green-500/20 text-green-400' : ''}
                    ${isBuyNo ? 'bg-red-500/20 text-red-400' : ''}
                `}>
                    {isBuyYes && '🎯 ACHETER YES'}
                    {isBuyNo && '🎯 ACHETER NO (vendre YES)'}
                </div>
            )}

            {/* Meta Info */}
            <div className="mt-3 pt-3 border-t border-white/10 flex justify-between text-xs text-gray-400">
                <span>Target: {formatPrice(opportunity.target_price)}</span>
                <span>Current: {formatPrice(opportunity.current_price)}</span>
            </div>

            {/* Action Button */}
            <a
                href={`https://polymarket.com/event/${opportunity.slug}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 flex items-center justify-center gap-2 w-full py-2 rounded-lg font-medium text-sm transition-colors bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white border border-white/5 hover:border-white/20"
            >
                <span>Voir sur Polymarket</span>
                <ExternalLink className="w-3 h-3" />
            </a>
        </div>
    );
}

export default function MonteCarloPanel() {
    const [opportunities, setOpportunities] = useState<EdgeOpportunity[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stats, setStats] = useState({ total: 0, analyzed: 0 });
    const [minEdge, setMinEdge] = useState(0.01);

    const fetchEdgeOpportunities = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/monte-carlo/edge?min_edge=${minEdge}&limit=20`);
            if (!response.ok) throw new Error('Failed to fetch');
            const data: EdgeResponse = await response.json();
            setOpportunities(data.opportunities);
            setStats({ total: data.total, analyzed: data.crypto_markets_analyzed });
        } catch (err) {
            setError('Erreur lors du chargement des opportunités Monte Carlo');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [minEdge]);

    useEffect(() => {
        fetchEdgeOpportunities();
    }, [fetchEdgeOpportunities]);

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <BarChart3 className="w-5 h-5 text-purple-400" />
                    <h2 className="text-lg font-bold text-white">Monte Carlo Analysis</h2>
                    <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 text-xs">
                        {stats.analyzed} marchés analysés
                    </span>
                </div>
                <button
                    onClick={fetchEdgeOpportunities}
                    disabled={loading}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Rafraîchir
                </button>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 p-3 rounded-lg bg-white/5">
                <span className="text-sm text-gray-400">Edge minimum:</span>
                <select
                    value={minEdge}
                    onChange={(e) => setMinEdge(parseFloat(e.target.value))}
                    className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm"
                >
                    <option value={0.01}>1%</option>
                    <option value={0.02}>2%</option>
                    <option value={0.05}>5%</option>
                    <option value={0.10}>10%</option>
                </select>
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
                    <span className="ml-3 text-gray-400">Calcul Monte Carlo en cours...</span>
                </div>
            ) : error ? (
                <div className="text-center py-12 text-red-400">
                    {error}
                </div>
            ) : opportunities.length === 0 ? (
                <div className="text-center py-12">
                    <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                    <p className="text-gray-400">Aucune opportunité d&apos;edge détectée</p>
                    <p className="text-gray-500 text-sm mt-2">
                        Baissez le seuil d&apos;edge minimum ou réessayez plus tard
                    </p>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {opportunities.map((opp) => (
                        <EdgeCard key={opp.market_id} opportunity={opp} />
                    ))}
                </div>
            )}

            {/* Explanation */}
            <div className="mt-6 p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <h4 className="text-sm font-bold text-purple-400 mb-2">💡 Comment ça marche ?</h4>
                <p className="text-xs text-gray-400 leading-relaxed">
                    Le modèle Monte Carlo simule 10,000 trajectoires de prix basées sur l&apos;historique (1 an de données horaires).
                    Il calcule la probabilité qu&apos;un actif atteigne un prix cible et compare cette estimation au prix Polymarket.
                    Un <strong className="text-green-400">edge positif</strong> signifie que Polymarket sous-estime la probabilité (opportunité d&apos;achat).
                    Un <strong className="text-red-400">edge négatif</strong> signifie que Polymarket surestime (opportunité de vente).
                </p>
            </div>
        </div>
    );
}
