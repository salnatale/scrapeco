const express = require('express');
const multer = require('multer');
const FormData = require('form-data');
require('dotenv').config();
const path = require('path');
const fs = require('fs');


const app = express();
const port = process.env.PORT || 5001;
const axios = require('axios');


console.log("Starting Express server...");

// Simple in-memory cache implementation
const cache = {
  data: {},
  timestamps: {},
  
  // Set a cache entry with expiration
  set(key, value, ttlSeconds = 300) {
    console.log(`Cache: Setting ${key} with TTL ${ttlSeconds}s`);
    this.data[key] = value;
    this.timestamps[key] = Date.now() + (ttlSeconds * 1000);
  },
  
  // Get a cache entry if still valid
  get(key) {
    const timestamp = this.timestamps[key];
    if (!timestamp) return null;
    
    // Check if expired
    if (Date.now() > timestamp) {
      console.log(`Cache: ${key} expired`);
      delete this.data[key];
      delete this.timestamps[key];
      return null;
    }
    
    console.log(`Cache: Hit for ${key}, expires in ${Math.round((timestamp - Date.now())/1000)}s`);
    return this.data[key];
  },
  
  // Check if a key is in the cache and not expired
  has(key) {
    return this.get(key) !== null;
  }
};

// Global request limiter to prevent excessive API calls
// Track requests by IP + endpoint
const requestLimiter = {
  // Store request timestamps: { 'ip:endpoint': timestamp }
  requests: {},
  
  // Default cooldown periods for different endpoints (in ms)
  cooldowns: {
    '/api/vc/skills/trending': 5000,  // 5 seconds for trending skills
    '/api/vc/companies/search': 2000, // 2 seconds for company search
    'default': 500                    // 500ms for other endpoints (less aggressive)
  },
  
  // Check if a request is allowed
  isAllowed(req) {
    const ip = req.ip || req.connection.remoteAddress;
    const endpoint = req.originalUrl.split('?')[0]; // Remove query params for better matching
    const key = `${ip}:${endpoint}`;
    
    const now = Date.now();
    const lastRequest = this.requests[key] || 0;
    
    // Get cooldown for this endpoint or use default
    const cooldown = this.cooldowns[endpoint] || this.cooldowns.default;
    
    // Check if enough time has passed since last request
    if (now - lastRequest < cooldown) {
      console.log(`Rate limit exceeded for ${key}, last: ${now - lastRequest}ms ago, cooldown: ${cooldown}ms`);
      return false;
    }
    
    // Update last request timestamp
    this.requests[key] = now;
    return true;
  }
};

// Global request limiter middleware
app.use((req, res, next) => {
  // Skip rate limiting for static assets and OPTIONS requests
  if (req.path.startsWith('/static/') || req.method === 'OPTIONS') {
    return next();
  }
  
  // Create a key that includes the request body hash for POST requests
  let requestKey = req.originalUrl;
  
  // Check if request is allowed
  if (requestLimiter.isAllowed(req)) {
    return next();
  }
  
  // If rate limited, either return cached data or 429 error
  if (req.method === 'GET' && cache.has(requestKey)) {
    console.log(`Rate limited GET request, serving from cache: ${requestKey}`);
    return res.json(cache.get(requestKey));
  }
  
  // For POST requests to search endpoints, check cache with body params as key
  if (req.method === 'POST' && req.originalUrl === '/api/vc/companies/search' && req.body) {
    const cacheKey = `companies_search_${JSON.stringify(req.body)}`;
    if (cache.has(cacheKey)) {
      console.log(`Rate limited POST request, serving from cache: ${cacheKey}`);
      return res.json(cache.get(cacheKey));
    }
  }
  
  // Instead of returning 429, pass through but with a flag to use mock data
  // This avoids breaking the client application
  req.useBackupData = true;
  next();
});

// Ensure the uploads directory exists
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

const cors = require('cors');
// Configure CORS with more specific options
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:5173'], // Frontend URLs
  credentials: true, // Allow credentials
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  exposedHeaders: ['Content-Length', 'Authorization'],
  maxAge: 86400 // Cache preflight requests for 24 hours
}));

// Add detailed request logging
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  console.log('Request headers:', req.headers);
  
  // Add CORS headers to all responses
  res.header('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.header('Access-Control-Allow-Credentials', 'true');
  
  // Log the response on finish
  res.on('finish', () => {
    console.log(`[${new Date().toISOString()}] Response ${res.statusCode} for ${req.method} ${req.originalUrl}`);
  });
  
  next();
});

// Add JSON body parser middleware
app.use(express.json());

// Configure storage for multer
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    // Prepend a timestamp to the original filename
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ storage: storage });

// Endpoint for resume uploads
app.post('/api/upload/resume', upload.single('file'), async (req, res) => {
  console.log('/api/upload/resume endpoint hit');
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }

  const uploadedFilePath = path.join(__dirname, 'uploads', req.file.filename);

  try {
    // Send file to FastAPI for processing
    const form = new FormData();
    form.append('file', fs.createReadStream(uploadedFilePath), req.file.originalname);

    const fastApiRes = await axios.post(
      'http://localhost:8000/api/upload/resume', // your FastAPI resume endpoint
      form,
      { headers: form.getHeaders() }
    );

    console.log('Resume processed by FastAPI:', fastApiRes.data);

    // Respond to client
    res.json({
      message: 'Resume uploaded and processed successfully.',
      file: req.file.filename,
      fastApiResponse: fastApiRes.data
    });

  } catch (err) {
    console.error('Failed to process resume via FastAPI:', err.message);
    res.status(500).send({
      error: 'Resume uploaded but processing failed.',
      detail: err.message
    });
  }
});

// Endpoint for LinkedIn screenshot uploads
app.post('/api/upload/linkedin', upload.single('file'), async (req, res) => {
  console.log('/api/upload/linkedin endpoint hit');
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }

  const uploadedFilePath = path.join(__dirname, 'uploads', req.file.filename);

  try {
    // Send file to FastAPI for processing
    const form = new FormData();
    form.append('file', fs.createReadStream(uploadedFilePath), req.file.originalname);

    const fastApiRes = await axios.post(
      'http://localhost:8000/api/upload/linkedin', // fastAPI endpoint
      form,
      { headers: form.getHeaders() }
    );

    console.log('File processed by FastAPI:', fastApiRes.data);

    // Respond back to client
    res.json({
      message: 'LinkedIn screenshot uploaded and processed successfully.',
      file: req.file.filename,
      fastApiResponse: fastApiRes.data
    });
    // error handling

  } catch (err) {
    console.error('Failed to process file via FastAPI:', err.message);
    res.status(500).send({
      error: 'File uploaded but processing failed.',
      detail: err.message
    });
  }
});

// --------- VC Dashboard API Endpoints ---------

// Companies search endpoint
app.post('/api/vc/companies/search', async (req, res) => {
  console.log('/api/vc/companies/search endpoint hit:', req.body);
  
  // Create cache key from request body
  const cacheKey = `companies_search_${JSON.stringify(req.body)}`;
  
  // If we have a valid cached response, return it
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for companies search: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  // Use mock data if rate limited or if useBackupData flag is set
  if (req.useBackupData) {
    console.log('Using mock data for rate limited companies search request');
    const mockResponse = {
      success: true,
      companies: [
        {
          name: 'TechNova AI',
          urn: 'urn:li:company:tech1',
          industry: 'AI/ML',
          employeeCount: 86,
          recentTransitions: 15,
          growthRate: 18.5,
          churnRate: 7.2
        },
        {
          name: 'DataSphere',
          urn: 'urn:li:company:data1',
          industry: 'Data/Analytics',
          employeeCount: 120,
          recentTransitions: 10,
          growthRate: 12.8,
          churnRate: 9.3
        },
        {
          name: 'CloudSecure',
          urn: 'urn:li:company:cloud1',
          industry: 'Cybersecurity',
          employeeCount: 65,
          recentTransitions: 7,
          growthRate: 9.5,
          churnRate: 6.1
        }
      ],
      total: 3
    };
    
    // Cache mock response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    return res.json(mockResponse);
  }
  
  try {
    // Add a small delay to prevent rapid successive requests (helps with race conditions)
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const fastApiRes = await axios.post(
      'http://localhost:8000/api/vc/companies/search',
      req.body,
      { 
        headers: { 'Content-Type': 'application/json' },
        timeout: 5000 // Add timeout to prevent hanging requests
      }
    );
    
    console.log('Companies search result:', fastApiRes.data);
    
    // Cache successful response for 5 minutes
    cache.set(cacheKey, fastApiRes.data, 300);
    
    res.json(fastApiRes.data);
  } catch (err) {
    console.error('Failed to fetch companies:', err.message);
    
    // If the backend API is not responding, return mock data
    const mockResponse = {
      success: true,
      companies: [
        {
          name: 'TechNova AI',
          urn: 'urn:li:company:tech1',
          industry: req.body.industries?.[0] || 'AI/ML',
          employeeCount: 86,
          recentTransitions: 15,
          growthRate: 18.5,
          churnRate: 7.2
        },
        {
          name: 'DataSphere',
          urn: 'urn:li:company:data1',
          industry: 'Data/Analytics',
          employeeCount: 120,
          recentTransitions: 10,
          growthRate: 12.8,
          churnRate: 9.3
        },
        {
          name: 'CloudSecure',
          urn: 'urn:li:company:cloud1',
          industry: 'Cybersecurity',
          employeeCount: 65,
          recentTransitions: 7,
          growthRate: 9.5,
          churnRate: 6.1
        }
      ],
      total: 3
    };
    
    // Cache error response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    res.json(mockResponse);
  }
});

// Portfolio overview endpoint
app.post('/api/vc/portfolio/overview', async (req, res) => {
  console.log('/api/vc/portfolio/overview endpoint hit:', req.body);
  
  // Create cache key from request body
  const cacheKey = `portfolio_overview_${JSON.stringify(req.body)}`;
  
  // If we have a valid cached response, return it
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for portfolio overview: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  // Use mock data if rate limited or if useBackupData flag is set
  if (req.useBackupData) {
    console.log('Using mock data for rate limited portfolio overview request');
    const mockResponse = getMockPortfolioData();
    
    // Cache mock response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    return res.json(mockResponse);
  }
  
  try {
    // Add a small delay to prevent rapid successive requests
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const fastApiRes = await axios.post(
      'http://localhost:8000/api/vc/portfolio/overview',
      req.body,
      { 
        headers: { 'Content-Type': 'application/json' },
        timeout: 5000 // Add timeout to prevent hanging requests
      }
    );
    
    console.log('Portfolio overview result:', fastApiRes.data);
    
    // Cache successful response for 5 minutes
    cache.set(cacheKey, fastApiRes.data, 300);
    
    res.json(fastApiRes.data);
  } catch (err) {
    console.error('Failed to fetch portfolio overview:', err.message);
    
    // If the backend API is not responding, return mock data
    const mockResponse = getMockPortfolioData();
    
    // Cache error response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    res.json(mockResponse);
  }
});

// Helper function to get mock portfolio overview data
function getMockPortfolioData() {
  return {
    success: true,
    overview: {
      totalCompanies: 5,
      totalEmployees: 532,
      growthRate: 14.2,
      churnRate: 8.5,
      topPerformers: [
        { name: 'TechNova', growth: 18.5 },
        { name: 'DataSphere', growth: 12.8 }
      ],
      atRisk: [
        { name: 'CloudMobile', churn: 15.3 }
      ]
    }
  };
}

// Skills trending endpoint with caching
app.get('/api/vc/skills/trending', async (req, res) => {
  console.log('/api/vc/skills/trending endpoint hit');
  const limit = req.query.limit || 10;
  const cacheKey = `skills_trending_${limit}`;
  const cacheTTL = 600; // 10 minutes cache TTL
  
  // Check if we have a valid cached response
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for trending skills: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  // Use mock data if rate limited or if useBackupData flag is set
  if (req.useBackupData) {
    console.log('Using mock data for rate limited skills trending request');
    const mockResponse = getMockSkillsData(limit);
    
    // Cache the mock response for 5 minutes
    cache.set(cacheKey, mockResponse, 300);
    
    return res.json(mockResponse);
  }
  
  try {
    // Add a small delay to prevent rapid successive requests
    await new Promise(resolve => setTimeout(resolve, 100));
    
    console.log('Cache miss for trending skills, fetching from FastAPI');
    const fastApiRes = await axios.get(
      `http://localhost:8000/api/vc/skills/trending?limit=${limit}`,
      { timeout: 5000 } // Add timeout to prevent hanging requests
    );
    
    console.log('Skills trending result:', fastApiRes.data);
    
    // Cache the successful response
    cache.set(cacheKey, fastApiRes.data, cacheTTL);
    
    res.json(fastApiRes.data);
  } catch (err) {
    console.error('Failed to fetch trending skills:', err.message);
    
    // If the backend API is not responding, return mock data
    const mockResponse = getMockSkillsData(limit);
    
    // Cache the mock response (but for a shorter time)
    cache.set(cacheKey, mockResponse, 300);
    
    res.json(mockResponse);
  }
});

// Helper function to get mock skills data
function getMockSkillsData(limit = 10) {
  const allSkills = [
    { skill: 'Machine Learning', totalProfiles: 235, recentHires: 67, trendScore: 28.5 },
    { skill: 'React', totalProfiles: 186, recentHires: 34, trendScore: 18.2 },
    { skill: 'Cloud Architecture', totalProfiles: 142, recentHires: 22, trendScore: 15.7 },
    { skill: 'Python', totalProfiles: 310, recentHires: 38, trendScore: 12.3 },
    { skill: 'Data Science', totalProfiles: 175, recentHires: 39, trendScore: 22.1 },
    { skill: 'Kubernetes', totalProfiles: 98, recentHires: 32, trendScore: 32.5 },
    { skill: 'Natural Language Processing', totalProfiles: 76, recentHires: 33, trendScore: 42.8 },
    { skill: 'GraphQL', totalProfiles: 68, recentHires: 17, trendScore: 24.3 },
    { skill: 'DevOps', totalProfiles: 122, recentHires: 24, trendScore: 19.7 },
    { skill: 'TypeScript', totalProfiles: 154, recentHires: 45, trendScore: 28.9 },
    { skill: 'Docker', totalProfiles: 87, recentHires: 26, trendScore: 29.9 },
    { skill: 'Go', totalProfiles: 62, recentHires: 20, trendScore: 32.3 },
    { skill: 'Rust', totalProfiles: 42, recentHires: 18, trendScore: 42.9 },
    { skill: 'Vue.js', totalProfiles: 76, recentHires: 19, trendScore: 25.0 },
    { skill: 'AWS', totalProfiles: 198, recentHires: 35, trendScore: 17.7 }
  ];
  
  // Return the requested number of skills (or all if limit > available)
  return {
    success: true,
    skills: allSkills.slice(0, Math.min(limit, allSkills.length))
  };
}

// Add analytics recommendations endpoint
app.get('/api/analytics/recommendations', async (req, res) => {
  console.log('/api/analytics/recommendations endpoint hit:', req.query);
  
  const mode = req.query.mode || 'investment';
  const cacheKey = `analytics_recommendations_${mode}_${JSON.stringify(req.query)}`;
  const cacheTTL = 600; // 10 minutes cache TTL
  
  // Check if we have a valid cached response
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for analytics recommendations: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  try {
    // Add a small delay to simulate API processing
    await new Promise(resolve => setTimeout(resolve, 100));
    
    console.log('Cache miss for analytics recommendations, returning sample data for mode:', mode);
    
    // Ensure we always return valid data
    let sampleData = [];
    
    if (mode === 'investment') {
      sampleData = [
        {
          id: 'rec-001',
          companyId: 'comp-001',
          companyName: 'TechNova AI',
          sector: 'AI/ML',
          stage: 'Series A',
          valuation: 25,
          growthRate: 28.5,
          score: 0.87,
          talentInflow: 15,
          talentOutflow: 3,
          keyFactors: ['Strong talent acquisition', 'Growing revenue', 'Market position'],
          aiExplanation: 'TechNova AI shows significant growth potential based on talent acquisition patterns and market positioning.'
        },
        {
          id: 'rec-002',
          companyId: 'comp-002',
          companyName: 'DataSphere',
          sector: 'Data Analytics',
          stage: 'Series B',
          valuation: 48,
          growthRate: 32.1,
          score: 0.82,
          talentInflow: 12,
          talentOutflow: 5,
          keyFactors: ['Technology leadership', 'Strong exec team', 'Market growth'],
          aiExplanation: 'DataSphere is positioned well in the rapidly growing data analytics space with strong technical leadership.'
        },
        {
          id: 'rec-003',
          companyId: 'comp-003',
          companyName: 'CloudSecure',
          sector: 'Cybersecurity',
          stage: 'Series A',
          valuation: 18,
          growthRate: 45.2,
          score: 0.79,
          talentInflow: 10,
          talentOutflow: 2,
          keyFactors: ['High growth rate', 'Strong product-market fit', 'Talent retention'],
          aiExplanation: 'CloudSecure demonstrates exceptional growth in the cybersecurity sector with strong talent retention metrics.'
        },
        {
          id: 'rec-004',
          companyId: 'comp-004',
          companyName: 'FinStack',
          sector: 'FinTech',
          stage: 'Seed',
          valuation: 7,
          growthRate: 62.8,
          score: 0.75,
          talentInflow: 8,
          talentOutflow: 1,
          keyFactors: ['Innovative technology', 'Early traction', 'Experienced founders'],
          aiExplanation: 'FinStack is an early-stage company showing remarkable growth and strong founder credentials in fintech.'
        },
        {
          id: 'rec-005',
          companyId: 'comp-005',
          companyName: 'HealthAI',
          sector: 'HealthTech',
          stage: 'Series B',
          valuation: 35,
          growthRate: 24.3,
          score: 0.81,
          talentInflow: 13,
          talentOutflow: 4,
          keyFactors: ['Strategic partnerships', 'Regulatory advantage', 'Market expansion'],
          aiExplanation: 'HealthAI has established key partnerships in healthcare with significant regulatory advantages driving growth.'
        }
      ];
    } else if (mode === 'talent') {
      sampleData = [
        {
          id: 'rec-101',
          candidateName: 'Alex Johnson',
          currentRole: 'Senior ML Engineer',
          currentCompany: 'TechGiant Inc',
          skillMatch: 0.92,
          cultureMatch: 0.89,
          retentionScore: 0.85,
          fitScore: 4.7,
          skills: ['Deep Learning', 'TensorFlow', 'PyTorch', 'Computer Vision', 'NLP'],
          aiExplanation: 'Candidate shows strong match (92%) with required skills and culture fit.'
        },
        {
          id: 'rec-102',
          candidateName: 'Sarah Patel',
          currentRole: 'Data Science Lead',
          currentCompany: 'DataWorks',
          skillMatch: 0.88,
          cultureMatch: 0.91,
          retentionScore: 0.82,
          fitScore: 4.5,
          skills: ['Machine Learning', 'Python', 'Data Architecture', 'Team Leadership'],
          aiExplanation: 'Candidate shows strong match (88%) with required skills and culture fit.'
        },
        {
          id: 'rec-103',
          candidateName: 'Michael Chen',
          currentRole: 'AI Researcher',
          currentCompany: 'Research Labs',
          skillMatch: 0.95,
          cultureMatch: 0.82,
          retentionScore: 0.78,
          fitScore: 4.3,
          skills: ['Reinforcement Learning', 'Generative AI', 'Research Publication', 'Algorithm Design'],
          aiExplanation: 'Candidate shows strong match (95%) with required skills and culture fit.'
        }
      ];
    } else if (mode === 'partnership') {
      sampleData = [
        {
          id: 'rec-201',
          companyName: 'CloudNet Solutions',
          industry: 'Cloud Infrastructure',
          size: 'Large',
          score: 0.88,
          synergies: ['Technology Integration', 'Market Access', 'Complementary Products'],
          aiExplanation: 'Potential synergies in technology integration and market access make this partnership promising.'
        },
        {
          id: 'rec-202',
          companyName: 'SecurityPro',
          industry: 'Cybersecurity',
          size: 'Medium',
          score: 0.84,
          synergies: ['Product Enhancement', 'Customer Base', 'Technical Expertise'],
          aiExplanation: 'Strong potential for product enhancement and shared customer base advantages.'
        },
        {
          id: 'rec-203',
          companyName: 'DataFlow Systems',
          industry: 'Data Analytics',
          size: 'Medium',
          score: 0.81,
          synergies: ['Data Integration', 'Joint R&D', 'Market Positioning'],
          aiExplanation: 'Complementary data capabilities and R&D opportunities present strong partnership potential.'
        }
      ];
    }
    
    // Log the sample data being returned
    console.log(`Returning ${sampleData.length} recommendations for mode: ${mode}`);
    
    // Cache successful response
    cache.set(cacheKey, sampleData, cacheTTL);
    
    // Return the response
    return res.json(sampleData);
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    
    // Even on error, return mock data to prevent client-side failures
    const mockData = fs.existsSync('./mockRecommendations.json') 
      ? JSON.parse(fs.readFileSync('./mockRecommendations.json', 'utf8'))
      : [];
    
    // Log the mock data from file
    console.log(`Error recovery: Returning ${mockData.length} recommendations from mockRecommendations.json`);
    
    // Cache the mock data
    cache.set(cacheKey, mockData, 300); // Shorter TTL for error response
    
    // Return the mock data response
    return res.json(mockData);
  }
});

// Add analytics insights endpoint
app.get('/api/analytics/insights', async (req, res) => {
  console.log('/api/analytics/insights endpoint hit:', req.query);
  
  const cacheKey = `analytics_insights_${JSON.stringify(req.query)}`;
  const cacheTTL = 600; // 10 minutes cache TTL
  
  // Check if we have a valid cached response
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for analytics insights: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  try {
    // Add a small delay to prevent rapid successive requests
    await new Promise(resolve => setTimeout(resolve, 100));
    
    console.log('Cache miss for analytics insights, fetching from FastAPI');
    const fastApiRes = await axios.get(
      `http://localhost:8000/api/analytics/insights`,
      { 
        params: req.query,
        timeout: 5000 // Add timeout to prevent hanging requests
      }
    );
    
    console.log('Analytics insights result:', fastApiRes.data);
    
    // Cache the successful response
    cache.set(cacheKey, fastApiRes.data, cacheTTL);
    
    res.json(fastApiRes.data);
  } catch (err) {
    console.error('Failed to fetch analytics insights:', err.message);
    
    // If the backend API is not responding, return mock data
    const mockResponse = [
      {
        id: 'insight-001',
        title: 'Rising Talent Movement in AI/ML',
        description: 'Companies in AI/ML sector are experiencing 25% higher talent acquisition compared to other sectors.',
        confidence: 0.89,
        trend: 'rising',
        source: 'talent flow analysis',
        category: 'industry trend'
      },
      {
        id: 'insight-002',
        title: 'FinTech Investment Slowdown',
        description: 'Early-stage investments in FinTech have decreased by 12% in the past quarter.',
        confidence: 0.82,
        trend: 'falling',
        source: 'funding data',
        category: 'investment trend'
      }
    ];
    
    // Cache error response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    res.json(mockResponse);
  }
});

// Add analytics opportunities endpoint
app.get('/api/analytics/opportunities', async (req, res) => {
  console.log('/api/analytics/opportunities endpoint hit:', req.query);
  
  const cacheKey = `analytics_opportunities_${JSON.stringify(req.query)}`;
  const cacheTTL = 600; // 10 minutes cache TTL
  
  // Check if we have a valid cached response
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for analytics opportunities: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  try {
    // Add a small delay to prevent rapid successive requests
    await new Promise(resolve => setTimeout(resolve, 100));
    
    console.log('Cache miss for analytics opportunities, fetching from FastAPI');
    const fastApiRes = await axios.get(
      `http://localhost:8000/api/analytics/opportunities`,
      { 
        params: req.query,
        timeout: 5000 // Add timeout to prevent hanging requests
      }
    );
    
    console.log('Analytics opportunities result:', fastApiRes.data);
    
    // Cache the successful response
    cache.set(cacheKey, fastApiRes.data, cacheTTL);
    
    res.json(fastApiRes.data);
  } catch (err) {
    console.error('Failed to fetch analytics opportunities:', err.message);
    
    // If the backend API is not responding, return mock data
    const mockResponse = [
      {
        id: 'opp-001',
        title: 'Early Investment in Quantum Computing Startups',
        description: 'Emerging quantum computing startups are seeking seed funding with potential high returns.',
        priority: 'high',
        timeWindow: 'short',
        actionType: 'investment',
        targetSector: 'Quantum Computing'
      },
      {
        id: 'opp-002',
        title: 'Strategic Acquisition of AI Tools',
        description: 'Several early-stage AI tool companies are showing acquisition readiness with valuable IP.',
        priority: 'medium',
        timeWindow: 'medium',
        actionType: 'acquisition',
        targetSector: 'AI Tools'
      }
    ];
    
    // Cache error response for 2 minutes
    cache.set(cacheKey, mockResponse, 120);
    
    res.json(mockResponse);
  }
});

// Add analytics talent-flow endpoint
app.post('/api/analytics/talent-flow', async (req, res) => {
  console.log('/api/analytics/talent-flow endpoint hit:', req.body);
  
  const cacheKey = `analytics_talent_flow_${JSON.stringify(req.body)}`;
  const cacheTTL = 600; // 10 minutes cache TTL
  
  // Check if we have a valid cached response
  if (cache.has(cacheKey)) {
    console.log(`Cache hit for analytics talent flow: ${cacheKey}`);
    return res.json(cache.get(cacheKey));
  }
  
  try {
    // Add a small delay to prevent rapid successive requests
    await new Promise(resolve => setTimeout(resolve, 100));
    
    console.log('Cache miss for analytics talent flow, returning sample data');
    
    // First try to load mock data from file
    let sampleData;
    
    try {
      if (fs.existsSync('./mockTalentFlow.json')) {
        sampleData = JSON.parse(fs.readFileSync('./mockTalentFlow.json', 'utf8'));
        console.log(`Loaded talent flow data from mockTalentFlow.json with ${sampleData.nodes?.length || 0} nodes and ${sampleData.links?.length || 0} links`);
      }
    } catch (fileError) {
      console.error('Error reading mockTalentFlow.json:', fileError);
    }
    
    // If file reading failed, use hardcoded sample data
    if (!sampleData || !sampleData.nodes || !sampleData.links) {
      console.log('Using hardcoded sample talent flow data');
      
      // Sample response structure matching what TalentFlowVisualizer expects
      sampleData = {
        nodes: [
          { id: 'google', name: 'Google', inflow: 45, outflow: 30 },
          { id: 'meta', name: 'Meta', inflow: 38, outflow: 25 },
          { id: 'amazon', name: 'Amazon', inflow: 50, outflow: 40 },
          { id: 'microsoft', name: 'Microsoft', inflow: 42, outflow: 25 },
          { id: 'apple', name: 'Apple', inflow: 35, outflow: 20 },
          { id: 'netflix', name: 'Netflix', inflow: 25, outflow: 15 },
          { id: 'uber', name: 'Uber', inflow: 20, outflow: 30 },
          { id: 'lyft', name: 'Lyft', inflow: 15, outflow: 25 },
          { id: 'airbnb', name: 'Airbnb', inflow: 18, outflow: 22 },
          { id: 'stripe', name: 'Stripe', inflow: 22, outflow: 10 }
        ],
        links: [
          { source: 'google', target: 'meta', value: 12 },
          { source: 'google', target: 'amazon', value: 8 },
          { source: 'meta', target: 'google', value: 10 },
          { source: 'amazon', target: 'google', value: 7 },
          { source: 'amazon', target: 'meta', value: 9 },
          { source: 'microsoft', target: 'amazon', value: 11 },
          { source: 'microsoft', target: 'google', value: 9 },
          { source: 'apple', target: 'google', value: 8 },
          { source: 'apple', target: 'meta', value: 6 },
          { source: 'netflix', target: 'google', value: 5 },
          { source: 'netflix', target: 'amazon', value: 7 },
          { source: 'uber', target: 'lyft', value: 14 },
          { source: 'lyft', target: 'uber', value: 9 },
          { source: 'airbnb', target: 'meta', value: 6 },
          { source: 'airbnb', target: 'stripe', value: 4 },
          { source: 'stripe', target: 'meta', value: 3 },
          { source: 'stripe', target: 'amazon', value: 5 }
        ],
        top_sources: [
          { name: 'Google', outflow: 30 },
          { name: 'Amazon', outflow: 40 },
          { name: 'Microsoft', outflow: 25 },
          { name: 'Uber', outflow: 30 },
          { name: 'Meta', outflow: 25 }
        ],
        top_destinations: [
          { name: 'Google', inflow: 45 },
          { name: 'Amazon', inflow: 50 },
          { name: 'Meta', inflow: 38 },
          { name: 'Microsoft', inflow: 42 },
          { name: 'Apple', inflow: 35 }
        ]
      };
    }
    
    // Log data stats
    console.log(`Returning talent flow data with ${sampleData.nodes.length} nodes and ${sampleData.links.length} links`);
    
    // Add to cache
    cache.set(cacheKey, sampleData, cacheTTL);
    
    // Return the response
    return res.json(sampleData);
  } catch (error) {
    console.error('Error fetching talent flow data:', error);
    
    // Ensure we always return valid data even on error
    const fallbackData = {
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
    
    // Add fallback data to cache with shorter TTL
    cache.set(cacheKey, fallbackData, 120);
    
    console.log('Returning fallback talent flow data due to error');
    return res.json(fallbackData);
  }
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});


// LinkedIn OAuth callback
app.get('/auth/linkedin/callback', async (req, res) => {
  const { code } = req.query;

  try {
    const tokenRes = await axios.post('https://www.linkedin.com/oauth/v2/accessToken', null, {
      params: {
        grant_type: 'authorization_code',
        code,
        redirect_uri: 'http://localhost:5001/auth/linkedin/callback',
        client_id: process.env.LINKEDIN_CLIENT_ID,
        client_secret: process.env.LINKEDIN_CLIENT_SECRET
      },
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });

    const accessToken = tokenRes.data.access_token;

    // Optional: Fetch profile data
    const profileRes = await axios.get('https://api.linkedin.com/v2/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    const emailRes = await axios.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))', {
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    const profile = profileRes.data;
    const email = emailRes.data.elements[0]['handle~'].emailAddress;

    // Do something with profile/email (e.g., create user, session, etc.)
    console.log(profile, email);

    const profileData = {
      id: profile.id,
      firstName: profile.localizedFirstName,
      lastName: profile.localizedLastName,
      email: email,
      headline: profile.headline || '',
      // Add more fields as needed -> determine what we can get from LinkedIn login,
    };

    // 🔁 Send to FastAPI backend
    const fastApiRes = await axios.post('http://localhost:8000/api/db/store_profile', profileData);

    console.log('✅ Sent to FastAPI:', fastApiRes.data);


    res.send(`<h2>Logged in as ${profile.localizedFirstName}</h2><p>Email: ${email}</p>`);
  } catch (err) {
    console.error(err.response?.data || err.message);
    res.status(500).send('LinkedIn authentication failed.');
  }
});