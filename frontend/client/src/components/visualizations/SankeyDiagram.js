// frontend/client/src/components/visualizations/SankeyDiagram.js
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Box } from '@mui/material';

// Simple Sankey diagram replacement - intentionally avoiding d3-sankey library issues
const SankeyDiagram = ({ data, height = 500 }) => {
  const svgRef = useRef();

  useEffect(() => {
    // Clear any existing content
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    // Get dimensions
    const width = svgRef.current.clientWidth;
    const margin = { top: 20, right: 30, bottom: 20, left: 30 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    
    // Create container group
    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);
    
    try {
      console.log("Creating basic flow diagram with:", 
        data.nodes?.length || 0, "nodes and", 
        data.links?.length || 0, "links");
      
      // Simplified flow diagram approach
      // Create fixed column positions
      const NODE_RADIUS = 10;
      const SOURCE_X = innerWidth * 0.2;  // Sources on the left
      const TARGET_X = innerWidth * 0.8;  // Targets on the right
      
      // Create a Set of all source and target names
      const sourceIds = new Set(data.links.map(d => d.source));
      const targetIds = new Set(data.links.map(d => d.target));
      
      // Find nodes that are both sources and targets
      const bothIds = new Set([...sourceIds].filter(id => targetIds.has(id)));
      
      // Assign positions to nodes
      const nodePositions = {};
      const sourceNodes = data.nodes.filter(n => sourceIds.has(n.id) && !targetIds.has(n.id));
      const targetNodes = data.nodes.filter(n => targetIds.has(n.id) && !sourceIds.has(n.id));
      const middleNodes = data.nodes.filter(n => bothIds.has(n.id));
      
      // Calculate vertical spacing
      const sourcesHeight = innerHeight * 0.8;
      const targetsHeight = innerHeight * 0.8;
      const sourceSpacing = sourceNodes.length > 1 ? sourcesHeight / (sourceNodes.length - 1) : 0;
      const targetSpacing = targetNodes.length > 1 ? targetsHeight / (targetNodes.length - 1) : 0;
      
      // Position source nodes
      sourceNodes.forEach((node, i) => {
        nodePositions[node.id] = {
          x: SOURCE_X,
          y: margin.top + (sourceNodes.length > 1 
            ? i * sourceSpacing 
            : innerHeight / 2),
          type: 'source',
          node
        };
      });
      
      // Position target nodes
      targetNodes.forEach((node, i) => {
        nodePositions[node.id] = {
          x: TARGET_X,
          y: margin.top + (targetNodes.length > 1 
            ? i * targetSpacing
            : innerHeight / 2),
          type: 'target',
          node
        };
      });
      
      // Position middle nodes (if any)
      const MIDDLE_X = innerWidth * 0.5;
      const middleSpacing = middleNodes.length > 1 ? innerHeight * 0.8 / (middleNodes.length - 1) : 0;
      
      middleNodes.forEach((node, i) => {
        nodePositions[node.id] = {
          x: MIDDLE_X,
          y: margin.top + (middleNodes.length > 1 
            ? i * middleSpacing 
            : innerHeight / 2),
          type: 'both',
          node
        };
      });
      
      // Draw flow paths
      const linkGroup = g.append("g").attr("class", "links");
      
      // Color scale based on link value
      const linkColorScale = d3.scaleSequential()
        .domain([0, d3.max(data.links, d => d.value) || 1])
        .interpolator(d3.interpolateBlues);
      
      // Create links
      data.links.forEach(link => {
        const sourcePos = nodePositions[link.source];
        const targetPos = nodePositions[link.target];
        
        if (sourcePos && targetPos) {
          // Draw a curved path
          const path = linkGroup.append("path")
            .attr("d", () => {
              const x1 = sourcePos.x;
              const y1 = sourcePos.y;
              const x2 = targetPos.x;
              const y2 = targetPos.y;
              
              // Calculate control points for a nice curve
              const controlX = (x1 + x2) / 2;
              
              return `M${x1},${y1} C${controlX},${y1} ${controlX},${y2} ${x2},${y2}`;
            })
            .attr("stroke", linkColorScale(link.value))
            .attr("stroke-width", Math.max(1, Math.min(10, link.value / 2))) // Scale width based on value, but limit size
            .attr("stroke-opacity", 0.7)
            .attr("fill", "none");
          
          // Add tooltip to path
          path.append("title")
            .text(`${sourcePos.node.name} → ${targetPos.node.name}: ${link.value} transitions`);
        }
      });
      
      // Draw nodes
      const nodeGroup = g.append("g").attr("class", "nodes");
      
      // Create nodes
      Object.values(nodePositions).forEach(pos => {
        // Node group
        const nodeG = nodeGroup.append("g")
          .attr("transform", `translate(${pos.x},${pos.y})`)
          .attr("data-id", pos.node.id);
        
        // Node circle
        nodeG.append("circle")
          .attr("r", NODE_RADIUS)
          .attr("fill", pos.type === 'source' ? "#4682B4" : 
                        pos.type === 'target' ? "#6A5ACD" : "#20B2AA")
          .attr("stroke", "#333")
          .attr("stroke-width", 1);
        
        // Node label
        nodeG.append("text")
          .attr("x", pos.type === 'source' ? -15 : 15)
          .attr("y", 0)
          .attr("text-anchor", pos.type === 'source' ? "end" : "start")
          .attr("dominant-baseline", "middle")
          .attr("fill", "white")
          .text(pos.node.name)
          .style("font-size", "12px");
        
        // Add tooltips
        nodeG.append("title")
          .text(() => {
            const inflow = pos.node.inflow || 0;
            const outflow = pos.node.outflow || 0;
            return `${pos.node.name}\nInflow: ${inflow}\nOutflow: ${outflow}`;
          });
      });
    } catch (error) {
      console.error("Error rendering diagram:", error);
      
      // Show error message in SVG
      svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "white")
        .style("font-size", "14px")
        .text("Error rendering Sankey diagram");
    }
  }, [data, height]);

  return (
    <Box sx={{ width: '100%', height: height }}>
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        style={{ background: '#1A2338', borderRadius: '4px' }}
      />
    </Box>
  );
};

export default SankeyDiagram;