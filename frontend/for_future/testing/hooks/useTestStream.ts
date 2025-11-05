/**
 * React hook for WebSocket test streaming
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { TestWebSocket, createTestWebSocket } from '../../../lib/websocket/testSocket';
import {
  TestEvent,
  ConnectionStatus,
  EventType,
  TestProgress,
  TestStats,
  TestLogEvent
} from '../../../types/testEvents';

export interface UseTestStreamOptions {
  testId: string;
  baseUrl?: string;
  autoConnect?: boolean;
  onComplete?: (stats: TestStats) => void;
}

export interface UseTestStreamReturn {
  // Connection state
  status: ConnectionStatus;
  isConnected: boolean;
  
  // Test data
  events: TestEvent[];
  logs: TestLogEvent[];
  progress: TestProgress | null;
  stats: TestStats | null;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  clearLogs: () => void;
  
  // WebSocket instance (for advanced usage)
  ws: TestWebSocket | null;
}

export function useTestStream(options: UseTestStreamOptions): UseTestStreamReturn {
  const { testId, baseUrl, autoConnect = true, onComplete } = options;
  
  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const [events, setEvents] = useState<TestEvent[]>([]);
  const [logs, setLogs] = useState<TestLogEvent[]>([]);
  const [progress, setProgress] = useState<TestProgress | null>(null);
  const [stats, setStats] = useState<TestStats | null>(null);
  
  const wsRef = useRef<TestWebSocket | null>(null);
  const onCompleteRef = useRef(onComplete);
  
  // Update onComplete ref
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);
  
  // Handle incoming events
  const handleEvent = useCallback((event: TestEvent) => {
    setEvents(prev => [...prev, event]);
    
    switch (event.type) {
      case EventType.TEST_START:
        setProgress({
          currentStep: 0,
          totalSteps: event.data.total_steps,
          stepName: 'Starting...',
          percentage: 0,
          successCount: 0,
          failureCount: 0,
          warningCount: 0
        });
        setStats({
          totalTests: event.data.total_steps,
          passed: 0,
          failed: 0,
          duration: 0,
          isComplete: false
        });
        break;
      
      case EventType.TEST_PROGRESS:
        setProgress(prev => ({
          currentStep: event.data.step,
          totalSteps: event.data.total_steps,
          stepName: event.data.step_name,
          percentage: event.data.percentage,
          successCount: prev?.successCount ?? 0,
          failureCount: prev?.failureCount ?? 0,
          warningCount: prev?.warningCount ?? 0
        }));
        break;
      
      case EventType.TEST_LOG:
        setLogs(prev => [...prev, event as TestLogEvent]);
        break;
      
      case EventType.TEST_SUCCESS:
        setProgress(prev => prev ? {
          ...prev,
          successCount: prev.successCount + 1
        } : null);
        break;
      
      case EventType.TEST_ERROR:
        setProgress(prev => prev ? {
          ...prev,
          failureCount: prev.failureCount + 1
        } : null);
        break;
      
      case EventType.TEST_WARNING:
        setProgress(prev => prev ? {
          ...prev,
          warningCount: prev.warningCount + 1
        } : null);
        break;
      
      case EventType.TEST_COMPLETE:
        setStats({
          totalTests: event.data.total_steps,
          passed: event.data.success_count,
          failed: event.data.failure_count,
          duration: event.data.duration,
          isComplete: true
        });
        
        // Call onComplete callback
        if (onCompleteRef.current) {
          onCompleteRef.current({
            totalTests: event.data.total_steps,
            passed: event.data.success_count,
            failed: event.data.failure_count,
            duration: event.data.duration,
            isComplete: true
          });
        }
        break;
    }
  }, []);
  
  // Connect function
  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.connect();
    }
  }, []);
  
  // Disconnect function
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
    }
  }, []);
  
  // Clear logs function
  const clearLogs = useCallback(() => {
    setEvents([]);
    setLogs([]);
    setProgress(null);
    setStats(null);
  }, []);
  
  // Initialize WebSocket
  useEffect(() => {
    const ws = createTestWebSocket(testId, baseUrl);
    wsRef.current = ws;
    
    // Subscribe to messages
    const unsubscribeMessage = ws.onMessage(handleEvent);
    const unsubscribeStatus = ws.onStatus(setStatus);
    
    // Auto-connect if enabled
    if (autoConnect) {
      ws.connect();
    }
    
    // Cleanup
    return () => {
      unsubscribeMessage();
      unsubscribeStatus();
      ws.disconnect();
    };
  }, [testId, baseUrl, autoConnect, handleEvent]);
  
  return {
    status,
    isConnected: status === ConnectionStatus.CONNECTED,
    events,
    logs,
    progress,
    stats,
    connect,
    disconnect,
    clearLogs,
    ws: wsRef.current
  };
}
