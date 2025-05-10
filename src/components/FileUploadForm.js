import React, { useState } from 'react';

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
                  backgroundColor: 'rgba(9, 211, 172, 0.08)'
                }
              }}
            >
              Select File
            </Button>
          </label>
        </Box> 