// frontend/client/src/components/Navbar.js
import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link } from 'react-router-dom';
import { Assessment, CloudUpload, Home } from '@mui/icons-material';

const Navbar = () => {
  return (
    <AppBar
      position="static"
      sx={{
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', px: { xs: 2, md: 4 } }}>
        <Typography 
          variant="h6" 
          sx={{ 
            fontWeight: 700,
            background: 'linear-gradient(90deg, #3CDFFF, #B992FF)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}
        >
          Intelligence Platform
        </Typography>
        <Box>
          <Button
            component={Link}
            to="/"
            startIcon={<Home />}
            sx={{
              color: 'white',
              mx: 1,
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.1)'
              }
            }}
          >
            Home
          </Button>
          <Button
            component={Link}
            to="/upload"
            startIcon={<CloudUpload />}
            sx={{
              color: 'white',
              mx: 1,
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.1)'
              }
            }}
          >
            Upload
          </Button>
          <Button
            component={Link}
            to="/vc-dashboard"
            startIcon={<Assessment />}
            sx={{
              color: 'white',
              mx: 1,
              backgroundColor: 'rgba(60, 223, 255, 0.15)',
              '&:hover': {
                backgroundColor: 'rgba(60, 223, 255, 0.25)'
              }
            }}
          >
            VC Dashboard
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;