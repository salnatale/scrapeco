// AI Service - Centralizes all AI-related functionality and API calls
const API_BASE_URL = 'http://localhost:8000/api';

// Helper function to make API calls
const callApi = async (endpoint, method = 'GET', body = null, token = null) => {
  const fullUrl = `${API_BASE_URL}${endpoint}`;
  console.log(`AI Service: STARTING API request to: ${fullUrl}`, { method, body });
  console.log(`AI Service: Request time:`, new Date().toISOString());
  
  try {
    const options = {
      method,
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
      }
    };

    // Add authentication token if provided
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (body) {
      options.body = JSON.stringify(body);
    }

    console.log(`AI Service: Calling fetch with options:`, options);
    console.log(`AI Service: Full URL:`, fullUrl);
    
    // Add timeout to detect hanging requests
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    options.signal = controller.signal;
    
    try {
      const response = await fetch(fullUrl, options);
      // Clear the timeout
      clearTimeout(timeoutId);
      
      console.log(`AI Service: API response status: ${response.status}`);
      console.log(`AI Service: Response headers:`, Object.fromEntries([...response.headers.entries()]));
      
      if (!response.ok) {
        const responseText = await response.text();
        console.error(`AI Service: Error response text:`, responseText);
        
        let errorData;
        
        try {
          // Try to parse response as JSON
          errorData = JSON.parse(responseText);
        } catch (e) {
          // If not valid JSON, use the raw text
          errorData = { detail: responseText };
        }
        
        // Create enhanced error with additional info for rate limiting
        const error = new Error(`API Error (${response.status}): ${errorData.detail || responseText}`);
        
        // Add response info to the error for better handling
        error.status = response.status;
        error.response = response;
        error.responseData = errorData;
        
        // Add rate limit specific info if available
        if (response.status === 429) {
          error.isRateLimit = true;
          error.retryAfter = errorData.retry_after || 
                             parseInt(response.headers.get('Retry-After'), 10) || 
                             60; // Default to 60 seconds
          
          error.debugInfo = errorData.debug_info || {};
          console.warn(`Rate limit hit for ${endpoint}. Suggested retry after: ${error.retryAfter}s`);
        }
        
        throw error;
      }

      // Log response type before parsing
      console.log(`AI Service: Response content-type:`, response.headers.get('content-type'));
      
      // Clone the response for debugging
      const clonedResponse = response.clone();
      const rawText = await clonedResponse.text();
      console.log(`AI Service: Raw response text (first 500 chars):`, rawText.substring(0, 500));
      
      // Parse JSON from the original response
      let data;
      try {
        data = JSON.parse(rawText);
        console.log("AI Service: Successfully parsed JSON data:", data);
      } catch (e) {
        console.error("AI Service: JSON parsing error:", e);
        console.error("AI Service: Raw response was:", rawText);
        throw new Error(`Failed to parse JSON response from ${endpoint}: ${e.message}`);
      }
      
      return data;
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') {
        console.error(`AI Service: Request to ${fullUrl} timed out after 10 seconds`);
        throw new Error(`Request to ${fullUrl} timed out after 10 seconds`);
      }
      throw e;
    }
  } catch (error) {
    console.error(`AI Service: API call failed for endpoint: ${endpoint}`, error);
    throw error;
  }
};

// AI Service methods
const aiService = {
  // Recommendation related functions
  getRecommendations: async (mode = 'investment', context = {}, token = null, retryCount = 0) => {
    // Determine query parameters based on mode
    const params = new URLSearchParams({
      mode,
      ...context
    });
    
    try {
      // Fetch recommendations from AI analytics endpoint
      return await callApi(`/analytics/recommendations?${params}`, 'GET', null, token);
    } catch (error) {
      console.error('AI Service: Get recommendations error:', error);
      
      // Implement retry with exponential backoff for rate limit errors
      if (error.isRateLimit && retryCount < 3) {
        // Calculate backoff time: 2^retryCount * base delay (in ms)
        const baseDelay = 1000; // 1 second base
        const backoffDelay = Math.min(
          (2 ** retryCount) * baseDelay,
          error.retryAfter ? error.retryAfter * 1000 : 10000 // Use server suggestion if available
        );
        
        console.log(`Rate limit hit, retrying after ${backoffDelay/1000}s delay (retry ${retryCount + 1}/3)`);
        
        // Wait for the backoff period
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        
        // Retry the request with incremented retry count
        return aiService.getRecommendations(mode, context, token, retryCount + 1);
      }
      
      throw error;
    }
  },
  
  getInsights: async (context = {}, token = null, retryCount = 0) => {
    // Determine query parameters
    const params = new URLSearchParams(context);
    
    try {
      // Fetch insights from AI analytics endpoint
      return await callApi(`/analytics/insights?${params}`, 'GET', null, token);
    } catch (error) {
      console.error('AI Service: Get insights error:', error);
      
      // Implement retry with exponential backoff for rate limit errors
      if (error.isRateLimit && retryCount < 3) {
        // Calculate backoff time: 2^retryCount * base delay (in ms)
        const baseDelay = 1000; // 1 second base
        const backoffDelay = Math.min(
          (2 ** retryCount) * baseDelay,
          error.retryAfter ? error.retryAfter * 1000 : 10000 // Use server suggestion if available
        );
        
        console.log(`Rate limit hit, retrying after ${backoffDelay/1000}s delay (retry ${retryCount + 1}/3)`);
        
        // Wait for the backoff period
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        
        // Retry the request with incremented retry count
        return aiService.getInsights(context, token, retryCount + 1);
      }
      
      throw error;
    }
  },
  
  getOpportunities: async (context = {}, token = null, retryCount = 0) => {
    // Determine query parameters
    const params = new URLSearchParams(context);
    
    try {
      // Fetch opportunities from AI analytics endpoint
      return await callApi(`/analytics/opportunities?${params}`, 'GET', null, token);
    } catch (error) {
      console.error('AI Service: Get opportunities error:', error);
      
      // Implement retry with exponential backoff for rate limit errors
      if (error.isRateLimit && retryCount < 3) {
        // Calculate backoff time: 2^retryCount * base delay (in ms)
        const baseDelay = 1000; // 1 second base
        const backoffDelay = Math.min(
          (2 ** retryCount) * baseDelay,
          error.retryAfter ? error.retryAfter * 1000 : 10000 // Use server suggestion if available
        );
        
        console.log(`Rate limit hit, retrying after ${backoffDelay/1000}s delay (retry ${retryCount + 1}/3)`);
        
        // Wait for the backoff period
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        
        // Retry the request with incremented retry count
        return aiService.getOpportunities(context, token, retryCount + 1);
      }
      
      throw error;
    }
  },
  
  // Talent flow analysis
  getTalentFlowAnalysis: async (request, token = null, retryCount = 0) => {
    try {
      // Fetch talent flow data from AI analytics endpoint
      return await callApi('/analytics/talent-flow', 'POST', request, token);
    } catch (error) {
      console.error('AI Service: Get talent flow analysis error:', error);
      
      // Implement retry with exponential backoff for rate limit errors
      if (error.isRateLimit && retryCount < 3) {
        // Calculate backoff time: 2^retryCount * base delay (in ms)
        const baseDelay = 1000; // 1 second base
        const backoffDelay = Math.min(
          (2 ** retryCount) * baseDelay,
          error.retryAfter ? error.retryAfter * 1000 : 10000 // Use server suggestion if available
        );
        
        console.log(`Rate limit hit, retrying after ${backoffDelay/1000}s delay (retry ${retryCount + 1}/3)`);
        
        // Wait for the backoff period
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
        
        // Retry the request with incremented retry count
        return aiService.getTalentFlowAnalysis(request, token, retryCount + 1);
      }
      
      // For non-rate limit errors or if max retries reached
      throw error;
    }
  },
  
  // Company deep dive analysis
  getCompanyAnalytics: async (companyId, options = {}, token = null) => {
    try {
      const request = {
        company_id: companyId,
        ...options
      };
      
      // Fetch company analytics from AI analytics endpoint
      return await callApi('/analytics/company-deep-dive', 'POST', request, token);
    } catch (error) {
      console.error('AI Service: Get company analytics error:', error);
      throw error;
    }
  },
  
  // Company scoring
  getCompanyScores: async (companyUrns = [], token = null) => {
    try {
      const request = {
        company_urns: companyUrns,
        include_pagerank: true,
        include_birank: true, 
        include_talent_flow: true
      };
      
      // Fetch company scores from AI analytics endpoint
      return await callApi('/analytics/company-scores', 'POST', request, token);
    } catch (error) {
      console.error('AI Service: Get company scores error:', error);
      throw error;
    }
  },
  
  // Geographic analysis 
  getGeographicAnalysis: async (request, token = null) => {
    try {
      // Fetch geographic analysis from AI analytics endpoint
      return await callApi('/analytics/geographic', 'POST', request, token);
    } catch (error) {
      console.error('AI Service: Get geographic analysis error:', error);
      throw error;
    }
  },
  
  // Alert monitoring system
  createAlert: async (alertConfig, token = null) => {
    try {
      // Create new alert in the monitoring system
      return await callApi('/analytics/create-alert', 'POST', alertConfig, token);
    } catch (error) {
      console.error('AI Service: Create alert error:', error);
      throw error;
    }
  },
  
  checkAlerts: async (token = null) => {
    try {
      // Check for triggered alerts
      return await callApi('/analytics/check-alerts', 'GET', null, token);
    } catch (error) {
      console.error('AI Service: Check alerts error:', error);
      throw error;
    }
  },
  
  // Upload and process resumes using AI
  processResume: async (formData, token = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/upload/resume`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('AI Service: Process resume error:', error);
      throw error;
    }
  },
  
  // Get trending skills analysis
  getTrendingSkills: async (limit = 10, token = null) => {
    try {
      return await callApi(`/vc/skills/trending?limit=${limit}`, 'GET', null, token);
    } catch (error) {
      console.error('AI Service: Get trending skills error:', error);
      throw error;
    }
  }
};

export default aiService; 