/**
 * Partner Dashboard - Main management interface
 */
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BuildingOfficeIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import IntegrationViewer from '../../integration/components/IntegrationViewer';

interface Partner {
  id: string;
  companyName: string;
  status: 'active' | 'pending' | 'inactive';
  integrationsCount: number;
  lastActivity: string;
  apiCallsToday: number;
}

const PartnerDashboard: React.FC = () => {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPartners();
  }, []);

  const loadPartners = async () => {
    try {
      setLoading(true);
      // TODO: Fetch from API
      // const data = await partnersAPI.getAllPartners();
      
      // Mock data for now
      const mockPartners: Partner[] = [
        {
          id: '1',
          companyName: 'Acme Logistics',
          status: 'active',
          integrationsCount: 3,
          lastActivity: '2 hours ago',
          apiCallsToday: 145,
        },
        {
          id: '2',
          companyName: 'Fast Shipping Co',
          status: 'active',
          integrationsCount: 2,
          lastActivity: '1 day ago',
          apiCallsToday: 89,
        },
        {
          id: '3',
          companyName: 'Global Freight',
          status: 'pending',
          integrationsCount: 0,
          lastActivity: '3 days ago',
          apiCallsToday: 0,
        },
      ];
      
      setPartners(mockPartners);
    } catch (error) {
      console.error('Failed to load partners:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'inactive':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="w-5 h-5" />;
      case 'pending':
        return <ClockIcon className="w-5 h-5" />;
      case 'inactive':
        return <ExclamationCircleIcon className="w-5 h-5" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Partner Dashboard</h1>
              <p className="mt-1 text-gray-600">
                Manage all your logistics integrations in one place
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => (window.location.href = '/ocr')}
                className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                OCR Viewer
              </button>
              <button
                onClick={() => (window.location.href = '/onboard')}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
              >
                + Add Partner
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                <BuildingOfficeIcon className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Partners</p>
                <p className="text-2xl font-bold text-gray-900">{partners.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircleIcon className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Active</p>
                <p className="text-2xl font-bold text-gray-900">
                  {partners.filter(p => p.status === 'active').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <ChartBarIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">API Calls Today</p>
                <p className="text-2xl font-bold text-gray-900">
                  {partners.reduce((sum, p) => sum + p.apiCallsToday, 0)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <ChartBarIcon className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Integrations</p>
                <p className="text-2xl font-bold text-gray-900">
                  {partners.reduce((sum, p) => sum + p.integrationsCount, 0)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Partners List */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Partner Cards */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Partners</h2>
            {partners.map((partner) => (
              <motion.div
                key={partner.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`bg-white border rounded-xl p-6 cursor-pointer transition-all ${
                  selectedPartner === partner.id
                    ? 'border-primary-600 shadow-lg'
                    : 'border-gray-200 hover:border-primary-300 hover:shadow-md'
                }`}
                onClick={() => setSelectedPartner(partner.id)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-lg">
                      {partner.companyName.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {partner.companyName}
                      </h3>
                      <p className="text-sm text-gray-500">ID: {partner.id}</p>
                    </div>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                      partner.status
                    )}`}
                  >
                    {getStatusIcon(partner.status)}
                    {partner.status}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {partner.integrationsCount}
                    </p>
                    <p className="text-xs text-gray-500">Integrations</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {partner.apiCallsToday}
                    </p>
                    <p className="text-xs text-gray-500">API Calls</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {partner.lastActivity}
                    </p>
                    <p className="text-xs text-gray-500">Last Active</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Integration Details */}
          <div>
            {selectedPartner ? (
              <div className="bg-white border border-gray-200 rounded-xl p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">
                  Integration Details
                </h2>
                <IntegrationViewer partnerId={selectedPartner} />
              </div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                <BuildingOfficeIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">
                  Select a partner to view integration details
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PartnerDashboard;

