import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Grid,
  Divider,
  Chip
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
  BarChart as MetricsIcon,
  CalendarToday as TimeIcon,
  Public as GlobeIcon
} from '@mui/icons-material';
import * as d3 from 'd3';
import { useVC } from '../context/VCContext';
import api from '../services/api';

// Constants for metrics
const METRICS = {
  TALENT_FLOW: 'talent_flow',
  COMPANY_DENSITY: 'company_density',
  AVG_SALARY: 'avg_salary',
  FUNDING_ACTIVITY: 'funding_activity',
  SKILL_DEMAND: 'skill_demand'
};

// Constants for time periods
const TIME_PERIODS = {
  LAST_MONTH: 'last_month',
  LAST_QUARTER: 'last_quarter',
  LAST_YEAR: 'last_year',
  LAST_5_YEARS: 'last_5_years',
  ALL_TIME: 'all_time'
};

// Metric display names and descriptions
const METRIC_INFO = {
  [METRICS.TALENT_FLOW]: {
    name: 'Talent Flow',
    description: 'Movement of employees between companies and regions',
    unit: 'people'
  },
  [METRICS.COMPANY_DENSITY]: {
    name: 'Company Density',
    description: 'Number of companies per square mile/kilometer',
    unit: 'companies'
  },
  [METRICS.AVG_SALARY]: {
    name: 'Average Salary',
    description: 'Average compensation for tech roles',
    unit: 'USD'
  },
  [METRICS.FUNDING_ACTIVITY]: {
    name: 'Funding Activity',
    description: 'Total funding amount in the region',
    unit: 'USD'
  },
  [METRICS.SKILL_DEMAND]: {
    name: 'Skill Demand',
    description: 'Most in-demand skills based on job postings',
    unit: 'demand index'
  }
};

// Color scales for different metrics
const COLOR_SCALES = {
  [METRICS.TALENT_FLOW]: d3.interpolateBlues,
  [METRICS.COMPANY_DENSITY]: d3.interpolateGreens,
  [METRICS.AVG_SALARY]: d3.interpolateOranges,
  [METRICS.FUNDING_ACTIVITY]: d3.interpolatePurples,
  [METRICS.SKILL_DEMAND]: d3.interpolateReds
};

const GeographicHeatmap = () => {
  const { state, actions } = useVC();
  const [loading, setLoading] = useState(false);
  const [geoData, setGeoData] = useState(null);
  const [regionData, setRegionData] = useState([]);
  const [cityData, setCityData] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [selectedCity, setSelectedCity] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [center, setCenter] = useState({ x: 0, y: 0 });
  const [metric, setMetric] = useState(METRICS.TALENT_FLOW);
  const [timePeriod, setTimePeriod] = useState(TIME_PERIODS.LAST_YEAR);
  const [showCities, setShowCities] = useState(true);
  const [detailLevel, setDetailLevel] = useState(2); // 1 = low, 3 = high
  const mapRef = useRef(null);
  const tooltipRef = useRef(null);

  // Load data on mount and when parameters change
  useEffect(() => {
    loadData();
  }, [metric, timePeriod, detailLevel]);

  const loadData = async () => {
    setLoading(true);
    
    try {
      // Fetch World GeoJSON data
      await fetchGeoData();
      
      // Fetch region data based on selected metric and time period
      await fetchRegionData();
      
      // Fetch city data
      await fetchCityData();
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  // Data fetching functions using real APIs
  const fetchGeoData = async () => {
    try {
      // In a production app, you'd load GeoJSON data from a CDN or your own server
      const response = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch GeoJSON: ${response.status}`);
      }
      
      const geoData = await response.json();
      setGeoData(geoData);
    } catch (error) {
      console.error('Error fetching GeoJSON data:', error);
      // Set a simplified mock GeoJSON as fallback
      const mockGeoData = { type: "FeatureCollection", features: [] };
      setGeoData(mockGeoData);
    }
  };

  const fetchRegionData = async () => {
    try {
      // Create request parameters for geographic analysis API
      const params = {
        metrics: [metric], // Use the currently selected metric
        time_period: timePeriod,
      };
      
      // Call the geographic analysis API
      const data = await api.analytics.getGeographicAnalysis(params);
      
      // Use the regions from the API response
      setRegionData(data.regions);
    } catch (error) {
      console.error('Error fetching region data:', error);
      // Fallback to mock data for development
      const mockRegionData = [
        {
          id: "us-ca",
          name: "California",
          coordinates: [-119.4179, 36.7783],
          metrics: {
            [METRICS.TALENT_FLOW]: 8700,
            [METRICS.COMPANY_DENSITY]: 85,
            [METRICS.AVG_SALARY]: 125000,
            [METRICS.FUNDING_ACTIVITY]: 98500000000,
            [METRICS.SKILL_DEMAND]: 92
          },
          details: {
            top_companies: ["Apple", "Google", "Meta", "Netflix"],
            top_skills: ["Machine Learning", "Cloud Computing", "Mobile Development"],
            year_over_year_growth: 5.3
          }
        },
        {
          id: "us-ny",
          name: "New York",
          coordinates: [-74.0060, 40.7128],
          metrics: {
            [METRICS.TALENT_FLOW]: 7200,
            [METRICS.COMPANY_DENSITY]: 78,
            [METRICS.AVG_SALARY]: 118000,
            [METRICS.FUNDING_ACTIVITY]: 72000000000,
            [METRICS.SKILL_DEMAND]: 88
          },
          details: {
            top_companies: ["JPMorgan Chase", "Goldman Sachs", "IBM"],
            top_skills: ["Data Science", "FinTech", "Blockchain"],
            year_over_year_growth: 3.9
          }
        },
        {
          id: "gb-lon",
          name: "London",
          coordinates: [-0.1278, 51.5074],
          metrics: {
            [METRICS.TALENT_FLOW]: 5500,
            [METRICS.COMPANY_DENSITY]: 62,
            [METRICS.AVG_SALARY]: 95000,
            [METRICS.FUNDING_ACTIVITY]: 42000000000,
            [METRICS.SKILL_DEMAND]: 85
          },
          details: {
            top_companies: ["DeepMind", "Revolut", "Monzo"],
            top_skills: ["AI", "FinTech", "Data Analytics"],
            year_over_year_growth: 4.1
          }
        }
      ];
      
      setRegionData(mockRegionData);
    }
  };

  const fetchCityData = async () => {
    try {
      // Get geographic talent density data
      const data = await api.analytics.getGeographicTalentDensity();
      
      // Transform the API response to match our expected format
      const cityData = data.map(item => {
        // Create a default metrics object
        const metrics = {
          [METRICS.TALENT_FLOW]: 0,
          [METRICS.COMPANY_DENSITY]: 0,
          [METRICS.AVG_SALARY]: 0,
          [METRICS.FUNDING_ACTIVITY]: 0,
          [METRICS.SKILL_DEMAND]: 0
        };
        
        // Set the talent flow metric from the API data
        metrics[METRICS.TALENT_FLOW] = item.talent_count || 0;
        
        // Extract lat/lng if available, otherwise assign placeholders
        const lat = item.lat || (Math.random() * 180 - 90);
        const lng = item.lng || (Math.random() * 360 - 180);
        
        return {
          id: `city-${item.location.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`,
          name: item.location,
          coordinates: [lng, lat],
          metrics: metrics
        };
      });
      
      setCityData(cityData);
    } catch (error) {
      console.error('Error fetching city data:', error);
      // Fallback to mock data for development
      const mockCityData = [
        {
          id: "us-sfo",
          name: "San Francisco",
          coordinates: [-122.4194, 37.7749],
          metrics: {
            [METRICS.TALENT_FLOW]: 4200,
            [METRICS.COMPANY_DENSITY]: 92,
            [METRICS.AVG_SALARY]: 145000,
            [METRICS.FUNDING_ACTIVITY]: 45000000000,
            [METRICS.SKILL_DEMAND]: 95
          }
        },
        {
          id: "us-nyc",
          name: "New York City",
          coordinates: [-74.0060, 40.7128],
          metrics: {
            [METRICS.TALENT_FLOW]: 3800,
            [METRICS.COMPANY_DENSITY]: 85,
            [METRICS.AVG_SALARY]: 135000,
            [METRICS.FUNDING_ACTIVITY]: 38000000000,
            [METRICS.SKILL_DEMAND]: 90
          }
        },
        {
          id: "us-bos",
          name: "Boston",
          coordinates: [-71.0589, 42.3601],
          metrics: {
            [METRICS.TALENT_FLOW]: 2100,
            [METRICS.COMPANY_DENSITY]: 75,
            [METRICS.AVG_SALARY]: 125000,
            [METRICS.FUNDING_ACTIVITY]: 22000000000,
            [METRICS.SKILL_DEMAND]: 87
          }
        }
      ];
      
      setCityData(mockCityData);
    }
  };

  // Event handlers
  const handleMetricChange = (event) => {
    setMetric(event.target.value);
  };

  const handleTimePeriodChange = (event) => {
    setTimePeriod(event.target.value);
  };

  const handleRegionClick = (region) => {
    setSelectedRegion(region);
    setCenter({ x: region.coordinates[0], y: region.coordinates[1] });
    setZoom(4);
  };

  const handleCityClick = (city) => {
    setSelectedCity(city);
  };

  const handleZoomIn = () => {
    setZoom(Math.min(zoom * 1.5, 10));
  };

  const handleZoomOut = () => {
    setZoom(Math.max(zoom / 1.5, 1));
  };

  const handleDetailLevelChange = (event, newValue) => {
    setDetailLevel(newValue);
  };

  const handleToggleCities = () => {
    setShowCities(!showCities);
  };

  const handleReset = () => {
    setZoom(1);
    setCenter({ x: 0, y: 0 });
    setSelectedRegion(null);
    setSelectedCity(null);
  };

  // Setup D3 visualization when data changes
  useEffect(() => {
    if (mapRef.current && regionData.length > 0) {
      renderMap();
    }
  }, [regionData, cityData, metric, zoom, center, showCities, detailLevel]);

  // Helper function to format metric values
  const formatMetricValue = (value, metricType) => {
    if (metricType === METRICS.AVG_SALARY) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
      }).format(value);
    } else if (metricType === METRICS.FUNDING_ACTIVITY) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        compactDisplay: 'short',
        maximumFractionDigits: 1
      }).format(value);
    } else if (metricType === METRICS.COMPANY_DENSITY) {
      return `${value} / km²`;
    } else if (metricType === METRICS.SKILL_DEMAND) {
      return `${value}/100`;
    } else {
      return value.toLocaleString();
    }
  };

  // D3 rendering function
  const renderMap = () => {
    // Clear existing map
    d3.select(mapRef.current).selectAll("*").remove();

    const width = 900;
    const height = 500;
    
    // Setup SVG
    const svg = d3.select(mapRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .style("width", "100%")
      .style("height", "auto");
    
    // Setup projection
    // In a real implementation, we would use a proper geographic projection
    // For this mock, we use a simple scale
    const projection = d3.geoMercator()
      .scale(100 * zoom)
      .center([center.x, center.y])
      .translate([width / 2, height / 2]);
    
    // Create a group for zoom/pan
    const g = svg.append("g");
    
    // Setup colors
    const colorScale = d3.scaleSequential(COLOR_SCALES[metric])
      .domain(d3.extent(regionData, d => d.metrics[metric]));
    
    // Draw base map (world or countries)
    // In a real implementation, we would use GeoJSON data
    g.append("rect")
      .attr("width", width)
      .attr("height", height)
      .attr("fill", "#f0f8ff");
    
    // Draw regions - would be based on GeoJSON in real implementation
    g.selectAll(".region")
      .data(regionData)
      .enter()
      .append("circle")
      .attr("class", "region")
      .attr("cx", d => projection(d.coordinates)[0])
      .attr("cy", d => projection(d.coordinates)[1])
      .attr("r", 15 * Math.sqrt(detailLevel))
      .attr("fill", d => colorScale(d.metrics[metric]))
      .attr("stroke", "#fff")
      .attr("stroke-width", 1)
      .attr("opacity", 0.8)
      .on("mouseover", function(event, d) {
        d3.select(this)
          .transition()
          .attr("opacity", 1)
          .attr("stroke-width", 2);
        
        showTooltip(event, d);
      })
      .on("mouseout", function() {
        d3.select(this)
          .transition()
          .attr("opacity", 0.8)
          .attr("stroke-width", 1);
        
        hideTooltip();
      })
      .on("click", function(event, d) {
        handleRegionClick(d);
      });
    
    // Draw cities if enabled
    if (showCities) {
      g.selectAll(".city")
        .data(cityData)
        .enter()
        .append("circle")
        .attr("class", "city")
        .attr("cx", d => projection(d.coordinates)[0])
        .attr("cy", d => projection(d.coordinates)[1])
        .attr("r", 5 * Math.sqrt(detailLevel))
        .attr("fill", d => colorScale(d.metrics[metric]))
        .attr("stroke", "#000")
        .attr("stroke-width", 1)
        .attr("opacity", 0.9)
        .on("mouseover", function(event, d) {
          d3.select(this)
            .transition()
            .attr("r", 7 * Math.sqrt(detailLevel))
            .attr("stroke-width", 2);
          
          showTooltip(event, d);
        })
        .on("mouseout", function() {
          d3.select(this)
            .transition()
            .attr("r", 5 * Math.sqrt(detailLevel))
            .attr("stroke-width", 1);
          
          hideTooltip();
        })
        .on("click", function(event, d) {
          handleCityClick(d);
        });
      
      // Add city labels
      if (detailLevel >= 2) {
        g.selectAll(".city-label")
          .data(cityData)
          .enter()
          .append("text")
          .attr("class", "city-label")
          .attr("x", d => projection(d.coordinates)[0])
          .attr("y", d => projection(d.coordinates)[1] - 10)
          .attr("text-anchor", "middle")
          .attr("font-size", `${8 + detailLevel}px`)
          .attr("fill", "#000")
          .text(d => d.name);
      }
    }
    
    // Add legend
    const legendWidth = 250;
    const legendHeight = 50;
    
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${width - legendWidth - 20}, ${height - legendHeight - 20})`);
    
    // Add legend title
    legend.append("text")
      .attr("x", 0)
      .attr("y", 0)
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .text(`${METRIC_INFO[metric].name} (${METRIC_INFO[metric].unit})`);
    
    // Create gradient for legend
    const defs = svg.append("defs");
    
    const gradient = defs.append("linearGradient")
      .attr("id", "legend-gradient")
      .attr("x1", "0%")
      .attr("x2", "100%")
      .attr("y1", "0%")
      .attr("y2", "0%");
    
    // Set the gradient colors
    gradient.append("stop")
      .attr("offset", "0%")
      .attr("stop-color", colorScale.range()[0]);
    
    gradient.append("stop")
      .attr("offset", "100%")
      .attr("stop-color", colorScale.range()[1]);
    
    // Draw the colored rectangle
    legend.append("rect")
      .attr("x", 0)
      .attr("y", 10)
      .attr("width", legendWidth)
      .attr("height", 15)
      .style("fill", "url(#legend-gradient)");
    
    // Add tick marks and labels
    const legendScale = d3.scaleLinear()
      .domain(colorScale.domain())
      .range([0, legendWidth]);
    
    const legendAxis = d3.axisBottom(legendScale)
      .ticks(5)
      .tickFormat(d => formatMetricValue(d, metric));
    
    legend.append("g")
      .attr("transform", `translate(0, 25)`)
      .call(legendAxis);
  };

  // Tooltip handlers
  const showTooltip = (event, d) => {
    const tooltip = d3.select("body").append("div")
      .attr("class", "map-tooltip")
      .style("position", "absolute")
      .style("padding", "10px")
      .style("background", "rgba(0, 0, 0, 0.8)")
      .style("color", "#fff")
      .style("border-radius", "4px")
      .style("pointer-events", "none")
      .style("font-size", "12px")
      .style("z-index", 1000)
      .style("opacity", 0);
    
    tooltip.transition()
      .duration(200)
      .style("opacity", 1);
    
    const metricValue = formatMetricValue(d.metrics[metric], metric);
    
    // Different tooltip content for regions vs cities
    if (d.details) {
      // It's a region
      tooltip.html(`
        <strong>${d.name}</strong><br/>
        ${METRIC_INFO[metric].name}: ${metricValue}<br/>
        YoY Growth: ${d.details.year_over_year_growth}%<br/>
        <br/>
        <em>Click for details</em>
      `);
    } else {
      // It's a city
      tooltip.html(`
        <strong>${d.name}</strong><br/>
        ${METRIC_INFO[metric].name}: ${metricValue}<br/>
        <br/>
        <em>Click for details</em>
      `);
    }
    
    tooltip.style("left", (event.pageX + 15) + "px")
      .style("top", (event.pageY - 30) + "px");
    
    tooltipRef.current = tooltip;
  };

  const hideTooltip = () => {
    if (tooltipRef.current) {
      tooltipRef.current.transition()
        .duration(200)
        .style("opacity", 0)
        .remove();
    }
  };

  // Render region detail panel
  const renderRegionDetail = () => {
    if (!selectedRegion) return null;
    
    const region = selectedRegion;
    const metricValue = formatMetricValue(region.metrics[metric], metric);
    
    return (
      <Paper sx={{ p: 2, mt: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">{region.name} Details</Typography>
          <IconButton size="small" onClick={() => setSelectedRegion(null)}>
            <InfoIcon fontSize="small" />
          </IconButton>
        </Box>
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>Key Metrics</Typography>
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {METRIC_INFO[metric].name}
                  </Typography>
                  <Typography variant="h5">{metricValue}</Typography>
                </Box>
                
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Year-over-year Growth
                  </Typography>
                  <Typography variant="h5">{region.details.year_over_year_growth}%</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>Top Companies</Typography>
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {region.details.top_companies.map((company, index) => (
                    <Chip key={index} label={company} size="small" />
                  ))}
                </Box>
                
                <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
                  Top Skills in Demand
                </Typography>
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {region.details.top_skills.map((skill, index) => (
                    <Chip key={index} label={skill} size="small" />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>
    );
  };

  // Render UI controls
  const renderControls = () => {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Metric</InputLabel>
              <Select value={metric} onChange={handleMetricChange} label="Metric">
                <MenuItem value={METRICS.TALENT_FLOW}>Talent Flow</MenuItem>
                <MenuItem value={METRICS.COMPANY_DENSITY}>Company Density</MenuItem>
                <MenuItem value={METRICS.AVG_SALARY}>Average Salary</MenuItem>
                <MenuItem value={METRICS.FUNDING_ACTIVITY}>Funding Activity</MenuItem>
                <MenuItem value={METRICS.SKILL_DEMAND}>Skill Demand</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Time Period</InputLabel>
              <Select value={timePeriod} onChange={handleTimePeriodChange} label="Time Period">
                <MenuItem value={TIME_PERIODS.LAST_MONTH}>Last Month</MenuItem>
                <MenuItem value={TIME_PERIODS.LAST_QUARTER}>Last Quarter</MenuItem>
                <MenuItem value={TIME_PERIODS.LAST_YEAR}>Last Year</MenuItem>
                <MenuItem value={TIME_PERIODS.LAST_5_YEARS}>Last 5 Years</MenuItem>
                <MenuItem value={TIME_PERIODS.ALL_TIME}>All Time</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ mr: 2 }}>
                Detail Level:
              </Typography>
              <Slider
                value={detailLevel}
                min={1}
                max={3}
                step={1}
                marks
                onChange={handleDetailLevelChange}
                sx={{ ml: 1 }}
              />
            </Box>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Tooltip title="Zoom In">
                <IconButton onClick={handleZoomIn}>
                  <ZoomInIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Zoom Out">
                <IconButton onClick={handleZoomOut}>
                  <ZoomOutIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Toggle Cities">
                <IconButton onClick={handleToggleCities} color={showCities ? "primary" : "default"}>
                  <GlobeIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Reset View">
                <IconButton onClick={handleReset}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    );
  };

  // Render metric info panel
  const renderMetricInfo = () => {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          {METRIC_INFO[metric].name}
        </Typography>
        
        <Typography variant="body2" color="text.secondary">
          {METRIC_INFO[metric].description}
        </Typography>
        
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2">
            Currently showing data for: <strong>{
              timePeriod === TIME_PERIODS.LAST_MONTH ? 'Last Month' :
              timePeriod === TIME_PERIODS.LAST_QUARTER ? 'Last Quarter' :
              timePeriod === TIME_PERIODS.LAST_YEAR ? 'Last Year' :
              timePeriod === TIME_PERIODS.LAST_5_YEARS ? 'Last 5 Years' : 'All Time'
            }</strong>
          </Typography>
        </Box>
      </Paper>
    );
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h5">Geographic Analysis</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Visualize spatial patterns of talent, funding, and company growth
        </Typography>
      </Paper>
      
      {/* Controls */}
      {renderControls()}
      
      {/* Metric information */}
      {renderMetricInfo()}
      
      {/* Main visualization */}
      <Paper sx={{ p: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '500px' }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ width: '100%', height: '500px', overflow: 'hidden' }}>
            <svg ref={mapRef} width="100%" height="100%" />
          </Box>
        )}
      </Paper>
      
      {/* Selected region details */}
      {selectedRegion && renderRegionDetail()}
    </Box>
  );
};

export default GeographicHeatmap;
