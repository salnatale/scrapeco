import React, { useState } from 'react';
import { Container, Typography, Box, Paper } from '@mui/material';
import FileUploadForm from '../components/FileUploadForm';

const UploadPage = () => {
  // Single endpoint for all uploads
  const uploadEndpoint = 'http://localhost:5001/api/upload/resume';
  
  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: 'background.default',
        color: 'text.primary',
        pt: 4,
        pb: 8
      }}
    >
      <Container maxWidth="md">
        <Typography variant="h4" align="center" sx={{ fontWeight: 'bold', mb: 4, color: 'primary.main' }}>
          Upload Your Professional Profile
        </Typography>
        
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            borderRadius: 2,
            backgroundColor: 'background.paper',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)'
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 2 }}>
            Resume & LinkedIn Upload
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 3 }}>
            Upload your resume or LinkedIn data to visualize your career path and professional network. 
            We support PDF, DOCX, images, and other common file formats.
          </Typography>
          
          <FileUploadForm endpoint={uploadEndpoint} />
        </Paper>
      </Container>
    </Box>
  );
};

export default UploadPage;
