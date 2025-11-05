/**
 * OCR Viewer - Test and view extracted text from documents
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  DocumentIcon,
  CloudArrowUpIcon,
  SparklesIcon,
  ClockIcon,
  CheckCircleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { extractTextFromFile, OCRExtractResponse } from '@/lib/api/vision';

const OCRViewer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extractMode, setExtractMode] = useState<'full' | 'structured' | 'tables'>('full');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<OCRExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState<number>(0);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
      setError(null);
    }
  };

  const handleExtract = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);

    try {
      console.log('🚀 Starting OCR extraction...');
      console.log('📁 File:', selectedFile.name, 'Size:', selectedFile.size, 'Type:', selectedFile.type);
      console.log('⚙️ Extract Mode:', extractMode);
      
      const response = await extractTextFromFile(selectedFile, extractMode);
      console.log('✅ OCR complete:', response);
      setResult(response);
      setSelectedPage(0);
    } catch (err: any) {
      console.error('❌ OCR failed:', err);
      console.error('❌ Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      });
      
      // Show more detailed error message
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error occurred';
      setError(`Backend Error: ${errorMessage}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <SparklesIcon className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Ultra-Fast OCR Viewer</h1>
              <p className="mt-1 text-gray-600">
                Extract text from PDFs, images, and documents with AI-powered OCR
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel - Upload & Controls */}
          <div className="space-y-6">
            {/* File Upload */}
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload Document</h2>

              <div className="space-y-4">
                {/* File Input */}
                <div>
                  <label className="block">
                    <div
                      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                        selectedFile
                          ? 'border-green-400 bg-green-50'
                          : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="file"
                        onChange={handleFileSelect}
                        accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.docx"
                        className="hidden"
                      />
                      <CloudArrowUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-3" />
                      {selectedFile ? (
                        <div className="space-y-2">
                          <p className="font-medium text-green-700">{selectedFile.name}</p>
                          <p className="text-sm text-gray-500">
                            {formatFileSize(selectedFile.size)}
                          </p>
                          <p className="text-xs text-gray-400">Click to change file</p>
                        </div>
                      ) : (
                        <div>
                          <p className="font-medium text-gray-700">Click to upload a file</p>
                          <p className="text-sm text-gray-500 mt-1">
                            PDF, PNG, JPG, DOCX supported
                          </p>
                        </div>
                      )}
                    </div>
                  </label>
                </div>

                {/* Extraction Mode */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Extraction Mode
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { value: 'full', label: 'Full Text', icon: DocumentTextIcon },
                      { value: 'structured', label: 'Structured', icon: DocumentIcon },
                      { value: 'tables', label: 'Tables', icon: DocumentIcon },
                    ].map((mode) => (
                      <button
                        key={mode.value}
                        onClick={() => setExtractMode(mode.value as any)}
                        className={`p-3 rounded-lg border-2 transition-all ${
                          extractMode === mode.value
                            ? 'border-primary-600 bg-primary-50 text-primary-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <mode.icon className="w-5 h-5 mx-auto mb-1" />
                        <p className="text-xs font-medium">{mode.label}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Extract Button */}
                <button
                  onClick={handleExtract}
                  disabled={!selectedFile || isProcessing}
                  className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <SparklesIcon className="w-5 h-5" />
                      Extract Text
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Metadata */}
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white border border-gray-200 rounded-xl p-6"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Extraction Info</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">File Name</span>
                    <span className="text-sm font-medium text-gray-900">
                      {result.file_name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Pages</span>
                    <span className="text-sm font-medium text-gray-900">
                      {result.page_count}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Processing Time</span>
                    <span className="text-sm font-medium text-gray-900 flex items-center gap-1">
                      <ClockIcon className="w-4 h-4" />
                      {result.processing_time.toFixed(2)}s
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Characters</span>
                    <span className="text-sm font-medium text-gray-900">
                      {result.text.length.toLocaleString()}
                    </span>
                  </div>
                  {result.from_cache && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Cache</span>
                      <span className="text-sm font-medium text-green-700 flex items-center gap-1">
                        <CheckCircleIcon className="w-4 h-4" />
                        From Cache
                      </span>
                    </div>
                  )}
                  <div className="pt-3 border-t border-gray-200">
                    <span className="text-sm text-gray-600">Format</span>
                    <p className="text-sm font-medium text-gray-900 mt-1">
                      {result.metadata?.format || 'Unknown'}
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 border border-red-200 rounded-xl p-6"
              >
                <h3 className="text-lg font-semibold text-red-900 mb-2">Error</h3>
                <p className="text-sm text-red-700">{error}</p>
              </motion.div>
            )}
          </div>

          {/* Right Panel - Results */}
          <div className="space-y-6">
            {result ? (
              <>
                {/* Page Selector (for multi-page documents) */}
                {result.pages.length > 1 && (
                  <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-medium text-gray-900">Pages</h3>
                      <span className="text-sm text-gray-500">
                        {selectedPage + 1} of {result.pages.length}
                      </span>
                    </div>
                    <div className="flex gap-2 overflow-x-auto pb-2">
                      {result.pages.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedPage(index)}
                          className={`flex-shrink-0 px-4 py-2 rounded-lg border-2 transition-all ${
                            selectedPage === index
                              ? 'border-primary-600 bg-primary-50 text-primary-700'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          Page {index + 1}
                        </button>
                      ))}
                      <button
                        onClick={() => setSelectedPage(-1)}
                        className={`flex-shrink-0 px-4 py-2 rounded-lg border-2 transition-all ${
                          selectedPage === -1
                            ? 'border-primary-600 bg-primary-50 text-primary-700'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        All Pages
                      </button>
                    </div>
                  </div>
                )}

                {/* Extracted Text */}
                <motion.div
                  key={selectedPage}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-white border border-gray-200 rounded-xl p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {selectedPage === -1
                        ? 'All Extracted Text'
                        : `Page ${selectedPage + 1} Text`}
                    </h3>
                    <button
                      onClick={() => {
                        const textToCopy =
                          selectedPage === -1 ? result.text : result.pages[selectedPage];
                        navigator.clipboard.writeText(textToCopy);
                      }}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Copy
                    </button>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 max-h-[600px] overflow-y-auto">
                    <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                      {selectedPage === -1 ? result.text : result.pages[selectedPage]}
                    </pre>
                  </div>
                </motion.div>
              </>
            ) : (
              <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                <DocumentTextIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No Results Yet
                </h3>
                <p className="text-gray-500">
                  Upload a document and click "Extract Text" to see the results
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OCRViewer;

