import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import multer from 'multer';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import onboardingRouter from './onboarding-kyc-flow.js';

dotenv.config();

const app = express();
const upload = multer({ dest: 'uploads/' });

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static('public'));
app.use('/advanced_catbox', express.static('advanced_catbox'));

// Onboarding + KYC API routes
app.use('/api/onboarding', onboardingRouter);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', message: 'Mistral OCR API Server Running' });
});

// Vision OCR Endpoint
app.post('/api/vision', async (req, res) => {
  try {
    const { imageBase64, prompt, model } = req.body;

    if (!imageBase64) {
      return res.status(400).json({ error: 'No image provided' });
    }

    // Detect file type
    const isPDF = imageBase64.startsWith('data:application/pdf');
    const fileType = isPDF ? 'PDF' : 'Image';
    const sizeKB = Math.round(imageBase64.length / 1024);
    
    console.log(`📄 Processing ${fileType} with Mistral Vision API`);
    console.log(`📊 Data size: ${sizeKB} KB`);
    console.log(`📝 Prompt length: ${prompt?.length || 0} characters`);

    // Call Mistral API
    const response = await fetch('https://api.mistral.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.MISTRAL_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: model || 'pixtral-12b-2409',
        messages: [{
          role: 'user',
          content: [
            {
              type: 'text',
              text: prompt || 'Extract all text and data from this image'
            },
            {
              type: 'image_url',
              image_url: imageBase64
            }
          ]
        }],
        max_tokens: 2000
      })
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('❌ Mistral Vision API Error:', {
        status: response.status,
        error: data.error?.message || data.message,
        type: data.error?.type,
        code: data.error?.code,
        fileType,
        sizeKB
      });
      
      return res.status(response.status).json({
        error: data.error?.message || data.message || 'Mistral API error',
        details: data,
        hint: `${fileType} size: ${sizeKB} KB. Check if file is too large or format is unsupported.`
      });
    }

    console.log(`✅ ${fileType} processed successfully!`);

    res.json({
      success: true,
      content: data.choices[0].message.content,
      usage: data.usage,
      model: data.model,
      fileType
    });

  } catch (error) {
    console.error('❌ Vision API Server Error:', error);
    res.status(500).json({
      error: 'Server error',
      message: error.message
    });
  }
});

// Audio Transcription Endpoint
app.post('/api/audio', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }
    
    const ext = path.extname(req.file.originalname).toLowerCase();
    
    console.log('📁 Audio file received:', {
      filename: req.file.originalname,
      mimetype: req.file.mimetype,
      size: req.file.size,
      extension: ext
    });

    // Check if file is WhatsApp audio format (not supported by Mistral API)
    if (ext === '.opus' || (ext === '.ogg' && req.file.originalname.includes('whatsapp'))) {
      // Clean up uploaded file
      fs.unlinkSync(req.file.path);
      
      return res.status(400).json({
        error: 'WhatsApp audio format not supported',
        message: 'WhatsApp .opus/.ogg files need to be converted to MP3 or WAV first',
        solution: {
          option1: 'Use online converter: https://cloudconvert.com/opus-to-mp3',
          option2: 'Use https://www.online-convert.com/',
          option3: 'Or install FFmpeg and convert with: ffmpeg -i input.opus output.mp3'
        },
        detectedFormat: ext,
        supportedFormats: ['mp3', 'wav', 'm4a', 'flac']
      });
    }

    // Use form-data package for proper multipart/form-data
    const FormData = (await import('form-data')).default;
    const formData = new FormData();
    
    // Create a readable stream from the file
    const audioStream = fs.createReadStream(req.file.path);
    
    // Handle audio formats
    let contentType = req.file.mimetype;
    if (!contentType || contentType === 'application/octet-stream') {
      // Detect format from filename extension
      if (ext === '.mp3') {
        contentType = 'audio/mpeg';
      } else if (ext === '.wav') {
        contentType = 'audio/wav';
      } else if (ext === '.m4a') {
        contentType = 'audio/mp4';
      } else if (ext === '.flac') {
        contentType = 'audio/flac';
      }
    }
    
    formData.append('file', audioStream, {
      filename: req.file.originalname,
      contentType: contentType
    });
    
    // Use Mistral audio model - voxtral-small-latest is confirmed available
    formData.append('model', 'voxtral-small-latest');

    const response = await fetch('https://api.mistral.ai/v1/audio/transcriptions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.MISTRAL_API_KEY}`,
        ...formData.getHeaders()
      },
      body: formData
    });

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    // Handle response - check if it's JSON or text
    let data;
    const responseContentType = response.headers.get('content-type');
    
    try {
      if (responseContentType && responseContentType.includes('application/json')) {
        data = await response.json();
      } else {
        // If not JSON, get as text and try to parse
        const textResponse = await response.text();
        console.log('Raw API response:', textResponse);
        
        try {
          data = JSON.parse(textResponse);
        } catch (parseError) {
          // If parsing fails, treat as plain text transcription
          data = { text: textResponse };
        }
      }
    } catch (error) {
      console.error('Error parsing response:', error);
      return res.status(500).json({
        error: 'Failed to parse API response',
        message: error.message
      });
    }

    if (!response.ok) {
      console.error('❌ Mistral Audio API Error:', {
        status: response.status,
        statusText: response.statusText,
        error: data
      });
      return res.status(response.status).json({
        error: data.error?.message || 'Mistral API error',
        details: data,
        suggestion: 'Try converting WhatsApp audio to MP3 format or check API key'
      });
    }

    console.log('✅ Transcription successful:', {
      model: data.model,
      textLength: (data.text || '').length
    });

    res.json({
      success: true,
      transcription: data.text || data.transcription || JSON.stringify(data),
      model: data.model || 'voxtral-small-latest'
    });

  } catch (error) {
    // Clean up uploaded file if it exists
    if (req.file && fs.existsSync(req.file.path)) {
      try {
        fs.unlinkSync(req.file.path);
      } catch (cleanupError) {
        console.error('Error cleaning up file:', cleanupError);
      }
    }
    
    console.error('Audio transcription error:', error);
    res.status(500).json({
      error: 'Server error',
      message: error.message
    });
  }
});

// Local Whisper Transcription Endpoint (supports .opus files!)
app.post('/api/audio-local', upload.single('audio'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    const originalPath = req.file.path;
    const ext = path.extname(req.file.originalname).toLowerCase();
    
    // Rename file to have proper extension for Whisper
    const newPath = `${originalPath}${ext}`;
    fs.renameSync(originalPath, newPath);

    console.log('🎙️ Processing with local Whisper:', {
      filename: req.file.originalname,
      size: req.file.size,
      extension: ext
    });

    // Get model and language from request
    // Use 'large' for maximum accuracy with numbers/pincodes (slower but most accurate)
    const model = req.body.model || 'large';
    const language = req.body.language || 'en';

    // Call Python Whisper script
    const python = spawn('python', [
      'transcribe-opus.py',
      newPath,
      model,
      language
    ]);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
      console.log(data.toString());
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', async (code) => {
      // Clean up files
      try {
        if (fs.existsSync(newPath)) fs.unlinkSync(newPath);
        
        if (code !== 0) {
          console.error('❌ Whisper error:', stderr);
          return res.status(500).json({
            error: 'Transcription failed',
            message: stderr || 'Unknown error',
            stdout: stdout
          });
        }

        // Read the generated JSON file
        const jsonPath = newPath.replace(/\.[^.]+$/, '.json');
        
        if (!fs.existsSync(jsonPath)) {
          return res.status(500).json({
            error: 'Transcription output not found',
            message: 'JSON file was not created'
          });
        }

        const result = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
        
        // Clean up generated files
        const txtPath = newPath.replace(/\.[^.]+$/, '.txt');
        const srtPath = newPath.replace(/\.[^.]+$/, '.srt');
        
        if (fs.existsSync(jsonPath)) fs.unlinkSync(jsonPath);
        if (fs.existsSync(txtPath)) fs.unlinkSync(txtPath);
        if (fs.existsSync(srtPath)) fs.unlinkSync(srtPath);

        console.log('✅ Local transcription successful:', {
          textLength: result.text.length,
          language: result.language,
          duration: result.segments[result.segments.length - 1]?.end || 0
        });

        res.json({
          success: true,
          transcription: result.text.trim(),
          language: result.language,
          duration: result.segments[result.segments.length - 1]?.end || 0,
          segments: result.segments,
          model: model,
          source: 'local-whisper'
        });

      } catch (cleanupError) {
        console.error('Cleanup/parse error:', cleanupError);
        res.status(500).json({
          error: 'Failed to process transcription',
          message: cleanupError.message
        });
      }
    });

    python.on('error', (err) => {
      // Clean up on error
      if (fs.existsSync(newPath)) {
        try {
          fs.unlinkSync(newPath);
        } catch (e) {
          console.error('Error cleaning up:', e);
        }
      }
      
      console.error('Failed to start Python:', err);
      res.status(500).json({
        error: 'Failed to start transcription process',
        message: err.message,
        hint: 'Make sure Python and Whisper are installed (run test-whisper.bat)'
      });
    });

  } catch (error) {
    // Clean up uploaded file if it exists
    if (req.file && fs.existsSync(req.file.path)) {
      try {
        fs.unlinkSync(req.file.path);
      } catch (cleanupError) {
        console.error('Error cleaning up file:', cleanupError);
      }
    }
    
    console.error('Local transcription error:', error);
    res.status(500).json({
      error: 'Server error',
      message: error.message
    });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Mistral OCR Server running on http://localhost:${PORT}`);
  console.log(`📝 Test endpoint: http://localhost:${PORT}/api/health`);
});

