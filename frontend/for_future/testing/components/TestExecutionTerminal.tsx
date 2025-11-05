/**
 * Test Execution Terminal - Complete View
 * Shows real-time test execution with terminal and progress
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTestStream } from '../hooks/useTestStream';
import { TerminalViewer } from './TerminalViewer';
import { TestProgressBar } from './TestProgress';
import { ConnectionStatus } from '../../../types/testEvents';
import {
  SignalIcon,
  SignalSlashIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';

interface TestExecutionTerminalProps {
  testId: string;
  baseUrl?: string;
  onComplete?: (stats: any) => void;
  className?: string;
}

export const TestExecutionTerminal: React.FC<TestExecutionTerminalProps> = ({
  testId,
  baseUrl,
  onComplete,
  className = ''
}) => {
  const {
    status,
    isConnected,
    logs,
    progress,
    stats,
    connect,
    disconnect,
    clearLogs
  } = useTestStream({
    testId,
    baseUrl,
    autoConnect: true,
    onComplete
  });

  const [autoScroll, setAutoScroll] = useState(true);

  const getStatusBadge = () => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
            <SignalIcon className="w-4 h-4" />
            <span>Connected</span>
          </div>
        );
      case ConnectionStatus.CONNECTING:
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-sm">
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
            <span>Connecting...</span>
          </div>
        );
      case ConnectionStatus.ERROR:
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm">
            <SignalSlashIcon className="w-4 h-4" />
            <span>Error</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-gray-500/20 text-gray-400 rounded-full text-sm">
            <SignalSlashIcon className="w-4 h-4" />
            <span>Disconnected</span>
          </div>
        );
    }
  };

  const exportLogs = () => {
    const logsText = logs.map(log => 
      `[${new Date(log.timestamp).toLocaleTimeString()}] ${log.data.level.toUpperCase()}: ${log.data.message}`
    ).join('\n');
    
    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-logs-${testId}-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`flex flex-col h-full bg-gray-900 rounded-xl overflow-hidden shadow-2xl ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-2xl">🧪</span>
            <span>Test Execution Terminal</span>
          </div>
          {getStatusBadge()}
        </div>

        <div className="flex items-center gap-2">
          {!isConnected && (
            <button
              onClick={connect}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <ArrowPathIcon className="w-4 h-4" />
              Reconnect
            </button>
          )}
          
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              autoScroll
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            }`}
          >
            Auto-scroll
          </button>

          {logs.length > 0 && (
            <button
              onClick={exportLogs}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              title="Export logs"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              Export
            </button>
          )}
        </div>
      </div>

      {/* Progress Section */}
      {progress && (
        <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700">
          <TestProgressBar progress={progress} />
        </div>
      )}

      {/* Terminal Section */}
      <div className="flex-1 overflow-hidden">
        <TerminalViewer logs={logs} autoScroll={autoScroll} className="h-full" />
      </div>

      {/* Stats Footer (shown when complete) */}
      <AnimatePresence>
        {stats?.isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className={`px-4 py-3 border-t ${
              stats.failed === 0
                ? 'bg-green-900/30 border-green-700'
                : 'bg-red-900/30 border-red-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {stats.failed === 0 ? (
                  <CheckCircleIcon className="w-6 h-6 text-green-400" />
                ) : (
                  <XCircleIcon className="w-6 h-6 text-red-400" />
                )}
                
                <div className="flex items-center gap-6 text-sm">
                  <span className="text-green-400 font-medium">
                    ✓ {stats.passed} Passed
                  </span>
                  <span className="text-red-400 font-medium">
                    ✗ {stats.failed} Failed
                  </span>
                  <span className="text-gray-400">
                    ⏱ {stats.duration.toFixed(2)}s
                  </span>
                  <span className="text-gray-400">
                    Total: {stats.totalTests} tests
                  </span>
                </div>
              </div>

              <div className="text-2xl font-bold">
                {stats.failed === 0 ? (
                  <span className="text-green-400">100%</span>
                ) : (
                  <span className="text-yellow-400">
                    {Math.round((stats.passed / stats.totalTests) * 100)}%
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
