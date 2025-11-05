/**
 * Individual chat message bubble component
 */
import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/solid';
import { ChatMessage } from '@/lib/api/chat';
import ReactMarkdown from 'react-markdown';

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.2 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-3xl ${
          isUser
            ? 'bg-primary-600 text-white rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl'
            : isSystem
            ? 'bg-gray-100 text-gray-700 rounded-lg border border-gray-200'
            : 'bg-white text-gray-900 rounded-tl-2xl rounded-tr-2xl rounded-br-2xl shadow-sm border border-gray-200'
        } px-4 py-3`}
      >
        {/* Message content */}
        <div className="prose prose-sm max-w-none">
          {isUser ? (
            <p className="mb-0">{message.content}</p>
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>

        {/* Intent and entities (for assistant messages) */}
        {!isUser && !isSystem && message.intent && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
            {/* Intent */}
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-gray-600">Intent:</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-md">
                {message.intent}
              </span>
            </div>

            {/* Entities */}
            {message.entities && Object.keys(message.entities).length > 0 && (
              <div className="text-xs">
                <span className="font-medium text-gray-600">Extracted:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(message.entities).map(([key, value]) => (
                    <span
                      key={key}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded-md"
                    >
                      {key}: {String(value)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* API Calls */}
            {message.apiCalls && message.apiCalls.length > 0 && (
              <div className="text-xs">
                <span className="font-medium text-gray-600">API Calls:</span>
                <div className="space-y-1 mt-1">
                  {message.apiCalls.map((call, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      {call.status === 'success' ? (
                        <CheckCircleIcon className="w-4 h-4 text-green-500" />
                      ) : (
                        <ExclamationCircleIcon className="w-4 h-4 text-red-500" />
                      )}
                      <span className="text-gray-600">
                        {call.method || 'POST'} {call.endpoint}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-2 text-xs opacity-70">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  );
};

export default ChatMessageBubble;

