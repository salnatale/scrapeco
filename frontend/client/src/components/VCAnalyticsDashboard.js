import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  AppBar,
  Toolbar,
  Paper,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert
} from '@mui/material';
import {
  Dashboard,
  Analytics,
  Notifications,
  Business,
  TrendingUp,
  Settings,
  MoreVert,
  Refresh,
  Download,
  Share
} from '@mui/icons-material';

// Import all our new components
import PortfolioMap from './PortfolioMap';
import AlertsDashboard from './AlertsDashboard';
import CompanyDeepDive from './CompanyDeepDive';
import RecommendationEngine from './RecommendationEngine';
import TalentFlowSankey from './TalentFlowSankey';
import GeographicHeatmap from './GeographicHeatmap';
import CompanyNetworkGraph from './CompanyNetworkGraph';

const VCAnalyticsDashboard = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [portfolioData, setPortfolioData] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [networkData, setNetworkData] = useState(null);
  const [geographicData, setGeographicData] = useState([]);
  const [talentFlowData, setTalentFlowData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [companiesToCompare, setCompaniesToCompare] = useState([]);

  // Fetch initial data
  useEffect(() => {
    fetchPortfolioData();
    fetchNotifications();
    fetchVisualizationData();
  }, []);

  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      // Simulate API call to get company scores
      const response = await fetch('/api/analytics/company-scores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_urns: [], // Empty to get all companies
          include_pagerank: true,
          include_birank: true,
          include_talent_flow: true
        })
      });
      
      const data = await response.json();
      setPortfolioData(data);
    } catch (error) {
      console.error('Error fetching portfolio data:', error);
      // Fallback to mock data
      setPortfolioData([
        {
          company_urn: 'urn:li:company:123',
          company_name: 'TechCorp',
          composite_score: 0.78,
          pagerank_score: 0.045,
          birank_company_score: 0.067,
          talent_inflow: 45,
          talent_outflow: 23,
          net_talent_flow: 22
        },
        {
          company_urn: 'urn:li:company:456',
          company_name: 'StartupXYZ',
          composite_score: 0.65,
          pagerank_score: 0.032,
          birank_company_score: 0.041,
          talent_inflow: 28,
          talent_outflow: 15,
          net_talent_flow: 13
        }
      ]);
    }
    setLoading(false);
  };

  const fetchNotifications = async () => {
    try {
      const response = await fetch('/api/analytics/check-alerts');
      const alerts = await response.json();
      setNotifications(alerts);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  };

  const fetchVisualizationData = async () => {
    try {
      // Fetch talent flow network data
      const networkResponse = await fetch('/api/analytics/talent-flow-network?min_transitions=5');
      const network = await networkResponse.json();
      setNetworkData(network);

      // Fetch geographic talent density
      const geoResponse = await fetch('/api/analytics/geographic-talent-density');
      const geo = await geoResponse.json();
      setGeographicData(geo);

      // Mock Sankey data for talent flow
      setTalentFlowData({
        nodes: [
          { id: 'tech-giants', name: 'Tech Giants' },
          { id: 'portfolio-co-1', name: 'Portfolio Co 1' },
          { id: 'portfolio-co-2', name: 'Portfolio Co 2' },
          { id: 'startups', name: 'Startups' },
          { id: 'consulting', name: 'Consulting' }
        ],
        links: [
          { source: 'tech-giants', target: 'portfolio-co-1', value: 15 },
          { source: 'tech-giants', target: 'portfolio-co-2', value: 8 },
          { source: 'consulting', target: 'portfolio-co-1', value: 12 },
          { source: 'portfolio-co-1', target: 'startups', value: 5 },
          { source: 'portfolio-co-2', target: 'startups', value: 7 }
        ]
      });
    } catch (error) {
      console.error('Error fetching visualization data:', error);
    }
  };

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const handleCompanyClick = (company) => {
    setSelectedCompany(company);
    setSelectedTab(4); // Switch to company deep dive tab
  };

  const handleCompareCompany = (company) => {
    if (companiesToCompare.length < 2) {
      setCompaniesToCompare(prev => [...prev, company]);
    }
    if (companiesToCompare.length === 1) {
      setCompareDialogOpen(true);
    }
  };

  const handleAddToPortfolio = (recommendation) => {
    // Add recommendation to portfolio tracking
    console.log('Adding to portfolio:', recommendation);
    // In a real app, this would make an API call
  };

  const handleRefresh = async () => {
    await fetchPortfolioData();
    await fetchNotifications();
    await fetchVisualizationData();
  };

  const exportData = () => {
    // Export portfolio data as CSV/Excel
    console.log('Exporting data...');
  };

  const shareReport = () => {
    // Share functionality
    console.log('Sharing report...');
  };

  const tabs = [
    { label: 'Portfolio Overview', icon: <Dashboard /> },
    { label: 'Talent Analytics', icon: <TrendingUp /> },
    { label: 'Recommendations', icon: <Business /> },
    { label: 'Alerts', icon: <Badge badgeContent={notifications.length} color="error"><Notifications /></Badge> },
    { label: 'Company Deep Dive', icon: <Analytics /> }
  ];

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Header */}
      <AppBar position="static" color="transparent" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Portfolio Analytics Dashboard
          </Typography>
          
          <Button
            color="inherit"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>

          <IconButton
            color="inherit"
            onClick={(e) => setMenuAnchor(e.currentTarget)}
          >
            <MoreVert />
          </IconButton>

          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={() => setMenuAnchor(null)}
          >
            <MenuItem onClick={exportData}>
              <Download sx={{ mr: 1 }} /> Export Data
            </MenuItem>
            <MenuItem onClick={shareReport}>
              <Share sx={{ mr: 1 }} /> Share Report
            </MenuItem>
            <MenuItem onClick={() => setMenuAnchor(null)}>
              <Settings sx={{ mr: 1 }} /> Settings
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Notifications Bar */}
      {notifications.length > 0 && (
        <Alert severity="warning" sx={{ m: 2 }}>
          You have {notifications.length} active alert{notifications.length !== 1 ? 's' : ''} requiring attention.
        </Alert>
      )}

      {/* Navigation Tabs */}
      <Paper sx={{ bgcolor: 'background.paper' }}>
        <Tabs 
          value={selectedTab} 
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          {tabs.map((tab, index) => (
            <Tab 
              key={index}
              label={tab.label} 
              icon={tab.icon}
              iconPosition="start"
            />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
        {/* Portfolio Overview */}
        {selectedTab === 0 && (
          <PortfolioMap
            portfolioData={portfolioData}
            onCompanyClick={handleCompanyClick}
          />
        )}

        {/* Talent Analytics */}
        {selectedTab === 1 && (
          <Box>
            <Typography variant="h4" gutterBottom>
              Talent Flow Analytics
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12}>
                {talentFlowData && (
                  <TalentFlowSankey 
                    data={talentFlowData}
                    height={400}
                  />
                )}
              </Grid>
              
              <Grid item xs={12} lg={6}>
                {networkData && (
                  <CompanyNetworkGraph 
                    data={networkData}
                    height={500}
                  />
                )}
              </Grid>
              
              <Grid item xs={12} lg={6}>
                <GeographicHeatmap 
                  data={geographicData}
                  height={500}
                />
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Recommendations */}
        {selectedTab === 2 && (
          <RecommendationEngine
            portfolioData={portfolioData}
            onRecommendationClick={handleCompanyClick}
            onAddToPortfolio={handleAddToPortfolio}
          />
        )}

        {/* Alerts */}
        {selectedTab === 3 && (
          <AlertsDashboard portfolioCompanies={portfolioData} />
        )}

        {/* Company Deep Dive */}
        {selectedTab === 4 && (
          selectedCompany ? (
            <CompanyDeepDive
              companyUrn={selectedCompany.company_urn}
              onBack={() => {
                setSelectedCompany(null);
                setSelectedTab(0);
              }}
              portfolioData={portfolioData}
              onCompareCompany={handleCompareCompany}
            />
          ) : (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Analytics sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Select a Company to Analyze
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Click on any company from the portfolio overview to see detailed analytics.
              </Typography>
              <Button
                variant="outlined"
                onClick={() => setSelectedTab(0)}
                sx={{ mt: 2 }}
              >
                Go to Portfolio Overview
              </Button>
            </Paper>
          )
        )}
      </Container>

      {/* Company Comparison Dialog */}
      <Dialog 
        open={compareDialogOpen} 
        onClose={() => setCompareDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Company Comparison</DialogTitle>
        <DialogContent>
          {companiesToCompare.length === 2 && (
            <Typography variant="body1">
              Comparing {companiesToCompare[0].company_name} with {companiesToCompare[1].company_name}
            </Typography>
          )}
          {/* Add comparison table/charts here */}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setCompareDialogOpen(false);
            setCompaniesToCompare([]);
          }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default VCAnalyticsDashboard;