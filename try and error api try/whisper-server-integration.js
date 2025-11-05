/**
 * Node.js Integration for Whisper Transcription
 * Call Whisper from your Express server
 */

import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';

/**
 * Transcribe audio file using local Whisper
 * @param {string} audioPath - Path to audio file (.opus, .mp3, etc.)
 * @param {object} options - Transcription options
 * @returns {Promise<object>} Transcription result
 */
export async function transcribeWithWhisper(audioPath, options = {}) {
  const {
    model = 'base',      // tiny, base, small, medium, large
    language = 'en',     // Language code or null for auto-detect
    outputFormat = 'json' // txt, json, srt, vtt
  } = options;

  return new Promise((resolve, reject) => {
    // Build command arguments
    const args = [
      'transcribe-opus.py',
      audioPath,
      model
    ];

    if (language) {
      args.push(language);
    }

    // Spawn Python process
    const python = spawn('python', args);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', async (code) => {
      if (code !== 0) {
        reject(new Error(`Whisper failed: ${stderr || stdout}`));
        return;
      }

      try {
        // Read the generated JSON file
        const jsonPath = audioPath.replace(/\.[^.]+$/, '.json');
        const jsonContent = await fs.readFile(jsonPath, 'utf-8');
        const result = JSON.parse(jsonContent);

        resolve({
          success: true,
          text: result.text,
          language: result.language,
          segments: result.segments,
          duration: result.segments[result.segments.length - 1]?.end || 0,
          model: model,
          outputFiles: {
            json: jsonPath,
            txt: audioPath.replace(/\.[^.]+$/, '.txt'),
            srt: audioPath.replace(/\.[^.]+$/, '.srt')
          }
        });
      } catch (err) {
        reject(new Error(`Failed to read transcription result: ${err.message}`));
      }
    });

    python.on('error', (err) => {
      reject(new Error(`Failed to start Python process: ${err.message}`));
    });
  });
}

/**
 * Batch transcribe multiple files
 * @param {string} folderPath - Path to folder with audio files
 * @param {object} options - Transcription options
 * @returns {Promise<object>} Batch transcription results
 */
export async function batchTranscribeWithWhisper(folderPath, options = {}) {
  const {
    model = 'base',
    language = 'en',
    outputFormat = 'json'
  } = options;

  return new Promise((resolve, reject) => {
    const args = [
      'batch-transcribe.py',
      folderPath,
      model,
      language || 'auto',
      outputFormat
    ];

    const python = spawn('python', args);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
      // Log progress in real-time
      console.log(data.toString());
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', async (code) => {
      if (code !== 0) {
        reject(new Error(`Batch transcription failed: ${stderr || stdout}`));
        return;
      }

      try {
        // Read summary file
        const summaryPath = path.join(folderPath, 'transcripts', '_transcription_summary.json');
        const summaryContent = await fs.readFile(summaryPath, 'utf-8');
        const summary = JSON.parse(summaryContent);

        resolve({
          success: true,
          summary: summary,
          outputFolder: path.join(folderPath, 'transcripts')
        });
      } catch (err) {
        // If summary doesn't exist, still return success
        resolve({
          success: true,
          message: stdout,
          outputFolder: path.join(folderPath, 'transcripts')
        });
      }
    });

    python.on('error', (err) => {
      reject(new Error(`Failed to start Python process: ${err.message}`));
    });
  });
}

/**
 * Example Express route integration
 */
export function setupWhisperRoutes(app, upload) {
  // Single file transcription endpoint
  app.post('/api/transcribe-local', upload.single('audio'), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: 'No audio file uploaded' });
      }

      const result = await transcribeWithWhisper(req.file.path, {
        model: req.body.model || 'base',
        language: req.body.language || 'en'
      });

      res.json(result);
    } catch (error) {
      console.error('Transcription error:', error);
      res.status(500).json({ 
        error: 'Transcription failed', 
        details: error.message 
      });
    }
  });

  // Batch transcription endpoint
  app.post('/api/transcribe-batch', async (req, res) => {
    try {
      const { folder, model, language } = req.body;

      if (!folder) {
        return res.status(400).json({ error: 'Folder path required' });
      }

      const result = await batchTranscribeWithWhisper(folder, {
        model: model || 'base',
        language: language || 'en'
      });

      res.json(result);
    } catch (error) {
      console.error('Batch transcription error:', error);
      res.status(500).json({ 
        error: 'Batch transcription failed', 
        details: error.message 
      });
    }
  });
}

// Example usage:
/*
import express from 'express';
import multer from 'multer';
import { setupWhisperRoutes } from './whisper-server-integration.js';

const app = express();
const upload = multer({ dest: 'uploads/' });

setupWhisperRoutes(app, upload);

app.listen(3000, () => {
  console.log('Server running on http://localhost:3000');
});
*/

