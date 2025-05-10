import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  LinearProgress, 
  Alert, 
  AlertTitle,
  Stack,
  CircularProgress,
  Fade
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { CloudUpload, CheckCircle, Error } from '@mui/icons-material';

const FileUploadForm = ({ endpoint }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle', 'uploading', 'success', 'error'
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus('idle');
      setErrorMessage('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    // Reset state
    setUploadStatus('uploading');
    setUploadProgress(0);
    setErrorMessage('');
    
    // Create FormData object
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Use XMLHttpRequest to track upload progress
      const xhr = new XMLHttpRequest();
      
      // Set up progress tracking
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });
      
      // Set up completion handler
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setUploadStatus('success');
          
          // Parse the response to get profile data
          try {
            const responseData = JSON.parse(xhr.responseText);
            
            // Wait 1 second before navigating (to show success state)
            setTimeout(() => {
              navigate('/results', { state: { profileData: responseData } });
            }, 1000);
          } catch (parseError) {
            console.error('Error parsing response:', parseError);
            // If can't parse response, still navigate but without data
            setTimeout(() => {
              navigate('/results');
            }, 1000);
          }
        } else {
          setUploadStatus('error');
          setErrorMessage(`Server responded with status code ${xhr.status}`);
        }
      });
      
      // Set up error handler
      xhr.addEventListener('error', () => {
        setUploadStatus('error');
        setErrorMessage('An error occurred during upload. Please try again.');
      });
      
      // Set up timeout handler
      xhr.addEventListener('timeout', () => {
        setUploadStatus('error');
        setErrorMessage('Request timed out. Please check your connection and try again.');
      });
      
      // Open and send the request
      xhr.open('POST', endpoint);
      xhr.timeout = 30000; // 30 second timeout
      xhr.send(formData);
      
    } catch (error) {
      setUploadStatus('error');
      setErrorMessage('An unexpected error occurred. Please try again.');
      console.error('Upload error:', error);
    }
  };

  // Render different UI based on upload status
  const renderUploadStatus = () => {
    switch (uploadStatus) {
      case 'uploading':
        return (
          <Box sx={{ width: '100%', mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Uploading: {uploadProgress}%
            </Typography>
            <LinearProgress variant="determinate" value={uploadProgress} color="primary" />
          </Box>
        );
        
      case 'success':
        return (
          <Alert severity="success" sx={{ mt: 2 }}>
            <AlertTitle>Success</AlertTitle>
            Upload complete! Navigating to results...
            <CircularProgress size={20} sx={{ ml: 2 }} />
          </Alert>
        );
        
      case 'error':
        return (
          <Alert severity="error" sx={{ mt: 2 }}>
            <AlertTitle>Error</AlertTitle>
            {errorMessage || 'An error occurred during upload. Please try again.'}
          </Alert>
        );
        
      default:
        return null;
    }
  };

  return (
    <Paper 
      elevation={3}
      sx={{ 
        p: 3, 
        backgroundColor: 'background.paper', 
        color: 'text.primary',
        borderRadius: 2,
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)'
      }}
    >
      <Stack spacing={2} alignItems="center">
        <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
        
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          Upload Your Professional Profile
        </Typography>
        
        <Typography variant="body1" sx={{ mb: 2, textAlign: 'center' }}>
          Upload your resume, LinkedIn profile data, or photo of your resume to visualize your career path and professional network. We support PDF, DOCX, images, and other common file formats.
        </Typography>
        
        <Box sx={{ width: '100%', textAlign: 'center' }}>
          <input
            accept=".json,.csv,.xml,.pdf,.docx,.doc,.txt,.rtf,.html,.htm,.odt,.jpg,.jpeg,.png,.gif,.tiff,.bmp"
            style={{ display: 'none' }}
            id="upload-file"
            type="file"
            onChange={handleFileChange}
          />
          <label htmlFor="upload-file">
            <Button
              variant="outlined"
              component="span"
              sx={{
                borderColor: 'primary.main',
                color: 'primary.main',
                py: 1.5,
                px: 3,
                mr: 2,
                '&:hover': {
                  borderColor: 'primary.dark',
                  backgroundColor: 'rgba(60, 223, 255, 0.08)'
                }
              }}
            >
              Select File
            </Button>
          </label>
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!selectedFile || uploadStatus === 'uploading'}
            sx={{
              backgroundColor: 'primary.main',
              color: 'primary.contrastText',
              fontWeight: 'bold',
              py: 1.5,
              px: 3,
              '&:hover': {
                backgroundColor: 'primary.dark'
              }
            }}
          >
            {uploadStatus === 'uploading' ? (
              <>
                Uploading... <CircularProgress size={20} sx={{ ml: 1, color: 'black' }} />
              </>
            ) : (
              'Upload & Visualize'
            )}
          </Button>
        </Box>
        
        {selectedFile && (
          <Fade in={!!selectedFile}>
            <Alert severity="info" sx={{ mt: 2, width: '100%' }}>
              <AlertTitle>Selected File</AlertTitle>
              {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
            </Alert>
          </Fade>
        )}
        
        {renderUploadStatus()}
      </Stack>
    </Paper>
  );
};

export default FileUploadForm;
