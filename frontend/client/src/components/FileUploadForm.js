import React, { useState } from 'react';
import { Box, Button, Typography, Paper } from '@mui/material';

const FileUploadForm = ({ endpoint }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        await response.json();
        setUploadStatus('Upload successful!');
      } else {
        setUploadStatus('Upload failed.');
      }
    } catch (error) {
      setUploadStatus('An error occurred during upload.');
    }
  };

  return (
    <Paper sx={{ p: 3, backgroundColor: 'background.paper', color: 'text.primary' }}>
      <Typography variant="body1" sx={{ mb: 2 }}>
        Choose an image to upload:
      </Typography>
      <input
        accept="image/*"
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
            mr: 2,
            '&:hover': {
              borderColor: 'primary.dark',
              backgroundColor: 'transparent'
            }
          }}
        >
          Select File
        </Button>
      </label>
      <Button
        variant="contained"
        onClick={handleUpload}
        disabled={!selectedFile}
        sx={{
          backgroundColor: 'primary.main',
          color: 'black',
          fontWeight: 'bold',
          '&:hover': {
            backgroundColor: 'primary.dark'
          }
        }}
      >
        Upload
      </Button>
      {selectedFile && (
        <Typography variant="body2" sx={{ mt: 2 }}>
          Selected File: {selectedFile.name}
        </Typography>
      )}
      {uploadStatus && (
        <Typography variant="body2" sx={{ mt: 2 }}>
          {uploadStatus}
        </Typography>
      )}
    </Paper>
  );
};

export default FileUploadForm;
