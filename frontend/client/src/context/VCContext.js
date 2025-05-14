// frontend/client/src/context/VCContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';

// API base URL
const API_BASE_URL = 'http://localhost:5001/api';

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
  portfolioOverview: null
};

// Action types
const ActionTypes = {
  SET_MODE: 'SET_MODE',
  SET_FILTERS: 'SET_FILTERS',
  SET_COMPANIES: 'SET_COMPANIES',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_PORTFOLIO_OVERVIEW: 'SET_PORTFOLIO_OVERVIEW',
  CLEAR_ERROR: 'CLEAR_ERROR'
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
        const data = await callApi(`/vc/skills/trending?limit=${limit}`);
        
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