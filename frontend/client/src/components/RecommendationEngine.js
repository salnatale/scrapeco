import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Button,
  Avatar,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Divider,
  Paper,
  Tabs,
  Tab,
  Rating,
  IconButton,
  Tooltip,
  Badge,
  CircularProgress
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Business,
  People,
  School,
  LocationOn,
  AttachMoney,
  Assessment,
  Lightbulb,
  Warning,
  CheckCircle,
  ExpandMore,
  Star,
  ArrowForward,
  Refresh,
  FilterList,
  Info
} from '@mui/icons-material';
import { useVC } from '../context/VCContext';

const RecommendationEngine = ({ 
  mode = 'investment', // 'investment', 'talent', 'partnership'
  context = {},
  onActionClick,
  onCompanySelect 
}) => {
  const [recommendations, setRecommendations] = useState([]);
  const [insights, setInsights] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    confidence: 'all',
    sector: 'all',
    stage: 'all',
    geography: 'all'
  });
  
  // Get the VC context
  const { actions } = useVC();
  
  // Keep track of last fetch time to prevent excessive calls
  const [lastFetchTime, setLastFetchTime] = useState({
    recommendations: 0,
    insights: 0,
    opportunities: 0
  });

  // Track if component is mounted to prevent state updates after unmount
  const isMounted = useRef(true);
  
  // Create a memoized debounced filters value
  const debouncedFilters = useRef(filters);
  
  // Implement debouncing for filter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      debouncedFilters.current = filters;
      if (isMounted.current) {
        fetchRecommendations();
      }
    }, 800); // 800ms debounce delay
    
    return () => clearTimeout(timer);
  }, [filters, mode, context]);
  
  // Add initial load effect
  useEffect(() => {
    console.log("RecommendationEngine: Component mounted with mode:", mode);
    // Set initial state
    setLoading(true);
    
    // Fetch real data immediately
    fetchRecommendations();
    
    // Safety timeout to prevent infinite loading state
    const safetyTimer = setTimeout(() => {
      if (isMounted.current && loading) {
        console.log("RecommendationEngine: Safety timeout triggered to reset loading state");
        setLoading(false);
      }
    }, 10000); // 10 second safety timeout
    
    // Set up cleanup on unmount
    return () => {
      isMounted.current = false;
      clearTimeout(safetyTimer);
    };
  }, [mode]); // Only re-run if mode changes
  
  // Set up cleanup on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Add direct API test to bypass middleware 
  useEffect(() => {
    console.log("RecommendationEngine: Running direct API test");
    
    // Direct API test to bypass any middleware issues
    const testApiDirectly = async () => {
      try {
        console.log("RecommendationEngine: Making direct fetch request to API");
        
        // Use the more robust raw API test function
        testApiRawResponse();
        
        // Also test direct fetch with proper JSON parsing
        const response = await fetch('http://localhost:8000/api/analytics/recommendations?mode=investment', {
          method: 'GET',
          mode: 'cors',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        
        console.log("RecommendationEngine: Direct API test response status:", response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log("RecommendationEngine: Direct API test SUCCESS! Data:", data);
          
          // If we got data directly but the regular flow is stuck, use this data
          if (recommendations.length === 0 && loading) {
            console.log("RecommendationEngine: Using direct API data to update recommendations");
            
            // Process data to ensure it has all required properties
            const processedData = Array.isArray(data) ? data.map((item, index) => ({
              id: item.id || `auto-${index}`,
              companyName: item.companyName || `Company ${index+1}`,
              score: item.score !== undefined ? item.score : 0.7,
              ...item
            })) : [];
            
            setRecommendations(processedData);
            setLoading(false);
          }
        } else {
          console.error("RecommendationEngine: Direct API test FAILED with status:", response.status);
        }
      } catch (error) {
        console.error("RecommendationEngine: Direct API test ERROR:", error.message);
      }
    };
    
    // Run test after a short delay to allow other effects to complete
    const timer = setTimeout(() => {
      testApiDirectly();
    }, 2000);
    
    return () => clearTimeout(timer);
  }, []);

  const fetchRecommendations = async () => {
    // Only fetch if not already loading or if this is initial load
    console.log("RecommendationEngine: fetchRecommendations called", { loading });
    console.log("RecommendationEngine: Current mode", mode);
    console.log("RecommendationEngine: Current context", context);
    console.log("RecommendationEngine: Current filters", filters);
    
    setLoading(true);
    setError(null);
    
    // Current time for cache validation
    const currentTime = Date.now();
    const CACHE_THRESHOLD = 30000; // 30 seconds cache validity
    
    try {
      // Build parameters for API requests based on mode and context
      const apiContext = {
        mode,
        ...context,
        confidence_threshold: filters.confidence === 'all' ? '0' : filters.confidence,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, v]) => v !== 'all')
        )
      };
      
      console.log("RecommendationEngine: API context object:", apiContext);
      
      // Create a URLSearchParams object to see how it's encoded
      const testParams = new URLSearchParams({
        mode,
        ...context
      });
      console.log("RecommendationEngine: URL params as string:", testParams.toString());
      console.log("RecommendationEngine: Full URL would be:", `http://localhost:8000/api/analytics/recommendations?${testParams.toString()}`);
      
      // Create promises array with conditional fetching based on cache
      const promises = [];
      const shouldFetchRecommendations = currentTime - lastFetchTime.recommendations > CACHE_THRESHOLD;
      const shouldFetchInsights = currentTime - lastFetchTime.insights > CACHE_THRESHOLD;
      const shouldFetchOpportunities = currentTime - lastFetchTime.opportunities > CACHE_THRESHOLD;
      
      console.log("RecommendationEngine: Should fetch data:", { 
        recommendations: shouldFetchRecommendations, 
        insights: shouldFetchInsights, 
        opportunities: shouldFetchOpportunities 
      });
      
      // Only fetch data if needed (based on cache or active tab)
      if (shouldFetchRecommendations || activeTab === 0) {
        console.log("RecommendationEngine: Fetching recommendations");
        console.log("RecommendationEngine: Calling actions.getRecommendations with:", mode, apiContext);
        promises.push(
          actions.getRecommendations(mode, apiContext)
            .then(data => {
              console.log("RecommendationEngine: getRecommendations resolved with:", data);
              return data;
            })
            .catch(err => {
              console.error("RecommendationEngine: getRecommendations rejected with:", err);
              throw err;
            })
        );
        setLastFetchTime(prev => ({ ...prev, recommendations: currentTime }));
      } else {
        promises.push(Promise.resolve(null));
      }
      
      if (shouldFetchInsights || activeTab === 1) {
        console.log("RecommendationEngine: Fetching insights");
        promises.push(actions.getInsights(apiContext));
        setLastFetchTime(prev => ({ ...prev, insights: currentTime }));
      } else {
        promises.push(Promise.resolve(null));
      }
      
      if (shouldFetchOpportunities || activeTab === 2) {
        console.log("RecommendationEngine: Fetching opportunities");
        promises.push(actions.getOpportunities(apiContext));
        setLastFetchTime(prev => ({ ...prev, opportunities: currentTime }));
      } else {
        promises.push(Promise.resolve(null));
      }
      
      // Add a timeout to prevent hanging
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error('Request timed out after 15 seconds'));
        }, 15000);
      });
      
      // Fetch data in parallel using the context actions
      console.log("RecommendationEngine: Awaiting promises");
      const [recsResponse, insightsResponse, oppsResponse] = await Promise.race([
        Promise.all(promises.map(p => 
          p.catch(err => {
            console.error("Promise rejection in fetchRecommendations:", err);
            return null;
          })
        )),
        timeoutPromise
      ]);

      console.log("RecommendationEngine: Got responses", { 
        recommendations: recsResponse ? `Array with ${recsResponse.length} items` : 'null', 
        insights: insightsResponse ? `Array with ${insightsResponse.length} items` : 'null',
        opportunities: oppsResponse ? `Array with ${oppsResponse.length} items` : 'null'
      });
      
      console.log("RecommendationEngine: First recommendation item:", recsResponse?.[0]);

      // Only update state if valid responses received
      if (recsResponse && isMounted.current) {
        // Apply AI-based ranking to recommendations
        console.log("RecommendationEngine: Processing recommendations:", recsResponse);
        const processedRecs = recsResponse.map(rec => ({
          ...rec,
          // Calculate composite score combining ML model predictions with heuristics
          score: rec.score || calculateCompositeScore(rec),
          aiExplanation: rec.aiExplanation || generateExplanation(rec, mode)
        })).sort((a, b) => b.score - a.score);

        console.log("RecommendationEngine: Final processed recommendations:", processedRecs);
        setRecommendations(processedRecs);
        console.log("RecommendationEngine: Recommendations set", processedRecs);
      } else {
        console.warn("RecommendationEngine: No recommendations data received or component unmounted");
      }
      
      // Process insights with confidence levels
      if (insightsResponse && isMounted.current) {
        const processedInsights = insightsResponse.map(insight => ({
          ...insight,
          confidence: insight.confidence || calculateInsightConfidence(insight),
          aiLabels: insight.aiLabels || categorizeInsight(insight)
        }));
        
        setInsights(processedInsights);
      }
      
      // Process opportunities with additional metrics
      if (oppsResponse && isMounted.current) {
        setOpportunities(oppsResponse);
      }
      
      // Always set loading to false after processing all data, regardless of responses
      if (isMounted.current) {
        setLoading(false);
      }
      
    } catch (error) {
      console.error("RecommendationEngine: Error fetching data:", error);
      
      if (isMounted.current) {
        setError(error.message || "Failed to fetch recommendations data");
        setLoading(false);
      }
    }
  };

  // AI logic to calculate a composite score from multiple factors
  const calculateCompositeScore = (rec) => {
    // Return existing model score if available
    if (rec.modelScore) return rec.modelScore;
    if (rec.score) return rec.score;
    
    try {
      // Check if minimal required properties exist for calculation
      if (!rec || typeof rec !== 'object') {
        console.error("Invalid recommendation item:", rec);
        return 0.5; // Default score
      }
      
      // Otherwise compute a score based on available signals
      let score = 0;
      const weights = {
        growthRate: 0.3,
        talentFlow: 0.25,
        fundingProgress: 0.2,
        marketPosition: 0.15,
        innovationIndex: 0.1
      };
      
      // Normalize each component to 0-1 range and apply weights
      if (rec.growthRate !== undefined) {
        const normalizedGrowth = Math.min(rec.growthRate / 100, 1);
        score += normalizedGrowth * weights.growthRate;
      }
      
      if (rec.talentInflow !== undefined && rec.talentOutflow !== undefined) {
        const netTalentFlow = rec.talentInflow - rec.talentOutflow;
        const normalizedTalentFlow = Math.max(Math.min((netTalentFlow + 20) / 40, 1), 0);
        score += normalizedTalentFlow * weights.talentFlow;
      }
      
      if (rec.fundingStage) {
        const stageScores = {
          'Seed': 0.3,
          'Series A': 0.5,
          'Series B': 0.7,
          'Series C': 0.9,
          'Late Stage': 1.0
        };
        score += (stageScores[rec.fundingStage] || 0.5) * weights.fundingProgress;
      }
      
      if (rec.marketShare !== undefined) {
        score += Math.min(rec.marketShare / 15, 1) * weights.marketPosition;
      }
      
      if (rec.patents !== undefined) {
        score += Math.min(rec.patents / 10, 1) * weights.innovationIndex;
      }
      
      // If we couldn't calculate anything, use a default score
      if (score === 0) {
        return 0.5; // Default mid-range score
      }
      
      return score;
    } catch (error) {
      console.error("Error calculating composite score:", error, rec);
      return 0.5; // Default score on error
    }
  };
  
  // Function to generate natural language explanations for recommendations
  const generateExplanation = (rec, mode) => {
    try {
      // Return existing explanation if available
      if (rec.aiExplanation) return rec.aiExplanation;
      
      // Check for minimal required properties
      if (!rec || typeof rec !== 'object') {
        return 'Recommendation based on AI analysis';
      }
      
      if (mode === 'investment') {
        const factors = [];
        
        if (rec.growthRate !== undefined) {
          if (rec.growthRate > 50) factors.push('exceptional growth rate');
          else if (rec.growthRate > 20) factors.push('strong growth rate');
        }
        
        if (rec.talentInflow !== undefined && rec.talentOutflow !== undefined) {
          if (rec.talentInflow > rec.talentOutflow + 10) factors.push('significant talent acquisition');
        }
        
        if (rec.competitivePosition === 'leader') factors.push('market leadership');
        
        if (factors.length === 0) {
          if (rec.companyName) {
            return `${rec.companyName} is recommended based on overall performance metrics`;
          }
          return 'Recommended based on overall performance metrics';
        }
        
        return `Recommended due to ${factors.join(', ')}.`;
      } 
      
      if (mode === 'talent') {
        const score = rec.score !== undefined ? rec.score : 0.7;
        return `Candidate shows strong match (${Math.round(score * 100)}%) with required skills and culture fit.`;
      }
      
      if (mode === 'partnership') {
        if (rec.synergies && Array.isArray(rec.synergies) && rec.synergies.length > 0) {
          return `Potential synergies in ${rec.synergies.join(', ')}.`;
        }
        return 'Recommended for strategic partnership based on business alignment.';
      }
      
      return 'AI-generated recommendation based on multiple factors';
    } catch (error) {
      console.error("Error generating explanation:", error, rec);
      return 'Recommendation generated by AI analysis';
    }
  };
  
  // Calculate confidence score for insights
  const calculateInsightConfidence = (insight) => {
    // Simple heuristic based on data points and signal strength
    return insight.dataPoints ? Math.min(0.4 + (insight.dataPoints / 50), 0.95) : 0.7;
  };
  
  // Categorize insights into themes using keyword analysis
  const categorizeInsight = (insight) => {
    const text = insight.description.toLowerCase();
    const categories = [];
    
    if (text.includes('talent') || text.includes('employee') || text.includes('hire')) {
      categories.push('talent');
    }
    
    if (text.includes('market') || text.includes('industry') || text.includes('sector')) {
      categories.push('market');
    }
    
    if (text.includes('competitor') || text.includes('competition')) {
      categories.push('competition');
    }
    
    if (text.includes('growth') || text.includes('expansion')) {
      categories.push('growth');
    }
    
    if (text.includes('risk') || text.includes('danger') || text.includes('threat')) {
      categories.push('risk');
    }
    
    return categories.length ? categories : ['general'];
  };
  
  // Calculate priority for opportunities
  const calculatePriority = (opportunity) => {
    if (opportunity.priority) return opportunity.priority;
    
    if (opportunity.score > 0.8) return 'high';
    if (opportunity.score > 0.5) return 'medium';
    return 'low';
  };
  
  // Estimate time window for opportunities
  const estimateTimeWindow = (opportunity) => {
    if (opportunity.timeWindow) return opportunity.timeWindow;
    
    if (opportunity.expirationDays) {
      if (opportunity.expirationDays < 30) return 'immediate';
      if (opportunity.expirationDays < 90) return 'near-term';
      return 'long-term';
    }
    
    return opportunity.urgency === 'high' ? 'immediate' : 'near-term';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.8) return <CheckCircle color="success" />;
    if (confidence >= 0.6) return <Warning color="warning" />;
    return <Warning color="error" />;
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const renderInvestmentRecommendations = () => (
    <Grid container spacing={3}>
      {recommendations.length === 0 && !loading ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No investment recommendations available with the current filters.
          </Alert>
        </Grid>
      ) : (
        recommendations.map((rec, index) => {
          // Ensure recommendation has required properties with defaults
          const safeRec = {
            id: rec.id || `fallback-${index}`,
            companyId: rec.companyId || `company-${index}`,
            companyName: rec.companyName || `Company ${index + 1}`,
            sector: rec.sector || 'Technology',
            stage: rec.stage || 'Growth',
            valuation: rec.valuation || 10,
            growthRate: rec.growthRate !== undefined ? rec.growthRate : 20,
            score: rec.score !== undefined ? rec.score : 0.7,
            keyFactors: Array.isArray(rec.keyFactors) ? rec.keyFactors : [],
            aiExplanation: rec.aiExplanation || generateExplanation(rec, 'investment')
          };
          
          return (
            <Grid item xs={12} md={6} lg={4} key={safeRec.id}>
              <Card 
                sx={{ 
                  height: '100%',
                  position: 'relative',
                  cursor: 'pointer',
                  '&:hover': { boxShadow: 4 }
                }}
                onClick={() => onCompanySelect?.(safeRec.companyId)}
              >
                <Badge
                  badgeContent={Math.round(safeRec.score * 100)}
                  color={getConfidenceColor(safeRec.score)}
                  sx={{ 
                    position: 'absolute',
                    top: 16,
                    right: 16
                  }}
                >
                  <Box sx={{ width: 40, height: 40 }}>
                    <Avatar sx={{ bgcolor: 'primary.main' }}>
                      <Business />
                    </Avatar>
                  </Box>
                </Badge>

                <CardContent sx={{ pt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    {safeRec.companyName}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {safeRec.sector} • {safeRec.stage}
                  </Typography>

                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" gutterBottom>
                      Investment Confidence
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={safeRec.score * 100}
                      color={getConfidenceColor(safeRec.score)}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {Math.round(safeRec.score * 100)}% confidence
                    </Typography>
                  </Box>

                  <Grid container spacing={1} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Valuation
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        ${safeRec.valuation}M
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Growth Rate
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {safeRec.growthRate}%
                      </Typography>
                    </Grid>
                  </Grid>

                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {safeRec.aiExplanation}
                  </Typography>

                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                    {safeRec.keyFactors.map((factor, index) => (
                      <Chip
                        key={index}
                        label={factor}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    ))}
                  </Box>

                  <Button
                    variant="contained"
                    fullWidth
                    onClick={(e) => {
                      e.stopPropagation();
                      onActionClick?.('invest', safeRec);
                    }}
                  >
                    View Investment Details
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          );
        })
      )}
    </Grid>
  );

  const renderTalentRecommendations = () => (
    <Grid container spacing={3}>
      {recommendations.length === 0 && !loading ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No talent recommendations available with the current filters.
          </Alert>
        </Grid>
      ) : (
        recommendations.map((rec) => (
          <Grid item xs={12} md={6} key={rec.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar sx={{ mr: 2, bgcolor: 'secondary.main' }}>
                    <People />
                  </Avatar>
                  <Box>
                    <Typography variant="h6">
                      {rec.candidateName}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {rec.currentRole} at {rec.currentCompany}
                    </Typography>
                  </Box>
                  <Box sx={{ ml: 'auto' }}>
                    <Rating value={rec.fitScore} readOnly max={5} />
                  </Box>
                </Box>

                <Typography variant="body2" sx={{ mb: 2 }}>
                  {rec.aiExplanation || rec.summary}
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Skill Match
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={rec.skillMatch * 100}
                    color="success"
                    sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  />
                  
                  <Typography variant="body2" gutterBottom>
                    Culture Fit
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={rec.cultureMatch * 100}
                    color="info"
                    sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  />
                  
                  <Typography variant="body2" gutterBottom>
                    Retention Probability
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={rec.retentionScore * 100}
                    color="warning"
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                  {rec.skills?.map((skill, index) => (
                    <Chip
                      key={index}
                      label={skill}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Button
                      variant="outlined"
                      fullWidth
                      onClick={(e) => {
                        e.stopPropagation();
                        onActionClick?.('view_profile', rec);
                      }}
                    >
                      View Profile
                    </Button>
                  </Grid>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      fullWidth
                      onClick={(e) => {
                        e.stopPropagation();
                        onActionClick?.('contact', rec);
                      }}
                    >
                      Contact
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        ))
      )}
    </Grid>
  );

  const renderPartnershipRecommendations = () => (
    <Grid container spacing={3}>
      {recommendations.length === 0 && !loading ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No partnership recommendations available with the current filters.
          </Alert>
        </Grid>
      ) : (
        recommendations.map((rec) => (
          <Grid item xs={12} md={6} key={rec.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
                    <Business />
                  </Avatar>
                  <Box>
                    <Typography variant="h6">
                      {rec.companyName}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {rec.industry} • {rec.size}
                    </Typography>
                  </Box>
                  <Box sx={{ ml: 'auto' }}>
                    <Chip 
                      label={`${Math.round(rec.score * 100)}% Match`}
                      color={getConfidenceColor(rec.score)}
                    />
                  </Box>
                </Box>

                <Typography variant="body2" sx={{ mb: 2 }}>
                  {rec.aiExplanation || rec.description}
                </Typography>

                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography>Partnership Synergies</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List dense disablePadding>
                      {rec.synergies?.map((synergy, index) => (
                        <ListItem key={index} disableGutters>
                          <ListItemIcon sx={{ minWidth: 36 }}>
                            <CheckCircle color="success" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={synergy} />
                        </ListItem>
                      ))}
                    </List>
                  </AccordionDetails>
                </Accordion>

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Button
                      variant="outlined"
                      fullWidth
                      onClick={(e) => {
                        e.stopPropagation();
                        onActionClick?.('view_company', rec);
                      }}
                    >
                      View Company
                    </Button>
                  </Grid>
                  <Grid item xs={6}>
                    <Button
                      variant="contained"
                      fullWidth
                      onClick={(e) => {
                        e.stopPropagation();
                        onActionClick?.('initiate_partnership', rec);
                      }}
                    >
                      Initiate Partnership
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        ))
      )}
    </Grid>
  );

  const renderInsights = () => (
    <Grid container spacing={3}>
      {insights.length === 0 && !loading ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No insights available with the current filters.
          </Alert>
        </Grid>
      ) : (
        insights.map((insight) => (
          <Grid item xs={12} key={insight.id}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                <Lightbulb color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">
                  {insight.title}
                </Typography>
                <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                    Confidence:
                  </Typography>
                  <Chip 
                    size="small"
                    label={`${Math.round(insight.confidence * 100)}%`}
                    color={getConfidenceColor(insight.confidence)}
                  />
                </Box>
              </Box>

              <Typography variant="body2" sx={{ mb: 2 }}>
                {insight.description}
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  {insight.aiLabels?.map((label, index) => (
                    <Chip
                      key={index}
                      label={label}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {insight.timestamp ? new Date(insight.timestamp).toLocaleDateString() : 'Recent insight'}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))
      )}
    </Grid>
  );

  const renderOpportunities = () => (
    <Grid container spacing={3}>
      {opportunities.length === 0 && !loading ? (
        <Grid item xs={12}>
          <Alert severity="info">
            No opportunities available with the current filters.
          </Alert>
        </Grid>
      ) : (
        opportunities.map((opportunity) => (
          <Grid item xs={12} md={6} key={opportunity.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="h6">
                    {opportunity.title}
                  </Typography>
                  <Chip
                    label={opportunity.priority}
                    color={getPriorityColor(opportunity.priority)}
                    size="small"
                  />
                </Box>

                <Typography variant="body2" sx={{ mb: 2 }}>
                  {opportunity.description}
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Potential Impact
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={opportunity.impactScore * 100}
                    color="primary"
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Time Window
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {opportunity.timeWindow}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Difficulty
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {opportunity.difficulty || 'Medium'}
                    </Typography>
                  </Grid>
                </Grid>

                <Button
                  variant="contained"
                  fullWidth
                  onClick={() => onActionClick?.('pursue_opportunity', opportunity)}
                >
                  Pursue Opportunity
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))
      )}
    </Grid>
  );

  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ py: 4, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <CircularProgress size={40} sx={{ mb: 2 }} />
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            Loading recommendations...
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button 
              variant="outlined" 
              color="primary" 
              onClick={directFetchRecommendations}
              startIcon={<Refresh />}
            >
              Fetch Data
            </Button>
            
            <Button 
              variant="outlined" 
              color="secondary" 
              onClick={testApiRawResponse}
            >
              Test Raw API
            </Button>
          </Box>
        </Box>
      );
    }

    if (error && recommendations.length === 0 && insights.length === 0 && opportunities.length === 0) {
      return (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={fetchRecommendations} startIcon={<Refresh />}>
              Retry
            </Button>
          }
        >
          <Typography variant="body1" gutterBottom>
            We encountered an issue loading {mode} recommendations.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Error details: {error}
          </Typography>
        </Alert>
      );
    }

    // For debugging - show if data is empty even after loading
    if (!loading && recommendations.length === 0 && !error) {
      return (
        <Alert 
          severity="info" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={fetchRecommendations} startIcon={<Refresh />}>
              Retry
            </Button>
          }
        >
          <Typography variant="body1" gutterBottom>
            No recommendations data available.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This could be due to API connection issues or empty response data. Check the browser console for details.
          </Typography>
        </Alert>
      );
    }

    switch (activeTab) {
      case 0:
        return mode === 'investment' ? renderInvestmentRecommendations() : 
               mode === 'talent' ? renderTalentRecommendations() : 
               renderPartnershipRecommendations();
      case 1:
        return renderInsights();
      case 2:
        return renderOpportunities();
      default:
        return null;
    }
  };

  const renderFilters = () => {
    const commonFilters = (
      <Box sx={{ mb: 3, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        <Chip
          label="Confidence"
          deleteIcon={<FilterList />}
          onDelete={() => {}}
          onClick={() => {}}
        />
        
        {mode === 'investment' && (
          <>
            <Chip
              label={`Sector: ${filters.sector === 'all' ? 'All' : filters.sector}`}
              deleteIcon={<FilterList />}
              onDelete={() => {}}
              onClick={() => {}}
            />
            <Chip
              label={`Stage: ${filters.stage === 'all' ? 'All' : filters.stage}`}
              deleteIcon={<FilterList />}
              onDelete={() => {}}
              onClick={() => {}}
            />
          </>
        )}
        
        <Chip
          label={`Geography: ${filters.geography === 'all' ? 'All' : filters.geography}`}
          deleteIcon={<FilterList />}
          onDelete={() => {}}
          onClick={() => {}}
        />
        
        <IconButton size="small" onClick={fetchRecommendations}>
          <Refresh fontSize="small" />
        </IconButton>
      </Box>
    );
    
    return commonFilters;
  };

  // Mock data generation for fallback purposes
  const generateMockRecommendations = (mode, count = 5) => {
    if (mode === 'investment') {
      return Array.from({ length: count }, (_, i) => ({
        id: `rec-${i}`,
        companyId: `company-${i}`,
        companyName: `AI Company ${i+1}`,
        sector: ['AI/ML', 'SaaS', 'FinTech', 'HealthTech', 'EdTech'][i % 5],
        stage: ['Seed', 'Series A', 'Series B', 'Series C'][i % 4],
        valuation: Math.round(5 + Math.random() * 45),
        growthRate: Math.round(15 + Math.random() * 85),
        score: 0.5 + Math.random() * 0.45,
        talentInflow: Math.round(5 + Math.random() * 25),
        talentOutflow: Math.round(1 + Math.random() * 8),
        keyFactors: [
          'Strong talent acquisition',
          'Innovative technology',
          'Market leader in segment',
          'Strong founder background'
        ].slice(0, 2 + Math.floor(Math.random() * 3)),
        aiExplanation: `Recommended due to exceptional growth rate and strong talent acquisition.`
      }));
    } else if (mode === 'talent') {
      return Array.from({ length: count }, (_, i) => ({
        id: `rec-${i}`,
        candidateName: `Talent ${i+1}`,
        currentRole: ['Senior ML Engineer', 'Data Scientist', 'AI Researcher', 'CTO', 'VP of Engineering'][i % 5],
        currentCompany: `Tech Company ${i+1}`,
        skillMatch: 0.7 + Math.random() * 0.25,
        cultureMatch: 0.6 + Math.random() * 0.3,
        retentionScore: 0.5 + Math.random() * 0.4,
        fitScore: 3 + Math.floor(Math.random() * 3),
        skills: [
          'Machine Learning',
          'Deep Learning',
          'Python',
          'TensorFlow',
          'PyTorch',
          'NLP',
          'Computer Vision'
        ].sort(() => Math.random() - 0.5).slice(0, 3 + Math.floor(Math.random() * 4)),
        aiExplanation: `Candidate shows strong match (${Math.round((0.7 + Math.random() * 0.25) * 100)}%) with required skills and culture fit.`
      }));
    } else { // partnership
      return Array.from({ length: count }, (_, i) => ({
        id: `rec-${i}`,
        companyName: `Partner Co ${i+1}`,
        industry: ['AI Services', 'Cloud Infrastructure', 'Data Analytics', 'Security', 'IoT'][i % 5],
        size: ['Small', 'Medium', 'Large', 'Enterprise'][i % 4],
        score: 0.6 + Math.random() * 0.35,
        synergies: [
          'Technology Integration',
          'Market Access',
          'Complementary Products',
          'Shared Customer Base',
          'R&D Collaboration'
        ].sort(() => Math.random() - 0.5).slice(0, 2 + Math.floor(Math.random() * 3)),
        aiExplanation: `Potential synergies in technology integration and market access make this partnership promising.`
      }));
    }
  };

  const generateMockInsights = (mode, count = 3) => {
    const insightTemplates = [
      {
        title: 'Rising Talent Flight Risk',
        description: 'Several key employees from top companies have updated their profiles recently, indicating potential job seeking.',
        confidence: 0.85,
        aiLabels: ['talent', 'risk']
      },
      {
        title: 'Market Consolidation Trend',
        description: 'Increasing M&A activity detected in the AI sector with smaller companies being acquired by larger platforms.',
        confidence: 0.92,
        aiLabels: ['market', 'growth']
      },
      {
        title: 'Competitive Expansion Alert',
        description: 'Major competitor has been rapidly expanding engineering team with specialization in quantum computing.',
        confidence: 0.78,
        aiLabels: ['competition', 'growth']
      },
      {
        title: 'Emerging Skill Demand',
        description: 'Sharp increase in demand for LLM fine-tuning specialists across multiple industry verticals.',
        confidence: 0.88,
        aiLabels: ['talent', 'growth']
      },
      {
        title: 'Regional Expansion Opportunity',
        description: 'Southeast Asian market showing accelerated adoption of AI solutions with limited local provider presence.',
        confidence: 0.75,
        aiLabels: ['market', 'growth']
      }
    ];
    
    return Array.from({ length: count }, (_, i) => ({
      id: `insight-${i}`,
      ...insightTemplates[i % insightTemplates.length],
      timestamp: new Date(Date.now() - Math.floor(Math.random() * 30) * 24 * 60 * 60 * 1000).toISOString()
    }));
  };

  const generateMockOpportunities = (mode, count = 3) => {
    const opportunityTemplates = [
      {
        title: 'Strategic Talent Acquisition',
        description: 'Senior AI team from recently dissolved startup available for immediate hiring.',
        impactScore: 0.85,
        difficulty: 'Medium',
        urgency: 'high',
        expirationDays: 14
      },
      {
        title: 'Market Entry Partnership',
        description: 'Established provider seeking technology partner for expansion into healthcare vertical.',
        impactScore: 0.92,
        difficulty: 'High',
        urgency: 'medium',
        expirationDays: 45
      },
      {
        title: 'Early Access to New LLM API',
        description: 'Limited spots available for beta integration with next-generation language model.',
        impactScore: 0.78,
        difficulty: 'Low',
        urgency: 'high',
        expirationDays: 7
      },
      {
        title: 'Exclusive Distribution Agreement',
        description: 'Regional leader looking for exclusive technology provider for government contracts.',
        impactScore: 0.88,
        difficulty: 'Medium',
        urgency: 'medium',
        expirationDays: 30
      },
      {
        title: 'Data Partnership Opportunity',
        description: 'Major retailer offering access to anonymized consumer behavior data for co-development.',
        impactScore: 0.75,
        difficulty: 'High',
        urgency: 'low',
        expirationDays: 90
      }
    ];
    
    return Array.from({ length: count }, (_, i) => ({
      id: `opportunity-${i}`,
      ...opportunityTemplates[i % opportunityTemplates.length]
    }));
  };

  // Direct fetch function as a fallback mechanism
  const directFetchRecommendations = () => {
    console.log("RecommendationEngine: Making direct API call");
    setLoading(true);
    
    // Build URL with query parameters
    const params = new URLSearchParams({
      mode,
      ...context
    });
    
    const url = `http://localhost:8000/api/analytics/recommendations?${params.toString()}`;
    console.log("DirectFetch: Calling URL:", url);
    
    fetch(url, {
      method: 'GET',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      console.log("DirectFetch API Response Status:", response.status);
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log("DirectFetch API Data:", data);
      
      try {
        if (Array.isArray(data)) {
          console.log("DirectFetch: Processing data array with length:", data.length);
          
          // Check if first item has expected properties
          if (data.length > 0) {
            console.log("DirectFetch: First item in data:", data[0]);
          }
          
          // Process the data the same way as in fetchRecommendations
          const processedRecs = data.map(rec => {
            try {
              const newRec = {
                ...rec,
                score: rec.score !== undefined ? rec.score : calculateCompositeScore(rec),
                aiExplanation: rec.aiExplanation || generateExplanation(rec, mode)
              };
              console.log("DirectFetch: Processed item:", newRec);
              return newRec;
            } catch (err) {
              console.error("DirectFetch: Error processing recommendation item:", err, rec);
              // Return the original item if processing fails
              return rec;
            }
          }).sort((a, b) => (b.score || 0) - (a.score || 0));
          
          console.log("DirectFetch: All items processed successfully");
          console.log("DirectFetch: Setting recommendations state with processed data");
          setRecommendations(processedRecs);
          setLoading(false);
          setError(null);
        } else {
          console.error("DirectFetch: Data is not an array:", typeof data, data);
          throw new Error("Invalid data format received - expected an array");
        }
      } catch (err) {
        console.error("DirectFetch: Error during data processing:", err);
        setError(`Processing Error: ${err.message}`);
        
        // Set the raw data anyway as a fallback
        if (Array.isArray(data)) {
          console.log("DirectFetch: Setting raw data as fallback");
          setRecommendations(data);
        }
        setLoading(false);
      }
    })
    .catch(err => {
      console.error("DirectFetch API Error:", err);
      setError(`Direct API Error: ${err.message}`);
      setLoading(false);
    });
  };

  // Add a debug function to test the raw API response
  const testApiRawResponse = () => {
    console.log("RecommendationEngine: Testing raw API response");
    
    const url = `http://localhost:8000/api/analytics/recommendations?mode=${mode}`;
    console.log("Raw API Test: Fetching from URL:", url);
    
    // Use fetch with text response to check raw data
    fetch(url, {
      method: 'GET',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      console.log("Raw API Test: Response status:", response.status);
      return response.text(); // Get raw text instead of JSON
    })
    .then(rawText => {
      console.log("Raw API Test: Raw response text:", rawText);
      
      // Try to parse as JSON to validate the response
      try {
        const jsonData = JSON.parse(rawText);
        console.log("Raw API Test: Successfully parsed JSON:", jsonData);
        
        // Set data directly from the parsed JSON
        if (Array.isArray(jsonData)) {
          setRecommendations(jsonData);
          setLoading(false);
          console.log("Raw API Test: Successfully set recommendations from parsed JSON");
        } else {
          console.error("Raw API Test: Parsed JSON is not an array");
        }
      } catch (err) {
        console.error("Raw API Test: Failed to parse response as JSON:", err);
      }
    })
    .catch(err => {
      console.error("Raw API Test: Fetch error:", err);
    });
  };

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">
          {mode === 'investment' && 'Investment Recommendations'}
          {mode === 'talent' && 'Talent Recommendations'}
          {mode === 'partnership' && 'Partnership Recommendations'}
        </Typography>
        <Tooltip title="These recommendations are powered by our AI engine that analyzes talent flow, company growth metrics, and market positioning data">
          <IconButton>
            <Info />
          </IconButton>
        </Tooltip>
      </Box>
      
      {renderFilters()}
      
      <Box sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab label="Recommendations" />
          <Tab label="Insights" />
          <Tab label="Opportunities" />
        </Tabs>
      </Box>
      
      {renderContent()}
    </Box>
  );
};

export default RecommendationEngine;