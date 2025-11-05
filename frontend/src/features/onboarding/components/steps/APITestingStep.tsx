/**
 * Step 5: API Testing Step - SIMPLE VERSION
 * Clean, effective API testing
 */
import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import { OnboardingState } from '../../types/onboarding.types';
import { simpleTestingAPI, TestResponse, TestResult } from '../../../../lib/api/testing';

interface APITestingStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

const APITestingStep: React.FC<APITestingStepProps> = ({ onNext, onBack, state }) => {
  const [testResults, setTestResults] = useState<TestResponse | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentEndpoint, setCurrentEndpoint] = useState<string>('');
  const hasStartedRef = useRef(false);

  useEffect(() => {
    // Auto-start testing when component mounts
    if (!hasStartedRef.current) {
      hasStartedRef.current = true;
      startTesting();
    }
  }, []);

  const startTesting = async () => {
    if (!state.partnerId || !state.documentInfo?.uploadedDocIds?.[0]) {
      setError('Missing partner ID or documentation ID');
      return;
    }

    setIsTesting(true);
    setError(null);

    try {
      console.log('🧪 Starting simple API testing...');
      
      const response = await simpleTestingAPI.startTest({
        partnerId: state.partnerId,
        documentationId: state.documentInfo.uploadedDocIds[0],
        baseUrl: state.apiConfig?.baseUrl,
      });
      
      setTestResults(response);
      console.log('✅ Testing complete:', response);
    } catch (err: any) {
      setError(err.message || 'Testing failed');
      console.error('❌ Testing error:', err);
    } finally {
      setIsTesting(false);
    }
  };

  const isComplete = testResults && testResults.status === 'completed';
  const canProceed = isComplete;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">API Testing</h2>
        <p className="text-gray-600">
          Automated testing of your API endpoints
        </p>
      </div>

      {/* Testing Status */}
      {isTesting && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-blue-50 border border-blue-200 rounded-xl p-6"
        >
          <div className="flex items-center space-x-3 mb-4">
            <div className="animate-spin">
              <SparklesIcon className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-blue-900">
              Testing in Progress
            </h3>
          </div>
          <p className="text-blue-700">
            AI is analyzing your API documentation and testing endpoints...
          </p>
          {currentEndpoint && (
            <p className="text-sm text-blue-600 mt-2">
              Current: {currentEndpoint}
            </p>
          )}
        </motion.div>
      )}

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 border border-red-200 rounded-xl p-6"
        >
          <div className="flex items-center space-x-3 mb-2">
            <XCircleIcon className="w-6 h-6 text-red-600" />
            <h3 className="text-lg font-semibold text-red-900">Testing Failed</h3>
          </div>
          <p className="text-red-700">{error}</p>
        </motion.div>
      )}

      {/* Results Display */}
      {testResults && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Summary */}
          <div className="bg-gradient-to-br from-green-50 to-blue-50 border border-green-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <CheckCircleIcon className="w-8 h-8 text-green-600" />
              <h3 className="text-xl font-bold text-gray-900">Testing Complete!</h3>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4">
                <div className="text-2xl font-bold text-gray-900">{testResults.total_tests}</div>
                <div className="text-sm text-gray-600">Total Tests</div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-2xl font-bold text-green-600">{testResults.passed}</div>
                <div className="text-sm text-gray-600">Passed</div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-2xl font-bold text-red-600">{testResults.failed}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-600">{testResults.pass_rate.toFixed(1)}%</div>
                <div className="text-sm text-gray-600">Pass Rate</div>
              </div>
            </div>

            <div className="mt-4 text-sm text-gray-600">
              <div>Base URL: <span className="font-mono text-gray-900">{testResults.base_url}</span></div>
              <div>Execution Time: {testResults.execution_time.toFixed(2)}s</div>
            </div>
          </div>

          {/* Individual Results */}
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-900">Endpoint Results:</h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {testResults.results.map((result: TestResult, idx: number) => (
                <div
                  key={idx}
                  className={`border rounded-lg p-4 ${
                    result.success
                      ? 'bg-green-50 border-green-200'
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        {result.success ? (
                          <CheckCircleIcon className="w-5 h-5 text-green-600" />
                        ) : (
                          <XCircleIcon className="w-5 h-5 text-red-600" />
                        )}
                        <span className="font-mono text-sm font-semibold">
                          {result.endpoint}
                        </span>
                      </div>
                      <div className="mt-2 text-sm text-gray-600">
                        <div>Status: <span className={result.success ? 'text-green-700' : 'text-red-700'}>{result.status_code}</span></div>
                        <div>Attempts: {result.attempts}</div>
                        {result.error && (
                          <div className="text-red-700 mt-1">Error: {result.error}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        
        <button
          onClick={() => onNext({ testResults })}
          disabled={!canProceed}
          className={`px-6 py-2 rounded-lg font-medium transition-colors ${
            canProceed
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Complete Onboarding
        </button>
      </div>
    </div>
  );
};

export default APITestingStep;
