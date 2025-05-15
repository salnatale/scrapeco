// frontend/client/src/components/visualizations/SankeyDiagram.js
import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal } from 'd3-sankey';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  Tooltip,
  IconButton
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

const SankeyDiagram = ({ data, title, height = 600 }) => {
  const svgRef = useRef();
  const [timeRange, setTimeRange] = useState('3M');
  const [flowData, setFlowData] = useState(null);

  // Process the raw data into Sankey format
  const processData = (rawData, range) => {
    if (!rawData || !rawData.flows) return null;

    // Filter data by time range
    const cutoffDate = new Date();
    const months = parseInt(range.replace('M', ''));
    cutoffDate.setMonth(cutoffDate.getMonth() - months);

    const filteredFlows = rawData.flows.filter(flow => 
      new Date(flow.date) >= cutoffDate
    );

    // Create nodes and links for Sankey
    const nodeMap = new Map();
    const links = [];

    // Process flows to create nodes and links
    filteredFlows.forEach(flow => {
      const sourceKey = `${flow.sourceCompany}-source`;
      const targetKey = `${flow.targetCompany}-target`;

      // Add nodes if they don't exist
      if (!nodeMap.has(sourceKey)) {
        nodeMap.set(sourceKey, {
          id: sourceKey,
          name: flow.sourceCompany,
          category: 'source',
          color: '#FF5FA2'
        });
      }

      if (!nodeMap.has(targetKey)) {
        nodeMap.set(targetKey, {
          id: targetKey,
          name: flow.targetCompany,
          category: 'target',
          color: '#3CDFFF'
        });
      }

      // Create link
      links.push({
        source: sourceKey,
        target: targetKey,
        value: flow.count,
        names: flow.names || []
      });
    });

    return {
      nodes: Array.from(nodeMap.values()),
      links: links
    };
  };

  // Fetch talent flow data
  const fetchFlowData = async () => {
    try {
      const response = await fetch(`/api/vc/talent-flows?timeRange=${timeRange}`);
      const data = await response.json();
      if (data.success) {
        const processed = processData(data, timeRange);
        setFlowData(processed);
      }
    } catch (error) {
      console.error('Error fetching flow data:', error);
    }
  };

  useEffect(() => {
    fetchFlowData();
  }, [timeRange]);

  useEffect(() => {
    if (!flowData || !svgRef.current) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth;
    const margin = { top: 20, right: 50, bottom: 20, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create Sankey generator
    const sankeyGenerator = sankey()
      .nodeWidth(20)
      .nodePadding(10)
      .extent([[0, 0], [innerWidth, innerHeight]]);

    // Generate Sankey layout
    const { nodes, links } = sankeyGenerator(flowData);

    // Color scale for links
    const colorScale = d3.scaleOrdinal()
      .domain(['low', 'medium', 'high'])
      .range(['#FFD166', '#FF8C42', '#FF5FA2']);

    // Add links
    const link = g.append('g')
      .selectAll('.link')
      .data(links)
      .enter().append('path')
      .attr('class', 'link')
      .attr('d', sankeyLinkHorizontal())
      .attr('stroke', d => {
        const intensity = d.value > 10 ? 'high' : d.value > 5 ? 'medium' : 'low';
        return colorScale(intensity);
      })
      .attr('stroke-width', d => Math.max(1, d.width))
      .attr('stroke-opacity', 0.7)
      .attr('fill', 'none');

    // Add link labels on hover
    link.on('mouseover', function(event, d) {
        const tooltip = d3.select('body').append('div')
          .attr('class', 'sankey-tooltip')
          .style('position', 'absolute')
          .style('background', 'rgba(0,0,0,0.9)')
          .style('color', 'white')
          .style('padding', '10px')
          .style('border-radius', '5px')
          .style('pointer-events', 'none')
          .style('z-index', 1000);

        tooltip.html(`
          <div><strong>${d.source.name} → ${d.target.name}</strong></div>
          <div>Transitions: ${d.value}</div>
          ${d.names && d.names.length > 0 ? 
            `<div>Recent: ${d.names.slice(0, 3).join(', ')}${d.names.length > 3 ? '...' : ''}</div>` 
            : ''
          }
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
      })
      .on('mouseout', function() {
        d3.selectAll('.sankey-tooltip').remove();
      });

    // Add nodes
    const node = g.append('g')
      .selectAll('.node')
      .data(nodes)
      .enter().append('g')
      .attr('class', 'node');

    // Add node rectangles
    node.append('rect')
      .attr('x', d => d.x0)
      .attr('y', d => d.y0)
      .attr('height', d => d.y1 - d.y0)
      .attr('width', d => d.x1 - d.x0)
      .attr('fill', d => d.color)
      .attr('stroke', '#000')
      .attr('stroke-width', 1);

    // Add node labels
    node.append('text')
      .attr('x', d => d.x0 - 6)
      .attr('y', d => (d.y1 + d.y0) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', 'end')
      .style('font-size', '12px')
      .style('fill', 'white')
      .text(d => d.name)
      .filter(d => d.x0 < innerWidth / 2)
      .attr('x', d => d.x1 + 6)
      .attr('text-anchor', 'start');

    // Add node values
    node.append('text')
      .attr('x', d => d.x0 < innerWidth / 2 ? d.x1 + 6 : d.x0 - 6)
      .attr('y', d => (d.y1 + d.y0) / 2 + 15)
      .attr('dy', '0.35em')
      .attr('text-anchor', d => d.x0 < innerWidth / 2 ? 'start' : 'end')
      .style('font-size', '10px')
      .style('fill', '#ccc')
      .text(d => `${d.value} transitions`);

  }, [flowData, height]);

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={600} sx={{ flexGrow: 1 }}>
          {title || 'Talent Flow Analysis'}
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120, mr: 2 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <MenuItem value="1M">1 Month</MenuItem>
            <MenuItem value="3M">3 Months</MenuItem>
            <MenuItem value="6M">6 Months</MenuItem>
            <MenuItem value="12M">1 Year</MenuItem>
          </Select>
        </FormControl>
        <Tooltip title="Refresh Data">
          <IconButton onClick={fetchFlowData} size="small">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ width: '100%', height: height }}>
        <svg
          ref={svgRef}
          width="100%"
          height={height}
          style={{ background: '#1A2338', borderRadius: '8px' }}
        />
      </Box>

      <Box sx={{ mt: 2, display: 'flex', gap: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 20, height: 4, bgcolor: '#FF5FA2', mr: 1 }} />
          <Typography variant="caption">High Volume (10+ transitions)</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 20, height: 4, bgcolor: '#FF8C42', mr: 1 }} />
          <Typography variant="caption">Medium Volume (5-10 transitions)</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 20, height: 4, bgcolor: '#FFD166', mr: 1 }} />
          <Typography variant="caption">Low Volume (&lt;5 transitions)</Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default SankeyDiagram;