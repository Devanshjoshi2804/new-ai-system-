/**
 * Step 2: Document Upload with Multiple Sources
 * Users can upload files AND paste text - all will be combined for analysis
 */
import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { DocumentIcon, CloudArrowUpIcon, XMarkIcon, CommandLineIcon, DocumentTextIcon, PlusIcon } from '@heroicons/react/24/outline';
import { partnersAPI } from '@/lib/api/partners';
import { OnboardingState } from '../../types/onboarding.types';

interface DocumentUploadStepProps {
  onNext: (data: any) => void;
  onBack: () => void;
  state: OnboardingState;
}

interface TextInput {
  id: string;
  type: 'curl' | 'json' | 'yaml';
  content: string;
}

const DocumentUploadStep: React.FC<DocumentUploadStepProps> = ({ onNext, onBack, state }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [textInputs, setTextInputs] = useState<TextInput[]>([]);
  const [showTextInput, setShowTextInput] = useState(false);
  const [newTextType, setNewTextType] = useState<'curl' | 'json' | 'yaml'>('curl');
  const [newTextContent, setNewTextContent] = useState('');
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
      'application/yaml': ['.yaml', '.yml'],
      'application/pdf': ['.pdf'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeTextInput = (id: string) => {
    setTextInputs(prev => prev.filter(input => input.id !== id));
  };

  const addTextInput = () => {
    if (!newTextContent.trim()) {
      setError('Please enter some content');
      return;
    }

    const newInput: TextInput = {
      id: Date.now().toString(),
      type: newTextType,
      content: newTextContent,
    };

    setTextInputs(prev => [...prev, newInput]);
    setNewTextContent('');
    setShowTextInput(false);
    setError(null);
  };

  const handleUpload = async () => {
    // Validate that we have at least one source
    if (files.length === 0 && textInputs.length === 0) {
      setError('Please upload at least one file or add text content');
      return;
    }

    console.log('📤 Starting upload with state:', state);
    console.log('📤 Files:', files.length, 'Text inputs:', textInputs.length);
    console.log('📤 Partner ID:', state.partnerId);

    if (!state.partnerId) {
      setError('Partner ID is missing. Please go back and complete company registration.');
      return;
    }

    setIsUploading(true);
    setError(null);
    const docIds: string[] = [];

    try {
      // Upload all files
      for (const file of files) {
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
        
        console.log('📤 Uploading file:', file.name, 'for partner:', state.partnerId);
        
        const response = await partnersAPI.uploadDocumentation(
          state.partnerId,
          file
        );
        
        console.log('✅ Upload response:', response);
        const docId = response.documentation_id || response.id;
        console.log('✅ Document ID:', docId);
        docIds.push(docId);
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
      }

      // Upload all text inputs as files
      for (const textInput of textInputs) {
        const fileName = `${textInput.type}-input-${textInput.id}.txt`;
        const blob = new Blob([textInput.content], { type: 'text/plain' });
        const file = new File([blob], fileName, { type: 'text/plain' });
        
        setUploadProgress(prev => ({ ...prev, [fileName]: 0 }));
        console.log('📤 Uploading text content as:', fileName);
        
        const response = await partnersAPI.uploadDocumentation(
          state.partnerId,
          file
        );
        
        console.log('✅ Upload response:', response);
        const docId = response.documentation_id || response.id;
        console.log('✅ Document ID:', docId);
        docIds.push(docId);
        setUploadProgress(prev => ({ ...prev, [fileName]: 100 }));
      }

      setUploadedDocs(docIds);
      
      console.log('✅ All uploads complete. Total docs:', docIds.length);
      
      // Move to next step
      onNext({
        documentInfo: {
          files,
          uploadedDocIds: docIds,
        },
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-3 mb-6">
        <CloudArrowUpIcon className="w-8 h-8 text-primary-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Upload API Documentation</h2>
          <p className="text-gray-600">
            Add files AND text from multiple sources - everything will be combined for analysis
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* File Upload Dropzone - Always Visible */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <CloudArrowUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-3" />
        {isDragActive ? (
          <p className="text-lg font-medium text-primary-600">Drop files here...</p>
        ) : (
          <>
            <p className="text-lg font-medium text-gray-700 mb-1">
              Drag & drop files here, or click to browse
            </p>
            <p className="text-sm text-gray-500">
              PDF, OpenAPI (JSON/YAML), Markdown, Images - all formats accepted
            </p>
          </>
        )}
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-medium text-gray-900 flex items-center gap-2">
            <DocumentIcon className="w-5 h-5 text-primary-600" />
            Files ({files.length})
          </h3>
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
            >
              <div className="flex items-center gap-3">
                <DocumentIcon className="w-6 h-6 text-gray-400" />
                <div>
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              {uploadProgress[file.name] !== undefined ? (
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 transition-all"
                      style={{ width: `${uploadProgress[file.name]}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-600">
                    {uploadProgress[file.name]}%
                  </span>
                </div>
              ) : (
                <button
                  onClick={() => removeFile(index)}
                  disabled={isUploading}
                  className="p-2 text-gray-400 hover:text-red-600 disabled:opacity-50 transition-colors"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Text Inputs Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-900 flex items-center gap-2">
            <CommandLineIcon className="w-5 h-5 text-primary-600" />
            Text/cURL Inputs ({textInputs.length})
          </h3>
          {!showTextInput && (
            <button
              onClick={() => setShowTextInput(true)}
              disabled={isUploading}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 disabled:opacity-50 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Add Text/cURL
            </button>
          )}
        </div>

        {/* Show existing text inputs */}
        {textInputs.map((textInput) => (
          <div
            key={textInput.id}
            className="p-4 bg-gray-50 rounded-lg border border-gray-200"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-primary-100 text-primary-700">
                    {textInput.type.toUpperCase()}
                  </span>
                  <span className="text-sm text-gray-500">
                    {textInput.content.length} characters
                  </span>
                </div>
                <p className="text-sm text-gray-600 font-mono truncate">
                  {textInput.content.substring(0, 100)}...
                </p>
              </div>
              <button
                onClick={() => removeTextInput(textInput.id)}
                disabled={isUploading}
                className="p-2 text-gray-400 hover:text-red-600 disabled:opacity-50 transition-colors flex-shrink-0"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}

        {/* Add new text input form */}
        {showTextInput && (
          <div className="p-4 bg-blue-50 rounded-lg border-2 border-blue-200 space-y-3">
            <div className="flex gap-2">
              <button
                onClick={() => setNewTextType('curl')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  newTextType === 'curl'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                cURL
              </button>
              <button
                onClick={() => setNewTextType('json')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  newTextType === 'json'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                JSON
              </button>
              <button
                onClick={() => setNewTextType('yaml')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  newTextType === 'yaml'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                YAML
              </button>
            </div>

            <textarea
              value={newTextContent}
              onChange={(e) => setNewTextContent(e.target.value)}
              placeholder={
                newTextType === 'curl'
                  ? 'Paste cURL commands...\n\ncurl -X GET https://api.example.com/users\ncurl -X POST https://api.example.com/orders'
                  : newTextType === 'json'
                  ? 'Paste JSON...\n\n{"endpoints": [...]}'
                  : 'Paste YAML...\n\nendpoints:\n  - path: /users'
              }
              className="w-full h-32 p-3 border border-gray-300 rounded font-mono text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
            />

            <div className="flex gap-2">
              <button
                onClick={addTextInput}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium transition-colors"
              >
                Add
              </button>
              <button
                onClick={() => {
                  setShowTextInput(false);
                  setNewTextContent('');
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Summary & Actions */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg p-4 border border-primary-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">
              Ready to process:
            </p>
            <p className="text-lg font-bold text-primary-700">
              {files.length + textInputs.length} source{files.length + textInputs.length !== 1 ? 's' : ''}
              <span className="text-sm font-normal text-gray-600 ml-2">
                ({files.length} file{files.length !== 1 ? 's' : ''}, {textInputs.length} text input{textInputs.length !== 1 ? 's' : ''})
              </span>
            </p>
          </div>
          {(files.length > 0 || textInputs.length > 0) && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              All sources will be combined for AI analysis
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <button
          onClick={onBack}
          disabled={isUploading}
          className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={handleUpload}
          disabled={isUploading || (files.length === 0 && textInputs.length === 0)}
          className="px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {isUploading ? 'Uploading...' : 'Process All & Continue →'}
        </button>
      </div>
    </motion.div>
  );
};

export default DocumentUploadStep;

