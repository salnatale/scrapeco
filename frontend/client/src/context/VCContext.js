// frontend/client/src/context/VCContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import aiService from '../services/aiService';
import { useAuth } from '../hooks/useAuth';

// API base URL
const API_BASE_URL = 'http://localhost:8000/api';

// Initial state
const initialState = {
  mode: 'research', // 'research' or 'portfolio'
  filters: {
    industries: [],
    funding_stages: [],
    geo_regions: [],
    portfolio_ids: []
  },
  companies: [],
  loading: false,
  error: null,
  portfolioOverview: null,
  recommendations: [],
  insights: [],
  opportunities: [],
  talentFlowData: null,
  companyAnalytics: null
};

// Cache for API responses
const apiCache = {
  recommendations: { data: null, timestamp: 0 },
  insights: { data: null, timestamp: 0 },
  opportunities: { data: null, timestamp: 0 },
  talentFlow: { data: null, timestamp: 0, key: '' }
};

// Cache validity duration in milliseconds
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Debounce timers
let debounceTimers = {
  recommendations: null,
  insights: null,
  opportunities: null,
  talentFlow: null
};

// Action types
const ActionTypes = {
  SET_MODE: 'SET_MODE',
  SET_FILTERS: 'SET_FILTERS',
  SET_COMPANIES: 'SET_COMPANIES',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_PORTFOLIO_OVERVIEW: 'SET_PORTFOLIO_OVERVIEW',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_RECOMMENDATIONS: 'SET_RECOMMENDATIONS',
  SET_INSIGHTS: 'SET_INSIGHTS',
  SET_OPPORTUNITIES: 'SET_OPPORTUNITIES',
  SET_TALENT_FLOW: 'SET_TALENT_FLOW',
  SET_COMPANY_ANALYTICS: 'SET_COMPANY_ANALYTICS'
};

// Reducer
function vcReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_MODE:
      return {
        ...state,
        mode: action.payload,
        companies: [], // Clear companies when switching modes
        error: null
      };
    
    case ActionTypes.SET_FILTERS:
      return {
        ...state,
        filters: {
          ...state.filters,
          ...action.payload
        }
      };
    
    case ActionTypes.SET_COMPANIES:
      return {
        ...state,
        companies: action.payload,
        loading: false,
        error: null
      };
    
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };
    
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };
    
    case ActionTypes.SET_PORTFOLIO_OVERVIEW:
      return {
        ...state,
        portfolioOverview: action.payload,
        loading: false
      };
    
    case ActionTypes.CLEAR_ERROR:
      return {
        ...state,
        error: null
      };
      
    case ActionTypes.SET_RECOMMENDATIONS:
      return {
        ...state,
        recommendations: action.payload,
        loading: false
      };
      
    case ActionTypes.SET_INSIGHTS:
      return {
        ...state,
        insights: action.payload,
        loading: false
      };
      
    case ActionTypes.SET_OPPORTUNITIES:
      return {
        ...state,
        opportunities: action.payload,
        loading: false
      };
      
    case ActionTypes.SET_TALENT_FLOW:
      return {
        ...state,
        talentFlowData: action.payload,
        loading: false
      };
      
    case ActionTypes.SET_COMPANY_ANALYTICS:
      return {
        ...state,
        companyAnalytics: action.payload,
        loading: false
      };
    
    default:
      return state;
  }
}

// Helper function for API calls
async function callApi(endpoint, method = 'GET', body = null) {
  console.log(`Making API request to: ${API_BASE_URL}${endpoint}`, { method, body });
  
  try {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    console.log(`API response status: ${response.status}`);
    
    if (!response.ok) {
      const errorText = await response.text();
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

// Context
const VCContext = createContext();

// Provider component
export function VCProvider({ children }) {
  const [state, dispatch] = useReducer(vcReducer, initialState);

  // Load user preferences from localStorage on mount
  useEffect(() => {
    const savedFilters = localStorage.getItem('vc_filters');
    const savedMode = localStorage.getItem('vc_mode');
    
    if (savedFilters) {
      try {
        const filters = JSON.parse(savedFilters);
        dispatch({ type: ActionTypes.SET_FILTERS, payload: filters });
      } catch (err) {
        console.error('Error loading saved filters:', err);
      }
    }
    
    if (savedMode && ['research', 'portfolio'].includes(savedMode)) {
      dispatch({ type: ActionTypes.SET_MODE, payload: savedMode });
    }
  }, []);

  // Save filters to localStorage when they change
  useEffect(() => {
    localStorage.setItem('vc_filters', JSON.stringify(state.filters));
  }, [state.filters]);

  // Save mode to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('vc_mode', state.mode);
  }, [state.mode]);

  // Actions
  const actions = {
    setMode: (mode) => {
      dispatch({ type: ActionTypes.SET_MODE, payload: mode });
    },
    
    setFilters: (filters) => {
      dispatch({ type: ActionTypes.SET_FILTERS, payload: filters });
    },
    
    clearError: () => {
      dispatch({ type: ActionTypes.CLEAR_ERROR });
    },
    
    searchCompanies: async () => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      try {
        const data = await callApi('/vc/companies/search', 'POST', {
          mode: state.mode,
          ...state.filters
        });
        
        if (data.success) {
          dispatch({ type: ActionTypes.SET_COMPANIES, payload: data.companies || [] });
        } else {
          dispatch({ type: ActionTypes.SET_ERROR, payload: data.error || 'Failed to fetch companies' });
        }
      } catch (error) {
        console.error('Search companies error:', error);
        dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
      }
    },
    
    loadPortfolioOverview: async () => {
      if (state.mode !== 'portfolio') return;
      
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      try {
        // If no portfolio IDs selected, use empty array
        const portfolioIds = state.filters.portfolio_ids || [];
        
        const data = await callApi('/vc/portfolio/overview', 'POST', portfolioIds);
        
        if (data.success) {
          dispatch({ type: ActionTypes.SET_PORTFOLIO_OVERVIEW, payload: data.overview || null });
        } else {
          dispatch({ type: ActionTypes.SET_ERROR, payload: data.error || 'Failed to fetch portfolio overview' });
        }
      } catch (error) {
        console.error('Load portfolio overview error:', error);
        dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
      }
    },
    
    loadTrendingSkills: async (limit = 10) => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      try {
        const data = await aiService.getTrendingSkills(limit);
        
        if (data.success) {
          return data.skills || [];
        } else {
          dispatch({ type: ActionTypes.SET_ERROR, payload: data.error || 'Failed to fetch trending skills' });
          return [];
        }
      } catch (error) {
        console.error('Load trending skills error:', error);
        dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
        return [];
      } finally {
        dispatch({ type: ActionTypes.SET_LOADING, payload: false });
      }
    },
    
    // AI-powered recommendation engine with caching and debouncing
    getRecommendations: async (mode = 'investment', context = {}) => {
      // Check cache first
      const currentTime = Date.now();
      if (apiCache.recommendations.data && 
          currentTime - apiCache.recommendations.timestamp < CACHE_DURATION) {
        // Return cached data if it's still valid
        console.log('Using cached recommendations data');
        return apiCache.recommendations.data;
      }
      
      // Clear any existing debounce timer
      if (debounceTimers.recommendations) {
        clearTimeout(debounceTimers.recommendations);
      }
      
      // Set loading state
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      console.log('VCContext: Getting recommendations with mode:', mode, 'context:', context);
      
      // Create a timeout promise to ensure we don't hang forever
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error('VCContext: Recommendations request timed out after 10 seconds'));
        }, 10000); // 10 second timeout
      });
      
      // Return a promise that resolves when the debounced API call completes
      const actionPromise = new Promise((resolve) => {
        // Create debounced API call
        debounceTimers.recommendations = setTimeout(async () => {
          try {
            // Direct fetch to bypass any possible aiService issues
            console.log('VCContext: Making direct fetch call to recommendations endpoint');
            const directResponse = await fetch(`${API_BASE_URL}/analytics/recommendations?mode=${mode}`, {
              method: 'GET',
              mode: 'cors',
              headers: {
                'Content-Type': 'application/json'
              }
            });
            
            console.log('VCContext: Direct fetch response status:', directResponse.status);
            
            let data;
            if (directResponse.ok) {
              data = await directResponse.json();
              console.log('VCContext: Direct fetch successful, data:', data);
            } else {
              console.error('VCContext: Direct fetch failed with status:', directResponse.status);
              
              // Fallback to aiService if direct fetch fails
              console.log('VCContext: Falling back to aiService');
              data = await aiService.getRecommendations(mode, context);
            }
            
            console.log('VCContext: Received recommendations data:', data);
            
            // Check that data is valid
            if (!data || !Array.isArray(data) || data.length === 0) {
              console.error('VCContext: Invalid recommendations data format:', data);
              
              // TEMPORARILY DISABLE MOCK DATA to see real errors
              // Generate mock data as fallback
              console.warn('VCContext: No data received or empty array. APIs may not be returning data.');
              // const mockData = actions.generateMockRecommendations(mode);
              
              // Store the mock data in cache to avoid repeated errors
              apiCache.recommendations = {
                data: [], // Empty array instead of mock data
                timestamp: Date.now()
              };
              
              // Store recommendations in state
              dispatch({ type: ActionTypes.SET_RECOMMENDATIONS, payload: [] });
              dispatch({ type: ActionTypes.SET_LOADING, payload: false });
              
              resolve([]);
              return;
            }
            
            // Store data in cache
            apiCache.recommendations = {
              data,
              timestamp: Date.now()
            };
            
            // Store recommendations in state
            dispatch({ type: ActionTypes.SET_RECOMMENDATIONS, payload: data || [] });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            
            resolve(data);
          } catch (error) {
            console.error('VCContext: Get recommendations error:', error);
            console.error('VCContext: Error details:', {
              message: error.message,
              status: error.status,
              endpoint: `/analytics/recommendations?mode=${mode}`,
              url: `${API_BASE_URL}/analytics/recommendations?mode=${mode}`,
              responseData: error.responseData || 'No response data',
              stack: error.stack
            });
            
            // TEMPORARILY DISABLE MOCK DATA to see real errors
            // const mockData = actions.generateMockRecommendations(mode);
            
            // Set detailed error
            const errorMessage = `API Error (${error.status || 'unknown'}): ${error.message}. Check console for details.`;
            
            dispatch({ type: ActionTypes.SET_ERROR, payload: errorMessage });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            // dispatch({ type: ActionTypes.SET_RECOMMENDATIONS, payload: mockData });
            dispatch({ type: ActionTypes.SET_RECOMMENDATIONS, payload: [] });
            
            // resolve(mockData);
            resolve([]);  // Return empty array instead of mock data
          }
        }, 300); // 300ms debounce time
      });
      
      // Wait for either the debounced API call or the timeout
      return Promise.race([actionPromise, timeoutPromise]);
    },
    
    // Helper to generate mock recommendations
    generateMockRecommendations: (mode = 'investment') => {
      if (mode === 'investment') {
        return [
          {
            id: 'mock-rec-001',
            companyId: 'mock-comp-001',
            companyName: 'AI Innovators',
            sector: 'AI/ML',
            stage: 'Series A',
            valuation: 25,
            growthRate: 28.5,
            score: 0.87,
            talentInflow: 15,
            talentOutflow: 3,
            keyFactors: ['Strong talent acquisition', 'Growing revenue', 'Market position'],
            aiExplanation: 'Shows significant growth potential based on talent acquisition patterns.'
          },
          {
            id: 'mock-rec-002',
            companyId: 'mock-comp-002',
            companyName: 'DataMind',
            sector: 'Data Analytics',
            stage: 'Series B',
            valuation: 48,
            growthRate: 32.1,
            score: 0.82,
            talentInflow: 12,
            talentOutflow: 5,
            keyFactors: ['Technology leadership', 'Strong exec team', 'Market growth'],
            aiExplanation: 'Well positioned in the rapidly growing data analytics space.'
          },
          {
            id: 'mock-rec-003',
            companyId: 'mock-comp-003',
            companyName: 'CyberDefense',
            sector: 'Cybersecurity',
            stage: 'Series A',
            valuation: 18,
            growthRate: 45.2,
            score: 0.79,
            talentInflow: 10,
            talentOutflow: 2,
            keyFactors: ['High growth rate', 'Strong product-market fit', 'Talent retention'],
            aiExplanation: 'Exceptional growth in the cybersecurity sector with strong talent metrics.'
          }
        ];
      } else if (mode === 'talent') {
        return [
          {
            id: 'mock-rec-t001',
            candidateName: 'Alex Chen',
            currentRole: 'Senior ML Engineer',
            currentCompany: 'TechCorp',
            skillMatch: 0.92,
            cultureMatch: 0.89,
            retentionScore: 0.85,
            fitScore: 4.7,
            skills: ['Deep Learning', 'TensorFlow', 'PyTorch', 'Computer Vision'],
            aiExplanation: 'Strong match (92%) with required skills and culture fit.'
          },
          {
            id: 'mock-rec-t002',
            candidateName: 'Sarah Johnson',
            currentRole: 'Data Science Lead',
            currentCompany: 'DataWorks',
            skillMatch: 0.88,
            cultureMatch: 0.91,
            retentionScore: 0.82,
            fitScore: 4.5,
            skills: ['Machine Learning', 'Python', 'Data Architecture', 'Team Leadership'],
            aiExplanation: 'Strong match (88%) with required skills and excellent leadership experience.'
          }
        ];
      } else { // partnership mode
        return [
          {
            id: 'mock-rec-p001',
            companyName: 'CloudNet Solutions',
            industry: 'Cloud Infrastructure',
            size: 'Large',
            score: 0.88,
            synergies: ['Technology Integration', 'Market Access', 'Complementary Products'],
            aiExplanation: 'Potential synergies in technology integration and market access.'
          },
          {
            id: 'mock-rec-p002',
            companyName: 'SecurityPro',
            industry: 'Cybersecurity',
            size: 'Medium',
            score: 0.84,
            synergies: ['Product Enhancement', 'Customer Base', 'Technical Expertise'],
            aiExplanation: 'Strong potential for product enhancement and shared customer base advantages.'
          }
        ];
      }
    },
    
    // Get AI-generated insights with caching and debouncing
    getInsights: async (context = {}) => {
      // Check cache first
      const currentTime = Date.now();
      if (apiCache.insights.data && 
          currentTime - apiCache.insights.timestamp < CACHE_DURATION) {
        // Return cached data if it's still valid
        console.log('Using cached insights data');
        return apiCache.insights.data;
      }
      
      // Clear any existing debounce timer
      if (debounceTimers.insights) {
        clearTimeout(debounceTimers.insights);
      }
      
      // Set loading state
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      // Return a promise that resolves when the debounced API call completes
      return new Promise((resolve) => {
        // Create debounced API call
        debounceTimers.insights = setTimeout(async () => {
          try {
            // Use aiService to fetch insights
            const data = await aiService.getInsights(context);
            
            // Store data in cache
            apiCache.insights = {
              data,
              timestamp: Date.now()
            };
            
            // Store insights in state
            dispatch({ type: ActionTypes.SET_INSIGHTS, payload: data || [] });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            
            resolve(data);
          } catch (error) {
            console.error('Get insights error:', error);
            dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            resolve([]);
          }
        }, 300); // 300ms debounce time
      });
    },
    
    // Get AI-identified opportunities with caching and debouncing
    getOpportunities: async (context = {}) => {
      // Check cache first
      const currentTime = Date.now();
      if (apiCache.opportunities.data && 
          currentTime - apiCache.opportunities.timestamp < CACHE_DURATION) {
        // Return cached data if it's still valid
        console.log('Using cached opportunities data');
        return apiCache.opportunities.data;
      }
      
      // Clear any existing debounce timer
      if (debounceTimers.opportunities) {
        clearTimeout(debounceTimers.opportunities);
      }
      
      // Set loading state
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      // Return a promise that resolves when the debounced API call completes
      return new Promise((resolve) => {
        // Create debounced API call
        debounceTimers.opportunities = setTimeout(async () => {
          try {
            // Use aiService to fetch opportunities
            const data = await aiService.getOpportunities(context);
            
            // Store data in cache
            apiCache.opportunities = {
              data,
              timestamp: Date.now()
            };
            
            // Store opportunities in state
            dispatch({ type: ActionTypes.SET_OPPORTUNITIES, payload: data || [] });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            
            resolve(data);
          } catch (error) {
            console.error('Get opportunities error:', error);
            dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
            dispatch({ type: ActionTypes.SET_LOADING, payload: false });
            resolve([]);
          }
        }, 300); // 300ms debounce time
      });
    },
    
    // Get talent flow data
    getTalentFlowAnalysis: async (request = {}) => {
      console.log('VCContext: Getting talent flow analysis with request:', request);
      
      try {
        // Use aiService to fetch talent flow data
        const data = await aiService.getTalentFlowAnalysis(request);
        console.log('VCContext: Received talent flow data:', data);
        
        // Validate the response structure
        if (!data || !data.nodes || !data.links || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
          console.error('VCContext: Invalid talent flow data format:', data);
          
          // Generate mock data as fallback
          console.warn('VCContext: Generating mock talent flow data as fallback');
          const mockData = {
            nodes: [
              { id: 'company-1', name: 'TechNova AI', inflow: 15, outflow: 5 },
              { id: 'company-2', name: 'DataSphere', inflow: 8, outflow: 12 },
              { id: 'company-3', name: 'CloudSecure', inflow: 7, outflow: 9 },
              { id: 'company-4', name: 'FinStack', inflow: 10, outflow: 3 },
              { id: 'company-5', name: 'HealthAI', inflow: 14, outflow: 6 }
            ],
            links: [
              { source: 'company-2', target: 'company-1', value: 8 },
              { source: 'company-3', target: 'company-1', value: 7 },
              { source: 'company-3', target: 'company-5', value: 5 },
              { source: 'company-1', target: 'company-4', value: 3 },
              { source: 'company-2', target: 'company-5', value: 6 },
              { source: 'company-4', target: 'company-5', value: 3 },
              { source: 'company-5', target: 'company-1', value: 4 }
            ],
            top_sources: [
              { name: 'DataSphere', outflow: 14 },
              { name: 'CloudSecure', outflow: 12 }
            ],
            top_destinations: [
              { name: 'TechNova AI', inflow: 15 },
              { name: 'HealthAI', inflow: 14 }
            ]
          };
          
          return mockData;
        }
        
        return data;
      } catch (error) {
        console.error('VCContext: Get talent flow analysis error:', error);
        
        // Generate mock data as fallback on error
        console.warn('VCContext: Generating mock talent flow data due to error');
        const mockData = {
          nodes: [
            { id: 'company-1', name: 'TechNova AI', inflow: 15, outflow: 5 },
            { id: 'company-2', name: 'DataSphere', inflow: 8, outflow: 12 },
            { id: 'company-3', name: 'CloudSecure', inflow: 7, outflow: 9 },
            { id: 'company-4', name: 'FinStack', inflow: 10, outflow: 3 },
            { id: 'company-5', name: 'HealthAI', inflow: 14, outflow: 6 }
          ],
          links: [
            { source: 'company-2', target: 'company-1', value: 8 },
            { source: 'company-3', target: 'company-1', value: 7 },
            { source: 'company-3', target: 'company-5', value: 5 },
            { source: 'company-1', target: 'company-4', value: 3 },
            { source: 'company-2', target: 'company-5', value: 6 },
            { source: 'company-4', target: 'company-5', value: 3 },
            { source: 'company-5', target: 'company-1', value: 4 }
          ],
          top_sources: [
            { name: 'DataSphere', outflow: 14 },
            { name: 'CloudSecure', outflow: 12 }
          ],
          top_destinations: [
            { name: 'TechNova AI', inflow: 15 },
            { name: 'HealthAI', inflow: 14 }
          ]
        };
        
        return mockData;
      }
    },
    
    // Get company deep dive analysis
    getCompanyAnalytics: async (companyId, options = {}) => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      try {
        // Use aiService to fetch company analytics
        const data = await aiService.getCompanyAnalytics(companyId, options);
        
        // Store company analytics in state
        dispatch({ type: ActionTypes.SET_COMPANY_ANALYTICS, payload: data });
        
        return data;
      } catch (error) {
        console.error('Get company analytics error:', error);
        dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
        return null;
      } finally {
        dispatch({ type: ActionTypes.SET_LOADING, payload: false });
      }
    },
    
    // Get company score calculations
    getCompanyScores: async (companyUrns = []) => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: true });
      
      try {
        // Use aiService to fetch company scores
        const data = await aiService.getCompanyScores(companyUrns);
        
        return data;
      } catch (error) {
        console.error('Get company scores error:', error);
        dispatch({ type: ActionTypes.SET_ERROR, payload: error.message });
        return [];
      } finally {
        dispatch({ type: ActionTypes.SET_LOADING, payload: false });
      }
    }
  };

  return (
    <VCContext.Provider value={{ state, actions }}>
      {children}
    </VCContext.Provider>
  );
}

// Hook to use VC context
export function useVC() {
  const context = useContext(VCContext);
  if (!context) {
    throw new Error('useVC must be used within a VCProvider');
  }
  return context;
}