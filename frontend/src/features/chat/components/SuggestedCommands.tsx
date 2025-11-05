/**
 * Suggested commands component
 * Shows example commands users can try
 */
import React from 'react';
import { LightBulbIcon } from '@heroicons/react/24/outline';

interface SuggestedCommandsProps {
  commands: string[];
  onCommandClick: (command: string) => void;
}

const SuggestedCommands: React.FC<SuggestedCommandsProps> = ({ commands, onCommandClick }) => {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <LightBulbIcon className="w-5 h-5 text-blue-600" />
        <h3 className="text-sm font-medium text-blue-900">Suggested Commands</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        {commands.map((command, idx) => (
          <button
            key={idx}
            onClick={() => onCommandClick(command)}
            className="px-3 py-2 bg-white border border-blue-300 rounded-lg text-sm text-blue-700 hover:bg-blue-100 transition-colors"
          >
            {command}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedCommands;

