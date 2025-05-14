import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { Box, Typography, Paper, Switch, FormControlLabel, Slider } from '@mui/material';

const CompanyNetworkGraph = ({ data, width = 900, height = 700 }) => {
  const svgRef = useRef();
  const simulationRef = useRef();
  const [showLabels, setShowLabels] = useState(true);
  const [linkStrength, setLinkStrength] = useState(0.5);
  const [chargeStrength, setChargeStrength] = useState(-300);

  useEffect(() => {
    if (!data || !data.nodes || !data.links) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .style("width", "100%")
      .style("height", "auto");

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    const g = svg.append("g");

    // Color scales
    const nodeColorScale = d3.scaleOrdinal(d3.schemeSet3);
    const linkColorScale = d3.scaleOrdinal(d3.schemeTableau10);

    // Size scales
    const nodeSize = d3.scaleSqrt()
      .domain(d3.extent(data.nodes, d => d.size || 1))
      .range([8, 30]);

    const linkWidth = d3.scaleLinear()
      .domain(d3.extent(data.links, d => d.value || 1))
      .range([1, 8]);

    // Create force simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links)
        .id(d => d.id)
        .distance(100)
        .strength(linkStrength))
      .force("charge", d3.forceManyBody().strength(chargeStrength))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(d => nodeSize(d.size || 1) + 5));

    simulationRef.current = simulation;

    // Create links
    const links = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke", d => linkColorScale(d.type || 'default'))
      .attr("stroke-width", d => linkWidth(d.value || 1))
      .attr("stroke-opacity", 0.6)
      .attr("marker-end", "url(#arrowhead)");

    // Create arrowheads
    svg.append("defs").selectAll("marker")
      .data(["arrowhead"])
      .join("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 15)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // Create node groups
    const nodeGroups = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .attr("class", "node-group")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Create nodes (circles)
    const nodes = nodeGroups.append("circle")
      .attr("r", d => nodeSize(d.size || 1))
      .attr("fill", d => nodeColorScale(d.type || d.id))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2);

    // Create node labels
    const labels = nodeGroups.append("text")
      .attr("dx", d => nodeSize(d.size || 1) + 5)
      .attr("dy", "0.35em")
      .attr("font-family", "sans-serif")
      .attr("font-size", "12px")
      .attr("fill", "#333")
      .text(d => d.name || d.id)
      .style("display", showLabels ? "block" : "none");

    // Add hover effects
    nodeGroups
      .on("mouseover", function(event, d) {
        // Highlight node
        d3.select(this).select("circle")
          .transition()
          .duration(200)
          .attr("stroke", "#ff6b6b")
          .attr("stroke-width", 4);

        // Highlight connected links
        links
          .attr("stroke-opacity", l => 
            (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1)
          .attr("stroke-width", l => 
            (l.source.id === d.id || l.target.id === d.id) 
              ? linkWidth(l.value || 1) * 1.5 
              : linkWidth(l.value || 1));

        // Highlight connected nodes
        const connectedNodes = new Set();
        data.links.forEach(l => {
          if (l.source.id === d.id) connectedNodes.add(l.target.id);
          if (l.target.id === d.id) connectedNodes.add(l.source.id);
        });

        nodeGroups.select("circle")
          .attr("fill-opacity", n => 
            connectedNodes.has(n.id) || n.id === d.id ? 1 : 0.3);

        // Show tooltip
        const tooltip = d3.select("body").append("div")
          .attr("class", "network-tooltip")
          .style("position", "absolute")
          .style("background", "rgba(0, 0, 0, 0.9)")
          .style("color", "white")
          .style("padding", "10px")
          .style("border-radius", "6px")
          .style("pointer-events", "none")
          .style("opacity", 0)
          .style("font-size", "14px");

        tooltip.transition().duration(200).style("opacity", 1);
        tooltip.html(`
          <strong>${d.name || d.id}</strong><br/>
          Type: ${d.type || 'Unknown'}<br/>
          ${d.description ? `Description: ${d.description}<br/>` : ''}
          Connections: ${data.links.filter(l => 
            l.source.id === d.id || l.target.id === d.id).length}
        `)
        .style("left", (event.pageX + 15) + "px")
        .style("top", (event.pageY - 15) + "px");
      })
      .on("mouseout", function(event, d) {
        // Reset node styling
        d3.select(this).select("circle")
          .transition()
          .duration(200)
          .attr("stroke", "#fff")
          .attr("stroke-width", 2);

        // Reset link styling
        links
          .transition()
          .duration(200)
          .attr("stroke-opacity", 0.6)
          .attr("stroke-width", l => linkWidth(l.value || 1));

        // Reset node opacity
        nodeGroups.select("circle")
          .transition()
          .duration(200)
          .attr("fill-opacity", 1);

        // Remove tooltip
        d3.selectAll(".network-tooltip").remove();
      });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      links
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      nodeGroups
        .attr("transform", d => `translate(${d.x},${d.y})`);
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
      d.fx = null;
      d.fy = null;
    }

    // Add legend
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(20, 20)`);

    const nodeTypes = [...new Set(data.nodes.map(d => d.type || 'default'))];
    
    legend.selectAll("rect")
      .data(nodeTypes)
      .join("rect")
      .attr("x", 0)
      .attr("y", (d, i) => i * 25)
      .attr("width", 15)
      .attr("height", 15)
      .attr("fill", d => nodeColorScale(d));

    legend.selectAll("text")
      .data(nodeTypes)
      .join("text")
      .attr("x", 25)
      .attr("y", (d, i) => i * 25 + 12.5)
      .attr("font-family", "sans-serif")
      .attr("font-size", "12px")
      .attr("fill", "#ffffff")
      .text(d => d.charAt(0).toUpperCase() + d.slice(1));

  }, [data, linkStrength, chargeStrength, width, height]);

  // Update label visibility
  useEffect(() => {
    d3.select(svgRef.current)
      .selectAll(".node-group text")
      .style("display", showLabels ? "block" : "none");
  }, [showLabels]);

  // Update force strengths
  useEffect(() => {
    if (simulationRef.current) {
      simulationRef.current
        .force("link").strength(linkStrength)
        .force("charge").strength(chargeStrength)
        .alpha(0.3)
        .restart();
    }
  }, [linkStrength, chargeStrength]);

  const handleReset = () => {
    if (simulationRef.current) {
      simulationRef.current.alpha(1).restart();
    }
  };

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
        <Typography variant="h6" gutterBottom>
          Company Network Graph
        </Typography>
        <Typography variant="body1" color="text.secondary">
          No network data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
      <Typography variant="h6" gutterBottom>
        Company Relationship Network
      </Typography>
      
      {/* Controls */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControlLabel
          control={
            <Switch
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              color="primary"
            />
          }
          label="Show Labels"
        />
        
        <Box sx={{ minWidth: 200 }}>
          <Typography variant="body2" gutterBottom>
            Link Strength: {linkStrength}
          </Typography>
          <Slider
            value={linkStrength}
            onChange={(e, value) => setLinkStrength(value)}
            min={0.1}
            max={2}
            step={0.1}
            size="small"
            sx={{ color: 'primary.main' }}
          />
        </Box>
        
        <Box sx={{ minWidth: 200 }}>
          <Typography variant="body2" gutterBottom>
            Charge Strength: {chargeStrength}
          </Typography>
          <Slider
            value={chargeStrength}
            onChange={(e, value) => setChargeStrength(value)}
            min={-1000}
            max={-100}
            step={50}
            size="small"
            sx={{ color: 'primary.main' }}
          />
        </Box>
        
        <button
          onClick={handleReset}
          style={{
            background: '#3CDFFF',
            color: '#121212',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: '600'
          }}
        >
          Reset Layout
        </button>
      </Box>

      <Box sx={{ width: '100%', overflow: 'auto' }}>
        <svg ref={svgRef}></svg>
      </Box>
    </Paper>
  );
};

export default CompanyNetworkGraph;