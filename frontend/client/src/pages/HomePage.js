import React from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  Grid, 
  Card, 
  CardContent, 
  CardActions,
  Divider
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { 
  CloudUpload, 
  Insights, 
  AccountTree, 
  TrendingUp 
} from '@mui/icons-material';

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        width: '100%',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(135deg, #0F172A 0%, #25314D 100%)'
      }}
    >
      {/* Hero Section */}
      <Box 
        sx={{
          pt: 12,
          pb: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Container
          maxWidth="md"
          sx={{
            textAlign: 'center',
            color: 'white'
          }}
        >
          <Typography variant="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
            Visualize Your Career Path
          </Typography>
          
          <Typography variant="h5" sx={{ mb: 4, color: 'primary.main' }}>
            Interactive Graph Visualization for Private Market Insights
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 4, fontSize: '1.1rem' }}>
            Transform your professional history into powerful visual insights. Upload your LinkedIn profile 
            or resume data to generate interactive graph visualizations that reveal your career transitions, 
            skill connections, and professional network in a Neo4j-like graph format.
          </Typography>
          
          <Button
            variant="contained"
            size="large"
            startIcon={<CloudUpload />}
            onClick={() => navigate('/upload')}
            sx={{
              backgroundColor: 'primary.main',
              color: 'primary.contrastText',
              fontWeight: 'bold',
              py: 1.5,
              px: 4,
              fontSize: '1.1rem',
              '&:hover': {
                backgroundColor: 'primary.dark'
              }
            }}
          >
            Upload & Visualize Now
          </Button>
        </Container>
      </Box>
      
      {/* Feature Cards Section */}
      <Box sx={{ py: 8, backgroundColor: 'rgba(15, 23, 42, 0.7)' }}>
        <Container maxWidth="lg">
          <Typography variant="h4" sx={{ color: 'white', mb: 6, textAlign: 'center', fontWeight: 'bold' }}>
            How It Works
          </Typography>
          
          <Grid container spacing={4}>
            {/* Card 1: Upload */}
            <Grid item xs={12} md={4}>
              <Card sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                backgroundColor: 'background.paper',
                color: 'text.primary',
                transition: 'transform 0.3s',
                '&:hover': {
                  transform: 'translateY(-10px)'
                }
              }}>
                <Box sx={{ 
                  p: 2, 
                  display: 'flex', 
                  justifyContent: 'center', 
                  backgroundColor: 'rgba(60, 223, 255, 0.1)'
                }}>
                  <CloudUpload sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h5" component="h2" gutterBottom>
                    1. Upload Your Data
                  </Typography>
                  <Typography variant="body2">
                    Simply upload your LinkedIn profile export or resume data. 
                    Our system securely processes your professional information.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    size="small" 
                    onClick={() => navigate('/linkedin-instructions')}
                    sx={{ color: 'primary.main' }}
                  >
                    How to Export LinkedIn Data
                  </Button>
                </CardActions>
              </Card>
            </Grid>
            
            {/* Card 2: Analyze */}
            <Grid item xs={12} md={4}>
              <Card sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                backgroundColor: 'background.paper',
                color: 'text.primary',
                transition: 'transform 0.3s',
                '&:hover': {
                  transform: 'translateY(-10px)'
                }
              }}>
                <Box sx={{ 
                  p: 2, 
                  display: 'flex', 
                  justifyContent: 'center', 
                  backgroundColor: 'rgba(60, 223, 255, 0.1)'
                }}>
                  <Insights sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h5" component="h2" gutterBottom>
                    2. Smart Analysis
                  </Typography>
                  <Typography variant="body2">
                    Our system analyzes your career history, skills, education, and 
                    professional connections to identify meaningful patterns and relationships.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    size="small" 
                    sx={{ color: 'primary.main' }}
                  >
                    Learn More
                  </Button>
                </CardActions>
              </Card>
            </Grid>
            
            {/* Card 3: Visualize */}
            <Grid item xs={12} md={4}>
              <Card sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                backgroundColor: 'background.paper',
                color: 'text.primary',
                transition: 'transform 0.3s',
                '&:hover': {
                  transform: 'translateY(-10px)'
                }
              }}>
                <Box sx={{ 
                  p: 2, 
                  display: 'flex', 
                  justifyContent: 'center', 
                  backgroundColor: 'rgba(60, 223, 255, 0.1)'
                }}>
                  <AccountTree sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h5" component="h2" gutterBottom>
                    3. Interactive Visualization
                  </Typography>
                  <Typography variant="body2">
                    Explore your professional journey as an interactive graph. Zoom, filter, 
                    and highlight connections to gain insights about your career transitions.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    size="small" 
                    onClick={() => navigate('/results')}
                    sx={{ color: 'primary.main' }}
                  >
                    See Example
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          </Grid>
        </Container>
      </Box>
      
      {/* Benefits Section */}
      <Box sx={{ py: 8 }}>
        <Container maxWidth="md">
          <Typography variant="h4" sx={{ color: 'white', mb: 4, textAlign: 'center', fontWeight: 'bold' }}>
            Discover Hidden Insights
          </Typography>
          
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" sx={{ color: 'primary.main', mb: 2 }}>
                  Interactive Graph Visualizations
                </Typography>
                <Typography variant="body1" sx={{ color: 'white', mb: 3 }}>
                  Our Neo4j-style graph visualizations allow you to:
                </Typography>
                <Box component="ul" sx={{ color: 'white', pl: 2 }}>
                  <Typography component="li" variant="body1" sx={{ mb: 1 }}>
                    Visualize career progression through connected nodes
                  </Typography>
                  <Typography component="li" variant="body1" sx={{ mb: 1 }}>
                    Identify key relationships between skills and opportunities
                  </Typography>
                  <Typography component="li" variant="body1" sx={{ mb: 1 }}>
                    Discover patterns in your professional development
                  </Typography>
                  <Typography component="li" variant="body1">
                    Explore interactive transitions between roles and companies
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box 
                sx={{ 
                  height: 300, 
                  backgroundColor: 'background.paper',
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid rgba(60, 223, 255, 0.3)',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
                }}
              >
                <TrendingUp sx={{ fontSize: 120, color: 'primary.main', opacity: 0.7 }} />
              </Box>
            </Grid>
          </Grid>
          
          <Box sx={{ mt: 6, textAlign: 'center' }}>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/upload')}
              sx={{
                borderColor: 'primary.main',
                color: 'primary.main',
                fontWeight: 'bold',
                '&:hover': {
                  borderColor: 'primary.light',
                  backgroundColor: 'rgba(9, 211, 172, 0.08)'
                }
              }}
            >
              Start Exploring Your Career Graph
            </Button>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default HomePage;
