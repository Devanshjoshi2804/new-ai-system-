/**
 * Integration Viewer - View discovered API endpoints and workflows
 */
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  CodeBracketIcon, 
  CubeIcon, 
  ChartBarIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { partnersAPI } from '@/lib/api/partners';

interface IntegrationViewerProps {
  partnerId: string;
}

const IntegrationViewer: React.FC<IntegrationViewerProps> = ({ partnerId }) => {
  const [integration, setIntegration] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'endpoints' | 'workflows' | 'code'>('endpoints');

  useEffect(() => {
    loadIntegration();
  }, [partnerId]);

  const loadIntegration = async () => {
    try {
      setLoading(true);
      // TODO: Add API endpoint to get integration details
      // const data = await partnersAPI.getIntegration(partnerId);
      
      // Mock data for now
      const mockData = {
        id: partnerId,
        baseUrl: 'https://api.demologs.com',
        endpoints: [
          {
            path: '/bookings',
            method: 'POST',
            summary: 'Create Booking',
            parameters: [
              { name: 'origin', required: true, type: 'string' },
              { name: 'destination', required: true, type: 'string' },
              { name: 'weight', required: true, type: 'string' }
            ]
          },
          {
            path: '/tracking/{awb}',
            method: 'GET',
            summary: 'Track Shipment',
            parameters: [
              { name: 'awb', required: true, type: 'string' }
            ]
          },
          {
            path: '/rate',
            method: 'POST',
            summary: 'Calculate Rate',
            parameters: []
          }
        ],
        workflows: [
          {
            name: 'Booking Workflow',
            description: 'Complete flow for creating a shipment booking',
            steps: [
              'Validate origin pincode',
              'Validate destination pincode',
              'Calculate shipping rate',
              'Create booking',
              'Generate AWB number'
            ]
          },
          {
            name: 'Tracking Workflow',
            description: 'Track shipment by AWB number',
            steps: [
              'Fetch tracking details',
              'Get current location',
              'Get delivery estimate'
            ]
          }
        ],
        generatedCode: `class DemoLogsAPIClient:
    def __init__(self, api_key: str):
        self.base_url = "https://api.demologs.com"
        self.api_key = api_key
    
    async def create_booking(self, origin: str, destination: str, weight: str):
        """Create a new booking"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/bookings",
                params={"origin": origin, "destination": destination, "weight": weight},
                headers={"X-API-Key": self.api_key}
            ) as response:
                return await response.json()
    
    async def track_shipment(self, awb: str):
        """Track shipment by AWB"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/tracking/{awb}",
                headers={"X-API-Key": self.api_key}
            ) as response:
                return await response.json()`
      };
      
      setIntegration(mockData);
    } catch (error) {
      console.error('Failed to load integration:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <ArrowPathIcon className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (!integration) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No integration found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 border border-primary-200 rounded-xl p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Integration Details</h2>
        <p className="text-gray-600">{integration.baseUrl}</p>
        <div className="flex gap-4 mt-4">
          <div className="bg-white rounded-lg px-4 py-2">
            <span className="text-2xl font-bold text-primary-600">
              {integration.endpoints?.length || 0}
            </span>
            <span className="text-sm text-gray-600 ml-2">Endpoints</span>
          </div>
          <div className="bg-white rounded-lg px-4 py-2">
            <span className="text-2xl font-bold text-primary-600">
              {integration.workflows?.length || 0}
            </span>
            <span className="text-sm text-gray-600 ml-2">Workflows</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-8">
          <button
            onClick={() => setActiveTab('endpoints')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'endpoints'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <CubeIcon className="w-5 h-5 inline-block mr-2" />
            API Endpoints
          </button>
          <button
            onClick={() => setActiveTab('workflows')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'workflows'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <ChartBarIcon className="w-5 h-5 inline-block mr-2" />
            Workflows
          </button>
          <button
            onClick={() => setActiveTab('code')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'code'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <CodeBracketIcon className="w-5 h-5 inline-block mr-2" />
            Generated Code
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {activeTab === 'endpoints' && (
          <div className="space-y-3">
            {integration.endpoints?.map((endpoint: any, index: number) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span
                    className={`px-3 py-1 text-sm font-bold rounded ${
                      endpoint.method === 'GET'
                        ? 'bg-blue-100 text-blue-700'
                        : endpoint.method === 'POST'
                        ? 'bg-green-100 text-green-700'
                        : endpoint.method === 'PUT'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {endpoint.method}
                  </span>
                  <span className="font-mono text-gray-900">{endpoint.path}</span>
                </div>
                {endpoint.summary && (
                  <p className="text-gray-600 mb-4">{endpoint.summary}</p>
                )}
                {endpoint.parameters && endpoint.parameters.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Parameters:</h4>
                    <div className="space-y-2">
                      {endpoint.parameters.map((param: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                            {param.name}
                          </span>
                          <span className="text-gray-500">{param.type}</span>
                          {param.required && (
                            <span className="text-red-600 text-xs">required</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className="space-y-4">
            {integration.workflows?.map((workflow: any, index: number) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-6"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {workflow.name}
                </h3>
                <p className="text-gray-600 mb-4">{workflow.description}</p>
                <div className="space-y-2">
                  {workflow.steps?.map((step: string, i: number) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center font-semibold text-sm">
                        {i + 1}
                      </div>
                      <span className="text-gray-700">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'code' && (
          <div className="border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Generated API Client
              </h3>
              <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm">
                Copy Code
              </button>
            </div>
            <div className="bg-gray-900 rounded-lg p-6 overflow-x-auto">
              <pre className="text-sm text-green-400 font-mono">
                {integration.generatedCode}
              </pre>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default IntegrationViewer;

