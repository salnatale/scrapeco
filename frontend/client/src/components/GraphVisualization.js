import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Box } from '@mui/material';

const GraphVisualization = ({ data }) => {
  const svgRef = useRef();
  
  useEffect(() => {
    if (!data || !data.nodes || !data.links || data.nodes.length === 0) {
      return;
    }
    
    // Clear any existing SVG content
    d3.select(svgRef.current).selectAll('*').remove();
    
    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create SVG element
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);
      
    // Add zoom capabilities
    const g = svg.append('g');
    
    svg.call(d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      }));

    // Define node colors based on type
    const nodeColors = {
      person: '#3CDFFF', // Primary color from new theme
      company: '#5C7CFA', // Info color
      skill: '#FF5FA2', // Secondary color
      education: '#FFD166', // Warning color
      default: '#3CDFFF'
    };

    // Create a simulation for positioning nodes
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.1))
      .force('y', d3.forceY(height / 2).strength(0.1));

    // Create links with arrows
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(data.links)
      .enter().append('g');
      
    // Link lines
    link.append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.value) || 1);

    // Link text labels
    link.append('text')
      .attr('class', 'link-label')
      .attr('dy', -5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#cccccc')
      .text(d => d.label || '');
      
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
      .attr('r', d => d.size || 10)
      .attr('fill', d => nodeColors[d.type] || nodeColors.default)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    // Node labels
    node.append('text')
      .attr('dy', 4)
      .attr('dx', 12)
      .text(d => d.label || d.name || d.id)
      .attr('fill', '#ffffff');

    // Add tooltips on hover
    node.append('title')
      .text(d => {
        let tooltip = `ID: ${d.id}\nType: ${d.type || 'Unknown'}`;
        if (d.name) tooltip += `\nName: ${d.name}`;
        if (d.description) tooltip += `\nDescription: ${d.description}`;
        return tooltip;
      });

    // Add interactivity for highlighting connections
    node.on('mouseover', function(event, d) {
      // Highlight the node
      d3.select(this).select('circle')
        .attr('stroke', '#ff0')
        .attr('stroke-width', 3);
      
      // Dim all links
      link.selectAll('line')
        .attr('stroke-opacity', 0.2);
      
      // Highlight connected links
      const connectedLinks = data.links.filter(l => l.source.id === d.id || l.target.id === d.id);
      
      link.filter(l => connectedLinks.includes(l))
        .selectAll('line')
        .attr('stroke', '#ff0')
        .attr('stroke-opacity', 1)
        .attr('stroke-width', 2);
        
      // Highlight connected nodes
      const connectedNodeIds = connectedLinks.map(l => 
        l.source.id === d.id ? l.target.id : l.source.id
      );
      
      node.filter(n => connectedNodeIds.includes(n.id))
        .select('circle')
        .attr('stroke', '#ff0')
        .attr('stroke-width', 2);
    })
    .on('mouseout', function() {
      // Reset all styling
      node.select('circle')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);
        
      link.selectAll('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => Math.sqrt(d.value) || 1);
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
      // Keep nodes in place after dragging ends
      d.fx = event.x;
      d.fy = event.y;
    }

    // Cleanup function
    return () => {
      simulation.stop();
    };
  }, [data]);

  return (
    <Box 
      sx={{ 
        width: '100%', 
        height: '600px', 
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
  );
};

export default GraphVisualization; 