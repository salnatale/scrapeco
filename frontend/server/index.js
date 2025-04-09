const express = require('express');
const multer  = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 5001;

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
