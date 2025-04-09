import React from 'react';
import { Box, Container, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        width: '100%',
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0E1117 0%, #2B2F36 100%)'
      }}
    >
      <Container
        maxWidth="md"
        sx={{
          textAlign: 'center',
          color: 'white',
          py: 8
        }}
      >
        <Typography variant="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
          Empower Your Private Market Insights
        </Typography>
        <Typography variant="body1" sx={{ mb: 4 }}>
          Ditch the spreadsheets. Collect your resume or LinkedIn data and harness cutting-edge analytics.
          Transform your career path data into meaningful intelligence for startups and professionals alike.
        </Typography>
        <Button
          variant="contained"
          size="large"
          onClick={() => navigate('/upload')}
          sx={{
            backgroundColor: 'primary.main',
            color: 'black',
            fontWeight: 'bold',
            '&:hover': {
              backgroundColor: 'primary.dark'
            }
          }}
        >
          Start Uploading
        </Button>
      </Container>
    </Box>
  );
};

export default HomePage;
