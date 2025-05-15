import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Avatar,
  Paper,
  LinearProgress,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  IconButton,
  Button,
  Stack
} from '@mui/material';
import {
  Business,
  TrendingUp,
  TrendingDown,
  People,
  School,
  LocationOn,
  ArrowForward,
  ArrowBack,
  Warning,
  CheckCircle
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
         BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

const CompanyDeepDive = ({ companyId, onNavigateToCompany, onClose }) => {
  const [company, setCompany] = useState(null);
  const [talentFlow, setTalentFlow] = useState(null);
  const [transitions, setTransitions] = useState([]);
  const [keyEmployees, setKeyEmployees] = useState([]);
  const [skillTrends, setSkillTrends] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1Y');

  useEffect(() => {
    if (companyId) {
      fetchCompanyData();
    }
  }, [companyId, timeRange]);

  const fetchCompanyData = async () => {
    setLoading(true);
    try {
      // Fetch company details
      const companyResponse = await fetch(`/api/company/${companyId}`);
      const companyData = await companyResponse.json();
      setCompany(companyData);

      // Fetch talent flow data
      const talentFlowResponse = await fetch(`/api/company/${companyId}/talent-flow?period=P${timeRange}`);
      const talentFlowData = await talentFlowResponse.json();
      setTalentFlow(talentFlowData);

      // Fetch recent transitions
      const transitionsResponse = await fetch(`/api/company/${companyId}/transitions?limit=20`);
      const transitionsData = await transitionsResponse.json();
      setTransitions(transitionsData);

      // Fetch key employees
      const employeesResponse = await fetch(`/api/company/${companyId}/key-employees`);
      const employeesData = await employeesResponse.json();
      setKeyEmployees(employeesData);

      // Fetch skill trends
      const skillsResponse = await fetch(`/api/company/${companyId}/skill-trends`);
      const skillsData = await skillsResponse.json();
      setSkillTrends(skillsData);
    } catch (error) {
      console.error('Error fetching company data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num);
  };

  const getHealthScoreColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getHealthScoreIcon = (score) => {
    if (score >= 80) return <CheckCircle color="success" />;
    if (score >= 60) return <Warning color="warning" />;
    return <Warning color="error" />;
  };

  const renderOverviewTab = () => (
    <Grid container spacing={3}>
      {/* Company Health Score */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Company Health Score
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              {getHealthScoreIcon(company?.healthScore || 0)}
              <Typography variant="h3" sx={{ ml: 1 }}>
                {company?.healthScore || 0}
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={company?.healthScore || 0}
              color={getHealthScoreColor(company?.healthScore || 0)}
              sx={{ height: 10, borderRadius: 5 }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Based on talent flow, growth metrics, and market position
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* Key Metrics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Key Metrics
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {formatNumber(company?.employeeCount || 0)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Employees
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="primary">
                    {company?.fundingRound || 'N/A'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Latest Round
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="success.main">
                    {talentFlow?.incomingTransitions || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Joined ({timeRange})
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color="error.main">
                    {talentFlow?.outgoingTransitions || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Left ({timeRange})
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Industry & Location */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Company Details
            </Typography>
            <Stack spacing={2}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Business sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography>{company?.industry || 'N/A'}</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <LocationOn sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography>{company?.headquarters || 'N/A'}</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUp sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography>Founded {company?.foundedYear || 'N/A'}</Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Top Skills */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Top Skills at Company
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {skillTrends.slice(0, 8).map((skill, index) => (
                <Chip
                  key={skill.name}
                  label={`${skill.name} (${skill.count})`}
                  variant="outlined"
                  color="primary"
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderTalentFlowTab = () => (
    <Grid container spacing={3}>
      {/* Talent Flow Chart */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Talent Flow Trends
            </Typography>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={talentFlow?.monthlyTrends || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="incoming" 
                    stroke="#2e7d32" 
                    strokeWidth={2}
                    name="Joined"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="outgoing" 
                    stroke="#d32f2f" 
                    strokeWidth={2}
                    name="Left"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Source & Destination Companies */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Top Source Companies
            </Typography>
            <List>
              {talentFlow?.topSourceCompanies?.slice(0, 5).map((source, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'primary.main' }}>
                      <Business />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={source.company}
                    secondary={`${source.count} transitions`}
                  />
                  <IconButton onClick={() => onNavigateToCompany(source.companyId)}>
                    <ArrowForward />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Top Destination Companies
            </Typography>
            <List>
              {talentFlow?.topDestinationCompanies?.slice(0, 5).map((dest, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'secondary.main' }}>
                      <Business />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={dest.company}
                    secondary={`${dest.count} transitions`}
                  />
                  <IconButton onClick={() => onNavigateToCompany(dest.companyId)}>
                    <ArrowForward />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderPeopleTab = () => (
    <Grid container spacing={3}>
      {/* Key Employees */}
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Key Employees
            </Typography>
            <List>
              {keyEmployees.map((employee, index) => (
                <React.Fragment key={employee.id}>
                  <ListItem>
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: 'primary.main' }}>
                        <People />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={employee.name}
                      secondary={
                        <Box>
                          <Typography variant="body2">{employee.title}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {employee.tenure} • {employee.previousCompany && `Previously at ${employee.previousCompany}`}
                          </Typography>
                        </Box>
                      }
                    />
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="body2" color="primary">
                        {employee.influenceScore}/100
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Influence Score
                      </Typography>
                    </Box>
                  </ListItem>
                  {index < keyEmployees.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>

      {/* Recent Transitions */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Transitions
            </Typography>
            <List>
              {transitions.slice(0, 10).map((transition, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {transition.type === 'incoming' ? (
                          <TrendingUp color="success" sx={{ mr: 1 }} />
                        ) : (
                          <TrendingDown color="error" sx={{ mr: 1 }} />
                        )}
                        <Typography variant="body2">
                          {transition.name}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Typography variant="caption">
                        {transition.title} • {transition.date}
                      </Typography>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <Typography>Loading company data...</Typography>
      </Box>
    );
  }

  if (!company) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <Typography>Company not found</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={onClose} sx={{ mr: 2 }}>
          <ArrowBack />
        </IconButton>
        <Avatar 
          src={company.logoUrl} 
          sx={{ width: 64, height: 64, mr: 2 }}
        >
          <Business />
        </Avatar>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" gutterBottom>
            {company.name}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {company.description}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {['3M', '6M', '1Y', '2Y'].map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? 'contained' : 'outlined'}
              size="small"
              onClick={() => setTimeRange(range)}
            >
              {range}
            </Button>
          ))}
        </Box>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="Talent Flow" />
          <Tab label="People" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && renderOverviewTab()}
      {activeTab === 1 && renderTalentFlowTab()}
      {activeTab === 2 && renderPeopleTab()}
    </Box>
  );
};

export default CompanyDeepDive;