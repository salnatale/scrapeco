import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <AppBar
      position="static"
      sx={{
        backgroundColor: 'transparent',
        boxShadow: 'none',
        borderBottom: '1px solid rgba(255,255,255,0.1)'
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', px: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Intelligence Platform
        </Typography>
        <Box>
          <Button
            component={Link}
            to="/"
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
            to="/linkedin-instructions"
            sx={{
              color: 'white',
              mx: 1,
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.1)'
              }
            }}
          >
            LinkedIn Instructions
          </Button>
          <Button
            component={Link}
            to="/login"
            sx={{
              backgroundColor: '#0A66C2', // LinkedIn blue
              color: 'white',
              mx: 1,
              '&:hover': {
                backgroundColor: '#004182' // darker blue on hover
              }
            }}
          >
            Linkedin Login
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
