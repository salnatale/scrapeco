import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { 
  Box, 
  Paper, 
  Typography, 
  IconButton, 
  Slider, 
  FormControlLabel, 
  Switch,
  Grid,
  Button
} from '@mui/material';
import {
  ZoomIn,
  ZoomOut,
  Refresh,
  Visibility,
  VisibilityOff
} from '@mui/icons-material';

const AdvancedGraphVisualization = ({ data }) => {
  const svgRef = useRef();
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showLabels, setShowLabels] = useState(true);
  const [linkStrength, setLinkStrength] = useState(100);
  const simulationRef = useRef(null);
  
  // Function to handle graph reset
  const resetGraph = () => {
    if (simulationRef.current) {
      // Reset node positions
      data.nodes.forEach(node => {
        delete node.fx;
        delete node.fy;
      });
      
      // Restart simulation
      simulationRef.current.alpha(1).restart();
    }
  };
  
  useEffect(() => {
    if (!data || !data.nodes || !data.links || data.nodes.length === 0) {
      return;
    }
    
    // Clear any existing SVG content
    d3.select(svgRef.current).selectAll('*').remove();
    
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;
    
    // Create SVG element with dark theme background
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);
      
    // Add zoom capabilities
    const g = svg.append('g');
    
    const zoom = d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoomLevel(event.transform.k);
      });
      
    svg.call(zoom);
    
    // Define node colors based on type with professional dark theme
    const nodeColors = {
      person: '#3CDFFF',    // Primary color
      company: '#5C7CFA',   // Info color
      skill: '#FF5FA2',     // Secondary color
      education: '#FFD166', // Warning color
      default: '#3CDFFF'
    };
    
    // Add a legend
    const legend = svg.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(20, ${height - 120})`);
      
    const legendItems = Object.entries(nodeColors).map(([key, value]) => ({
      type: key,
      color: value
    }));
    
    legend.selectAll('rect')
      .data(legendItems)
      .enter()
      .append('rect')
      .attr('x', 0)
      .attr('y', (d, i) => i * 25)
      .attr('width', 15)
      .attr('height', 15)
      .attr('fill', d => d.color);
      
    legend.selectAll('text')
      .data(legendItems)
      .enter()
      .append('text')
      .attr('x', 25)
      .attr('y', (d, i) => i * 25 + 12.5)
      .text(d => d.type.charAt(0).toUpperCase() + d.type.slice(1))
      .attr('fill', '#ffffff')
      .style('font-size', '12px');
      
    // Create a simulation for positioning nodes
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id(d => d.id).distance(linkStrength))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.1))
      .force('y', d3.forceY(height / 2).strength(0.1));
      
    // Store the simulation reference
    simulationRef.current = simulation;
    
    // Create links with arrows
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(data.links)
      .enter().append('g');
      
    // Link lines
    link.append('line')
      .attr('stroke', '#777')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.value) || 1.5);
      
    // Link text labels
    const linkLabels = link.append('text')
      .attr('class', 'link-label')
      .attr('dy', -5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#cccccc')
      .style('font-size', '10px')
      .text(d => d.label || '');
      
    // Update link label visibility based on showLabels state
    linkLabels.style('display', showLabels ? 'block' : 'none');
      
    // Add arrow markers for links
    svg.append('defs').selectAll('marker')
      .data(['end'])
      .enter().append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('fill', '#999')
      .attr('d', 'M0,-5L10,0L0,5');
      
    link.selectAll('line')
      .attr('marker-end', 'url(#arrow)');
      
    // Create node groups
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(data.nodes)
      .enter().append('g')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));
        
    // Node circles
    node.append('circle')
      .attr('r', d => d.size || 12)
      .attr('fill', d => nodeColors[d.type] || nodeColors.default)
      .attr('stroke', '#444')
      .attr('stroke-width', 1.5);
      
    // Node labels
    const nodeLabels = node.append('text')
      .attr('dy', 4)
      .attr('dx', 14)
      .attr('fill', '#ffffff')
      .style('font-size', '12px')
      .text(d => d.label || d.name || d.id);
      
    // Update node label visibility based on showLabels state
    nodeLabels.style('display', showLabels ? 'block' : 'none');
      
    // Add tooltips on hover
    node.append('title')
      .text(d => {
        let tooltip = `ID: ${d.id}\nType: ${d.type || 'Unknown'}`;
        if (d.name) tooltip += `\nName: ${d.name}`;
        if (d.description) tooltip += `\nDescription: ${d.description}`;
        return tooltip;
      });
      
    // Add interactivity for highlighting connections
    node.on('click', function(event, d) {
      // Prevent event from bubbling to SVG
      event.stopPropagation();
      
      // Unhighlight all nodes first
      node.select('circle')
        .attr('stroke', '#444')
        .attr('stroke-width', 1.5)
        .attr('r', n => n.size || 12);
        
      link.selectAll('line')
        .attr('stroke', '#777')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', l => Math.sqrt(l.value) || 1.5);
        
      // Highlight selected node
      d3.select(this).select('circle')
        .attr('stroke', '#fff')
        .attr('stroke-width', 3)
        .attr('r', (d.size || 12) * 1.2);
        
      // Find connected links
      const connectedLinks = data.links.filter(l => l.source.id === d.id || l.target.id === d.id);
      
      link.filter(l => connectedLinks.includes(l))
        .selectAll('line')
        .attr('stroke', '#fff')
        .attr('stroke-opacity', 1)
        .attr('stroke-width', 2);
        
      // Highlight connected nodes
      const connectedNodeIds = connectedLinks.map(l => 
        l.source.id === d.id ? l.target.id : l.source.id
      );
      
      node.filter(n => connectedNodeIds.includes(n.id))
        .select('circle')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);
    });
    
    // Double-click to reset view
    svg.on('dblclick', function() {
      // Reset zoom
      svg.transition().duration(750).call(
        zoom.transform,
        d3.zoomIdentity,
        d3.zoomTransform(svg.node()).invert([width / 2, height / 2])
      );
      
      // Reset highlighting
      node.select('circle')
        .attr('stroke', '#444')
        .attr('stroke-width', 1.5)
        .attr('r', n => n.size || 12);
        
      link.selectAll('line')
        .attr('stroke', '#777')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', l => Math.sqrt(l.value) || 1.5);
    });
    
    // Position updates on each simulation tick
    simulation.on('tick', () => {
      link.selectAll('line')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
        
      link.selectAll('text')
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2);
        
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      // Keep nodes fixed after dragging
      d.fx = event.x;
      d.fy = event.y;
    }
    
    // Update simulation if linkStrength changes
    if (simulation && data.links.length > 0) {
      simulation.force('link').distance(linkStrength);
      simulation.alpha(0.3).restart();
    }
    
    // Cleanup function
    return () => {
      if (simulation) simulation.stop();
    };
  }, [data, showLabels, linkStrength]);
  
  // Function to handle zoom in/out buttons
  const handleZoom = (direction) => {
    const svg = d3.select(svgRef.current);
    const currentTransform = d3.zoomTransform(svg.node());
    const newScale = direction === 'in' ? currentTransform.k * 1.3 : currentTransform.k / 1.3;
    
    svg.transition().duration(250).call(
      d3.zoom().transform,
      d3.zoomIdentity.translate(currentTransform.x, currentTransform.y).scale(newScale)
    );
    
    setZoomLevel(newScale);
  };
  
  // Function to handle link strength changes
  const handleLinkStrengthChange = (event, newValue) => {
    setLinkStrength(newValue);
  };
  
  // Function to toggle labels visibility
  const handleLabelsToggle = () => {
    setShowLabels(!showLabels);
  };
  
  return (
    <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* Controls panel */}
      <Paper 
        elevation={3} 
        sx={{ 
          position: 'absolute', 
          top: 10, 
          right: 10, 
          p: 2, 
          zIndex: 1000, 
          width: 250,
          backgroundColor: 'background.card',
          color: 'text.primary',
          borderRadius: 2,
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
        }}
      >
        <Typography variant="subtitle1" gutterBottom>
          Graph Controls
        </Typography>
        
        <Grid container spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Grid item>
            <Typography variant="body2">Zoom</Typography>
          </Grid>
          <Grid item>
            <IconButton size="small" onClick={() => handleZoom('out')} sx={{ color: 'primary.main' }}>
              <ZoomOut />
            </IconButton>
          </Grid>
          <Grid item xs>
            <Slider
              value={zoomLevel}
              min={0.1}
              max={4}
              step={0.1}
              onChange={(e, val) => setZoomLevel(val)}
              sx={{ color: 'primary.main' }}
            />
          </Grid>
          <Grid item>
            <IconButton size="small" onClick={() => handleZoom('in')} sx={{ color: 'primary.main' }}>
              <ZoomIn />
            </IconButton>
          </Grid>
        </Grid>
        
        <Typography variant="body2" sx={{ mb: 1 }}>
          Link Strength
        </Typography>
        <Slider
          value={linkStrength}
          min={10}
          max={300}
          onChange={handleLinkStrengthChange}
          sx={{ color: 'primary.main', mb: 2 }}
        />
        
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <FormControlLabel
              control={
                <Switch 
                  checked={showLabels} 
                  onChange={handleLabelsToggle}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {showLabels ? <Visibility fontSize="small" /> : <VisibilityOff fontSize="small" />}
                  <Typography variant="body2" sx={{ ml: 0.5 }}>
                    Labels
                  </Typography>
                </Box>
              }
            />
          </Grid>
          <Grid item xs={6}>
            <Button
              startIcon={<Refresh />}
              variant="outlined"
              size="small"
              onClick={resetGraph}
              sx={{ 
                borderColor: 'primary.main',
                color: 'primary.main'
              }}
            >
              Reset
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      {/* Graph visualization */}
      <Box 
        sx={{ 
          width: '100%', 
          height: '700px', 
          bgcolor: 'background.paper', 
          borderRadius: 2,
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
        }}
      >
        <svg 
          ref={svgRef} 
          style={{ width: '100%', height: '100%' }}
        />
      </Box>
    </Box>
  );
};

export default AdvancedGraphVisualization; 