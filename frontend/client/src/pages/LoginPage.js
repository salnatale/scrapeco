import React from 'react';
import { Button, Box, Typography } from '@mui/material';

const linkedinClientId = process.env.REACT_APP_LINKEDIN_CLIENT_ID;
// print the value of linkedinClientId to console
console.log('LinkedIn Client ID:', linkedinClientId);
const redirectUri = 'http://localhost:5001/auth/linkedin/callback';

const handleLinkedInLogin = () => {
  const scope = 'r_liteprofile r_emailaddress';
  const state = crypto.randomUUID(); // temp: can use a static string
  const authUrl = `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${linkedinClientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${scope}&state=${state}`;
  window.location.href = authUrl;
};

const LoginPage = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8 }}>
      <Typography variant="h4" gutterBottom>
        Please Login to Continue
      </Typography>
      <Button onClick={handleLinkedInLogin} variant="contained" color="primary">
        Login with LinkedIn
      </Button>
    </Box>
  );
};

export default LoginPage;
