const express = require('express');
const multer  = require('multer');
require('dotenv').config();
const path = require('path');
const fs = require('fs');


const app = express();
const port = process.env.PORT || 5001;
const axios = require('axios');




// Ensure the uploads directory exists
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)){
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
app.post('/api/upload/resume', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }
  res.json({ message: 'Resume uploaded successfully.', file: req.file.filename });
});

// Endpoint for LinkedIn screenshot uploads
app.post('/api/upload/linkedin', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).send({ error: 'No file uploaded.' });
  }
  res.json({ message: 'LinkedIn screenshot uploaded successfully.', file: req.file.filename });
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

    res.send(`<h2>Logged in as ${profile.localizedFirstName}</h2><p>Email: ${email}</p>`);
  } catch (err) {
    console.error(err.response?.data || err.message);
    res.status(500).send('LinkedIn authentication failed.');
  }
});