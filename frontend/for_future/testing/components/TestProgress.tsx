/**
 * Test Progress Component
 * Shows real-time test execution progress
 */
import React from 'react';
import { motion } from 'framer-motion';
import { TestProgress } from '../../../types/testEvents';

interface TestProgressBarProps {
  progress: TestProgress | null;
  className?: string;
}

export const TestProgressBar: React.FC<TestProgressBarProps> = ({
  progress,
  className = ''
}) => {
  if (!progress) {
    return (
      <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-center text-gray-400">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mr-3"></div>
          <span>Initializing test execution...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-4 space-y-3 ${className}`}>
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-300 font-medium">
            Step {progress.currentStep} of {progress.totalSteps}
          </span>
          <span className="text-blue-400 font-bold">
            {progress.percentage}%
          </span>
        </div>
        
        <div className="relative w-full bg-gray-700 rounded-full h-3 overflow-hidden">
          <motion.div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress.percentage}%` }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        </div>
      </div>

      {/* Current Step */}
      <div className="flex items-center gap-2 text-sm">
        <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        <span className="text-gray-300 truncate">
          {progress.stepName}
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3 pt-2">
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-400">
            {progress.successCount}
          </div>
          <div className="text-xs text-gray-400 mt-1">✓ Passed</div>
        </div>
        
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">
            {progress.failureCount}
          </div>
          <div className="text-xs text-gray-400 mt-1">✗ Failed</div>
        </div>
        
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-400">
            {progress.warningCount}
          </div>
          <div className="text-xs text-gray-400 mt-1">⚠ Warnings</div>
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  );
};
