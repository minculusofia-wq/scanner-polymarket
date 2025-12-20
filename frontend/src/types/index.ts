/**
 * Centralized TypeScript types for Polymarket Scanner
 */
import { LucideIcon } from 'lucide-react';

// ============ Signal Types ============

export type SignalLevel = 'watch' | 'interesting' | 'strong' | 'opportunity';
export type Direction = 'YES' | 'NO';
export type TradeRecommendation = 'BUY_YES' | 'BUY_NO' | 'HOLD';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Signal {
    id: string;
    market_id: string;
    condition_id: string;
    slug: string;
    market_question: string;
    score: number;
    level: SignalLevel;
    direction: Direction | string;
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
    created_at?: string;
}

// ============ Settings Types ============

export interface ScannerSettings {
    minWhaleCount: number;
    minUniqueWhales: number;
    minVolumeUsd: number;
    minLiquidity: number;
    maxSpread: number;
    maxTimeHours: number;
    minNewsCount: number;
    minScore: number;
    showWatchLevel: boolean;
}

// ============ Whale Types ============

export interface WhaleTrade {
    id: string;
    trader: string;
    market_id: string;
    market_question: string;
    slug: string;
    side: Direction;
    amount: number;
    price: number;
    timestamp: string;
    size_usd: number;
}

// ============ Arbitrage Types ============

export interface MarketDetail {
    id: string;
    question: string;
    yes_price: number;
    liquidity: number;
}

export interface ArbitrageOpportunity {
    event_id: string;
    event_slug: string;
    event_title: string;
    market_count: number;
    sum_yes_price: number;
    profit_pct: number;
    markets: MarketDetail[];
}

// ============ Monte Carlo Types ============

export interface EdgeOpportunity {
    market_id: string;
    market_question: string;
    slug: string;
    polymarket_yes_price: number;
    polymarket_no_price: number;
    mc_probability: number;
    mc_confidence_low: number;
    mc_confidence_high: number;
    edge: number;
    edge_percent: number;
    recommendation: TradeRecommendation;
    confidence: Confidence;
    asset: string;
    target_price: number;
    end_date: string;
    current_price: number;
}

export interface EdgeResponse {
    opportunities: EdgeOpportunity[];
    total: number;
    crypto_markets_analyzed: number;
}

// ============ WebSocket Types ============

export interface SignalsData {
    signals?: Signal[];
    cached?: boolean;
    cache_age?: number | null;
}

export interface WebSocketMessage {
    type: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data?: unknown;
    error?: string;
    message?: string;
}

export interface WebSocketCallbacks {
    onSignalsUpdate?: (signals: Signal[], cached: boolean, cacheAge: number | null, error: string | null) => void;
    onWhaleTrade?: (trade: WhaleTrade) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
}

// ============ Component Props Types ============

export interface StatCardProps {
    title: string;
    value: string;
    icon: LucideIcon;
    color: 'sky' | 'green' | 'purple' | 'orange' | 'yellow' | 'indigo' | 'rose' | 'fuchsia';
}

export interface SignalCardProps {
    signal: Signal;
}

export interface ArbitrageCardProps {
    opportunity: ArbitrageOpportunity;
}
