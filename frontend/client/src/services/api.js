/**
 * API Service for all backend interactions
 */

const API_BASE_URL = 'http://localhost:5001/api';

/**
 * Generic API call function with error handling
 */
async function callApi(endpoint, method = 'GET', body = null, headers = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log(`Making API request to: ${url}`, { method, body });
  
  try {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    console.log(`API response status: ${response.status}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API Error: ${errorText}`);
      throw new Error(`API Error (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    console.log("API response data:", data);
    return data;
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    throw error;
  }
}

/**
 * VC Portfolio API Endpoints
 */
export const vcApi = {
  // Search companies based on filters
  searchCompanies: (filters) => callApi('/vc/companies/search', 'POST', filters),
  
  // Analyze specific companies
  analyzeCompanies: (request) => callApi('/vc/companies/analyze', 'POST', request),
  
  // Get portfolio overview
  getPortfolioOverview: (portfolioIds) => callApi('/vc/portfolio/overview', 'POST', portfolioIds),
  
  // Get trending skills
  getTrendingSkills: (limit = 10) => callApi(`/vc/skills/trending?limit=${limit}`)
};

/**
 * Advanced Analytics API Endpoints
 */
export const analyticsApi = {
  // Company scores and rankings
  getCompanyScores: (request) => callApi('/analytics/company-scores', 'POST', request),
  
  // Deep dive analysis for a specific company
  companyDeepDive: (request) => callApi('/analytics/company-deep-dive', 'POST', request),
  
  // Talent flow analysis between companies
  analyzeTalentFlow: (request) => callApi('/analytics/talent-flow', 'POST', request),
  
  // Get talent flow network for visualization
  getTalentFlowNetwork: (minTransitions = 5) => 
    callApi(`/analytics/talent-flow-network?min_transitions=${minTransitions}`),
  
  // Geographic analysis
  getGeographicAnalysis: (request) => callApi('/analytics/geographic', 'POST', request),
  
  // Get geographic talent density data
  getGeographicTalentDensity: () => callApi('/analytics/geographic-talent-density'),
  
  // Create monitoring alert
  createAlert: (config) => callApi('/analytics/create-alert', 'POST', config),
  
  // Check for triggered alerts
  checkAlerts: () => callApi('/analytics/check-alerts')
};

/**
 * Data and Graph API Endpoints
 */
export const dataApi = {
  // Upload and process a resume
  uploadResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    console.log("Uploading resume to:", `${API_BASE_URL}/upload/resume`);
    
    const response = await fetch(`${API_BASE_URL}/upload/resume`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error("Resume upload failed:", errorText);
      throw new Error(`Upload failed (${response.status}): ${errorText}`);
    }
    
    const data = await response.json();
    console.log("Resume upload response:", data);
    return data;
  },
  
  // Store a profile in the database
  storeProfile: (profile) => callApi('/db/store_profile', 'POST', profile),
  
  // Run graph algorithms
  runPageRank: (request) => callApi('/graph/pagerank', 'POST', request),
  runBiRank: (request) => callApi('/graph/birank', 'POST', request),
  
  // Get graph rankings
  getRankings: (propertyName, label = null, limit = 20) => 
    callApi(`/graph/rankings?property_name=${propertyName}&label=${label || ''}&limit=${limit}`)
};

export default {
  vc: vcApi,
  analytics: analyticsApi,
  data: dataApi
}; 