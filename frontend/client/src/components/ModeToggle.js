// frontend/client/src/components/ModeToggle.js
import React from 'react';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Typography
} from '@mui/material';
import {
  Search as ResearchIcon,
  Business as PortfolioIcon
} from '@mui/icons-material';
import { useVC } from '../context/VCContext';

const ModeToggle = () => {
  const { state, actions } = useVC();

  const handleModeChange = (event, newMode) => {
    const mode = newMode === 0 ? 'research' : 'portfolio';
    actions.setMode(mode);
  };

  return (
    <Paper 
      elevation={2}
      sx={{ 
        mb: 3,
        backgroundColor: 'background.paper',
        borderRadius: 2
      }}
    >
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={state.mode === 'research' ? 0 : 1}
          onChange={handleModeChange}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              minHeight: 64,
              fontSize: '1rem',
              fontWeight: 600
            }
          }}
        >
          <Tab
            icon={<ResearchIcon />}
            label="Research View"
            iconPosition="start"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
                backgroundColor: 'rgba(60, 223, 255, 0.08)'
              }
            }}
          />
          <Tab
            icon={<PortfolioIcon />}
            label="Portfolio View"
            iconPosition="start"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
                backgroundColor: 'rgba(60, 223, 255, 0.08)'
              }
            }}
          />
        </Tabs>
      </Box>
      
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {state.mode === 'research' 
            ? 'Explore watchlist companies and investment opportunities'
            : 'Monitor your portfolio companies and their performance'
          }
        </Typography>
      </Box>
    </Paper>
  );
};

export default ModeToggle;