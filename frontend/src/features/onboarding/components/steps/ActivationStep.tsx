/**
 * Step 5: Activation & Success
 */
import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircleIcon, SparklesIcon, RocketLaunchIcon } from '@heroicons/react/24/solid';
import { OnboardingState } from '../../types/onboarding.types';

interface ActivationStepProps {
  onComplete: () => void;
  state: OnboardingState;
}

const ActivationStep: React.FC<ActivationStepProps> = ({ onComplete, state }) => {
  const handleGoToChat = () => {
    // Navigate to chat interface
    window.location.href = '/chat';
  };

  const handleGoToDashboard = () => {
    // Navigate to dashboard
    window.location.href = '/dashboard';
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center py-12"
    >
      {/* Success Icon */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
        className="inline-flex items-center justify-center w-24 h-24 bg-green-100 rounded-full mb-6"
      >
        <CheckCircleIcon className="w-16 h-16 text-green-600" />
      </motion.div>

      {/* Success Message */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <h2 className="text-3xl font-bold text-gray-900 mb-3">
          🎉 Integration Active!
        </h2>
        <p className="text-lg text-gray-600 mb-8">
          Your AI-powered logistics integration is now live and ready to use
        </p>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-12"
      >
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
          <SparklesIcon className="w-8 h-8 text-blue-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">
            {state.integrationReview?.apiSpec?.endpoints?.length || 0}
          </p>
          <p className="text-sm text-gray-600">Endpoints Integrated</p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6">
          <RocketLaunchIcon className="w-8 h-8 text-green-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">
            {state.integrationReview?.workflows?.length || 0}
          </p>
          <p className="text-sm text-gray-600">Workflows Learned</p>
        </div>

        <div className="bg-gradient-to-br from-yellow-50 to-amber-50 border border-yellow-200 rounded-xl p-6">
          <CheckCircleIcon className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">
            {state.apiTestingProgress?.passedTests || 0}/{(state.apiTestingProgress?.passedTests || 0) + (state.apiTestingProgress?.failedTests || 0)}
          </p>
          <p className="text-sm text-gray-600">Tests Passed</p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-6">
          <CheckCircleIcon className="w-8 h-8 text-purple-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">Ready</p>
          <p className="text-sm text-gray-600">Autonomous AI Active</p>
        </div>
      </motion.div>

      {/* Next Steps */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="bg-gradient-to-r from-primary-50 to-blue-50 border border-primary-200 rounded-xl p-8 mb-8"
      >
        <h3 className="text-xl font-semibold text-gray-900 mb-4">What's Next?</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Chat with AI</p>
              <p className="text-sm text-gray-600">
                Start using natural language to execute operations
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Test APIs</p>
              <p className="text-sm text-gray-600">
                Try booking, tracking, and other operations
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Monitor Dashboard</p>
              <p className="text-sm text-gray-600">
                Track usage, performance, and analytics
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold">
              4
            </div>
            <div>
              <p className="font-medium text-gray-900 mb-1">Iterate</p>
              <p className="text-sm text-gray-600">
                Add more docs, refine workflows, improve
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1 }}
        className="flex flex-wrap gap-4 justify-center"
      >
        <button
          onClick={handleGoToChat}
          className="px-8 py-4 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors font-semibold text-lg shadow-lg"
        >
          Start Chatting with AI 🤖
        </button>
        <button
          onClick={handleGoToDashboard}
          className="px-8 py-4 border-2 border-primary-600 text-primary-600 rounded-xl hover:bg-primary-50 transition-colors font-semibold text-lg"
        >
          Go to Dashboard
        </button>
        <button
          onClick={() => window.location.href = '/ocr'}
          className="px-8 py-4 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-semibold text-lg"
        >
          Test OCR Viewer ✨
        </button>
      </motion.div>

      {/* Tenant Info */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="mt-8 p-4 bg-gray-50 rounded-lg"
      >
        <p className="text-sm text-gray-600">
          <span className="font-medium">Partner ID:</span> {state.partnerId}
        </p>
        <p className="text-sm text-gray-600">
          <span className="font-medium">Tenant ID:</span> {state.tenantId}
        </p>
      </motion.div>
    </motion.div>
  );
};

export default ActivationStep;

