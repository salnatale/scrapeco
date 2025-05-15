// frontend/client/src/components/VCFilters.js
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Grid,
  Button,
  Autocomplete,
  TextField,
  OutlinedInput,
  ListItemText,
  Checkbox
} from '@mui/material';
import {
  FilterList as FilterIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import { useVC } from '../context/VCContext';

// Static data - in real app this would come from API
const INDUSTRIES = [
  'AI/ML',
  'FinTech',
  'HealthTech',
  'EdTech',
  'E-commerce',
  'Enterprise Software',
  'DevTools',
  'Climate Tech',
  'Cybersecurity',
  'Data/Analytics'
];

const FUNDING_STAGES = [
  'Pre-Seed',
  'Seed',
  'Series A',
  'Series B',
  'Series C',
  'Series D+'
];

const GEO_REGIONS = [
  'San Francisco Bay Area',
  'New York',
  'Boston',
  'Los Angeles',
  'Seattle',
  'Austin',
  'Chicago',
  'London',
  'Berlin',
  'Singapore'
];

// Mock portfolio companies - would come from user data
const PORTFOLIO_COMPANIES = [
  { id: 'urn:li:company:1', name: 'TechNova' },
  { id: 'urn:li:company:2', name: 'DataSphere' },
  { id: 'urn:li:company:3', name: 'QuantumLeap' },
  { id: 'urn:li:company:4', name: 'GreenWave' },
  { id: 'urn:li:company:5', name: 'HealthPulse' }
];

const VCFilters = () => {
  const { state, actions } = useVC();
  const [fundingRange, setFundingRange] = useState([0, 5]);

  const handleIndustryChange = (event) => {
    const value = typeof event.target.value === 'string' 
      ? event.target.value.split(',') 
      : event.target.value;
    
    actions.setFilters({ industries: value });
  };

  const handleGeoChange = (event, newValue) => {
    actions.setFilters({ geo_regions: newValue });
  };

  const handlePortfolioChange = (event, newValue) => {
    const portfolioIds = newValue.map(company => company.id);
    actions.setFilters({ portfolio_ids: portfolioIds });
  };

  const handleFundingRangeChange = (event, newValue) => {
    setFundingRange(newValue);
    const stages = FUNDING_STAGES.slice(newValue[0], newValue[1] + 1);
    actions.setFilters({ funding_stages: stages });
  };

  const clearFilters = () => {
    actions.setFilters({
      industries: [],
      funding_stages: [],
      geo_regions: [],
      portfolio_ids: []
    });
    setFundingRange([0, 5]);
  };

  const applyFilters = () => {
    if (state.mode === 'research') {
      actions.searchCompanies();
    } else {
      actions.loadPortfolioOverview();
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3, backgroundColor: 'background.paper' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <FilterIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {state.mode === 'research' ? 'Research Filters' : 'Portfolio Filters'}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          startIcon={<ClearIcon />}
          onClick={clearFilters}
          size="small"
          color="secondary"
        >
          Clear All
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Industry Filter - Always show in Research mode */}
        {state.mode === 'research' && (
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Industries</InputLabel>
              <Select
                multiple
                value={state.filters.industries || []}
                onChange={handleIndustryChange}
                input={<OutlinedInput label="Industries" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {INDUSTRIES.map((industry) => (
                  <MenuItem key={industry} value={industry}>
                    <Checkbox checked={state.filters.industries?.includes(industry)} />
                    <ListItemText primary={industry} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        )}

        {/* Funding Stage - Only in Research mode */}
        {state.mode === 'research' && (
          <Grid item xs={12} md={6}>
            <Typography gutterBottom>
              Funding Stage Range
            </Typography>
            <Slider
              value={fundingRange}
              onChange={handleFundingRangeChange}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => FUNDING_STAGES[value]}
              min={0}
              max={FUNDING_STAGES.length - 1}
              marks={FUNDING_STAGES.map((stage, index) => ({
                value: index,
                label: stage
              }))}
              sx={{ mt: 2 }}
            />
          </Grid>
        )}

        {/* Geography - Show in both modes */}
        <Grid item xs={12} md={6}>
          <Autocomplete
            multiple
            options={GEO_REGIONS}
            value={state.filters.geo_regions || []}
            onChange={handleGeoChange}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip
                  variant="outlined"
                  label={option}
                  {...getTagProps({ index })}
                  key={option}
                />
              ))
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Geographic Regions"
                placeholder="Select regions..."
              />
            )}
          />
        </Grid>

        {/* Portfolio Companies - Only in Portfolio mode */}
        {state.mode === 'portfolio' && (
          <Grid item xs={12} md={6}>
            <Autocomplete
              multiple
              options={PORTFOLIO_COMPANIES}
              getOptionLabel={(option) => option.name}
              value={PORTFOLIO_COMPANIES.filter(comp => 
                state.filters.portfolio_ids?.includes(comp.id)
              )}
              onChange={handlePortfolioChange}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip
                    variant="outlined"
                    label={option.name}
                    {...getTagProps({ index })}
                    key={option.id}
                  />
                ))
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Portfolio Companies"
                  placeholder="Select companies..."
                />
              )}
            />
          </Grid>
        )}

        {/* Apply Button */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <Button
              variant="contained"
              onClick={applyFilters}
              disabled={state.loading}
              sx={{
                backgroundColor: 'primary.main',
                '&:hover': {
                  backgroundColor: 'primary.dark'
                }
              }}
            >
              {state.loading ? 'Loading...' : 'Apply Filters'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default VCFilters;