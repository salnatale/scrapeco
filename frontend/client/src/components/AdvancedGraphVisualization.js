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
      console.warn("No visualization data available:", data);
      return;
    }
    
    console.log("Advanced visualization data:", data);
    
    // Make deep copies to avoid modifying the original data
    const nodes = JSON.parse(JSON.stringify(data.nodes));
    const nodeIds = new Set(nodes.map(n => n.id));
    
    // Fix any invalid links by ensuring source and target are properly formatted
    const validLinks = JSON.parse(JSON.stringify(data.links))
      .map(link => ({
        ...link,
        // Make sure source and target are strings or objects with id
        source: typeof link.source === 'object' ? link.source.id : link.source,
        target: typeof link.target === 'object' ? link.target.id : link.target
      }))
      .filter(link => {
        const isValid = nodeIds.has(link.source) && nodeIds.has(link.target);
        if (!isValid) {
          console.warn("Skipping invalid link:", link, "Source or target node not found");
        }
        return isValid;
      });
    
    // Clear any existing SVG content
    d3.select(svgRef.current).selectAll('*').remove();
    
    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;
    
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
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(validLinks).id(d => d.id).distance(linkStrength))
      .force('charge', d3.forceManyBody().strength(-600))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.1))
      .force('y', d3.forceY(height / 2).strength(0.1))
      .alphaDecay(0.02);  // Slower cooling for better layout
      
    // Store the simulation reference
    simulationRef.current = simulation;
    
    // Create links with arrows
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(validLinks)
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
      .data(nodes)
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
        if (d.label) tooltip += `\nLabel: ${d.label}`;
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
      const connectedLinks = validLinks.filter(l => {
        return l.source === d.id || l.target === d.id;
      });
      
      link.filter(l => connectedLinks.includes(l))
        .selectAll('line')
        .attr('stroke', '#fff')
        .attr('stroke-opacity', 1)
        .attr('stroke-width', 2);
        
      // Highlight connected nodes
      const connectedNodeIds = connectedLinks.map(l => {
        return l.source === d.id ? l.target : l.source;
      });
      
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
    
    // Run simulation for 300 ticks to get better initial positions
    for (let i = 0; i < 300; ++i) simulation.tick();
    
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
      // Keep nodes in place after dragging
      d.fx = event.x;
      d.fy = event.y;
    }
    
    // Cleanup function
    return () => {
      simulation.stop();
    };
  }, [data, linkStrength, showLabels]);
  
  const handleZoom = (direction) => {
    const svg = d3.select(svgRef.current);
    const currentTransform = d3.zoomTransform(svg.node());
    
    const scaleFactor = direction === 'in' ? 1.3 : 0.7;
    const newK = currentTransform.k * scaleFactor;
    
    svg.transition().duration(300).call(
      d3.zoom().transform,
      d3.zoomIdentity.scale(newK).translate(currentTransform.x, currentTransform.y)
    );
    
    setZoomLevel(newK);
  };
  
  const handleLinkStrengthChange = (event, newValue) => {
    setLinkStrength(newValue);
    // Simulation will be restarted in useEffect
  };
  
  const handleLabelsToggle = () => {
    setShowLabels(!showLabels);
  };

  return (
    <Box sx={{ position: 'relative' }}>
      <Box 
        sx={{ 
          width: '100%', 
          height: '600px', 
          bgcolor: 'background.paper', 
          borderRadius: 2,
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
          position: 'relative',
        }}
      >
        <svg 
          ref={svgRef} 
          style={{ width: '100%', height: '100%' }}
        />
      </Box>
      
      <Paper sx={{ 
        position: 'absolute', 
        top: 16, 
        right: 16, 
        p: 2, 
        bgcolor: 'rgba(18, 24, 40, 0.8)',
        backdropFilter: 'blur(8px)',
        borderRadius: 2,
        width: 240
      }}>
        <Typography variant="subtitle2" color="white" gutterBottom>
          Graph Controls
        </Typography>
        
        <Typography variant="caption" color="white" gutterBottom>
          Zoom
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton 
            size="small" 
            onClick={() => handleZoom('out')} 
            sx={{ color: 'primary.main' }}
          >
            <ZoomOut />
          </IconButton>
          
          <Slider
            size="small"
            value={zoomLevel}
            min={0.1}
            max={4}
            step={0.1}
            valueLabelDisplay="auto"
            sx={{ mx: 1, color: 'primary.main' }}
          />
          
          <IconButton 
            size="small" 
            onClick={() => handleZoom('in')} 
            sx={{ color: 'primary.main' }}
          >
            <ZoomIn />
          </IconButton>
        </Box>
        
        <Typography variant="caption" color="white" gutterBottom>
          Link Strength
        </Typography>
        <Slider
          size="small"
          value={linkStrength}
          min={20}
          max={200}
          step={10}
          onChange={handleLinkStrengthChange}
          valueLabelDisplay="auto"
          sx={{ mb: 2, color: 'primary.main' }}
        />
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch 
                checked={showLabels}
                onChange={handleLabelsToggle}
                size="small"
                sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: 'primary.main' } }}
              />
            }
            label={<Typography variant="caption" color="white">Labels</Typography>}
          />
          
          <Button
            variant="outlined"
            size="small"
            startIcon={<Refresh />}
            onClick={resetGraph}
            sx={{ 
              color: 'white', 
              borderColor: 'primary.main',
              '&:hover': { borderColor: 'primary.light' }
            }}
          >
            Reset
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default AdvancedGraphVisualization; 