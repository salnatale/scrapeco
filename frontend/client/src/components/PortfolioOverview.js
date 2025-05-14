// frontend/client/src/components/PortfolioOverview.js
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Error,
  Info as InfoIcon
} from '@mui/icons-material';

const MetricCard = ({ title, value, subtitle, trend, color = 'primary' }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          {title}
        </Typography>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {trend > 0 ? (
              <TrendingUp color="success" />
            ) : (
              <TrendingDown color="error" />
            )}
          </Box>
        )}
      </Box>
      <Typography variant="h3" sx={{ color: `${color}.main`, fontWeight: 'bold' }}>
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </CardContent>
  </Card>
);

const CompanyStatusChip = ({ company }) => {
  // Get metrics, falling back to reasonable defaults
  const churnRate = company.churnRate || company.churn || 0;
  const netFlow = company.netFlow || company.growth || 0;

  const getStatusInfo = () => {
    if (churnRate > 15) {
      return { color: 'error', icon: <Error />, label: 'High Risk' };
    }
    if (netFlow < -5) {
      return { color: 'warning', icon: <Warning />, label: 'At Risk' };
    }
    if (netFlow > 10) {
      return { color: 'success', icon: <CheckCircle />, label: 'Growing' };
    }
    return { color: 'default', icon: <InfoIcon />, label: 'Stable' };
  };

  const status = getStatusInfo();
  
  return (
    <Chip
      icon={status.icon}
      label={status.label}
      color={status.color}
      size="small"
      variant="outlined"
    />
  );
};

const PortfolioOverview = ({ overview }) => {
  if (!overview) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No portfolio data available
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Select portfolio companies using the filters above
        </Typography>
      </Paper>
    );
  }

  // Normalize our data structure to handle different API formats
  const normalizedOverview = {
    totalCompanies: overview.totalCompanies || 0,
    totalEmployees: overview.totalEmployees || 0,
    avgChurnRate: overview.avgChurnRate || overview.churnRate || 0,
    netTalentFlow: overview.netTalentFlow || 0,
    // Handle different property names from our mock API
    companies: overview.companies || [],
    atRiskCompanies: overview.atRiskCompanies || overview.atRisk?.map(company => ({
      name: company.name,
      churnRate: company.churnRate || company.churn || 0,
      netFlow: company.netFlow || 0,
      employees: company.employees || 0,
      urn: company.urn || `company-${company.name}`
    })) || []
  };

  // Process top performers if available
  if (overview.topPerformers && !normalizedOverview.companies.length) {
    normalizedOverview.companies = overview.topPerformers.map(company => ({
      name: company.name,
      churnRate: 0, // Default for top performers
      netFlow: company.growth || 0,
      employees: company.employees || 0,
      urn: company.urn || `company-${company.name}`
    }));
  }

  const {
    totalCompanies,
    totalEmployees,
    avgChurnRate,
    netTalentFlow,
    companies,
    atRiskCompanies
  } = normalizedOverview;

  return (
    <Box>
      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <MetricCard
            title="Portfolio Companies"
            value={totalCompanies}
            subtitle="Companies tracked"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard
            title="Total Employees"
            value={totalEmployees.toLocaleString()}
            subtitle="Across all companies"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard
            title="Average Churn"
            value={`${avgChurnRate.toFixed(1)}%`}
            subtitle="Last 3 months"
            color={avgChurnRate > 10 ? 'error' : avgChurnRate > 5 ? 'warning' : 'success'}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard
            title="Net Talent Flow"
            value={netTalentFlow > 0 ? `+${netTalentFlow}` : netTalentFlow}
            subtitle="Hires - Departures"
            trend={netTalentFlow}
            color={netTalentFlow > 0 ? 'success' : 'error'}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* At-Risk Companies */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Warning color="warning" sx={{ mr: 1 }} />
              <Typography variant="h6" fontWeight={600}>
                Companies Requiring Attention
              </Typography>
            </Box>
            
            {atRiskCompanies.length > 0 ? (
              <List>
                {atRiskCompanies.map((company, index) => {
                  const churnRate = company.churnRate || company.churn || 0;
                  const netFlow = company.netFlow || 0;
                  const employees = company.employees || 0;
                  
                  return (
                    <React.Fragment key={company.urn || index}>
                      <ListItem sx={{ px: 0 }}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <Typography variant="subtitle2" fontWeight={600}>
                                {company.name}
                              </Typography>
                              <CompanyStatusChip company={company} />
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="caption" display="block">
                                Churn Rate: {churnRate.toFixed(1)}% | 
                                Net Flow: {netFlow > 0 ? '+' : ''}{netFlow} | 
                                Employees: {employees}
                              </Typography>
                              <LinearProgress
                                variant="determinate"
                                value={Math.min(churnRate, 25) * 4}
                                color={churnRate > 15 ? 'error' : 'warning'}
                                sx={{ mt: 1, height: 6, borderRadius: 3 }}
                              />
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < atRiskCompanies.length - 1 && <Divider />}
                    </React.Fragment>
                  );
                })}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                No companies requiring immediate attention
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* All Portfolio Companies */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Portfolio Performance
            </Typography>
            
            {companies.length > 0 ? (
              <List>
                {companies.map((company, index) => {
                  const churnRate = company.churnRate || company.churn || 0;
                  const netFlow = company.netFlow || company.growth || 0;
                  const employees = company.employees || 0;
                  
                  return (
                    <React.Fragment key={company.urn || index}>
                      <ListItem sx={{ px: 0 }}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <Typography variant="subtitle2" fontWeight={600}>
                                {company.name}
                              </Typography>
                              <CompanyStatusChip company={company} />
                            </Box>
                          }
                          secondary={
                            <Grid container spacing={1} sx={{ mt: 0.5 }}>
                              <Grid item xs={4}>
                                <Typography variant="caption" color="text.secondary">
                                  Employees
                                </Typography>
                                <Typography variant="body2" fontWeight={600}>
                                  {employees}
                                </Typography>
                              </Grid>
                              <Grid item xs={4}>
                                <Typography variant="caption" color="text.secondary">
                                  Churn Rate
                                </Typography>
                                <Typography variant="body2" fontWeight={600}>
                                  {churnRate.toFixed(1)}%
                                </Typography>
                              </Grid>
                              <Grid item xs={4}>
                                <Typography variant="caption" color="text.secondary">
                                  Net Flow
                                </Typography>
                                <Typography 
                                  variant="body2" 
                                  fontWeight={600}
                                  color={netFlow > 0 ? 'success.main' : 'error.main'}
                                >
                                  {netFlow > 0 ? '+' : ''}{netFlow}
                                </Typography>
                              </Grid>
                            </Grid>
                          }
                        />
                      </ListItem>
                      {index < companies.length - 1 && <Divider />}
                    </React.Fragment>
                  );
                })}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                No portfolio companies data available
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PortfolioOverview;