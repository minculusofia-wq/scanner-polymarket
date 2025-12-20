import React from 'react';
import { DollarSign, ExternalLink } from 'lucide-react';
import { ArbitrageOpportunity, ArbitrageCardProps } from '@/types';

export function ArbitrageCard({ opportunity }: ArbitrageCardProps) {
    // Calculate the width of the progress bar (capped at 100% for the base, overflow for profit)
    // sum_yes_price e.g. 1.05 -> 105%

    const percentage = opportunity.sum_yes_price * 100;
    const profit = percentage - 100;

    return (
        <div className="bg-[#151921] border border-emerald-500/30 rounded-xl p-4 mb-4 hover:border-emerald-500/60 transition-colors group">
            <div className="flex flex-col gap-4">

                {/* Header */}
                <div className="flex justify-between items-start">
                    <div>
                        <h3 className="text-lg font-bold text-white group-hover:text-emerald-400 transition-colors">
                            {opportunity.event_title}
                        </h3>
                        <p className="text-sm text-gray-400">
                            {opportunity.market_count} Marchés liés • Arbitrage "Negative Risk"
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg flex items-center gap-2">
                            <DollarSign className="w-4 h-4 text-emerald-400" />
                            <span className="text-emerald-400 font-bold">Rendement: +{opportunity.profit_pct.toFixed(2)}%</span>
                        </div>
                        <a
                            href={`https://polymarket.com/event/${opportunity.event_slug}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-white transition-colors"
                        >
                            <ExternalLink className="w-5 h-5" />
                        </a>
                    </div>
                </div>

                {/* Progress Bar Visualization */}
                <div className="relative h-8 bg-gray-800 rounded-full overflow-hidden flex items-center">
                    {/* Background (100% Marker) */}
                    <div className="absolute left-[80%] top-0 bottom-0 w-0.5 bg-white/20 z-10" title="1.00 (Break-even)"></div>

                    {/* The Cost Part (1.0) */}
                    <div className="h-full bg-gray-600 flex items-center justify-center text-xs font-bold text-white/50" style={{ width: '80%' }}>
                        Coût (1.00$)
                    </div>

                    {/* The Profit Part (Overflow) */}
                    {/* We map the overflow. If total is 1.05, and 1.0 is 80% width. Then 0.05 is (0.05/1.0)*80% ? No.
                        Let's say Total Width = 1.0 + Profit.
                        Visual scale: Let 1.0 = 80% of the bar width.
                        If Sum = 1.05. Then bar should fill 80% + (0.05 * 80%) = 84%.
                    */}
                    <div
                        className="h-full bg-emerald-500 flex items-center justify-center text-xs font-bold text-black"
                        style={{ width: `${(profit / 100) * 80}%` }}
                    >
                        Profit
                    </div>
                </div>

                <div className="flex justify-between text-xs text-gray-500 font-mono">
                    <span>Somme des Prix OUI : {opportunity.sum_yes_price.toFixed(3)}$</span>
                    <span>Cible : Acheter tous les NON</span>
                </div>

                {/* Market Details (Collapsed or Grid) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {opportunity.markets.slice(0, 6).map((market) => (
                        <div key={market.id} className="flex justify-between items-center bg-white/5 px-3 py-2 rounded border border-white/5">
                            <span className="text-sm truncate max-w-[150px]" title={market.question}>{market.question}</span>
                            <div className="flex items-center gap-3">
                                <span className="text-red-400 font-bold text-sm">NON: {(1 - market.yes_price).toFixed(2)}$</span>
                                <span className="text-xs text-gray-500">Liq: ${(market.liquidity / 1000).toFixed(0)}k</span>
                            </div>
                        </div>
                    ))}
                    {opportunity.markets.length > 6 && (
                        <div className="text-center text-xs text-gray-500 py-1">
                            + {opportunity.markets.length - 6} autres marchés...
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
