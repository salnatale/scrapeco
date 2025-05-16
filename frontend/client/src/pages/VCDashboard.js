// frontend/client/src/pages/VCDashboard.js
import React, { useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Paper,
  Button
} from '@mui/material';
import { useVC } from '../context/VCContext';
import ModeToggle from '../components/ModeToggle';
import VCFilters from '../components/VCFilters';
import CompanyLeaderboard from '../components/CompanyLeaderboard';
import PortfolioOverview from '../components/PortfolioOverview';
import SkillTrends from '../components/SkillTrends';
import RecommendationEngine from '../components/RecommendationEngine';
import TalentFlowVisualizer from '../components/visualizations/TalentFlowVisualizer';
import RefreshIcon from '@mui/icons-material/Refresh';

// Create single instance of SkillTrends to reuse
const skillTrendsInstance = <SkillTrends />;

const VCDashboard = () => {
  const { state, actions } = useVC();
  const [activeTab, setActiveTab] = React.useState(0);

  // Clear any existing errors on mount
  useEffect(() => {
    actions.clearError();
  }, []);

  // Handle tab changes for Research/Portfolio sub-sections
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Handle action clicks from recommendation engine
  const handleRecommendationAction = (actionType, item) => {
    console.log(`Recommendation action: ${actionType}`, item);
    
    switch(actionType) {
      case 'invest':
      case 'view_company':
        // Navigate to company details or open investment modal
        alert(`Viewing details for ${item.companyName || item.name}`);
        break;
      case 'contact':
        // Open contact form or modal
        alert(`Contacting ${item.candidateName || item.name}`);
        break;
      case 'view_profile':
        // Open profile view
        alert(`Viewing profile for ${item.candidateName || item.name}`);
        break;
      case 'pursue_opportunity':
        // Take action on opportunity
        alert(`Pursuing opportunity: ${item.title}`);
        break;
      case 'initiate_partnership':
        // Initiate partnership workflow
        alert(`Initiating partnership with ${item.companyName}`);
        break;
      default:
        console.log('Unknown action:', actionType);
    }
  };

  // Handle company selection
  const handleCompanySelect = (companyId) => {
    alert(`Selected company with ID: ${companyId}`);
    // In a real implementation, you would navigate to company details page
    // or open a modal with company details
  };

  // Render content based on mode and active tab
  const renderContent = () => {
    if (state.loading) {
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={40} sx={{ mb: 2 }} />
          <Typography variant="body1" color="text.secondary">
            Loading data...
          </Typography>
        </Box>
      );
    }

    if (state.error) {
      return (
        <Alert 
          severity="error" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={() => actions.clearError()} startIcon={<RefreshIcon />}>
              Retry
            </Button>
          }
        >
          <Typography variant="body1" gutterBottom>
            Error loading data
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {state.error}
          </Typography>
        </Alert>
      );
    }

    if (state.mode === 'research') {
      switch (activeTab) {
        case 0: // Overview
          return (
            <Box>
              {skillTrendsInstance}
              {state.companies.length > 0 && (
                <CompanyLeaderboard companies={state.companies} />
              )}
            </Box>
          );
        case 1: // Companies
          return <CompanyLeaderboard companies={state.companies} />;
        case 2: // Skills/Hiring
          return skillTrendsInstance;
        case 3: // Flows
          return (
            <TalentFlowVisualizer 
              companyIds={state.companies.map(c => c.urn).slice(0, 10)} 
              regionIds={state.filters.geo_regions}
              timePeriod="6m"
            />
          );
        case 4: // Recommendations
          return (
            <RecommendationEngine 
              mode="investment"
              context={{
                industries: state.filters.industries,
                funding_stages: state.filters.funding_stages,
                geo_regions: state.filters.geo_regions
              }}
              onActionClick={handleRecommendationAction}
              onCompanySelect={handleCompanySelect}
            />
          );
        default:
          return <Typography>Tab content coming soon...</Typography>;
      }
    } else {
      // Portfolio mode
      switch (activeTab) {
        case 0: // Overview
          return <PortfolioOverview overview={state.portfolioOverview} />;
        case 1: // Portfolio Map
          return <Typography>Portfolio map visualization coming soon...</Typography>;
        case 2: // Alerts
          return <Typography>Portfolio alerts coming soon...</Typography>;
        case 3: // Company Health
          return (
            <RecommendationEngine 
              mode="portfolio"
              context={{
                portfolio_ids: state.filters.portfolio_ids
              }}
              onActionClick={handleRecommendationAction}
              onCompanySelect={handleCompanySelect}
            />
          );
        default:
          return <Typography>Tab content coming soon...</Typography>;
      }
    }
  };

  const getTabLabels = () => {
    if (state.mode === 'research') {
      return ['Overview', 'Companies', 'Hiring', 'Flows', 'Recommendations'];
    } else {
      return ['Overview', 'Portfolio Map', 'Alerts', 'Company Health'];
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1" sx={{ flexGrow: 1, fontWeight: 500 }}>
              VC Dashboard
            </Typography>
            <ModeToggle />
          </Box>
          
          {/* Filters */}
          <VCFilters />
          
          {/* Tab navigation */}
          <Paper sx={{ mb: 3 }}>
            <Tabs 
              value={activeTab} 
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              variant="scrollable"
              scrollButtons="auto"
              aria-label="dashboard tabs"
            >
              {getTabLabels().map((label, index) => (
                <Tab key={index} label={label} />
              ))}
            </Tabs>
          </Paper>
          
          {/* Content based on mode & active tab */}
          {renderContent()}
        </Box>
      </Container>
    </Box>
  );
};

export default VCDashboard;