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

    // Store latest callbacks in a ref to avoid reconnecting when they change
    const callbacksRef = useRef(options);

    // Update callbacks whenever options change
    useEffect(() => {
        callbacksRef.current = options;
    }, [options]);

    const connect = useCallback(() => {
        // Don't reconnect if already connected
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            // Get WebSocket URL from environment or current origin
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.hostname;
            const port = process.env.NEXT_PUBLIC_WS_PORT || '8000';
            const wsUrl = `${protocol}//${host}:${port}/ws`;

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('🔌 WebSocket connected');
                setIsConnected(true);
                setConnectionError(null);
                callbacksRef.current.onConnect?.();

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
                                callbacksRef.current.onSignalsUpdate?.(
                                    message.data.signals || [],
                                    message.data.cached || false,
                                    message.data.cache_age || null,
                                    message.error || null
                                );
                            }
                            break;

                        case 'whale_trade':
                            if (message.data) {
                                callbacksRef.current.onWhaleTrade?.(message.data);
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
                callbacksRef.current.onDisconnect?.();

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
    }, []); // Empty dependency array - connect function never changes

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
