/**
 * Testing Report Viewer - Display comprehensive API test results
 */
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircleIcon,
  XCircleIcon,
  BeakerIcon,
  ClockIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { testingAPI, TestingResultsResponse } from '../../../lib/api/testing';

interface TestingReportViewerProps {
  testExecutionId: string;
}

const TestingReportViewer: React.FC<TestingReportViewerProps> = ({ testExecutionId }) => {
  const [results, setResults] = useState<TestingResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResults();
  }, [testExecutionId]);

  const loadResults = async () => {
    try {
      setLoading(true);
      const data = await testingAPI.getResults(testExecutionId);
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load test results');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
          <p className="text-gray-600">Loading test results...</p>
        </div>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error || 'No results found'}</p>
      </div>
    );
  }

  const passRate = Math.round(results.passRate);

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <BeakerIcon className="w-8 h-8 text-blue-600" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">API Testing Report</h2>
            <p className="text-sm text-gray-600">Test Execution ID: {testExecutionId}</p>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">{results.testedEndpoints}</p>
            <p className="text-xs text-gray-600 mt-1">Endpoints Tested</p>
          </div>
          <div className="bg-white rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{results.passedTests}</p>
            <p className="text-xs text-gray-600 mt-1">Tests Passed</p>
          </div>
          <div className="bg-white rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-red-600">{results.failedTests}</p>
            <p className="text-xs text-gray-600 mt-1">Tests Failed</p>
          </div>
          <div className="bg-white rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">{passRate}%</p>
            <p className="text-xs text-gray-600 mt-1">Pass Rate</p>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="mt-4 flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-gray-500" />
            <span className="text-gray-600">
              Total Time: {results.totalExecutionTime.toFixed(1)}s
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-gray-500" />
            <span className="text-gray-600">
              Avg Response: {results.averageResponseTime.toFixed(3)}s
            </span>
          </div>
        </div>
      </div>

      {/* Test Results by Endpoint */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Test Results by Endpoint</h3>

        {/* Group by endpoint */}
        <div className="space-y-3">
          {results.executionOrder.map((endpoint, index) => {
            const endpointResults = results.testResults.filter(r => r.endpoint === endpoint);
            const passed = endpointResults.filter(r => r.status === 'passed').length;
            const failed = endpointResults.length - passed;

            return (
              <motion.div
                key={endpoint}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {failed === 0 ? (
                      <CheckCircleIcon className="w-5 h-5 text-green-600" />
                    ) : (
                      <XCircleIcon className="w-5 h-5 text-red-600" />
                    )}
                    <span className="font-mono text-sm text-gray-900">{endpoint}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-green-600">{passed} passed</span>
                    {failed > 0 && <span className="text-red-600">{failed} failed</span>}
                  </div>
                </div>

                {/* Expandable test cases */}
                {endpointResults.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {endpointResults.map((test, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                        <span className="text-gray-700">{test.testCaseName || `Test ${idx + 1}`}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-500">{test.executionTime.toFixed(3)}s</span>
                          <span className={`px-2 py-0.5 rounded ${
                            test.status === 'passed' 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-red-100 text-red-700'
                          }`}>
                            {test.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Status Badge */}
      <div className={`border-2 rounded-xl p-4 text-center ${
        results.status === 'completed'
          ? 'bg-green-50 border-green-300'
          : 'bg-yellow-50 border-yellow-300'
      }`}>
        <p className="text-lg font-semibold text-gray-900">
          {results.status === 'completed'
            ? '✅ All Tests Passed Successfully'
            : `⚠️ ${results.failedTests} Test${results.failedTests > 1 ? 's' : ''} Failed`}
        </p>
      </div>
    </div>
  );
};

export default TestingReportViewer;

