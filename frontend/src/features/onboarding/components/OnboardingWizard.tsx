/**
 * Multi-step onboarding wizard for partners
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircleIcon } from '@heroicons/react/24/solid';
import { OnboardingStep, OnboardingState } from '../types/onboarding.types';
import CompanyInfoStep from './steps/CompanyInfoStep';
import DocumentUploadStep from './steps/DocumentUploadStep';
import ParsingProgressStep from './steps/ParsingProgressStep';
import OCRReviewStep from './steps/OCRReviewStep';
import IntegrationReviewStep from './steps/IntegrationReviewStep';
import APITestingStep from './steps/APITestingStep';
import ActivationStep from './steps/ActivationStep';

const steps = [
  { id: OnboardingStep.COMPANY_INFO, name: 'Company Info', description: 'Tell us about your company' },
  { id: OnboardingStep.DOCUMENT_UPLOAD, name: 'Upload Docs', description: 'Upload API documentation' },
  { id: OnboardingStep.PARSING_PROGRESS, name: 'OCR Extract', description: 'Extract text from PDF' },
  { id: OnboardingStep.OCR_REVIEW, name: 'Review OCR', description: 'Review extracted text' },
  { id: OnboardingStep.INTEGRATION_REVIEW, name: 'AI Analysis', description: 'AI finds endpoints' },
  { id: OnboardingStep.API_TESTING, name: 'API Testing', description: 'Test all endpoints' },
  { id: OnboardingStep.ACTIVATION, name: 'Activate', description: 'Activate integration' },
];

const OnboardingWizard: React.FC = () => {
  const [state, setState] = useState<OnboardingState>({
    currentStep: OnboardingStep.COMPANY_INFO,
    isComplete: false,
  });

  const handleNext = (data: any) => {
    console.log('🔄 OnboardingWizard - handleNext called with data:', data);
    console.log('🔄 Previous state:', state);
    
    const newState = {
      ...state,
      ...data,
      currentStep: state.currentStep + 1,
    };
    
    console.log('🔄 New state:', newState);
    setState(newState);
  };

  const handleBack = () => {
    setState(prev => ({
      ...prev,
      currentStep: Math.max(0, prev.currentStep - 1),
    }));
  };

  const handleComplete = () => {
    setState(prev => ({ ...prev, isComplete: true }));
  };

  const currentStepData = steps[state.currentStep];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Welcome to CargoDham AI 🚀
          </h1>
          <p className="text-lg text-gray-600">
            Let's get your logistics API integrated in minutes!
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-12">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                {/* Step Circle */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all ${
                      index < state.currentStep
                        ? 'bg-green-500 border-green-500 text-white'
                        : index === state.currentStep
                        ? 'bg-primary-600 border-primary-600 text-white'
                        : 'bg-white border-gray-300 text-gray-400'
                    }`}
                  >
                    {index < state.currentStep ? (
                      <CheckCircleIcon className="w-6 h-6" />
                    ) : (
                      <span className="font-semibold">{index + 1}</span>
                    )}
                  </div>
                  <div className="mt-2 text-center">
                    <div className="text-sm font-medium text-gray-900">{step.name}</div>
                    <div className="text-xs text-gray-500">{step.description}</div>
                  </div>
                </div>

                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-4 transition-all ${
                      index < state.currentStep ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <motion.div
          key={state.currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="bg-white rounded-2xl shadow-xl p-8"
        >
          <AnimatePresence mode="wait">
            {state.currentStep === OnboardingStep.COMPANY_INFO && (
              <CompanyInfoStep onNext={handleNext} />
            )}
            {state.currentStep === OnboardingStep.DOCUMENT_UPLOAD && (
              <DocumentUploadStep onNext={handleNext} onBack={handleBack} state={state} />
            )}
            {state.currentStep === OnboardingStep.PARSING_PROGRESS && (
              <ParsingProgressStep onNext={handleNext} state={state} />
            )}
            {state.currentStep === OnboardingStep.OCR_REVIEW && (
              <OCRReviewStep onNext={handleNext} onBack={handleBack} state={state} />
            )}
            {state.currentStep === OnboardingStep.INTEGRATION_REVIEW && (
              <IntegrationReviewStep onNext={handleNext} onBack={handleBack} state={state} />
            )}
            {state.currentStep === OnboardingStep.API_TESTING && (
              <APITestingStep onNext={handleNext} onBack={handleBack} state={state} />
            )}
            {state.currentStep === OnboardingStep.ACTIVATION && (
              <ActivationStep onComplete={handleComplete} state={state} />
            )}
          </AnimatePresence>
        </motion.div>

        {/* Dev Mode Indicator */}
        <div className="mt-4 text-center">
          <div className="inline-flex items-center px-4 py-2 bg-yellow-100 border border-yellow-300 rounded-lg">
            <span className="text-yellow-800 text-sm font-medium">
              🧪 DEV MODE: Authentication bypassed for testing
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingWizard;

