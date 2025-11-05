/**
 * Step 3: Real-time AI Parsing Progress
 */
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { SparklesIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/solid';
import { partnersAPI } from '@/lib/api/partners';
import { OnboardingState, ParsingProgress } from '../../types/onboarding.types';

interface ParsingProgressStepProps {
  onNext: (data: any) => void;
  state: OnboardingState;
}

const ParsingProgressStep: React.FC<ParsingProgressStepProps> = ({ onNext, state }) => {
  const [progress, setProgress] = useState<ParsingProgress[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [integrationData, setIntegrationData] = useState<any>(null);

  useEffect(() => {
    console.log('📊 ParsingProgressStep - State:', state);
    console.log('📊 Document IDs:', state.documentInfo?.uploadedDocIds);
    
    if (state.documentInfo?.uploadedDocIds && state.documentInfo.uploadedDocIds.length > 0) {
      parseDocuments();
    } else {
      console.error('❌ No document IDs found in state!');
    }
  }, [state.documentInfo?.uploadedDocIds]);

  const parseDocuments = async () => {
    const docIds = state.documentInfo!.uploadedDocIds;
    
    // Initialize progress
    const initialProgress: ParsingProgress[] = docIds.map(docId => ({
      docId,
      status: 'pending',
      progress: 0,
    }));
    setProgress(initialProgress);

    // Parse each document (JUST extract text, don't analyze yet)
    for (let i = 0; i < docIds.length; i++) {
      const docId = docIds[i];
      
      try {
        // Update to processing
        setProgress(prev =>
          prev.map(p =>
            p.docId === docId
              ? { ...p, status: 'processing', progress: 50, message: 'Extracting text...' }
              : p
          )
        );

        // Call parse API (this just extracts text, doesn't analyze)
        const result = await partnersAPI.parseDocumentation(docId);

        // Update to completed
        setProgress(prev =>
          prev.map(p =>
            p.docId === docId
              ? {
                  ...p,
                  status: 'completed',
                  progress: 100,
                  message: 'Text extracted!',
                  format: result.format,
                  endpoints: 0, // No endpoints yet
                }
              : p
          )
        );
      } catch (error: any) {
        setProgress(prev =>
          prev.map(p =>
            p.docId === docId
              ? { ...p, status: 'failed', progress: 100, message: error.message }
              : p
          )
        );
      }
    }

    // All extraction done
    setIsComplete(true);
  };

  const handleAnalyzeWithAI = async () => {
    const docIds = state.documentInfo!.uploadedDocIds;
    
    setIsAnalyzing(true);
    
    try {
      console.log('🧠 Starting AI analysis for', docIds.length, 'documents');
      
      // Call the combined analyze endpoint
      const result = await partnersAPI.analyzeMultipleDocuments(docIds);
      
      console.log('✅ AI analysis complete:', result);
      
      setIntegrationData(result);
      
      // Update progress to show analysis complete
      setProgress(prev =>
        prev.map(p => ({
          ...p,
          message: 'AI analysis complete!',
          endpoints: result.api_spec?.endpoints?.length || 0,
        }))
      );
      
    } catch (error: any) {
      console.error('❌ AI analysis failed:', error);
      alert('AI analysis failed: ' + error.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleContinue = () => {
    onNext({
      parsingProgress: progress,
      integrationReview: integrationData,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <SparklesIcon className="w-8 h-8 text-primary-600 animate-pulse" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI is Analyzing Your Documentation</h2>
          <p className="text-gray-600">
            Sit back and relax while our AI understands your APIs
          </p>
        </div>
      </div>

      {/* Progress List */}
      <div className="space-y-4">
        {progress.map((item, index) => (
          <div key={item.docId} className="border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {item.status === 'completed' ? (
                  <CheckCircleIcon className="w-6 h-6 text-green-500" />
                ) : item.status === 'failed' ? (
                  <ExclamationCircleIcon className="w-6 h-6 text-red-500" />
                ) : item.status === 'processing' ? (
                  <SparklesIcon className="w-6 h-6 text-primary-500 animate-spin" />
                ) : (
                  <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                )}
                <span className="font-medium text-gray-900">
                  Document {index + 1}
                </span>
              </div>
              <span className="text-sm text-gray-500">{item.progress}%</span>
            </div>

            {/* Progress Bar */}
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-3">
              <motion.div
                className={`h-full ${
                  item.status === 'completed'
                    ? 'bg-green-500'
                    : item.status === 'failed'
                    ? 'bg-red-500'
                    : 'bg-primary-500'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${item.progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>

            {/* Status Message */}
            {item.message && (
              <p className="text-sm text-gray-600 mb-2">{item.message}</p>
            )}

            {/* Details */}
            {item.status === 'completed' && (
              <div className="flex gap-4 text-sm">
                <span className="text-gray-600">
                  Format: <span className="font-medium text-gray-900">{item.format}</span>
                </span>
                {item.endpoints !== undefined && (
                  <span className="text-gray-600">
                    Endpoints: <span className="font-medium text-gray-900">{item.endpoints}</span>
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Extracted Data Display */}
      {isComplete && integrationData?.api_spec?.schemas?.extracted_text && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <CheckCircleIcon className="w-6 h-6 text-green-600" />
            <h3 className="text-xl font-bold text-gray-900">✅ Text Extracted Successfully!</h3>
          </div>
          
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg p-4 text-center">
              <p className="text-sm text-gray-600 mb-1">Pages Processed</p>
              <p className="text-3xl font-bold text-green-600">
                {integrationData.api_spec.schemas.extracted_text.page_count || 0}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4 text-center">
              <p className="text-sm text-gray-600 mb-1">Characters Extracted</p>
              <p className="text-3xl font-bold text-green-600">
                {integrationData.api_spec.schemas.extracted_text.total_characters?.toLocaleString() || 0}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4 text-center">
              <p className="text-sm text-gray-600 mb-1">Processing Time</p>
              <p className="text-3xl font-bold text-green-600">
                {integrationData.api_spec.schemas.extracted_text.processing_time?.toFixed(1) || 0}s
              </p>
            </div>
          </div>

          {/* Extracted Text */}
          <div className="bg-white rounded-lg p-4 border border-green-200">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">📄 Extracted Text</h4>
            
            {/* Page-by-page view */}
            {integrationData.api_spec.schemas.extracted_text.pages && 
             integrationData.api_spec.schemas.extracted_text.pages.length > 0 ? (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {integrationData.api_spec.schemas.extracted_text.pages.map((page: any, index: number) => {
                  // Handle both old format (string) and new format (object with text property)
                  const pageText = typeof page === 'string' ? page : page.text;
                  const pageNum = typeof page === 'string' ? (index + 1) : (page.page_number || index + 1);
                  const charCount = typeof page === 'string' ? page.length : (page.char_count || page.text?.length || 0);
                  
                  return (
                    <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-green-700">
                          📄 Page {pageNum} of {integrationData.api_spec.schemas.extracted_text.page_count}
                        </span>
                        <span className="text-xs text-gray-500">
                          {charCount} characters
                        </span>
                      </div>
                      <div className="prose prose-sm max-w-none text-gray-700 max-h-60 overflow-y-auto bg-white p-3 rounded border border-gray-100">
                        <ReactMarkdown>{pageText}</ReactMarkdown>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-4 max-h-[600px] overflow-y-auto">
                <div className="prose prose-sm max-w-none text-gray-700">
                  <ReactMarkdown>{integrationData.api_spec.schemas.extracted_text.full_text}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Cache Info */}
          <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
            <span>
              {integrationData.api_spec.schemas.extracted_text.from_cache ? 
                '⚡ Retrieved from cache' : 
                '🔄 Fresh extraction'}
            </span>
            <span className="text-xs">
              {integrationData.api_spec.description}
            </span>
          </div>
        </motion.div>
      )}

      {/* Action Buttons */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-center pt-6 border-t border-gray-200"
        >
          {!integrationData ? (
            /* Show "Analyze with AI" button if extraction done but not analyzed yet */
            <div className="w-full">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200 mb-4">
                <p className="text-sm font-medium text-gray-700 mb-2">
                  ✅ Text extraction complete from {progress.length} source{progress.length !== 1 ? 's' : ''}!
                </p>
                <p className="text-sm text-gray-600">
                  Click "Analyze with AI" to combine all sources and extract API endpoints using Mistral AI
                </p>
              </div>
              <button
                onClick={handleAnalyzeWithAI}
                disabled={isAnalyzing}
                className="w-full px-8 py-4 bg-gradient-to-r from-primary-600 to-purple-600 text-white rounded-lg hover:from-primary-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-lg shadow-lg"
              >
                {isAnalyzing ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin">🧠</span>
                    Analyzing with AI...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    🤖 Analyze with AI ({progress.length} sources combined)
                  </span>
                )}
              </button>
            </div>
          ) : (
            /* Show "Continue" button after AI analysis is done */
            <div className="w-full">
              <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200 mb-4">
                <p className="text-sm font-medium text-green-700 mb-1">
                  ✅ AI Analysis Complete!
                </p>
                <p className="text-sm text-gray-600">
                  Found {integrationData.api_spec?.endpoints?.length || 0} API endpoints from {progress.length} combined sources
                </p>
              </div>
              <button
                onClick={handleContinue}
                className="w-full px-8 py-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-lg shadow-lg"
              >
                Continue to Review Endpoints →
              </button>
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
};

export default ParsingProgressStep;

