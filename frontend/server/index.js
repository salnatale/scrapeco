const express = require('express');
const multer = require('multer');
const FormData = require('form-data');
require('dotenv').config();
const path = require('path');
const fs = require('fs');


const app = express();
const port = process.env.PORT || 5001;
const axios = require('axios');


console.log("Starting Express server...");

// Ensure the uploads directory exists
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

const cors = require('cors');
app.use(cors());


// Configure storage for multer
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    // Prepend a timestamp to the original filename
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ storage: storage });

// Endpoint for resume uploads
app.post('/api/upload/resume', upload.single('file'), async (req, res) => {
  console.log('/api/upload/resume endpoint hit');
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }

  const uploadedFilePath = path.join(__dirname, 'uploads', req.file.filename);

  try {
    // Send file to FastAPI for processing
    const form = new FormData();
    form.append('file', fs.createReadStream(uploadedFilePath), req.file.originalname);

    const fastApiRes = await axios.post(
      'http://localhost:8000/api/upload/resume', // your FastAPI resume endpoint
      form,
      { headers: form.getHeaders() }
    );

    console.log('Resume processed by FastAPI:', fastApiRes.data);

    // Respond to client
    res.json({
      message: 'Resume uploaded and processed successfully.',
      file: req.file.filename,
      fastApiResponse: fastApiRes.data
    });

  } catch (err) {
    console.error('Failed to process resume via FastAPI:', err.message);
    res.status(500).send({
      error: 'Resume uploaded but processing failed.',
      detail: err.message
    });
  }
});

// Endpoint for LinkedIn screenshot uploads
app.post('/api/upload/linkedin', upload.single('file'), async (req, res) => {
  console.log('/api/upload/linkedin endpoint hit');
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }

  const uploadedFilePath = path.join(__dirname, 'uploads', req.file.filename);

  try {
    // Send file to FastAPI for processing
    const form = new FormData();
    form.append('file', fs.createReadStream(uploadedFilePath), req.file.originalname);

    const fastApiRes = await axios.post(
      'http://localhost:8000/api/upload/linkedin', // fastAPI endpoint
      form,
      { headers: form.getHeaders() }
    );

    console.log('File processed by FastAPI:', fastApiRes.data);

    // Respond back to client
    res.json({
      message: 'LinkedIn screenshot uploaded and processed successfully.',
      file: req.file.filename,
      fastApiResponse: fastApiRes.data
    });
    // error handling

  } catch (err) {
    console.error('Failed to process file via FastAPI:', err.message);
    res.status(500).send({
      error: 'File uploaded but processing failed.',
      detail: err.message
    });
  }
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});


// LinkedIn OAuth callback
app.get('/auth/linkedin/callback', async (req, res) => {
  const { code } = req.query;

  try {
    const tokenRes = await axios.post('https://www.linkedin.com/oauth/v2/accessToken', null, {
      params: {
        grant_type: 'authorization_code',
        code,
        redirect_uri: 'http://localhost:5001/auth/linkedin/callback',
        client_id: process.env.LINKEDIN_CLIENT_ID,
        client_secret: process.env.LINKEDIN_CLIENT_SECRET
      },
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });

    const accessToken = tokenRes.data.access_token;

    // Optional: Fetch profile data
    const profileRes = await axios.get('https://api.linkedin.com/v2/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    const emailRes = await axios.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))', {
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    const profile = profileRes.data;
    const email = emailRes.data.elements[0]['handle~'].emailAddress;

    // Do something with profile/email (e.g., create user, session, etc.)
    console.log(profile, email);

    const profileData = {
      id: profile.id,
      firstName: profile.localizedFirstName,
      lastName: profile.localizedLastName,
      email: email,
      headline: profile.headline || '',
      // Add more fields as needed -> determine what we can get from LinkedIn login,
    };

    // 🔁 Send to FastAPI backend
    const fastApiRes = await axios.post('http://localhost:8000/api/db/store_profile', profileData);

    console.log('✅ Sent to FastAPI:', fastApiRes.data);


    res.send(`<h2>Logged in as ${profile.localizedFirstName}</h2><p>Email: ${email}</p>`);
  } catch (err) {
    console.error(err.response?.data || err.message);
    res.status(500).send('LinkedIn authentication failed.');
  }
});