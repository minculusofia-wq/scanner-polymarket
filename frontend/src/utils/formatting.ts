/**
 * Centralized formatting utilities for Polymarket Scanner
 */

/**
 * Format a currency value with appropriate suffix (K, M)
 */
export function formatCurrency(value: number): string {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
}

/**
 * Format a price value with k suffix for thousands
 */
export function formatPrice(price: number): string {
    if (price >= 1000) return `$${(price / 1000).toFixed(0)}k`;
    return `$${price.toFixed(0)}`;
}

/**
 * Format a timestamp as relative time (e.g., "5m ago", "2h ago")
 */
export function formatTimeAgo(timestamp: string): string {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Format a percentage value
 */
export function formatPercentage(value: number, decimals: number = 1): string {
    return `${(value * 100).toFixed(decimals)}%`;
}
