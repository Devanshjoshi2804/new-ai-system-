/**
 * WebSocket client for real-time test execution streaming
 */

import { TestEvent, ConnectionStatus } from '../../types/testEvents';

export interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (event: TestEvent) => void;
}

export class TestWebSocket {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isManualClose = false;
  private messageHandlers: Set<(event: TestEvent) => void> = new Set();
  private statusHandlers: Set<(status: ConnectionStatus) => void> = new Set();
  
  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      ...config
    };
  }
  
  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    this.isManualClose = false;
    this.notifyStatus(ConnectionStatus.CONNECTING);
    
    try {
      console.log(`🔌 Connecting to WebSocket: ${this.config.url}`);
      this.ws = new WebSocket(this.config.url);
      
      this.ws.onopen = () => {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
        this.notifyStatus(ConnectionStatus.CONNECTED);
        this.config.onOpen?.();
      };
      
      this.ws.onclose = (event) => {
        console.log('👋 WebSocket closed', event.code, event.reason);
        this.notifyStatus(ConnectionStatus.DISCONNECTED);
        this.config.onClose?.();
        
        // Attempt reconnection if not manual close
        if (!this.isManualClose && this.shouldReconnect()) {
          this.scheduleReconnect();
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        this.notifyStatus(ConnectionStatus.ERROR);
        this.config.onError?.(error);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as TestEvent;
          console.log('📨 WebSocket message:', data.type);
          
          // Notify all message handlers
          this.messageHandlers.forEach(handler => handler(data));
          this.config.onMessage?.(data);
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('❌ Error creating WebSocket:', error);
      this.notifyStatus(ConnectionStatus.ERROR);
      
      if (this.shouldReconnect()) {
        this.scheduleReconnect();
      }
    }
  }
  
  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManualClose = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.notifyStatus(ConnectionStatus.DISCONNECTED);
  }
  
  /**
   * Send message to server
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send message');
    }
  }
  
  /**
   * Add message handler
   */
  onMessage(handler: (event: TestEvent) => void): () => void {
    this.messageHandlers.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler);
    };
  }
  
  /**
   * Add status handler
   */
  onStatus(handler: (status: ConnectionStatus) => void): () => void {
    this.statusHandlers.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.statusHandlers.delete(handler);
    };
  }
  
  /**
   * Get current connection status
   */
  getStatus(): ConnectionStatus {
    if (!this.ws) return ConnectionStatus.DISCONNECTED;
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return ConnectionStatus.CONNECTING;
      case WebSocket.OPEN:
        return ConnectionStatus.CONNECTED;
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return ConnectionStatus.DISCONNECTED;
      default:
        return ConnectionStatus.DISCONNECTED;
    }
  }
  
  /**
   * Check if should attempt reconnection
   */
  private shouldReconnect(): boolean {
    const maxAttempts = this.config.maxReconnectAttempts ?? 5;
    return this.reconnectAttempts < maxAttempts;
  }
  
  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const interval = this.config.reconnectInterval ?? 3000;
    const delay = Math.min(interval * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    console.log(`🔄 Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}`);
      this.connect();
    }, delay);
  }
  
  /**
   * Notify status handlers
   */
  private notifyStatus(status: ConnectionStatus): void {
    this.statusHandlers.forEach(handler => handler(status));
  }
}

/**
 * Create WebSocket connection for test execution
 */
export function createTestWebSocket(testId: string, baseUrl: string = 'ws://localhost:8000'): TestWebSocket {
  const wsUrl = `${baseUrl}/api/ws/test-execution/${testId}`;
  
  return new TestWebSocket({
    url: wsUrl,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5
  });
}
