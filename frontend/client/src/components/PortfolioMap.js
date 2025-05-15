import React, { useState, useEffect, useRef } from 'react';
import {
  Box, 
  Paper, 
  Typography, 
  ToggleButtonGroup, 
  ToggleButton, 
  Grid, 
  Card, 
  CardContent, 
  Chip, 
  CircularProgress,
  Autocomplete,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Map as MapIcon,
  Share as NetworkIcon,
  Timeline as SankeyIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  Business as CompanyIcon
} from '@mui/icons-material';
import * as d3 from 'd3';
import { useVC } from '../context/VCContext';
import CompanyNetworkGraph from './CompanyNetworkGraph';
import TalentFlowSankey from './TalentFlowSankey';
import api from '../services/api';

// Mock data for initial rendering - replace with actual API calls in production
const MOCK_HEALTH_SCORES = {
  overall: 78,
  funding: 85,
  talent: 72,
  product: 80,
  market: 75
};

const MOCK_FUNDING_STAGES = {
  seed: 15,
  seriesA: 25,
  seriesB: 30,
  seriesC: 20,
  late: 10
};

const PortfolioMap = () => {
  const { state, actions } = useVC();
  const [viewMode, setViewMode] = useState('geographic');
  const [loading, setLoading] = useState(false);
  const [mapData, setMapData] = useState(null);
  const [networkData, setNetworkData] = useState(null);
  const [sankeyData, setSankeyData] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [filterOptions, setFilterOptions] = useState({
    timeRange: 'all',
    fundingStage: 'all',
    industry: 'all'
  });
  const [companies, setCompanies] = useState([]);
  const mapRef = useRef(null);
  
  // Load data on mount and when filters change
  useEffect(() => {
    loadData();
  }, [state.filters, viewMode, filterOptions]);
  
  const loadData = async () => {
    setLoading(true);
    
    try {
      // Load appropriate data based on current view mode
      if (viewMode === 'geographic') {
        await fetchGeographicData();
      } else if (viewMode === 'network') {
        await fetchNetworkData();
      } else if (viewMode === 'sankey') {
        await fetchSankeyData();
      }
      
      // Load companies list
      await fetchCompanies();
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };
  
  const fetchGeographicData = async () => {
    try {
      // Create request parameters
      const params = {
        regions: filterOptions.region !== 'all' ? [filterOptions.region] : null,
        metrics: ["talent_density", "company_density", "avg_salary", "funding_activity"],
        time_period: filterOptions.timeRange
      };
      
      // Call the geographic analysis API using our service
      const data = await api.analytics.getGeographicAnalysis(params);
      
      // Transform API response to map data format
      const companies = [];
      
      // For each region with companies
      data.regions.forEach(region => {
        // Add fake coordinates for visualization - in production you'd use real geo-coordinates
        const lat = region.coordinates ? region.coordinates[1] : Math.random() * 180 - 90;
        const lng = region.coordinates ? region.coordinates[0] : Math.random() * 360 - 180;
        
        // Add as a company marker
        companies.push({
          id: region.id,
          name: region.name,
          lat,
          lng,
          industry: 'Region',
          healthScore: region.metrics.company_density,
          fundingStage: 'N/A',
          employeeCount: region.metrics.talent_density
        });
      });
      
      setMapData({ companies });
    } catch (error) {
      console.error('Error fetching geographic data:', error);
      // Fallback to mock data for development
      const mockMapData = {
        companies: [
          { id: 1, name: 'Company A', lat: 37.7749, lng: -122.4194, industry: 'AI', healthScore: 85, fundingStage: 'Series B', employeeCount: 120 },
          { id: 2, name: 'Company B', lat: 40.7128, lng: -74.0060, industry: 'Fintech', healthScore: 72, fundingStage: 'Series A', employeeCount: 75 },
          { id: 3, name: 'Company C', lat: 47.6062, lng: -122.3321, industry: 'SaaS', healthScore: 90, fundingStage: 'Series C', employeeCount: 230 },
          { id: 4, name: 'Company D', lat: 34.0522, lng: -118.2437, industry: 'Biotech', healthScore: 68, fundingStage: 'Seed', employeeCount: 45 },
          { id: 5, name: 'Company E', lat: 51.5074, lng: -0.1278, industry: 'Cleantech', healthScore: 76, fundingStage: 'Series A', employeeCount: 85 },
        ]
      };
      setMapData(mockMapData);
    }
  };
  
  const fetchNetworkData = async () => {
    try {
      // Set minTransitions parameter
      const minTransitions = 3;
      
      // Call the talent flow network API using our service
      const data = await api.analytics.getTalentFlowNetwork(minTransitions);
      
      // Transform API response to network data format
      const transformedData = {
        nodes: data.nodes.map(node => ({
          id: node.id,
          name: node.name,
          type: node.type || 'company',
          size: 5 + (node.inflow || 0) / 10, // Size based on inflow
          health: node.net_flow > 0 ? 80 : 60 // Health score based on net flow
        })),
        links: data.links.map(link => ({
          source: link.source,
          target: link.target,
          type: 'talent_flow',
          value: link.value
        }))
      };
      
      setNetworkData(transformedData);
    } catch (error) {
      console.error('Error fetching network data:', error);
      // Fallback to mock data for development
      const mockNetworkData = {
        nodes: [
          { id: 1, name: 'Company A', type: 'ai', size: 10, health: 85 },
          { id: 2, name: 'Company B', type: 'fintech', size: 6, health: 72 },
          { id: 3, name: 'Company C', type: 'saas', size: 12, health: 90 },
          { id: 4, name: 'Company D', type: 'biotech', size: 4, health: 68 },
          { id: 5, name: 'Company E', type: 'cleantech', size: 7, health: 76 },
        ],
        links: [
          { source: 1, target: 2, type: 'partnership', value: 3 },
          { source: 2, target: 3, type: 'partnership', value: 2 },
          { source: 3, target: 4, type: 'partnership', value: 4 },
          { source: 4, target: 5, type: 'partnership', value: 2 },
          { source: 5, target: 1, type: 'partnership', value: 3 },
        ]
      };
      setNetworkData(mockNetworkData);
    }
  };
  
  const fetchSankeyData = async () => {
    try {
      // Create request parameters
      const params = {
        company_ids: selectedCompany ? [selectedCompany.id] : null,
        time_period: filterOptions.timeRange,
        min_transitions: 5
      };
      
      // Call the talent flow API using our service
      const data = await api.analytics.analyzeTalentFlow(params);
      
      // Transform API response to Sankey data format
      // The Sankey component expects node IDs starting from 0 and sequential
      // Create a mapping from original IDs to sequential numbers
      const nodeMap = new Map();
      data.nodes.forEach((node, index) => {
        nodeMap.set(node.id, index);
      });
      
      const transformedData = {
        nodes: data.nodes.map((node, index) => ({
          id: index,
          name: node.name
        })),
        links: data.links.map(link => ({
          source: nodeMap.get(link.source),
          target: nodeMap.get(link.target),
          value: link.value
        }))
      };
      
      setSankeyData(transformedData);
    } catch (error) {
      console.error('Error fetching sankey data:', error);
      // Fallback to mock data for development
      const mockSankeyData = {
        nodes: [
          { id: 0, name: 'Company A' },
          { id: 1, name: 'Company B' },
          { id: 2, name: 'Company C' },
          { id: 3, name: 'Company D' },
          { id: 4, name: 'Company E' },
          { id: 5, name: 'Google' },
          { id: 6, name: 'Facebook' },
          { id: 7, name: 'Amazon' },
          { id: 8, name: 'Microsoft' }
        ],
        links: [
          { source: 5, target: 0, value: 15 },
          { source: 5, target: 1, value: 8 },
          { source: 6, target: 0, value: 10 },
          { source: 6, target: 2, value: 12 },
          { source: 7, target: 1, value: 5 },
        ]
      };
      setSankeyData(mockSankeyData);
    }
  };
  
  const fetchCompanies = async () => {
    try {
      // Create filters for VC company search
      const filters = {
        mode: "research",
        industries: filterOptions.industry !== 'all' ? [filterOptions.industry] : null,
        funding_stages: filterOptions.fundingStage !== 'all' ? [filterOptions.fundingStage] : null,
      };
      
      // Call the companies search API using our service
      const data = await api.vc.searchCompanies(filters);
      
      if (data.success && data.companies) {
        // Transform API response to expected format
        const companiesList = data.companies.map(company => ({
          id: company.urn || company.id,
          name: company.name,
          industry: company.industries?.[0] || 'Unknown',
          fundingStage: company.funding_data?.last_funding_round?.funding_type || 'Unknown'
        }));
        
        setCompanies(companiesList);
      }
    } catch (error) {
      console.error('Error fetching companies:', error);
      // Fallback to mock data for development
      const mockCompanies = [
        { id: 1, name: 'Company A', industry: 'AI', fundingStage: 'Series B' },
        { id: 2, name: 'Company B', industry: 'Fintech', fundingStage: 'Series A' },
        { id: 3, name: 'Company C', industry: 'SaaS', fundingStage: 'Series C' },
        { id: 4, name: 'Company D', industry: 'Biotech', fundingStage: 'Seed' },
        { id: 5, name: 'Company E', industry: 'Cleantech', fundingStage: 'Series A' },
      ];
      setCompanies(mockCompanies);
    }
  };
  
  const handleViewModeChange = (event, newMode) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };
  
  const handleCompanySelect = (event, value) => {
    setSelectedCompany(value);
  };
  
  const handleFilterChange = (filterType, value) => {
    setFilterOptions(prev => ({
      ...prev,
      [filterType]: value
    }));
  };
  
  const handleRefresh = () => {
    loadData();
  };
  
  // Initialize geographic map view
  useEffect(() => {
    if (viewMode === 'geographic' && mapData && mapRef.current) {
      // Clear previous map
      d3.select(mapRef.current).selectAll("*").remove();
      
      // This is a simplified map visualization - in production use Mapbox, Leaflet, or D3 Geo
      const width = 800;
      const height = 500;
      
      const svg = d3.select(mapRef.current)
        .attr('width', width)
        .attr('height', height);
        
      // Add world map background - in production use proper geojson/topojson
      svg.append('rect')
        .attr('width', width)
        .attr('height', height)
        .attr('fill', '#f0f8ff');
      
      // Simple x/y projection mapping (not a true geographic projection)
      // In production, use a proper geographic projection
      const projection = d3.scaleLinear()
        .domain([-180, 180])
        .range([0, width]);
        
      const yProjection = d3.scaleLinear()
        .domain([-90, 90])
        .range([height, 0]);
        
      // Size scale for company markers
      const sizeScale = d3.scaleSqrt()
        .domain([0, 250]) // Assuming employee counts from 0-250
        .range([5, 25]);
      
      // Color scale for health scores
      const colorScale = d3.scaleSequential(d3.interpolateRdYlGn)
        .domain([50, 100]);
      
      // Plot company locations
      svg.selectAll('circle')
        .data(mapData.companies)
        .enter()
        .append('circle')
        .attr('cx', d => projection(d.lng))
        .attr('cy', d => yProjection(d.lat))
        .attr('r', d => sizeScale(d.employeeCount))
        .attr('fill', d => colorScale(d.healthScore))
        .attr('opacity', 0.8)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .on('mouseover', function(event, d) {
          d3.select(this)
            .transition()
            .attr('r', sizeScale(d.employeeCount) * 1.3);
            
          // Show tooltip
          const tooltip = d3.select('body').append('div')
            .attr('class', 'map-tooltip')
            .style('position', 'absolute')
            .style('padding', '10px')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', '#fff')
            .style('border-radius', '4px')
            .style('pointer-events', 'none')
            .style('opacity', 0);
            
          tooltip.transition()
            .duration(200)
            .style('opacity', 1);
            
          tooltip.html(`
            <strong>${d.name}</strong><br/>
            Industry: ${d.industry}<br/>
            Funding: ${d.fundingStage}<br/>
            Health Score: ${d.healthScore}/100<br/>
            Team Size: ${d.employeeCount}
          `)
          .style('left', (event.pageX + 15) + 'px')
          .style('top', (event.pageY - 30) + 'px');
        })
        .on('mouseout', function(event, d) {
          d3.select(this)
            .transition()
            .attr('r', sizeScale(d.employeeCount));
            
          d3.selectAll('.map-tooltip').remove();
        });
    }
  }, [viewMode, mapData]);
  
  // Render the appropriate view based on viewMode
  const renderView = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
          <CircularProgress />
        </Box>
      );
    }
    
    switch (viewMode) {
      case 'geographic':
        return (
          <Box sx={{ width: '100%', height: '500px', overflow: 'hidden' }}>
            <svg ref={mapRef} width="100%" height="100%" />
          </Box>
        );
        
      case 'network':
        return (
          <Box sx={{ width: '100%', height: '500px', overflow: 'hidden' }}>
            {networkData && <CompanyNetworkGraph data={networkData} />}
          </Box>
        );
        
      case 'sankey':
        return (
          <Box sx={{ width: '100%', height: '500px', overflow: 'hidden' }}>
            {sankeyData && <TalentFlowSankey data={sankeyData} />}
          </Box>
        );
        
      default:
        return <Typography>Select a view mode to continue</Typography>;
    }
  };
  
  // Helper function to render health score with colored indicator
  const renderHealthScore = (label, score) => {
    let color = '#4caf50'; // green for good scores
    
    if (score < 60) {
      color = '#f44336'; // red for bad scores
    } else if (score < 80) {
      color = '#ff9800'; // orange for medium scores
    }
    
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: color, mr: 1 }} />
        <Typography variant="body2">{label}: </Typography>
        <Typography variant="body2" fontWeight="bold" sx={{ ml: 0.5 }}>{score}</Typography>
      </Box>
    );
  };
  
  // Render the portfolio summary dashboard
  const renderSummaryDashboard = () => {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Health Scores
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {renderHealthScore('Overall Health', MOCK_HEALTH_SCORES.overall)}
                {renderHealthScore('Funding Viability', MOCK_HEALTH_SCORES.funding)}
                {renderHealthScore('Team Quality', MOCK_HEALTH_SCORES.talent)}
                {renderHealthScore('Product Traction', MOCK_HEALTH_SCORES.product)}
                {renderHealthScore('Market Positioning', MOCK_HEALTH_SCORES.market)}
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Portfolio Composition
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip label={`Seed (${MOCK_FUNDING_STAGES.seed}%)`} size="small" />
                  <Chip label={`Series A (${MOCK_FUNDING_STAGES.seriesA}%)`} size="small" />
                  <Chip label={`Series B (${MOCK_FUNDING_STAGES.seriesB}%)`} size="small" />
                  <Chip label={`Series C (${MOCK_FUNDING_STAGES.seriesC}%)`} size="small" />
                  <Chip label={`Late Stage (${MOCK_FUNDING_STAGES.late}%)`} size="small" />
                </Box>
                
                <Typography variant="body2" gutterBottom>
                  Top Industries:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Chip label="AI/ML (28%)" size="small" />
                  <Chip label="Fintech (21%)" size="small" />
                  <Chip label="SaaS (17%)" size="small" />
                  <Chip label="Biotech (14%)" size="small" />
                  <Chip label="Cleantech (10%)" size="small" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Key Metrics
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2">Portfolio Companies:</Typography>
                  <Typography variant="h4">48</Typography>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2">Total Investment:</Typography>
                  <Typography variant="h4">$247M</Typography>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2">Talent Flow (Q3):</Typography>
                  <Typography variant="h4">+18%</Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2">Companies at Risk:</Typography>
                  <Typography variant="h4" color="error">5</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>
    );
  };

  return (
    <Box sx={{ mt: 2 }}>
      {/* Top toolbar with filters and controls */}
      <Paper sx={{ p: 2, mb: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5">Portfolio Map</Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Tooltip title="Refresh data">
              <IconButton onClick={handleRefresh}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="View mode explains the different portfolio visualizations">
              <IconButton>
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={handleViewModeChange}
            aria-label="visualization mode"
          >
            <ToggleButton value="geographic" aria-label="geographic view">
              <MapIcon sx={{ mr: 1 }} />
              Geographic
            </ToggleButton>
            <ToggleButton value="network" aria-label="network view">
              <NetworkIcon sx={{ mr: 1 }} />
              Network
            </ToggleButton>
            <ToggleButton value="sankey" aria-label="sankey view">
              <SankeyIcon sx={{ mr: 1 }} />
              Talent Flow
            </ToggleButton>
          </ToggleButtonGroup>
          
          <Divider orientation="vertical" flexItem />
          
          <Autocomplete
            options={companies}
            getOptionLabel={(option) => option.name}
            sx={{ width: 250 }}
            renderInput={(params) => <TextField {...params} label="Select Company" size="small" />}
            onChange={handleCompanySelect}
            isOptionEqualToValue={(option, value) => option.id === value.id}
          />
          
          <Divider orientation="vertical" flexItem />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={filterOptions.timeRange}
              label="Time Range"
              onChange={(e) => handleFilterChange('timeRange', e.target.value)}
            >
              <MenuItem value="all">All Time</MenuItem>
              <MenuItem value="year">Past Year</MenuItem>
              <MenuItem value="quarter">Past Quarter</MenuItem>
              <MenuItem value="month">Past Month</MenuItem>
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Funding Stage</InputLabel>
            <Select
              value={filterOptions.fundingStage}
              label="Funding Stage"
              onChange={(e) => handleFilterChange('fundingStage', e.target.value)}
            >
              <MenuItem value="all">All Stages</MenuItem>
              <MenuItem value="seed">Seed</MenuItem>
              <MenuItem value="seriesA">Series A</MenuItem>
              <MenuItem value="seriesB">Series B</MenuItem>
              <MenuItem value="seriesC">Series C+</MenuItem>
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Industry</InputLabel>
            <Select
              value={filterOptions.industry}
              label="Industry"
              onChange={(e) => handleFilterChange('industry', e.target.value)}
            >
              <MenuItem value="all">All Industries</MenuItem>
              <MenuItem value="ai">AI/ML</MenuItem>
              <MenuItem value="fintech">Fintech</MenuItem>
              <MenuItem value="saas">SaaS</MenuItem>
              <MenuItem value="biotech">Biotech</MenuItem>
              <MenuItem value="cleantech">Cleantech</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>
      
      {/* Portfolio Summary Dashboard */}
      {renderSummaryDashboard()}
      
      {/* Visualization View */}
      <Paper sx={{ p: 2 }}>
        {renderView()}
      </Paper>
    </Box>
  );
};

export default PortfolioMap;
