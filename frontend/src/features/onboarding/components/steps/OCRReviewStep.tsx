/**
 * Step 3.5: Review OCR Results and Trigger AI Analysis
 * This step shows OCR extracted text and allows user to trigger AI analysis
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { DocumentTextIcon, SparklesIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { OnboardingState } from '../../types/onboarding.types';
import { partnersAPI } from '../../../../lib/api/partners';

interface OCRReviewStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

const OCRReviewStep: React.FC<OCRReviewStepProps> = ({ onNext, onBack, state }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const integration = state.integrationReview;
  const ocrData = integration?.api_spec?.schemas?._ocr_metadata;
  const docId = state.documentInfo?.uploadedDocIds?.[0];
  
  const handleAnalyzeWithAI = async () => {
    if (!docId) {
      setError('Document ID not found');
      return;
    }
    
    setIsAnalyzing(true);
    setError(null);
    
    try {
      console.log('🧠 Triggering AI analysis for doc:', docId);
      const result = await partnersAPI.analyzeDocumentation(docId);
      console.log('✅ AI analysis complete:', result);
      
      // Update state with analyzed data
      onNext({
        integrationReview: result,
      });
    } catch (err: any) {
      console.error('❌ AI analysis failed:', err);
      setError(err.message || 'Failed to analyze documentation');
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  const handleSkipAnalysis = () => {
    // Continue with OCR data only
    onNext({});
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <DocumentTextIcon className="w-8 h-8 text-primary-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">OCR Extraction Complete!</h2>
          <p className="text-gray-600">
            Review the extracted text and analyze with AI to find API endpoints
          </p>
        </div>
      </div>

      {/* OCR Results Summary */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <CheckCircleIcon className="w-6 h-6 text-green-600" />
          Extraction Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Pages Processed</p>
            <p className="text-2xl font-bold text-gray-900">{ocrData?.page_count || 0}</p>
          </div>
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Characters Extracted</p>
            <p className="text-2xl font-bold text-gray-900">
              {ocrData?.total_characters?.toLocaleString() || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Processing Time</p>
            <p className="text-2xl font-bold text-gray-900">
              {ocrData?.processing_time || 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* OCR Text Preview */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Extracted Text Preview</h3>
        
        {ocrData?.pages && ocrData.pages.length > 0 ? (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {ocrData.pages.slice(0, 3).map((pageText: string, index: number) => (
              <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-700">
                    Page {index + 1} of {ocrData.page_count}
                  </span>
                  <span className="text-xs text-gray-500">
                    {pageText.length} characters
                  </span>
                </div>
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto">
                  {pageText.substring(0, 500)}
                  {pageText.length > 500 && '...'}
                </pre>
              </div>
            ))}
            {ocrData.pages.length > 3 && (
              <p className="text-sm text-gray-500 text-center">
                ... and {ocrData.pages.length - 3} more pages
              </p>
            )}
          </div>
        ) : (
          <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
              {ocrData?.full_text?.substring(0, 2000)}
              {(ocrData?.full_text?.length || 0) > 2000 && '...'}
            </pre>
          </div>
        )}
      </div>

      {/* AI Analysis Call-to-Action */}
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <SparklesIcon className="w-8 h-8 text-purple-600 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Ready for AI Analysis?
            </h3>
            <p className="text-gray-600 mb-4">
              Our AI will analyze the extracted text to automatically identify:
            </p>
            <ul className="space-y-2 mb-4">
              <li className="flex items-center gap-2 text-sm text-gray-700">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
                API Base URLs and endpoints
              </li>
              <li className="flex items-center gap-2 text-sm text-gray-700">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
                HTTP methods (GET, POST, PUT, DELETE)
              </li>
              <li className="flex items-center gap-2 text-sm text-gray-700">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
                Authentication requirements
              </li>
              <li className="flex items-center gap-2 text-sm text-gray-700">
                <CheckCircleIcon className="w-5 h-5 text-green-600" />
                Request parameters and responses
              </li>
            </ul>
            
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
            
            <div className="flex gap-3">
              <button
                onClick={handleAnalyzeWithAI}
                disabled={isAnalyzing}
                className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Analyzing with AI...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="w-5 h-5" />
                    Analyze with AI
                  </>
                )}
              </button>
              
              <button
                onClick={handleSkipAnalysis}
                disabled={isAnalyzing}
                className="px-6 py-3 rounded-lg font-medium border-2 border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Skip for Now
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-6">
        <button
          onClick={onBack}
          disabled={isAnalyzing}
          className="px-6 py-3 rounded-lg font-medium border-2 border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Back
        </button>
      </div>
    </motion.div>
  );
};

export default OCRReviewStep;

