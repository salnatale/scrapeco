import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Alert,
  AlertTitle,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Tabs,
  Tab,
  Badge,
  Switch,
  FormControlLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider
} from '@mui/material';
import {
  Warning,
  TrendingUp,
  TrendingDown,
  Notifications,
  NotificationsActive,
  Close,
  Add,
  Edit,
  Delete,
  CheckCircle,
  Schedule,
  Business,
  People,
  Analytics,
  Settings,
  Refresh
} from '@mui/icons-material';

const AlertsDashboard = ({ portfolioCompanies = [] }) => {
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [alertConfigs, setAlertConfigs] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [loading, setLoading] = useState(false);

  // New alert form state
  const [newAlert, setNewAlert] = useState({
    alert_type: 'talent_drain',
    threshold: 2.0,
    company_urns: [],
    enabled: true,
    name: '',
    description: ''
  });

  // Mock alert types with descriptions
  const alertTypes = {
    talent_drain: {
      label: 'Talent Drain',
      description: 'Triggers when outflow exceeds inflow by specified ratio',
      icon: <TrendingDown color="error" />,
      defaultThreshold: 2.0,
      unit: 'ratio'
    },
    high_growth: {
      label: 'High Growth',
      description: 'Triggers when hiring velocity exceeds threshold',
      icon: <TrendingUp color="success" />,
      defaultThreshold: 20,
      unit: 'hires/90d'
    },
    competitor_move: {
      label: 'Competitor Activity',
      description: 'Monitors talent movement to/from competitors',
      icon: <Business color="warning" />,
      defaultThreshold: 5,
      unit: 'transitions'
    },
    score_drop: {
      label: 'Score Drop',
      description: 'Alerts on significant composite score decreases',
      icon: <Analytics color="info" />,
      defaultThreshold: 0.2,
      unit: 'points'
    }
  };

  // Simulated active alerts
  useEffect(() => {
    // Simulate fetching active alerts
    setActiveAlerts([
      {
        id: '1',
        alert_type: 'talent_drain',
        company_urn: 'urn:li:company:123',
        company_name: 'TechCorp',
        metric_value: 3.2,
        threshold: 2.0,
        triggered_at: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        message: 'High talent drain detected: 3.2x more outflow than inflow',
        severity: 'high'
      },
      {
        id: '2',
        alert_type: 'high_growth',
        company_urn: 'urn:li:company:456',
        company_name: 'StartupXYZ',
        metric_value: 25,
        threshold: 20,
        triggered_at: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
        message: 'High growth detected: 25 hires in last 90 days',
        severity: 'medium'
      },
      {
        id: '3',
        alert_type: 'score_drop',
        company_urn: 'urn:li:company:789',
        company_name: 'Enterprise Solutions',
        metric_value: 0.25,
        threshold: 0.2,
        triggered_at: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
        message: 'Composite score dropped by 0.25 points',
        severity: 'low'
      }
    ]);

    // Simulate fetching alert configurations
    setAlertConfigs([
      {
        id: 'config1',
        name: 'Portfolio Talent Drain Monitor',
        alert_type: 'talent_drain',
        threshold: 2.0,
        company_urns: [],
        enabled: true,
        created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        triggered_count: 3,
        description: 'Monitors all portfolio companies for talent drain'
      },
      {
        id: 'config2',
        name: 'Growth Company Tracking',
        alert_type: 'high_growth',
        threshold: 20,
        company_urns: ['urn:li:company:456', 'urn:li:company:789'],
        enabled: true,
        created_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
        triggered_count: 1,
        description: 'Tracks hiring velocity for high-growth companies'
      }
    ]);
  }, []);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const formatTimeAgo = (date) => {
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return 'Just now';
  };

  const handleCreateAlert = async () => {
    setLoading(true);
    try {
      // Simulate API call
      const alertConfig = {
        ...newAlert,
        id: `config${alertConfigs.length + 1}`,
        created_at: new Date(),
        triggered_count: 0
      };
      
      setAlertConfigs(prev => [...prev, alertConfig]);
      setCreateDialogOpen(false);
      setNewAlert({
        alert_type: 'talent_drain',
        threshold: 2.0,
        company_urns: [],
        enabled: true,
        name: '',
        description: ''
      });
    } catch (error) {
      console.error('Error creating alert:', error);
    }
    setLoading(false);
  };

  const handleEditAlert = (alert) => {
    setSelectedAlert(alert);
    setEditDialogOpen(true);
  };

  const handleDeleteAlert = (alertId) => {
    setAlertConfigs(prev => prev.filter(alert => alert.id !== alertId));
  };

  const handleDismissAlert = (alertId) => {
    setActiveAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const handleToggleAlert = (alertId, enabled) => {
    setAlertConfigs(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, enabled } : alert
    ));
  };

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );

  return (
    <Box>
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={selectedTab} onChange={(e, value) => setSelectedTab(value)}>
            <Tab 
              label={
                <Badge badgeContent={activeAlerts.length} color="error">
                  Active Alerts
                </Badge>
              }
              icon={<NotificationsActive />}
            />
            <Tab 
              label="Alert Configuration"
              icon={<Settings />}
            />
            <Tab 
              label="Alert History"
              icon={<Schedule />}
            />
          </Tabs>
        </Box>

        <TabPanel value={selectedTab} index={0}>
          {/* Active Alerts */}
          <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5">Active Alerts</Typography>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={() => window.location.reload()}
              >
                Refresh
              </Button>
            </Box>

            {activeAlerts.length === 0 ? (
              <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'success.light' }}>
                <CheckCircle sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography variant="h6" color="success.main">
                  No Active Alerts
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  All your portfolio companies are performing within expected parameters.
                </Typography>
              </Paper>
            ) : (
              <Grid container spacing={2}>
                {activeAlerts.map((alert) => (
                  <Grid item xs={12} md={6} key={alert.id}>
                    <Alert 
                      severity={getSeverityColor(alert.severity)}
                      variant="outlined"
                      action={
                        <IconButton
                          color="inherit"
                          size="small"
                          onClick={() => handleDismissAlert(alert.id)}
                        >
                          <Close fontSize="inherit" />
                        </IconButton>
                      }
                    >
                      <AlertTitle>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {alertTypes[alert.alert_type]?.icon}
                          {alertTypes[alert.alert_type]?.label}
                        </Box>
                      </AlertTitle>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>{alert.company_name}</strong>
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        {alert.message}
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                        <Chip
                          label={`${alert.metric_value} (threshold: ${alert.threshold})`}
                          size="small"
                          color={getSeverityColor(alert.severity)}
                          variant="outlined"
                        />
                        <Typography variant="caption" color="text.secondary">
                          {formatTimeAgo(alert.triggered_at)}
                        </Typography>
                      </Box>
                    </Alert>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={selectedTab} index={1}>
          {/* Alert Configuration */}
          <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h5">Alert Configuration</Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create Alert
              </Button>
            </Box>

            <List>
              {alertConfigs.map((config, index) => (
                <React.Fragment key={config.id}>
                  <ListItem>
                    <ListItemIcon>
                      {alertTypes[config.alert_type]?.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1">
                            {config.name || alertTypes[config.alert_type]?.label}
                          </Typography>
                          <Chip
                            label={config.enabled ? 'Active' : 'Disabled'}
                            size="small"
                            color={config.enabled ? 'success' : 'default'}
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {config.description || alertTypes[config.alert_type]?.description}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Threshold: {config.threshold} {alertTypes[config.alert_type]?.unit} | 
                            Triggered: {config.triggered_count} times | 
                            Created: {config.created_at.toLocaleDateString()}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Switch
                          checked={config.enabled}
                          onChange={(e) => handleToggleAlert(config.id, e.target.checked)}
                          size="small"
                        />
                        <IconButton
                          edge="end"
                          onClick={() => handleEditAlert(config)}
                          size="small"
                        >
                          <Edit />
                        </IconButton>
                        <IconButton
                          edge="end"
                          onClick={() => handleDeleteAlert(config.id)}
                          size="small"
                          color="error"
                        >
                          <Delete />
                        </IconButton>
                      </Box>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < alertConfigs.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>

            {alertConfigs.length === 0 && (
              <Paper sx={{ p: 3, textAlign: 'center' }}>
                <Notifications sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No Alerts Configured
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Set up alerts to monitor your portfolio companies automatically.
                </Typography>
                <Button
                  variant="outlined"
                  onClick={() => setCreateDialogOpen(true)}
                >
                  Create Your First Alert
                </Button>
              </Paper>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={selectedTab} index={2}>
          {/* Alert History */}
          <Box sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>Alert History</Typography>
            <Typography variant="body2" color="text.secondary">
              Historical alert data will be displayed here. This feature shows past triggered alerts,
              their resolution status, and trend analysis.
            </Typography>
          </Box>
        </TabPanel>
      </Paper>

      {/* Create Alert Dialog */}
      <Dialog 
        open={createDialogOpen} 
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Alert</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Alert Name"
              value={newAlert.name}
              onChange={(e) => setNewAlert(prev => ({ ...prev, name: e.target.value }))}
              fullWidth
              placeholder="e.g., Portfolio Talent Monitoring"
            />

            <TextField
              label="Description"
              value={newAlert.description}
              onChange={(e) => setNewAlert(prev => ({ ...prev, description: e.target.value }))}
              fullWidth
              multiline
              rows={2}
              placeholder="Describe what this alert monitors..."
            />

            <FormControl fullWidth>
              <InputLabel>Alert Type</InputLabel>
              <Select
                value={newAlert.alert_type}
                label="Alert Type"
                onChange={(e) => setNewAlert(prev => ({ 
                  ...prev, 
                  alert_type: e.target.value,
                  threshold: alertTypes[e.target.value]?.defaultThreshold || 1
                }))}
              >
                {Object.entries(alertTypes).map(([key, type]) => (
                  <MenuItem key={key} value={key}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {type.icon}
                      <Box>
                        <Typography variant="body1">{type.label}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {type.description}
                        </Typography>
                      </Box>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label={`Threshold (${alertTypes[newAlert.alert_type]?.unit})`}
              type="number"
              value={newAlert.threshold}
              onChange={(e) => setNewAlert(prev => ({ ...prev, threshold: parseFloat(e.target.value) }))}
              fullWidth
              step={0.1}
            />

            <FormControl fullWidth>
              <InputLabel>Monitor Companies</InputLabel>
              <Select
                multiple
                value={newAlert.company_urns}
                label="Monitor Companies"
                onChange={(e) => setNewAlert(prev => ({ ...prev, company_urns: e.target.value }))}
                renderValue={(selected) => 
                  selected.length === 0 ? 'All Portfolio Companies' :
                  `${selected.length} companies selected`
                }
              >
                <MenuItem value="">
                  <em>All Portfolio Companies</em>
                </MenuItem>
                {portfolioCompanies.map((company) => (
                  <MenuItem key={company.company_urn} value={company.company_urn}>
                    {company.company_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={newAlert.enabled}
                  onChange={(e) => setNewAlert(prev => ({ ...prev, enabled: e.target.checked }))}
                />
              }
              label="Enable alert immediately"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateAlert}
            variant="contained"
            disabled={loading || !newAlert.name}
          >
            {loading ? 'Creating...' : 'Create Alert'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AlertsDashboard;