// Test script to verify API connection

const fetch = require('node-fetch');

const API_BASE_URL = 'http://localhost:8000/api';

async function testApiCall() {
  console.log('Starting API test...');
  
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/recommendations?mode=investment`);
    
    console.log('API Response Status:', response.status);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('API Response Data:', data);
    
    if (Array.isArray(data) && data.length > 0) {
      console.log('✅ API TEST SUCCESSFUL! Received recommendations data:', data.length, 'items');
      console.log('First item:', data[0]);
    } else {
      console.log('⚠️ API TEST WARNING! Received empty array or non-array response');
    }
    
    return data;
  } catch (error) {
    console.error('❌ API TEST FAILED! Error:', error.message);
    throw error;
  }
}

// Run the test
testApiCall()
  .then(data => console.log('Test completed successfully with', data.length, 'items'))
  .catch(err => console.error('Test failed with error:', err.message)); 