'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
    type: string;
    data?: any;
    error?: string;
    message?: string;
}

interface UseWebSocketOptions {
    onSignalsUpdate?: (signals: any[], cached: boolean, cacheAge: number | null, error: string | null) => void;
    onWhaleTrade?: (trade: any) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        // Don't reconnect if already connected
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            // Get WebSocket URL from current origin
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//localhost:8000/ws`;

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('🔌 WebSocket connected');
                setIsConnected(true);
                setConnectionError(null);
                options.onConnect?.();

                // Start ping interval to keep connection alive
                pingIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 25000);
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);

                    switch (message.type) {
                        case 'signals_update':
                            if (message.data) {
                                options.onSignalsUpdate?.(
                                    message.data.signals || [],
                                    message.data.cached || false,
                                    message.data.cache_age || null,
                                    message.error || null
                                );
                            }
                            break;

                        case 'whale_trade':
                            if (message.data) {
                                options.onWhaleTrade?.(message.data);
                            }
                            break;

                        case 'connection_ack':
                            console.log('✅ WebSocket acknowledged:', message.message);
                            break;

                        case 'pong':
                            // Heartbeat response, connection is alive
                            break;

                        default:
                            console.log('Unknown message type:', message.type);
                    }
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                setIsConnected(false);
                options.onDisconnect?.();

                // Clear ping interval
                if (pingIntervalRef.current) {
                    clearInterval(pingIntervalRef.current);
                }

                // Reconnect after 5 seconds
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('🔄 Attempting to reconnect...');
                    connect();
                }, 5000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setConnectionError('WebSocket connection error');
            };

        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            setConnectionError('Failed to connect to WebSocket');
        }
    }, [options]);

    const disconnect = useCallback(() => {
        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }

        // Clear ping interval
        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
        }

        // Close WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    // Connect on mount, disconnect on unmount
    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return {
        isConnected,
        connectionError,
        reconnect: connect
    };
}
