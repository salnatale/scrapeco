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
  Paper
} from '@mui/material';
import { useVC } from '../context/VCContext';
import ModeToggle from '../components/ModeToggle';
import VCFilters from '../components/VCFilters';
import CompanyLeaderboard from '../components/CompanyLeaderboard';
import PortfolioOverview from '../components/PortfolioOverview';
import SkillTrends from '../components/SkillTrends';

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

  // Render content based on mode and active tab
  const renderContent = () => {
    if (state.loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (state.error) {
      return (
        <Alert severity="error" sx={{ mb: 3 }}>
          {state.error}
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