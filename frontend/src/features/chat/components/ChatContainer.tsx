/**
 * Main chat container component
 * Provides interface for autonomous AI execution
 */
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PaperAirplaneIcon, SparklesIcon } from '@heroicons/react/24/solid';
import { chatAPI, ChatMessage } from '@/lib/api/chat';
import ChatMessageBubble from './ChatMessageBubble';
import APICallsPanel from './APICallsPanel';
import SuggestedCommands from './SuggestedCommands';

interface ChatContainerProps {
  tenantId: string;
  partnerName?: string;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ tenantId, partnerName }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [capabilities, setCapabilities] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Set tenant ID
    chatAPI.setTenantId(tenantId);

    // Load capabilities
    loadCapabilities();

    // Add welcome message
    addSystemMessage(
      `Welcome! I'm your AI assistant for ${partnerName || 'logistics operations'}. ` +
      `I can autonomously execute API operations for you. Just tell me what you need!`
    );
  }, [tenantId, partnerName]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadCapabilities = async () => {
    try {
      const caps = await chatAPI.getCapabilities();
      setCapabilities(caps);
    } catch (error) {
      console.error('Failed to load capabilities:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const addSystemMessage = (content: string) => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'system',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, message]);
  };

  const addUserMessage = (content: string): ChatMessage => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, message]);
    return message;
  };

  const addAssistantMessage = (
    content: string,
    intent?: string,
    entities?: Record<string, any>,
    apiCalls?: Array<any>
  ): ChatMessage => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content,
      timestamp: new Date(),
      intent,
      entities,
      apiCalls,
    };
    setMessages(prev => [...prev, message]);
    return message;
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Add user message
    addUserMessage(userMessage);

    try {
      // Send to backend for autonomous execution
      const response = await chatAPI.sendMessage({
        message: userMessage,
      });

      // Add assistant response
      addAssistantMessage(
        response.response,
        response.intent,
        response.entities,
        response.api_calls
      );
    } catch (error: any) {
      addAssistantMessage(
        `Sorry, I encountered an error: ${error.message}. Please try again.`
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              <SparklesIcon className="inline-block w-6 h-6 mr-2 text-primary-500" />
              Autonomous AI Assistant
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {capabilities?.integration_active
                ? `Connected to ${capabilities.partner_name}`
                : 'Setting up integration...'}
            </p>
          </div>
          {capabilities?.integration_active && (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                Active
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <ChatMessageBubble key={message.id} message={message} />
          ))}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 text-gray-500"
          >
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce delay-100"></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce delay-200"></div>
            </div>
            <span className="text-sm">AI is processing and calling APIs...</span>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Commands */}
      {messages.length <= 1 && capabilities && (
        <div className="px-6 py-2">
          <SuggestedCommands
            commands={capabilities.example_commands || []}
            onCommandClick={handleSuggestionClick}
          />
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a command... e.g., 'Book shipment from Mumbai to Delhi'"
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={isLoading || !capabilities?.integration_active}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading || !capabilities?.integration_active}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Tip: The AI will autonomously execute API calls to fulfill your request
        </p>
      </div>
    </div>
  );
};

export default ChatContainer;

