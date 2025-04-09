import React, { useState } from 'react';
import { Container, Typography, Tabs, Tab, Box } from '@mui/material';
import FileUploadForm from '../components/FileUploadForm';

const UploadPage = () => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (_, newValue) => {
    setTabValue(newValue);
  };

  const resumeUploadEndpoint = 'http://localhost:5001/api/upload/resume';
  const linkedinUploadEndpoint = 'http://localhost:5001/api/upload/linkedin';
  
  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: 'background.default',
        color: 'text.primary',
        pt: 4
      }}
    >
      <Container>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          centered
          textColor="inherit"
          TabIndicatorProps={{ style: { backgroundColor: '#09D3AC' } }}
        >
          <Tab label="Resume Upload" />
          <Tab label="LinkedIn Screenshot Upload" />
        </Tabs>
        <Box sx={{ mt: 4 }}>
          {tabValue === 0 && (
            <>
              <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 2 }}>
                Resume Upload
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                Upload a picture of your resume.
              </Typography>
              <FileUploadForm endpoint={resumeUploadEndpoint} />
            </>
          )}
          {tabValue === 1 && (
            <>
              <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 2 }}>
                LinkedIn Screenshot Upload
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                Upload a screenshot of your LinkedIn homepage.
              </Typography>
              <FileUploadForm endpoint={linkedinUploadEndpoint} />
            </>
          )}
        </Box>
      </Container>
    </Box>
  );
};

export default UploadPage;
