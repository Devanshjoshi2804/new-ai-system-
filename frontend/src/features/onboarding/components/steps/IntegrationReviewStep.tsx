/**
 * Step 4: Review Integration - SIMPLIFIED
 * Focus on essential info only
 */
import React from 'react';
import { motion } from 'framer-motion';
import { CheckBadgeIcon, ServerIcon, CodeBracketIcon } from '@heroicons/react/24/outline';
import { OnboardingState } from '../../types/onboarding.types';

interface IntegrationReviewStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

const IntegrationReviewStep: React.FC<IntegrationReviewStepProps> = ({ onNext, onBack, state }) => {
  const integration = state.integrationReview;
  const baseUrl = integration?.api_spec?.baseUrl || integration?.apiSpec?.baseUrl || '';
  const endpoints = integration?.api_spec?.endpoints || integration?.apiSpec?.endpoints || [];

  // If no integration data, show error
  if (!integration) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 font-semibold">No integration data available</p>
        <p className="text-gray-500 mt-2">Please go back and try parsing again</p>
        <button
          onClick={onBack}
          className="mt-4 px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <CheckBadgeIcon className="w-8 h-8 text-primary-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Integration Ready!</h2>
          <p className="text-gray-600">
            Review discovered endpoints and start testing
          </p>
        </div>
      </div>

      {/* API Overview */}
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <ServerIcon className="w-5 h-5" />
          API Overview
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Base URL</p>
            <p className="font-mono text-sm text-gray-900 break-all">
              {baseUrl || 'Not detected (will need to provide)'}
            </p>
          </div>
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Endpoints Found</p>
            <p className="text-3xl font-bold text-primary-600">
              {endpoints.length}
            </p>
          </div>
        </div>
      </div>

      {/* Endpoints List */}
      {endpoints.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <CodeBracketIcon className="w-5 h-5" />
            Discovered Endpoints
          </h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {endpoints.slice(0, 10).map((endpoint: any, idx: number) => {
              const method = endpoint.method || endpoint.http_method || 'GET';
              const path = endpoint.path || endpoint.url || endpoint.endpoint || '';
              const summary = endpoint.summary || endpoint.description || '';
              
              const methodColors: Record<string, string> = {
                GET: 'bg-blue-100 text-blue-700',
                POST: 'bg-green-100 text-green-700',
                PUT: 'bg-yellow-100 text-yellow-700',
                DELETE: 'bg-red-100 text-red-700',
                PATCH: 'bg-purple-100 text-purple-700',
              };

              return (
                <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${methodColors[method] || 'bg-gray-100 text-gray-700'}`}>
                    {method}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-gray-900 break-all">{path}</p>
                    {summary && (
                      <p className="text-xs text-gray-600 mt-1">{summary}</p>
                    )}
                  </div>
                </div>
              );
            })}
            {endpoints.length > 10 && (
              <p className="text-sm text-gray-500 text-center py-2">
                + {endpoints.length - 10} more endpoints
              </p>
            )}
          </div>
        </div>
      )}

      {/* Next Steps */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">Next: Automated Testing</h3>
        <p className="text-blue-700">
          AI will automatically test all discovered endpoints and generate comprehensive results.
        </p>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        
        <button
          onClick={() => onNext({})}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Start Testing
        </button>
      </div>
    </motion.div>
  );
};

export default IntegrationReviewStep;
