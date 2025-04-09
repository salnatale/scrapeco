import React from 'react';
import { Container, Typography, List, ListItem, ListItemText, Box } from '@mui/material';

const LinkedinInstructionsPage = () => {
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
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
          LinkedIn Homepage Screenshot Instructions
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
          Follow these steps to capture your LinkedIn homepage:
        </Typography>
        <List>
          <ListItem>
            <ListItemText primary="1. Log in to your LinkedIn account." />
          </ListItem>
          <ListItem>
            <ListItemText primary="2. Navigate to your homepage/dashboard." />
          </ListItem>
          <ListItem>
            <ListItemText primary="3. Make sure all relevant info is visible in your browser window." />
          </ListItem>
          <ListItem>
            <ListItemText primary="4. Use your system's screenshot tool (or press Print Screen)." />
          </ListItem>
          <ListItem>
            <ListItemText primary="5. Crop or edit if needed to keep only useful areas." />
          </ListItem>
          <ListItem>
            <ListItemText primary="6. Return here and use the upload functionality to submit your screenshot." />
          </ListItem>
        </List>
      </Container>
    </Box>
  );
};

export default LinkedinInstructionsPage;
