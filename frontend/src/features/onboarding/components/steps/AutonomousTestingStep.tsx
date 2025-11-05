/**
 * Autonomous Testing Step with Real-time Progress
 * Automatically analyzes documentation, generates tests, and executes them
 * Shows real-time progress updates
 */
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  BeakerIcon,
  DocumentMagnifyingGlassIcon,
  CpuChipIcon,
  RocketLaunchIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { OnboardingState } from '../../types/onboarding.types';

interface AutonomousTestingStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

interface ProgressStep {
  step_number: number;
  step_name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  data?: any;
  timestamp?: string;
}

interface Progress {
  operation_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_percentage: number;
  current_step: number;
  total_steps: number;
  steps: ProgressStep[];
  error?: string;
}

const AutonomousTestingStep: React.FC<AutonomousTestingStepProps> = ({
  onNext,
  onBack,
  state,
}) => {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [isStarted, setIsStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState('');
  const [autoExecute, setAutoExecute] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-start testing when component mounts
  useEffect(() => {
    if (!isStarted && state.partnerId) {
      // Auto-start after 2 seconds
      const timer = setTimeout(() => {
        startAutonomousTesting();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [state.partnerId]);

  const startAutonomousTesting = async () => {
    try {
      setIsStarted(true);
      setError(null);

      // Get the uploaded file from state
      const file = state.uploadedFiles?.[0];
      if (!file) {
        throw new Error('No documentation file found');
      }

      // Prepare form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('partner_id', state.partnerId || 'default');
      formData.append('base_url', baseUrl || 'https://api.example.com');
      formData.append('auto_execute', String(autoExecute));

      // Start the pipeline
      const response = await fetch(
        'http://localhost:8000/api/autonomous-testing-realtime/start-full-pipeline',
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error('Failed to start autonomous testing');
      }

      const result = await response.json();
      const operationId = result.operation_id;

      // Connect to progress stream
      connectToProgressStream(operationId);
    } catch (err: any) {
      console.error('Error starting autonomous testing:', err);
      setError(err.message || 'Failed to start testing');
      setIsStarted(false);
    }
  };

  const connectToProgressStream = (operationId: string) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create new EventSource for SSE
    const eventSource = new EventSource(
      `http://localhost:8000/api/autonomous-testing-realtime/progress-stream/${operationId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setProgress(data);

        // Auto-advance when completed
        if (data.status === 'completed') {
          setTimeout(() => {
            onNext({ testingResults: data });
          }, 2000);
        }
      } catch (err) {
        console.error('Error parsing progress data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource error:', err);
      eventSource.close();
      setError('Connection to progress stream lost');
    };

    eventSourceRef.current = eventSource;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-6 h-6 text-green-500" />;
      case 'in_progress':
        return <ClockIcon className="w-6 h-6 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircleIcon className="w-6 h-6 text-red-500" />;
      default:
        return <ClockIcon className="w-6 h-6 text-gray-400" />;
    }
  };

  const getStepDetails = (step: ProgressStep) => {
    const data = step.data || {};

    if (step.step_name.includes('Analyzing')) {
      return (
        <div className="mt-2 text-sm text-gray-600">
          {data.endpoints_found && (
            <p>✅ Found {data.endpoints_found} API endpoints</p>
          )}
          {data.test_scenarios && (
            <p>✅ Generated {data.test_scenarios} test scenarios</p>
          )}
        </div>
      );
    }

    if (step.step_name.includes('Generating')) {
      return (
        <div className="mt-2 text-sm text-gray-600">
          {data.tests_generated && (
            <p>✅ Created {data.tests_generated} comprehensive test cases</p>
          )}
          {data.test_data_sets && (
            <p>✅ Generated {data.test_data_sets} test data sets</p>
          )}
        </div>
      );
    }

    if (step.step_name.includes('Executing')) {
      return (
        <div className="mt-2 text-sm text-gray-600">
          {data.total_tests && (
            <>
              <p>✅ Ran {data.total_tests} tests</p>
              <p className="text-green-600">
                ✅ {data.passed} passed ({data.pass_rate?.toFixed(1)}%)
              </p>
              {data.failed > 0 && (
                <p className="text-orange-600">⚠️ {data.failed} failed (auto-fixed)</p>
              )}
            </>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full mb-4"
        >
          <CpuChipIcon className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          🤖 Autonomous API Testing
        </h2>
        <p className="text-gray-600">
          AI is analyzing your API documentation and running comprehensive tests
        </p>
      </div>

      {/* Configuration (before starting) */}
      {!isStarted && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg shadow-md p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Base URL
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.example.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="autoExecute"
              checked={autoExecute}
              onChange={(e) => setAutoExecute(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="autoExecute" className="ml-2 text-sm text-gray-700">
              Auto-execute tests after generation
            </label>
          </div>

          <button
            onClick={startAutonomousTesting}
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all"
          >
            🚀 Start Autonomous Testing
          </button>
        </motion.div>
      )}

      {/* Progress Display */}
      {isStarted && progress && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Overall Progress Bar */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Overall Progress
              </span>
              <span className="text-sm font-bold text-blue-600">
                {progress.progress_percentage}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress.progress_percentage}%` }}
                transition={{ duration: 0.5 }}
                className="bg-gradient-to-r from-purple-600 to-blue-600 h-3 rounded-full"
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Step {progress.current_step} of {progress.total_steps}
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-3">
            <AnimatePresence>
              {progress.steps.map((step, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.1 }}
                  className={`bg-white rounded-lg shadow-md p-4 border-l-4 ${
                    step.status === 'completed'
                      ? 'border-green-500'
                      : step.status === 'in_progress'
                      ? 'border-blue-500'
                      : step.status === 'failed'
                      ? 'border-red-500'
                      : 'border-gray-300'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-1">
                      {getStepIcon(step.status)}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-gray-900">
                        {step.step_name}
                      </h3>
                      {step.data?.message && (
                        <p className="text-sm text-gray-600 mt-1">
                          {step.data.message}
                        </p>
                      )}
                      {getStepDetails(step)}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Success Message */}
          {progress.status === 'completed' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg shadow-md p-6 text-center"
            >
              <CheckCircleIcon className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                🎉 Testing Complete!
              </h3>
              <p className="text-gray-600">
                Your API has been fully analyzed and tested. Advancing to results...
              </p>
            </motion.div>
          )}

          {/* Error Message */}
          {progress.status === 'failed' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-red-50 rounded-lg shadow-md p-6"
            >
              <div className="flex items-start space-x-3">
                <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-red-900 mb-2">
                    Testing Failed
                  </h3>
                  <p className="text-red-700">{progress.error}</p>
                  <button
                    onClick={startAutonomousTesting}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      )}

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4"
        >
          <p className="text-red-800">{error}</p>
        </motion.div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-6">
        <button
          onClick={onBack}
          disabled={isStarted && progress?.status === 'in_progress'}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          ← Back
        </button>

        {progress?.status === 'completed' && (
          <button
            onClick={() => onNext({ testingResults: progress })}
            className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all"
          >
            View Results →
          </button>
        )}
      </div>
    </div>
  );
};

export default AutonomousTestingStep;
