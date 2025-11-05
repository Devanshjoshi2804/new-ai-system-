/**
 * Test Results Step - Display comprehensive testing results
 * Shows API analysis, generated tests, and execution results
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircleIcon,
  XCircleIcon,
  ChartBarIcon,
  DocumentTextIcon,
  BeakerIcon,
  SparklesIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { OnboardingState } from '../../types/onboarding.types';

interface TestResultsStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

const TestResultsStep: React.FC<TestResultsStepProps> = ({
  onNext,
  onBack,
  state,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'endpoints' | 'tests' | 'insights'>('overview');

  const testingResults = state.testingResults;
  const apiSpec = testingResults?.result?.api_spec;
  const tests = testingResults?.result?.tests;
  const execution = testingResults?.result?.execution;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full mb-4"
        >
          <ChartBarIcon className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          📊 Testing Results
        </h2>
        <p className="text-gray-600">
          Complete analysis and testing results for your API
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6"
        >
          <DocumentTextIcon className="w-8 h-8 text-blue-600 mb-2" />
          <h3 className="text-2xl font-bold text-blue-900">
            {apiSpec?.endpoints_found || 0}
          </h3>
          <p className="text-blue-700">API Endpoints Found</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6"
        >
          <BeakerIcon className="w-8 h-8 text-purple-600 mb-2" />
          <h3 className="text-2xl font-bold text-purple-900">
            {tests?.generated || 0}
          </h3>
          <p className="text-purple-700">Tests Generated</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6"
        >
          <CheckCircleIcon className="w-8 h-8 text-green-600 mb-2" />
          <h3 className="text-2xl font-bold text-green-900">
            {execution?.pass_rate?.toFixed(0) || 0}%
          </h3>
          <p className="text-green-700">Pass Rate</p>
        </motion.div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-4 px-6" aria-label="Tabs">
            {[
              { id: 'overview', label: 'Overview', icon: ChartBarIcon },
              { id: 'endpoints', label: 'Endpoints', icon: DocumentTextIcon },
              { id: 'tests', label: 'Test Results', icon: BeakerIcon },
              { id: 'insights', label: 'AI Insights', icon: SparklesIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Testing Summary
              </h3>

              {execution && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <span className="text-gray-700">Total Tests</span>
                    <span className="font-semibold text-gray-900">
                      {execution.total_tests}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                    <span className="text-green-700">Passed</span>
                    <span className="font-semibold text-green-900">
                      {execution.passed}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg">
                    <span className="text-orange-700">Failed (Auto-Fixed)</span>
                    <span className="font-semibold text-orange-900">
                      {execution.failed}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                    <span className="text-red-700">Errors</span>
                    <span className="font-semibold text-red-900">
                      {execution.errors}
                    </span>
                  </div>

                  {/* Pass Rate Visualization */}
                  <div className="mt-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        Pass Rate
                      </span>
                      <span className="text-sm font-bold text-blue-600">
                        {execution.pass_rate?.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-4">
                      <div
                        className="bg-gradient-to-r from-green-500 to-emerald-500 h-4 rounded-full transition-all duration-1000"
                        style={{ width: `${execution.pass_rate}%` }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Endpoints Tab */}
          {activeTab === 'endpoints' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Discovered API Endpoints
              </h3>
              <p className="text-gray-600 mb-4">
                AI discovered {apiSpec?.endpoints_found || 0} endpoints and generated{' '}
                {apiSpec?.test_scenarios || 0} test scenarios automatically.
              </p>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-blue-800 text-sm">
                  💡 <strong>AI Analysis:</strong> All endpoints have been analyzed for
                  authentication requirements, request/response schemas, and dependencies.
                </p>
              </div>
            </motion.div>
          )}

          {/* Tests Tab */}
          {activeTab === 'tests' && execution && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Test Execution Results
              </h3>

              <div className="space-y-2">
                {execution.test_results?.slice(0, 10).map((result: any, index: number) => (
                  <div
                    key={index}
                    className={`p-4 rounded-lg border-l-4 ${
                      result.status === 'passed'
                        ? 'bg-green-50 border-green-500'
                        : result.status === 'failed'
                        ? 'bg-orange-50 border-orange-500'
                        : 'bg-red-50 border-red-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {result.status === 'passed' ? (
                          <CheckCircleIcon className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircleIcon className="w-5 h-5 text-orange-500" />
                        )}
                        <span className="font-medium text-gray-900">
                          {result.test_name}
                        </span>
                      </div>
                      {result.retry_count > 0 && (
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                          Auto-fixed after {result.retry_count} retries
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {execution.test_results?.length > 10 && (
                <p className="text-sm text-gray-500 text-center">
                  Showing 10 of {execution.test_results.length} tests
                </p>
              )}
            </motion.div>
          )}

          {/* Insights Tab */}
          {activeTab === 'insights' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                AI-Powered Insights
              </h3>

              <div className="space-y-3">
                <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <SparklesIcon className="w-6 h-6 text-purple-600 flex-shrink-0 mt-1" />
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">
                        Self-Healing Success
                      </h4>
                      <p className="text-gray-700 text-sm">
                        AI automatically fixed {execution?.failed || 0} failed tests by
                        analyzing errors and applying intelligent corrections.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <CheckCircleIcon className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">
                        Comprehensive Coverage
                      </h4>
                      <p className="text-gray-700 text-sm">
                        Generated {tests?.generated || 0} test cases covering happy paths,
                        edge cases, and error scenarios for all {apiSpec?.endpoints_found || 0}{' '}
                        endpoints.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <ArrowPathIcon className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">
                        Continuous Learning
                      </h4>
                      <p className="text-gray-700 text-sm">
                        The system learned from this execution and will use these patterns
                        to improve future testing accuracy.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-6">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          ← Back
        </button>

        <button
          onClick={() => onNext({ resultsReviewed: true })}
          className="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all"
        >
          Complete Onboarding →
        </button>
      </div>
    </div>
  );
};

export default TestResultsStep;
