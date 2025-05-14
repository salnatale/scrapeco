import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal } from 'd3-sankey';
import { Box, Typography, Paper } from '@mui/material';

const TalentFlowSankey = ({ data, width = 800, height = 600 }) => {
  const svgRef = useRef();

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

    // Create sankey layout
    const sankeyLayout = sankey()
      .nodeWidth(20)
      .nodePadding(10)
      .extent([[1, 1], [width - 1, height - 1]]);

    // Process data for sankey
    const sankeyData = sankeyLayout({
      nodes: data.nodes.map(d => ({ ...d })),
      links: data.links.map(d => ({ ...d, value: d.value || 1 }))
    });

    // Color scale for companies
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    // Create gradients for links
    const defs = svg.append("defs");
    
    sankeyData.links.forEach((link, i) => {
      const gradient = defs.append("linearGradient")
        .attr("id", `gradient-${i}`)
        .attr("gradientUnits", "userSpaceOnUse")
        .attr("x1", link.source.x1)
        .attr("x2", link.target.x0);

      gradient.append("stop")
        .attr("offset", "0%")
        .attr("stop-color", colorScale(link.source.name));

      gradient.append("stop")
        .attr("offset", "100%")
        .attr("stop-color", colorScale(link.target.name));
    });

    // Draw links
    const links = svg.append("g")
      .selectAll("path")
      .data(sankeyData.links)
      .join("path")
      .attr("d", sankeyLinkHorizontal())
      .attr("stroke", (d, i) => `url(#gradient-${i})`)
      .attr("stroke-width", d => Math.max(1, d.width))
      .attr("fill", "none")
      .attr("opacity", 0.7)
      .on("mouseover", function(event, d) {
        // Highlight on hover
        d3.select(this).attr("opacity", 1);
        
        // Show tooltip
        const tooltip = d3.select("body").append("div")
          .attr("class", "sankey-tooltip")
          .style("position", "absolute")
          .style("background", "rgba(0, 0, 0, 0.8)")
          .style("color", "white")
          .style("padding", "8px")
          .style("border-radius", "4px")
          .style("pointer-events", "none")
          .style("opacity", 0);

        tooltip.transition().duration(200).style("opacity", 1);
        tooltip.html(`
          <strong>${d.source.name} → ${d.target.name}</strong><br/>
          Talent Flow: ${d.value} people
        `)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px");
      })
      .on("mouseout", function(event, d) {
        d3.select(this).attr("opacity", 0.7);
        d3.selectAll(".sankey-tooltip").remove();
      });

    // Draw nodes
    const nodes = svg.append("g")
      .selectAll("rect")
      .data(sankeyData.nodes)
      .join("rect")
      .attr("x", d => d.x0)
      .attr("y", d => d.y0)
      .attr("height", d => d.y1 - d.y0)
      .attr("width", d => d.x1 - d.x0)
      .attr("fill", d => colorScale(d.name))
      .attr("stroke", "#000")
      .attr("stroke-width", 1);

    // Add node labels
    svg.append("g")
      .selectAll("text")
      .data(sankeyData.nodes)
      .join("text")
      .attr("x", d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
      .attr("y", d => (d.y1 + d.y0) / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
      .attr("font-family", "sans-serif")
      .attr("font-size", "14px")
      .attr("fill", "#ffffff")
      .text(d => d.name);

  }, [data, width, height]);

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
      <Typography variant="h6" gutterBottom>
        Talent Flow Between Companies
      </Typography>
      <Box sx={{ width: '100%', overflow: 'auto' }}>
        <svg ref={svgRef}></svg>
      </Box>
    </Paper>
  );
};

export default TalentFlowSankey;