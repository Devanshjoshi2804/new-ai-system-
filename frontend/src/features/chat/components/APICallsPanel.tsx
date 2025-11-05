/**
 * Panel to display API calls made by the AI
 */
import React from 'react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

interface APICall {
  endpoint: string;
  method: string;
  status: 'success' | 'error';
  response?: any;
}

interface APICallsPanelProps {
  calls: APICall[];
}

const APICallsPanel: React.FC<APICallsPanelProps> = ({ calls }) => {
  if (!calls || calls.length === 0) return null;

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-3">
      <h4 className="text-sm font-medium text-gray-700 mb-2">API Calls Made</h4>
      <div className="space-y-2">
        {calls.map((call, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm">
            {call.status === 'success' ? (
              <CheckCircleIcon className="w-5 h-5 text-green-500" />
            ) : (
              <XCircleIcon className="w-5 h-5 text-red-500" />
            )}
            <span className="font-mono text-xs bg-white px-2 py-1 rounded border">
              {call.method}
            </span>
            <span className="text-gray-600">{call.endpoint}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default APICallsPanel;

