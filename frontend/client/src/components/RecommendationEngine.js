import React, { useState, useEffect } from 'react';
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
  Badge
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
  const [filters, setFilters] = useState({
    confidence: 'all',
    sector: 'all',
    stage: 'all',
    geography: 'all'
  });

  useEffect(() => {
    fetchRecommendations();
  }, [mode, context, filters]);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        mode,
        ...context,
        ...filters
      });

      const [recsResponse, insightsResponse, oppsResponse] = await Promise.all([
        fetch(`/api/recommendations?${params}`),
        fetch(`/api/insights?${params}`),
        fetch(`/api/opportunities?${params}`)
      ]);

      const recsData = await recsResponse.json();
      const insightsData = await insightsResponse.json();
      const oppsData = await oppsResponse.json();

      setRecommendations(recsData);
      setInsights(insightsData);
      setOpportunities(oppsData);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    } finally {
      setLoading(false);
    }
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
      {recommendations.map((rec) => (
        <Grid item xs={12} md={6} lg={4} key={rec.id}>
          <Card 
            sx={{ 
              height: '100%',
              position: 'relative',
              cursor: 'pointer',
              '&:hover': { boxShadow: 4 }
            }}
            onClick={() => onCompanySelect?.(rec.companyId)}
          >
            <Badge
              badgeContent={rec.score}
              color={getConfidenceColor(rec.confidence)}
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
                {rec.companyName}
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {rec.sector} • {rec.stage}
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Investment Confidence
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={rec.confidence * 100}
                  color={getConfidenceColor(rec.confidence)}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {Math.round(rec.confidence * 100)}% confidence
                </Typography>
              </Box>

              <Grid container spacing={1} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Valuation
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    ${rec.valuation}M
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Growth Rate
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {rec.growthRate}%
                  </Typography>
                </Grid>
              </Grid>

              <Typography variant="body2" sx={{ mb: 2 }}>
                {rec.reasoning}
              </Typography>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                {rec.keyFactors.map((factor, index) => (
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
                  onActionClick?.('invest', rec);
                }}
              >
                View Investment Details
              </Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  const renderTalentRecommendations = () => (
    <Grid container spacing={3}>
      {recommendations.map((rec) => (
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
                {rec.summary}
              </Typography>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle2">Key Qualifications</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    {rec.qualifications.map((qual, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <CheckCircle color="success" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText primary={qual} />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle2">Experience Match</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {rec.skills.map((skill, index) => (
                      <Chip
                        key={index}
                        label={skill.name}
                        color={skill.match ? 'success' : 'default'}
                        variant={skill.match ? 'filled' : 'outlined'}
                        size="small"
                      />
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>

              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  onClick={() => onActionClick?.('contact', rec)}
                >
                  Contact Candidate
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => onActionClick?.('viewProfile', rec)}
                >
                  View Full Profile
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  const renderPartnershipRecommendations = () => (
    <Grid container spacing={3}>
      {recommendations.map((rec) => (
        <Grid item xs={12} md={6} lg={4} key={rec.id}>
          <Card 
            sx={{ 
              height: '100%',
              cursor: 'pointer',
              '&:hover': { boxShadow: 4 }
            }}
            onClick={() => onCompanySelect?.(rec.companyId)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar 
                  src={rec.logo} 
                  sx={{ mr: 2, bgcolor: 'primary.main' }}
                >
                  <Business />
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h6">
                    {rec.companyName}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {rec.partnershipType}
                  </Typography>
                </Box>
                <Chip
                  label={rec.synergy}
                  color={getConfidenceColor(rec.synergyScore)}
                  size="small"
                />
              </Box>

              <Typography variant="body2" sx={{ mb: 2 }}>
                {rec.description}
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Potential Benefits
                </Typography>
                <List dense>
                  {rec.benefits.map((benefit, index) => (
                    <ListItem key={index} sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <TrendingUp color="success" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText 
                        primary={benefit}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Grid container spacing={1}>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">
                    Market Overlap
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {rec.marketOverlap}%
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">
                    Tech Synergy
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {rec.techSynergy}%
                  </Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">
                    Cultural Fit
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {rec.culturalFit}%
                  </Typography>
                </Grid>
              </Grid>

              <Button
                variant="contained"
                fullWidth
                sx={{ mt: 2 }}
                onClick={(e) => {
                  e.stopPropagation();
                  onActionClick?.('explore', rec);
                }}
              >
                Explore Partnership
              </Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );

  const renderInsights = () => (
    <Grid container spacing={3}>
      {insights.map((insight) => (
        <Grid item xs={12} md={6} key={insight.id}>
          <Alert
            severity={insight.type}
            icon={insight.icon}
            action={
              <IconButton
                color="inherit"
                size="small"
                onClick={() => onActionClick?.('insight', insight)}
              >
                <Info />
              </IconButton>
            }
          >
            <Typography variant="subtitle2" gutterBottom>
              {insight.title}
            </Typography>
            <Typography variant="body2">
              {insight.description}
            </Typography>
            {insight.actionable && (
              <Button
                size="small"
                color="inherit"
                sx={{ mt: 1 }}
                onClick={() => onActionClick?.('takeAction', insight)}
              >
                Take Action
              </Button>
            )}
          </Alert>
        </Grid>
      ))}
    </Grid>
  );

  const renderOpportunities = () => (
    <List>
      {opportunities.map((opp) => (
        <React.Fragment key={opp.id}>
          <ListItem
            button
            onClick={() => onActionClick?.('opportunity', opp)}
            sx={{
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              mb: 1,
              '&:hover': { bgcolor: 'action.hover' }
            }}
          >
            <ListItemIcon>
              <Chip
                label={opp.priority}
                color={getPriorityColor(opp.priority)}
                size="small"
              />
            </ListItemIcon>
            <ListItemText
              primary={opp.title}
              secondary={
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {opp.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Chip label={`$${opp.potentialValue}M`} size="small" color="success" />
                    <Chip label={`${opp.timeframe} timeline`} size="small" />
                    <Chip label={`${opp.probability}% likely`} size="small" />
                  </Box>
                </Box>
              }
            />
            <ArrowForward />
          </ListItem>
        </React.Fragment>
      ))}
    </List>
  );

  const tabLabels = {
    investment: ['Companies', 'Market Insights', 'Opportunities'],
    talent: ['Candidates', 'Talent Insights', 'Pipeline'],
    partnership: ['Partners', 'Market Analysis', 'Opportunities']
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Recommendation Engine
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<FilterList />}
            onClick={() => {/* Open filters dialog */}}
          >
            Filters
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchRecommendations}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Mode Indicator */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
        <Typography variant="h6">
          {mode === 'investment' && 'Investment Recommendations'}
          {mode === 'talent' && 'Talent Acquisition Recommendations'}
          {mode === 'partnership' && 'Strategic Partnership Recommendations'}
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.9 }}>
          AI-powered recommendations based on your portfolio and market analysis
        </Typography>
      </Paper>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={(e, newValue) => setActiveTab(newValue)}
        sx={{ mb: 3 }}
      >
        {tabLabels[mode].map((label, index) => (
          <Tab key={index} label={label} />
        ))}
      </Tabs>

      {/* Tab Content */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <Typography>Loading recommendations...</Typography>
        </Box>
      ) : (
        <Box>
          {activeTab === 0 && (
            <>
              {mode === 'investment' && renderInvestmentRecommendations()}
              {mode === 'talent' && renderTalentRecommendations()}
              {mode === 'partnership' && renderPartnershipRecommendations()}
            </>
          )}
          {activeTab === 1 && renderInsights()}
          {activeTab === 2 && renderOpportunities()}
        </Box>
      )}

      {/* Summary Stats */}
      <Paper sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recommendation Summary
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h3" color="primary">
                {recommendations.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Recommendations
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h3" color="success.main">
                {recommendations.filter(r => r.confidence >= 0.8).length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                High Confidence
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h3" color="info.main">
                {insights.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Market Insights
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h3" color="warning.main">
                {opportunities.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                New Opportunities
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};

export default RecommendationEngine;