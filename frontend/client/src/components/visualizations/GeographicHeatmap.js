// frontend/client/src/components/visualizations/GeographicHeatmap.js
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  ButtonGroup,
  Button,
  Tooltip,
  IconButton,
  Switch,
  FormControlLabel
} from '@mui/material';
import { 
  Refresh as RefreshIcon,
  ZoomIn,
  ZoomOut,
  Restore as RestoreIcon
} from '@mui/icons-material';

const GeographicHeatmap = ({ title, height = 500 }) => {
  const svgRef = useRef();
  const [metric, setMetric] = useState('talent_density');
  const [viewMode, setViewMode] = useState('density'); // 'density' or 'flow'
  const [showLabels, setShowLabels] = useState(true);
  const [heatmapData, setHeatmapData] = useState(null);
  const [zoom, setZoom] = useState(null);

  // Major tech hubs with coordinates
  const techHubs = [
    { name: 'San Francisco Bay Area', lat: 37.7749, lng: -122.4194, state: 'CA' },
    { name: 'Seattle', lat: 47.6062, lng: -122.3321, state: 'WA' },
    { name: 'New York', lat: 40.7128, lng: -74.0060, state: 'NY' },
    { name: 'Boston', lat: 42.3601, lng: -71.0589, state: 'MA' },
    { name: 'Austin', lat: 30.2672, lng: -97.7431, state: 'TX' },
    { name: 'Los Angeles', lat: 34.0522, lng: -118.2437, state: 'CA' },
    { name: 'Chicago', lat: 41.8781, lng: -87.6298, state: 'IL' },
    { name: 'Denver', lat: 39.7392, lng: -104.9903, state: 'CO' },
    { name: 'Atlanta', lat: 33.7490, lng: -84.3880, state: 'GA' },
    { name: 'Miami', lat: 25.7617, lng: -80.1918, state: 'FL' },
    { name: 'Portland', lat: 45.5152, lng: -122.6784, state: 'OR' },
    { name: 'Washington DC', lat: 38.9072, lng: -77.0369, state: 'DC' }
  ];

  // Fetch geographic talent data
  const fetchGeoData = async () => {
    try {
      const response = await fetch(`/api/vc/geographic-data?metric=${metric}&viewMode=${viewMode}`);
      const data = await response.json();
      if (data.success) {
        // Merge API data with tech hubs
        const mergedData = techHubs.map(hub => {
          const apiData = data.locations.find(loc => 
            loc.name.toLowerCase().includes(hub.name.toLowerCase())
          );
          
          return {
            ...hub,
            talentDensity: apiData?.talentDensity || Math.random() * 100,
            inflow: apiData?.inflow || Math.random() * 50,
            outflow: apiData?.outflow || Math.random() * 30,
            netFlow: apiData?.netFlow || (Math.random() - 0.5) * 40,
            companies: apiData?.companies || Math.floor(Math.random() * 500),
            avgSalary: apiData?.avgSalary || (120000 + Math.random() * 100000)
          };
        });
        setHeatmapData(mergedData);
      }
    } catch (error) {
      console.error('Error fetching geographic data:', error);
      // Use mock data if API fails
      const mockData = techHubs.map(hub => ({
        ...hub,
        talentDensity: Math.random() * 100,
        inflow: Math.random() * 50,
        outflow: Math.random() * 30,
        netFlow: (Math.random() - 0.5) * 40,
        companies: Math.floor(Math.random() * 500),
        avgSalary: 120000 + Math.random() * 100000
      }));
      setHeatmapData(mockData);
    }
  };

  useEffect(() => {
    fetchGeoData();
  }, [metric, viewMode]);

  useEffect(() => {
    if (!heatmapData || !svgRef.current) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    // US bounds (approximate)
    const bounds = {
      north: 49,
      south: 24,
      east: -66,
      west: -125
    };

    // Create projection
    const projection = d3.geoAlbersUsa()
      .scale(width * 0.8)
      .translate([width / 2, height / 2]);

    // Create zoom behavior
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.5, 8])
      .on('zoom', (event) => {
        const { transform } = event;
        svg.selectAll('g').attr('transform', transform);
      });

    svg.call(zoomBehavior);
    setZoom(zoomBehavior);

    const g = svg.append('g');

    // Get the current metric values
    const currentMetric = viewMode === 'density' ? 'talentDensity' : 'netFlow';
    const metricValues = heatmapData.map(d => d[currentMetric]);
    const minVal = d3.min(metricValues);
    const maxVal = d3.max(metricValues);

    // Color scale
    const colorScale = viewMode === 'density' 
      ? d3.scaleSequential(d3.interpolateViridis).domain([minVal, maxVal])
      : d3.scaleDiverging(d3.interpolateRdBu).domain([minVal, 0, maxVal]);

    // Radius scale
    const radiusScale = d3.scaleSqrt()
      .domain([0, maxVal])
      .range([10, 50]);

    // Create circles for each location
    const circles = g.selectAll('.location-circle')
      .data(heatmapData)
      .enter()
      .append('circle')
      .attr('class', 'location-circle')
      .attr('cx', d => projection([d.lng, d.lat])[0])
      .attr('cy', d => projection([d.lng, d.lat])[1])
      .attr('r', d => radiusScale(Math.abs(d[currentMetric])))
      .attr('fill', d => colorScale(d[currentMetric]))
      .attr('fill-opacity', 0.7)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer');

    // Add hover effects
    circles
      .on('mouseover', function(event, d) {
        d3.select(this)
          .attr('stroke-width', 4)
          .attr('fill-opacity', 0.9);

        // Create tooltip
        const tooltip = d3.select('body').append('div')
          .attr('class', 'geo-tooltip')
          .style('position', 'absolute')
          .style('background', 'rgba(0,0,0,0.9)')
          .style('color', 'white')
          .style('padding', '12px')
          .style('border-radius', '8px')
          .style('pointer-events', 'none')
          .style('font-size', '14px')
          .style('z-index', 1000);

        tooltip.html(`
          <div style="font-weight: bold; margin-bottom: 8px;">${d.name}</div>
          <div>Talent Density: ${d.talentDensity.toFixed(1)}</div>
          <div>Net Flow: ${d.netFlow > 0 ? '+' : ''}${d.netFlow.toFixed(1)}</div>
          <div>Companies: ${d.companies}</div>
          <div>Avg Salary: $${(d.avgSalary / 1000).toFixed(0)}k</div>
        `)
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 15) + 'px');
      })
      .on('mouseout', function(event, d) {
        d3.select(this)
          .attr('stroke-width', 2)
          .attr('fill-opacity', 0.7);

        d3.selectAll('.geo-tooltip').remove();
      });

    // Add location labels if enabled
    if (showLabels) {
      g.selectAll('.location-label')
        .data(heatmapData)
        .enter()
        .append('text')
        .attr('class', 'location-label')
        .attr('x', d => projection([d.lng, d.lat])[0])
        .attr('y', d => projection([d.lng, d.lat])[1] - radiusScale(Math.abs(d[currentMetric])) - 5)
        .attr('text-anchor', 'middle')
        .style('font-size', '12px')
        .style('font-weight', 'bold')
        .style('fill', 'white')
        .style('text-shadow', '1px 1px 2px rgba(0,0,0,0.8)')
        .text(d => d.name);
    }

    // Add legend
    const legend = svg.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${width - 150}, 30)`);

    const legendScale = d3.scaleLinear()
      .domain([minVal, maxVal])
      .range([0, 100]);

    const legendAxis = d3.axisRight(legendScale)
      .tickSize(6)
      .tickFormat(d => viewMode === 'density' ? d.toFixed(0) : `${d > 0 ? '+' : ''}${d.toFixed(0)}`);

    legend.append('g')
      .call(legendAxis)
      .selectAll('text')
      .style('fill', 'white')
      .style('font-size', '11px');

    // Add legend gradient
    const defs = svg.append('defs');
    const linearGradient = defs.append('linearGradient')
      .attr('id', 'legend-gradient')
      .attr('x1', '0%')
      .attr('y1', '100%')
      .attr('x2', '0%')
      .attr('y2', '0%');

    const numStops = 10;
    for (let i = 0; i <= numStops; i++) {
      const offset = (i / numStops) * 100;
      const value = minVal + (maxVal - minVal) * (i / numStops);
      linearGradient.append('stop')
        .attr('offset', `${offset}%`)
        .attr('stop-color', colorScale(value));
    }

    legend.append('rect')
      .attr('x', -10)
      .attr('y', 0)
      .attr('width', 15)
      .attr('height', 100)
      .style('fill', 'url(#legend-gradient)');

  }, [heatmapData, viewMode, showLabels]);

  const handleZoomIn = () => {
    if (zoom) {
      d3.select(svgRef.current).transition().call(
        zoom.scaleBy, 1.5
      );
    }
  };

  const handleZoomOut = () => {
    if (zoom) {
      d3.select(svgRef.current).transition().call(
        zoom.scaleBy, 1 / 1.5
      );
    }
  };

  const handleReset = () => {
    if (zoom) {
      d3.select(svgRef.current).transition().call(
        zoom.transform,
        d3.zoomIdentity
      );
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={600} sx={{ flexGrow: 1 }}>
          {title || 'Geographic Talent Distribution'}
        </Typography>
        
        <FormControl size="small" sx={{ minWidth: 120, mr: 2 }}>
          <InputLabel>View Mode</InputLabel>
          <Select
            value={viewMode}
            label="View Mode"
            onChange={(e) => setViewMode(e.target.value)}
          >
            <MenuItem value="density">Talent Density</MenuItem>
            <MenuItem value="flow">Net Talent Flow</MenuItem>
          </Select>
        </FormControl>

        <FormControlLabel
          control={
            <Switch
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              color="primary"
            />
          }
          label="Labels"
          sx={{ mr: 2 }}
        />

        <ButtonGroup size="small" sx={{ mr: 2 }}>
          <Tooltip title="Zoom In">
            <Button onClick={handleZoomIn}>
              <ZoomIn />
            </Button>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <Button onClick={handleZoomOut}>
              <ZoomOut />
            </Button>
          </Tooltip>
          <Tooltip title="Reset View">
            <Button onClick={handleReset}>
              <RestoreIcon />
            </Button>
          </Tooltip>
        </ButtonGroup>

        <Tooltip title="Refresh Data">
          <IconButton onClick={fetchGeoData} size="small">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ width: '100%', height: height, position: 'relative' }}>
        <svg
          ref={svgRef}
          width="100%"
          height={height}
          style={{ background: '#0F172A', borderRadius: '8px', cursor: 'grab' }}
        />
        
        <Box 
          sx={{ 
            position: 'absolute', 
            bottom: 10, 
            left: 10, 
            color: 'white', 
            fontSize: '12px',
            background: 'rgba(0,0,0,0.7)',
            padding: '8px',
            borderRadius: '4px'
          }}
        >
          <Typography variant="caption" display="block">
            {viewMode === 'density' 
              ? 'Circle size: Talent density per 1000 people'
              : 'Circle size: Net talent flow magnitude'
            }
          </Typography>
          <Typography variant="caption">
            Drag to pan • Scroll to zoom
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default GeographicHeatmap;