// frontend/client/src/components/SkillTrends.js
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Alert
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material';
import { useVC } from '../context/VCContext';

// Create a global store for skills data to share between component instances
// This prevents multiple SkillTrends components from making duplicate requests
const globalSkillsStore = {
  data: null,
  lastFetched: 0,
  fetching: false,
  listeners: new Set(),
  
  // Register component to receive updates
  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  },
  
  // Notify all listeners when data changes
  notifyListeners() {
    this.listeners.forEach(callback => callback(this.data));
  },
  
  // Update data and notify listeners
  setData(newData) {
    this.data = newData;
    this.lastFetched = Date.now();
    this.fetching = false;
    this.notifyListeners();
  },
  
  // Check if data is stale
  isStale(maxAge = 60000) {
    return !this.data || (Date.now() - this.lastFetched) > maxAge;
  }
};

const SkillTrends = () => {
  const { state, actions } = useVC();
  const [trendingSkills, setTrendingSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const componentMounted = useRef(true);
  
  // The actual data fetching function - now uses the global store
  const fetchTrendingSkills = async (force = false) => {
    // If we're already fetching or have recent data and not forced, use existing data
    if (globalSkillsStore.fetching) {
      console.log('Global fetch already in progress, waiting for results');
      return;
    }
    
    if (!force && !globalSkillsStore.isStale()) {
      console.log('Using recent global skills data');
      setTrendingSkills(globalSkillsStore.data);
      return;
    }
    
    try {
      // Mark as fetching to prevent duplicate requests
      globalSkillsStore.fetching = true;
      setLoading(true);
      setError(null);
      
      console.log('Fetching fresh trending skills data...');
      const skills = await actions.loadTrendingSkills(10);
      
      // Transform the API data format to match our component's expected format
      const transformedSkills = skills.map(skill => ({
        skill: skill.name || skill.skill || 'Unknown Skill',
        trendScore: skill.trendScore || skill.growth || 0,
        recentHires: skill.recentHires || Math.floor((skill.count || 0) * 0.2) || 0, 
        totalProfiles: skill.totalProfiles || skill.count || 0
      }));
      
      // Update global store
      globalSkillsStore.setData(transformedSkills);
      
      // Only update state if component is still mounted
      if (componentMounted.current) {
        setTrendingSkills(transformedSkills);
      }
    } catch (err) {
      console.error('Error in fetchTrendingSkills:', err);
      globalSkillsStore.fetching = false;
      if (componentMounted.current) {
        setError('Error fetching trending skills');
      }
    } finally {
      if (componentMounted.current) {
        setLoading(false);
      }
    }
  };

  // On mount, subscribe to global store and load data if needed
  useEffect(() => {
    // Set up cleanup
    componentMounted.current = true;
    
    // Load data initially if needed
    if (globalSkillsStore.data) {
      // Use existing data
      setTrendingSkills(globalSkillsStore.data);
      
      // Refresh if data is stale
      if (globalSkillsStore.isStale()) {
        fetchTrendingSkills();
      }
    } else {
      // First load
      fetchTrendingSkills();
    }
    
    // Subscribe to store updates
    const unsubscribe = globalSkillsStore.subscribe(data => {
      if (componentMounted.current && data) {
        setTrendingSkills(data);
      }
    });
    
    // Cleanup on unmount
    return () => {
      componentMounted.current = false;
      unsubscribe();
    };
  }, []);

  const getSkillCategory = (skillName) => {
    const categories = {
      'Technical': ['Python', 'JavaScript', 'React', 'Node.js', 'Java', 'C++', 'Go', 'TypeScript'],
      'AI/ML': ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP', 'Natural Language'],
      'Cloud': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Cloud'],
      'Data': ['SQL', 'NoSQL', 'MongoDB', 'PostgreSQL', 'Analytics', 'Data Science'],
      'DevOps': ['CI/CD', 'Jenkins', 'Git', 'Linux', 'Infrastructure', 'DevOps', 'GraphQL']
    };

    for (const [category, skills] of Object.entries(categories)) {
      if (skills.some(skill => skillName.toLowerCase().includes(skill.toLowerCase()))) {
        return category;
      }
    }
    return 'Other';
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Technical': 'primary',
      'AI/ML': 'secondary',
      'Cloud': 'info',
      'Data': 'success',
      'DevOps': 'warning',
      'Other': 'default'
    };
    return colors[category] || 'default';
  };

  const formatTrendScore = (score) => {
    if (score > 30) return 'Hot';
    if (score > 20) return 'Rising';
    if (score > 10) return 'Growing';
    return 'Emerging';
  };

  const getTrendIcon = (score) => {
    if (score > 25) return <TrendingUp color="success" />;
    if (score > 10) return <TrendingUp color="warning" />;
    return <TrendingUp color="info" />;
  };

  // Use the global loading state or local loading state
  const isLoading = state.loading || loading;
  
  // Use the global error state or local error state
  const errorMessage = state.error || error;

  const handleRefreshClick = () => {
    // Force refresh regardless of cache
    fetchTrendingSkills(true);
  };

  if (errorMessage) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {errorMessage}
      </Alert>
    );
  }

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {/* Skill Momentum Section */}
      <Grid item xs={12} md={8}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <AnalyticsIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6" fontWeight={600} sx={{ flexGrow: 1 }}>
              Skill Momentum
            </Typography>
            <Tooltip title="Refresh Data">
              <IconButton 
                onClick={handleRefreshClick} 
                disabled={isLoading || globalSkillsStore.fetching}
                size="small"
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>

          {isLoading ? (
            <Box sx={{ py: 4 }}>
              <LinearProgress />
              <Typography variant="body2" sx={{ mt: 2, textAlign: 'center' }}>
                Loading trending skills...
              </Typography>
            </Box>
          ) : trendingSkills.length === 0 ? (
            <Typography variant="body2" sx={{ py: 4, textAlign: 'center' }}>
              No trending skills data available
            </Typography>
          ) : (
            <List>
              {trendingSkills.map((skill, index) => {
                const category = getSkillCategory(skill.skill);
                const categoryColor = getCategoryColor(category);
                
                return (
                  <ListItem key={skill.skill} sx={{ px: 0, py: 1.5 }}>
                    <Box sx={{ width: '100%' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle2" fontWeight={600} sx={{ flexGrow: 1 }}>
                          {skill.skill}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getTrendIcon(skill.trendScore)}
                          <Chip
                            label={formatTrendScore(skill.trendScore)}
                            size="small"
                            color={skill.trendScore > 25 ? 'success' : 'warning'}
                            variant="outlined"
                          />
                          <Chip
                            label={category}
                            size="small"
                            color={categoryColor}
                            variant="filled"
                          />
                        </Box>
                      </Box>
                      
                      <Grid container spacing={2} alignItems="center">
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">
                            Recent Hires
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {skill.recentHires}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">
                            Total Profiles
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {skill.totalProfiles}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Box sx={{ width: '100%' }}>
                            <Typography variant="caption" color="text.secondary">
                              Trend Score
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={Math.min(skill.trendScore, 100)}
                                sx={{ 
                                  flexGrow: 1, 
                                  height: 8, 
                                  borderRadius: 4,
                                  backgroundColor: 'rgba(0,0,0,0.1)'
                                }}
                                color={skill.trendScore > 25 ? 'success' : 'warning'}
                              />
                              <Typography variant="caption" fontWeight={600}>
                                {skill.trendScore.toFixed(1)}%
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                      </Grid>
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          )}
        </Paper>
      </Grid>

      {/* Skill Categories Summary */}
      <Grid item xs={12} md={4}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 3 }}>
            Skill Categories
          </Typography>
          
          {trendingSkills.length === 0 ? (
            <Typography variant="body2" sx={{ py: 4, textAlign: 'center' }}>
              No skill categories data available
            </Typography>
          ) : (
            Object.entries(
              trendingSkills.reduce((acc, skill) => {
                const category = getSkillCategory(skill.skill);
                if (!acc[category]) acc[category] = { count: 0, totalTrend: 0 };
                acc[category].count += 1;
                acc[category].totalTrend += skill.trendScore;
                return acc;
              }, {})
            ).map(([category, data]) => (
              <Card key={category} sx={{ mb: 2, backgroundColor: 'background.default' }}>
                <CardContent sx={{ py: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2" fontWeight={600} sx={{ flexGrow: 1 }}>
                      {category}
                    </Typography>
                    <Chip
                      label={data.count}
                      size="small"
                      color={getCategoryColor(category)}
                      variant="filled"
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Avg Trend Score: {(data.totalTrend / data.count).toFixed(1)}%
                  </Typography>
                </CardContent>
              </Card>
            ))
          )}
        </Paper>
      </Grid>
    </Grid>
  );
};

export default SkillTrends;