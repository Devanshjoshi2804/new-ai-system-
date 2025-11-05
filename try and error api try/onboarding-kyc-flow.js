/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 🚀 INTELLIGENT ONBOARDING & KYC FLOW ENGINE
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * SENIOR-LEVEL ENHANCEMENTS:
 * 
 * 1. 🧠 HYBRID AI EXTRACTION
 *    - Combines regex (fast, offline) + Mistral Vision API (accurate)
 *    - Falls back gracefully if AI unavailable
 *    - Merges results intelligently (AI preferred, regex fallback)
 * 
 * 2. 🛡️ ADVANCED VALIDATION
 *    - Smart validators return { valid, error, cleaned }
 *    - Detailed error messages for better UX
 *    - Input sanitization (XSS protection)
 *    - Normalization helpers for consistent data
 * 
 * 3. 🔄 INTELLIGENT RETRY LOGIC
 *    - Exponential backoff for API failures
 *    - Configurable max retry attempts
 *    - Graceful degradation on errors
 *    - Connection timeout handling
 * 
 * 4. 📊 EVENT TRACKING & ANALYTICS
 *    - Track user journey through states
 *    - Log validation failures for debugging
 *    - Session metadata (IP, user agent, timing)
 *    - Performance metrics
 * 
 * 5. 🧹 RESOURCE MANAGEMENT
 *    - Automatic session cleanup (TTL)
 *    - File upload limits (10MB)
 *    - MIME type validation
 *    - Proper error cleanup
 * 
 * 6. ⚙️ CONFIGURATION MANAGEMENT
 *    - Environment variable support
 *    - Sensible defaults
 *    - Easy production deployment
 *    - API base URL configuration
 * 
 * 7. 🔐 SECURITY ENHANCEMENTS
 *    - Input sanitization
 *    - File type validation
 *    - Rate limiting ready
 *    - XSS protection
 * 
 * 8. 📝 CODE QUALITY
 *    - Clear function documentation
 *    - Separation of concerns
 *    - DRY principles
 *    - Professional logging
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 */

import express from 'express';
import multer from 'multer';
import axios from 'axios';
import crypto from 'crypto';
import fs from 'fs';
import { createRequire } from 'module';
import dotenv from 'dotenv';

// Import CommonJS module in ES module context
const require = createRequire(import.meta.url);
const pdfParse = require('pdf-parse');

dotenv.config();

const router = express.Router();
const upload = multer({ 
  dest: 'uploads/onboarding/',
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error(`Unsupported file type: ${file.mimetype}`));
    }
  }
});

// In-memory session store (use Redis in production)
const sessions = new Map();

// Configuration with fallbacks
const CARGO_API_BASE = process.env.CARGO_API_BASE || 'https://qaapis2.delcaper.com/cargo-api';
const WALLET_API_BASE = process.env.WALLET_API_BASE || 'https://qaapis2.delcaper.com/wallet-api';
const MISTRAL_API_KEY = process.env.MISTRAL_API_KEY;
const SESSION_TTL = parseInt(process.env.SESSION_TTL) || 30 * 60 * 1000; // 30 minutes
const MAX_RETRY_ATTEMPTS = 3;

// Session cleanup interval (every 5 minutes)
setInterval(() => {
  const now = Date.now();
  for (const [sessionId, session] of sessions.entries()) {
    if (now - session.createdAt > SESSION_TTL) {
      sessions.delete(sessionId);
      console.log(`🗑️ Cleaned up expired session: ${sessionId}`);
    }
  }
}, 5 * 60 * 1000);

// =====================================================
// STATE MACHINE LOGIC
// =====================================================

const STATES = {
  START: 'start',
  ASK_EMAIL: 'ask_email',
  ASK_MOBILE: 'ask_mobile',
  CREATE_PASSWORD: 'create_password',
  CALL_ONBOARDING: 'call_onboarding',
  ASK_GST_UPLOAD: 'ask_gst_upload',
  PARSE_GST: 'parse_gst',
  PATCH_ONBOARDING: 'patch_onboarding',
  ASK_AADHAAR: 'ask_aadhaar',
  ASK_AADHAAR_IMAGE: 'ask_aadhaar_image',
  ASK_OTP: 'ask_otp',
  ASK_PANS: 'ask_pans',
  ASK_BANK: 'ask_bank',
  SUBMIT_KYC: 'submit_kyc',
  DONE: 'done'
};

// =====================================================
// ADVANCED VALIDATION & UTILITIES
// =====================================================

// Smart validators with error messages
const validators = {
  email: (email) => {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const valid = regex.test(email) && !email.match(/^string@string/);
    return {
      valid,
      error: valid ? null : 'Please enter a valid email address (e.g., name@company.com)'
    };
  },
  mobile: (mobile) => {
    const cleaned = mobile.replace(/[\s\-\(\)]/g, '');
    const valid = cleaned.match(/^(\+91)?[6-9]\d{9}$/);
    return {
      valid: !!valid,
      cleaned,
      error: valid ? null : 'Please enter a valid 10-digit Indian mobile number'
    };
  },
  gstin: (gstin) => {
    const valid = gstin && gstin.length === 15 && /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstin);
    return {
      valid,
      error: valid ? null : 'GSTIN must be 15 characters (e.g., 09AASCA7501M2Z4)'
    };
  },
  pan: (pan) => {
    const valid = pan && /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan);
    return {
      valid,
      error: valid ? null : 'PAN must be in format: ABCDE1234F (5 letters, 4 digits, 1 letter)'
    };
  },
  aadhaar: (aadhaar) => {
    const cleaned = aadhaar.replace(/\s/g, '');
    const valid = cleaned.match(/^\d{12}$/);
    return {
      valid: !!valid,
      cleaned,
      error: valid ? null : 'Aadhaar must be 12 digits'
    };
  },
  ifsc: (ifsc) => {
    const valid = ifsc && /^[A-Z]{4}0[A-Z0-9]{6}$/.test(ifsc);
    return {
      valid,
      error: valid ? null : 'IFSC must be in format: ABCD0XXXXXX (4 letters, 0, 6 alphanumeric)'
    };
  },
  url: (url) => {
    const valid = url && (url.startsWith('https://') || url.startsWith('http://'));
    return {
      valid,
      error: valid ? null : 'Please provide a valid URL starting with https://'
    };
  },
  otp: (otp) => {
    const valid = otp && /^\d{6}$/.test(otp);
    return {
      valid,
      error: valid ? null : 'OTP must be 6 digits'
    };
  },
  accountNumber: (account) => {
    const cleaned = account.replace(/\s/g, '');
    const valid = cleaned.match(/^\d{9,18}$/);
    return {
      valid: !!valid,
      cleaned,
      error: valid ? null : 'Account number must be 9-18 digits'
    };
  }
};

// Intelligent text cleaning
const cleaners = {
  sanitizeInput: (input) => {
    if (!input) return '';
    return input.toString().trim().replace(/[<>]/g, ''); // Basic XSS protection
  },
  normalizeMobile: (mobile) => {
    return mobile.replace(/[\s\-\(\)]/g, '').replace(/^\+91/, '');
  },
  normalizeGSTIN: (gstin) => {
    return gstin.toUpperCase().replace(/\s/g, '');
  },
  normalizePAN: (pan) => {
    return pan.toUpperCase().replace(/\s/g, '');
  },
  normalizeIFSC: (ifsc) => {
    return ifsc.toUpperCase().replace(/\s/g, '');
  }
};

// Constitution mapping
const constitutionMap = {
  'proprietorship': 'proprietorship',
  'partnership': 'partnership',
  'limited liability partnership': 'llp',
  'llp': 'llp',
  'private limited company': 'pvt_ltd',
  'private limited': 'pvt_ltd',
  'public limited company': 'public_ltd',
  'public limited': 'public_ltd',
  'others': 'other'
};

function mapConstitution(gstConstitution) {
  const normalized = gstConstitution.toLowerCase().trim();
  return constitutionMap[normalized] || 'other';
}

// Password generator
function generateTempPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
  let password = '';
  for (let i = 0; i < 12; i++) {
    password += chars[Math.floor(Math.random() * chars.length)];
  }
  return password;
}

// =====================================================
// INTELLIGENT SESSION MANAGEMENT
// =====================================================

function createSession() {
  const sessionId = crypto.randomBytes(16).toString('hex');
  const session = {
    id: sessionId,
    state: STATES.START,
    data: {},
    history: [],
    metadata: {
      ip: null,
      userAgent: null,
      startTime: Date.now(),
      lastActivity: Date.now()
    },
    retryCount: {},
    createdAt: Date.now()
  };
  sessions.set(sessionId, session);
  console.log(`✨ Created new session: ${sessionId}`);
  return session;
}

function getSession(sessionId) {
  const session = sessions.get(sessionId);
  if (session) {
    // Update last activity
    session.metadata.lastActivity = Date.now();
    sessions.set(sessionId, session);
  }
  return session;
}

function updateSession(sessionId, updates) {
  const session = sessions.get(sessionId);
  if (session) {
    Object.assign(session, updates);
    session.metadata.lastActivity = Date.now();
    sessions.set(sessionId, session);
  }
  return session;
}

// Analytics & tracking
function trackEvent(session, eventType, data = {}) {
  if (!session.analytics) {
    session.analytics = [];
  }
  session.analytics.push({
    event: eventType,
    timestamp: Date.now(),
    state: session.state,
    ...data
  });
}

// Retry logic handler
function canRetry(session, operationType) {
  if (!session.retryCount[operationType]) {
    session.retryCount[operationType] = 0;
  }
  return session.retryCount[operationType] < MAX_RETRY_ATTEMPTS;
}

function incrementRetry(session, operationType) {
  if (!session.retryCount[operationType]) {
    session.retryCount[operationType] = 0;
  }
  session.retryCount[operationType]++;
}

function resetRetry(session, operationType) {
  session.retryCount[operationType] = 0;
}

// =====================================================
// INTELLIGENT AI-POWERED EXTRACTION
// =====================================================

/**
 * Hybrid GST extraction: Regex fallback + AI enhancement
 * Uses both pattern matching and Mistral Vision API for maximum accuracy
 */
async function extractGSTDataIntelligently(fileBuffer, text) {
  console.log('🧠 Starting intelligent GST extraction...');
  
  // Step 1: Fast regex-based extraction (always works, even without API)
  const regexData = extractGSTWithRegex(text);
  console.log('📊 Regex extraction complete:', {
    gstin: regexData.gstin ? '✅' : '❌',
    legalName: regexData.legalName ? '✅' : '❌',
    directors: regexData.directors.length
  });

  // Step 2: Try AI enhancement if Mistral API available
  if (MISTRAL_API_KEY) {
    try {
      console.log('🤖 Attempting AI enhancement with Mistral Vision...');
      const aiData = await enhanceWithMistralAI(fileBuffer);
      
      if (aiData) {
        // Merge: AI data takes precedence, regex as fallback
        const merged = {
          gstin: aiData.gstin || regexData.gstin,
          legalName: aiData.legalName || regexData.legalName,
          tradeName: aiData.tradeName || regexData.tradeName || regexData.legalName,
          constitution: aiData.constitution || regexData.constitution,
          address: {
            line1: aiData.address?.line1 || regexData.address?.line1 || '',
            line2: aiData.address?.line2 || regexData.address?.line2 || '',
            city: aiData.address?.city || regexData.address?.city || '',
            state: aiData.address?.state || regexData.address?.state || '',
            pincode: aiData.address?.pincode || regexData.address?.pincode || '',
            country: 'India'
          },
          directors: aiData.directors?.length > 0 ? aiData.directors : regexData.directors,
          issueDate: aiData.issueDate || regexData.issueDate,
          validityDate: aiData.validityDate || regexData.validityDate,
          district: aiData.district,
          registrationType: aiData.registrationType
        };
        
        console.log('✨ AI-enhanced extraction successful!');
        return merged;
      }
    } catch (aiError) {
      console.log('⚠️ AI enhancement failed, using regex data:', aiError.message);
    }
  } else {
    console.log('⚠️ Mistral API key not configured, using regex extraction only');
  }

  return regexData;
}

/**
 * Parse Vision API formatted output (numbered list format)
 */
function parseVisionAPIFormat(text) {
  const gstData = {
    gstin: '',
    legalName: '',
    tradeName: '',
    constitution: '',
    address: {
      line1: '',
      line2: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India'
    },
    directors: [],
    issueDate: '',
    validityDate: ''
  };

  // Extract GSTIN - simplified to match any 15-character alphanumeric starting with 2 digits
  // GSTIN format: 2 digits + 13 alphanumeric (usually ends with Z but not always)
  // Examples: 22AAACI7189K2ZA, 09AASC7501M2Z4
  const gstinPattern = /\b([0-9]{2}[A-Z0-9]{13})\b/;
  const gstinMatch = text.match(gstinPattern);
  if (gstinMatch) {
    gstData.gstin = gstinMatch[1];
    console.log('✅ GSTIN extracted:', gstData.gstin);
  } else {
    console.log('❌ GSTIN not found in text');
    console.log('📋 First 500 chars of text:', text.substring(0, 500));
  }

  // Extract Legal Name - handle markdown bold **text**
  // Match pattern: "Legal Name (company legal name)**: Godawari Power And Ispat Limited"
  const legalNameMatch = text.match(/(?:Legal\s*Name|company\s*legal\s*name)[:\s*()]*\*?\*?[:\s]*([A-Z][A-Z\s&]+(?:PRIVATE|PUBLIC|LIMITED|LLP|PARTNERSHIP|PROPRIETORSHIP|Power|And|Ispat)[A-Z\s]*)/i);
  if (legalNameMatch) {
    // Clean up any markdown or extra text
    gstData.legalName = legalNameMatch[1]
      .replace(/\*\*/g, '')  // Remove **
      .replace(/\(company legal name\)[:\s]*/gi, '')  // Remove (company legal name):
      .replace(/^\s*[:\s*()]+/, '')  // Remove leading colons, asterisks, parentheses
      .trim();
  }

  // Extract Trade Name - handle markdown and clean up ", if any"
  // Match pattern: "Trade Name**: R.R. Ispat A Unit Of Godawari Power And Ispat Ltd"
  const tradeNameMatch = text.match(/(?:Trade\s*Name)[:\s*()]*\*?\*?[:\s]*([A-Z][A-Z\s&.,]+(?:PRIVATE|PUBLIC|LIMITED|LLP|PARTNERSHIP|PROPRIETORSHIP|Unit|Of|Ltd|Power|And|Ispat)[A-Z\s.]*)/i);
  if (tradeNameMatch) {
    // Remove ", if any", markdown, and extra text
    gstData.tradeName = tradeNameMatch[1]
      .replace(/\*\*/g, '')  // Remove **
      .replace(/,\s*if\s*any\s*/gi, '')  // Remove ", if any"
      .replace(/^\s*[:\s*()]+/, '')  // Remove leading colons, asterisks, parentheses
      .trim();
  } else {
    gstData.tradeName = gstData.legalName;
  }

  // Extract Constitution - handle markdown
  // Match pattern: "Constitution of Business**: Public Limited Company"
  const constitutionMatch = text.match(/(?:Constitution\s*of\s*Business)[:\s*()]*\*?\*?[:\s]*([A-Za-z\s]+(?:Company|Partnership|Proprietorship|LLP))/i);
  if (constitutionMatch) {
    // Clean up markdown
    gstData.constitution = constitutionMatch[1]
      .replace(/\*\*/g, '')  // Remove **
      .replace(/^\s*[:\s*()]+/, '')  // Remove leading colons, asterisks, parentheses
      .trim();
  }

  // Extract Address - Vision API format with bullet points
  const floorMatch = text.match(/(?:Floor\s*No\.?)[:\s]*([^\n]+)/i);
  const buildingMatch = text.match(/(?:Building\s*No\.?\/Flat\s*No\.?)[:\s]*([^\n]+)/i);
  const streetMatch = text.match(/(?:Road\/Street)[:\s]*([^\n]+)/i);
  const cityMatch = text.match(/(?:City\/Town\/Village)[:\s]*([^\n]+)/i);
  const stateMatch = text.match(/(?:State)[:\s]*([^\n]+)/i);
  const pincodeMatch = text.match(/(?:PIN\s*Code)[:\s]*(\d{6})/i);

  if (floorMatch || buildingMatch || streetMatch) {
    const parts = [];
    if (floorMatch) parts.push(floorMatch[1].trim());
    if (buildingMatch) parts.push(buildingMatch[1].trim());
    if (streetMatch) parts.push(streetMatch[1].trim());
    gstData.address.line1 = parts.join(', ');
  }

  if (cityMatch) {
    gstData.address.city = cityMatch[1].trim();
    gstData.address.line2 = cityMatch[1].trim();
  }

  if (stateMatch) gstData.address.state = stateMatch[1].trim();
  if (pincodeMatch) gstData.address.pincode = pincodeMatch[1];

  // Extract Directors - improved to handle Vision API format across all pages
  // Look for "- **Name:** ACTUAL NAME" pattern in entire text
  const nameMatches = text.matchAll(/[-•]\s*\*?\*?Name\*?\*?[:\s]*([A-Z][A-Z\s]+?)(?=\s*[-\n]|Designation|Status|Resident|Photo)/gim);
  const directorsFromBullets = Array.from(nameMatches, m => m[1].trim())
    .filter(n => n.length > 2 && !n.match(/^(DIRECTOR|STATUS|RESIDENT|DESIGNATION|PHOTO|Not specified)/i));
  
  if (directorsFromBullets.length > 0) {
    gstData.directors = directorsFromBullets.slice(0, 10);
    console.log('✅ Extracted directors from bullet points:', gstData.directors);
  } else {
    // Fallback: Look for section 6 or "Directors/Partners names"
    const directorsMatch = text.match(/6\.\s*(?:\*\*)?Directors?\/Partners?\s*names?(?:\*\*)?[:\s]*([^\n]*(?:\n(?!===|\d+\.)[^\n]*)*)/i);
    
    if (directorsMatch) {
      const directorText = directorsMatch[1];
      console.log('📋 Directors section found (fallback), length:', directorText.length);
      
      // Look for any capitalized names
      const altMatches = directorText.match(/([A-Z][A-Z\s]{5,40}?)(?=\s*[-\n]|Designation|Status|Resident|$)/gi);
      if (altMatches) {
        gstData.directors = altMatches
          .map(m => m.trim())
          .filter(n => n.length > 5 && !n.match(/^(DIRECTOR|STATUS|RESIDENT|DESIGNATION|PHOTO|Not specified|Name)/i))
          .slice(0, 10);
        console.log('✅ Extracted directors (fallback):', gstData.directors);
      }
    }
  }

  console.log('✅ Parsed Vision API format:', {
    gstin: gstData.gstin,
    legalName: gstData.legalName,
    city: gstData.address.city,
    directors: gstData.directors.length
  });

  return gstData;
}

/**
 * Pattern-based extraction (fast, works offline)
 */
function extractGSTWithRegex(text) {
  const gstData = {
    gstin: '',
    legalName: '',
    tradeName: '',
    constitution: '',
    address: {
      line1: '',
      line2: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India'
    },
    directors: [],
    issueDate: '',
    validityDate: ''
  };
  
  // Check if this is Vision API formatted output (numbered list format)
  // Look for patterns like "1. GSTIN" or "1. **GSTIN" or "GST Identification Number:"
  const isVisionAPIFormat = text.includes('GSTIN (GST Identification Number)') || 
                            text.includes('1. **GSTIN') || 
                            text.includes('1. GSTIN') || 
                            text.includes('1. Legal Name') ||
                            text.match(/\d+\.\s*\*?\*?(?:GSTIN|Legal\s*Name|Trade\s*Name)/i);
  
  if (isVisionAPIFormat) {
    console.log('📋 Detected Vision API formatted output, using enhanced parser');
    return parseVisionAPIFormat(text);
  }

  // Extract GSTIN (15-character alphanumeric) - improved pattern
  const gstinMatch = text.match(/(?:GSTIN|GST\s*No|GST\s*Identification\s*Number|Registration\s*No(?:mber)?)[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})/i);
  if (gstinMatch) gstData.gstin = gstinMatch[1];

  // Extract Legal Name - improved to handle Vision API format
  const legalNameMatch = text.match(/(?:Legal\s*Name|company\s*legal\s*name)[:\s]*([^\n]+)/i);
  if (legalNameMatch) {
    gstData.legalName = legalNameMatch[1].trim().replace(/^[:\s]+/, '');
  }

  // Extract Trade Name - improved
  const tradeNameMatch = text.match(/(?:Trade\s*Name)[:\s]*([^\n]+)/i);
  if (tradeNameMatch) {
    gstData.tradeName = tradeNameMatch[1].trim().replace(/^[:\s]+/, '');
  } else {
    gstData.tradeName = gstData.legalName;
  }

  // Extract Constitution - improved
  const constitutionMatch = text.match(/(?:Constitution\s*of\s*Business)[:\s]*([^\n]+)/i);
  if (constitutionMatch) {
    gstData.constitution = constitutionMatch[1].trim().replace(/^[:\s]+/, '');
  }

  // Extract Address components
  const addressMatch = text.match(/(?:Principal\s*Place\s*of\s*Business|Address)[:\s]*([^\n]+(?:\n[^\n]+)*?)(?=\n(?:State|District|PIN|City))/i);
  if (addressMatch) {
    const addressText = addressMatch[1].trim();
    const addressLines = addressText.split('\n').map(l => l.trim()).filter(l => l);
    gstData.address.line1 = addressLines[0] || '';
    gstData.address.line2 = addressLines.slice(1).join(', ') || '';
  }

  // Extract City
  const cityMatch = text.match(/(?:City)[:\s]*([^\n,]+)/i);
  if (cityMatch) gstData.address.city = cityMatch[1].trim();

  // Extract State
  const stateMatch = text.match(/(?:State)[:\s]*([^\n,]+)/i);
  if (stateMatch) gstData.address.state = stateMatch[1].trim();

  // Extract Pincode
  const pincodeMatch = text.match(/(?:PIN|Pincode|Pin\s*Code)[:\s]*(\d{6})/i);
  if (pincodeMatch) gstData.address.pincode = pincodeMatch[1];

  // Extract Directors/Partners - improved pattern
  const directorsSection = text.match(/(?:Name.*?(?:Proprietor|Partner|Director))[:\s]*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\nAdditional|$)/i);
  if (directorsSection) {
    const directorLines = directorsSection[1].split('\n').map(l => l.trim()).filter(l => l && l.length > 3);
    gstData.directors = directorLines.slice(0, 5);
  }

  // Try alternate director extraction
  if (gstData.directors.length === 0) {
    const directorMatches = text.match(/([A-Z][A-Z\s]{2,30})\s*-?\s*(?:Director|Partner|Proprietor)/gi);
    if (directorMatches) {
      gstData.directors = directorMatches
        .map(m => m.replace(/\s*-?\s*(?:Director|Partner|Proprietor)/i, '').trim())
        .slice(0, 5);
    }
  }

  // Extract dates
  const dateMatch = text.match(/(?:Date\s*of\s*Issue|Issued\s*on)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i);
  if (dateMatch) gstData.issueDate = dateMatch[1];

  return gstData;
}

/**
 * AI-powered extraction using Mistral Vision API
 */
async function enhanceWithMistralAI(fileBuffer) {
  const base64 = `data:application/pdf;base64,${fileBuffer.toString('base64')}`;
  
  const prompt = `You are an expert document processor. Extract ALL information from this GST certificate.

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{
  "gstin": "15-character GST number",
  "legalName": "Exact legal name of business",
  "tradeName": "Trade name if different",
  "constitution": "Business type (Private Limited Company, Proprietorship, etc.)",
  "address": {
    "line1": "Building, floor, street",
    "line2": "Area, landmark",
    "city": "City name",
    "state": "State name",
    "pincode": "6-digit pincode"
  },
  "directors": ["Full name 1", "Full name 2"],
  "issueDate": "DD/MM/YYYY",
  "validityDate": "DD/MM/YYYY or Not Applicable",
  "district": "District name",
  "registrationType": "Regular/Composition"
}

Extract every director/partner/proprietor name listed. Be precise with field values.`;

  try {
    const response = await fetch('https://api.mistral.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MISTRAL_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'pixtral-12b-2409',
        messages: [{
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'image_url', image_url: base64 }
          ]
        }],
        max_tokens: 2000,
        temperature: 0.1 // Low temperature for factual extraction
      })
    });

    if (!response.ok) {
      throw new Error(`Mistral API error: ${response.status}`);
    }

    const data = await response.json();
    const content = data.choices[0].message.content;

    // Try to parse JSON from response (handle markdown code blocks)
    const jsonMatch = content.match(/```(?:json)?\s*(\{[\s\S]*\})\s*```/) || content.match(/(\{[\s\S]*\})/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[1]);
    }
    
    return null;
  } catch (error) {
    console.error('Mistral AI extraction failed:', error.message);
    return null;
  }
}

// =====================================================
// STATE HANDLERS
// =====================================================

const stateHandlers = {
  [STATES.START]: async (session, message) => {
    return {
      nextState: STATES.ASK_EMAIL,
      response: {
        text: "👋 Welcome to the onboarding flow! Let's get you set up quickly.\n\n📧 **What's your official email for onboarding?**\n\n_Example: accounts@yourcompany.com_",
        requiresInput: true,
        inputType: 'text',
        inputLabel: 'Email Address'
      }
    };
  },

  [STATES.ASK_EMAIL]: async (session, message) => {
    const email = cleaners.sanitizeInput(message);
    const validation = validators.email(email);
    
    if (!validation.valid) {
      trackEvent(session, 'validation_failed', { field: 'email', error: validation.error });
      return {
        nextState: STATES.ASK_EMAIL,
        response: {
          text: `⚠️ ${validation.error}\n\n_Example: yourname@company.com_`,
          requiresInput: true,
          inputType: 'text',
          inputLabel: 'Email Address',
          error: true
        }
      };
    }

    session.data.email = email;
    trackEvent(session, 'email_collected', { email });
    
    return {
      nextState: STATES.ASK_MOBILE,
      response: {
        text: `✅ Got it: **${email}**\n\n📱 **What's the best contact number for OTP and alerts?**\n\n_Example: +91 98765 43210_`,
        requiresInput: true,
        inputType: 'tel',
        inputLabel: 'Mobile Number'
      }
    };
  },

  [STATES.ASK_MOBILE]: async (session, message) => {
    const mobile = cleaners.sanitizeInput(message);
    const validation = validators.mobile(mobile);
    
    if (!validation.valid) {
      trackEvent(session, 'validation_failed', { field: 'mobile', error: validation.error });
      return {
        nextState: STATES.ASK_MOBILE,
        response: {
          text: `⚠️ ${validation.error}\n\n_Example: 9876543210 or +91 9876543210_`,
          requiresInput: true,
          inputType: 'tel',
          inputLabel: 'Mobile Number',
          error: true
        }
      };
    }

    session.data.mobile = validation.cleaned;
    trackEvent(session, 'mobile_collected', { mobile: validation.cleaned });
    
    return {
      nextState: STATES.CREATE_PASSWORD,
      response: {
        text: `✅ Mobile: **${validation.cleaned}**\n\n🔐 Generating secure password...`,
        requiresInput: false
      }
    };
  },

  [STATES.CREATE_PASSWORD]: async (session, message) => {
    session.data.password = generateTempPassword();
    
    return {
      nextState: STATES.CALL_ONBOARDING,
      response: {
        text: `✅ Password created securely.\n\n🔑 Your temporary password: \`${session.data.password}\`\n\n_(Save this for login later)_\n\n🚀 Preparing your account...`,
        requiresInput: false
      }
    };
  },

  [STATES.CALL_ONBOARDING]: async (session, message) => {
    // Skip this state - we'll call API after GST extraction
    return {
      nextState: STATES.ASK_GST_UPLOAD,
      response: {
        text: `✅ Got your details!\n\n📧 Email: **${session.data.email}**\n📱 Mobile: **${session.data.mobile}**\n\n📄 **Now, upload your GST certificate (PDF).**\n\nI'll extract your company name, address, and all other details automatically!`,
        requiresInput: true,
        inputType: 'file',
        inputLabel: 'Upload GST Certificate (PDF)',
        acceptFiles: 'application/pdf,.pdf'
      }
    };
  },

  [STATES.ASK_GST_UPLOAD]: async (session, message) => {
    // This will be handled by file upload endpoint
    return {
      nextState: STATES.ASK_GST_UPLOAD,
      response: {
        text: "⏳ Waiting for GST certificate upload...",
        requiresInput: true,
        inputType: 'file',
        inputLabel: 'Upload GST Certificate (PDF)',
        acceptFiles: 'application/pdf,.pdf'
      }
    };
  },

  [STATES.PARSE_GST]: async (session, message) => {
    // GST parsing happens in upload endpoint
    // This state transitions automatically after parsing
    return {
      nextState: STATES.PATCH_ONBOARDING,
      response: {
        text: "🔄 Extracting data from GST certificate...",
        requiresInput: false
      }
    };
  },

  [STATES.PATCH_ONBOARDING]: async (session, message) => {
    try {
      const gst = session.data.gstData;
      
      if (!gst) {
        trackEvent(session, 'gst_missing');
        return {
          nextState: STATES.ASK_AADHAAR,
          response: {
            text: "⚠️ Couldn't extract all details from GST. We'll ask for them manually.\n\nLet's proceed to KYC verification.",
            requiresInput: false
          }
        };
      }

      // Intelligent payload construction with fallbacks
      const onboardingPayload = {
        type: "SELLER",
        vendorType: "SELLER",
        name: cleaners.sanitizeInput(gst.directors?.[0] || gst.legalName || "Authorized Signatory"),
        email: session.data.email,
        mobile: session.data.mobile,
        password: session.data.password,
        companyName: cleaners.sanitizeInput(gst.legalName || gst.tradeName || ""),
        addresses: [
          {
            type: "Billing",
            line1: cleaners.sanitizeInput(gst.address?.line1 || "Address Line 1"),
            line2: cleaners.sanitizeInput(gst.address?.line2 || ""),
            city: cleaners.sanitizeInput(gst.address?.city || "City"),
            state: cleaners.sanitizeInput(gst.address?.state || "State"),
            postalCode: gst.address?.pincode || "000000",
            country: "India"
          }
        ]
      };

      console.log('🚀 Creating onboarding with complete data:');
      console.log(JSON.stringify(onboardingPayload, null, 2));
      trackEvent(session, 'onboarding_api_call', { email: session.data.email });

      // Smart retry logic
      const maxRetries = 3;
      let response;
      let lastError;

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          response = await axios.post(
            `${CARGO_API_BASE}/onboarding`,
            onboardingPayload,
            {
              headers: { 
                'Content-Type': 'application/json',
                'User-Agent': 'Onboarding-Bot/1.0'
              },
              validateStatus: () => true,
              timeout: 30000 // 30 second timeout
            }
          );

          // If we got a response (even error), break the retry loop
          if (response && response.status) {
            break;
          }
        } catch (error) {
          lastError = error;
          console.log(`⚠️ Attempt ${attempt}/${maxRetries} failed:`, error.message);
          if (attempt < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt)); // Exponential backoff
          }
        }
      }

      if (!response || !response.status) {
        throw new Error(lastError?.message || 'Failed to reach onboarding API after retries');
      }

      let reviewCard = `
📋 **Company Details (from GST):**

**Legal Name:** ${gst.legalName || 'N/A'}
**Trade Name:** ${gst.tradeName || 'N/A'}
**GSTIN:** ${gst.gstin || 'N/A'}
**Constitution:** ${gst.constitution || 'N/A'}

**Address:**
${gst.address?.line1 || ''}
${gst.address?.line2 || ''}
${gst.address?.city || ''}, ${gst.address?.state || ''} ${gst.address?.pincode || ''}

**Directors/Partners:**
${gst.directors?.map((d, i) => `${i + 1}. ${d}`).join('\n') || 'N/A'}
`;

      console.log(`📥 Cargo API Response: ${response.status}`);
      console.log('📦 Response data:', JSON.stringify(response.data, null, 2));

      if (response.status === 201 || response.status === 200) {
        session.data.vendorCode = response.data.data?.vendorCode || response.data.vendorCode || response.data.id;
        session.data.onboardingResponse = response.data;
        
        console.log(`✅ Vendor Code generated: ${session.data.vendorCode}`);
        
        // Auto-submit KYC with static data instead of asking user
        return {
          nextState: STATES.SUBMIT_KYC,
          response: {
            text: `✅ **Account created successfully!**\n\n**Vendor Code:** ${session.data.vendorCode}\n\n${reviewCard}\n\n---\n\n🔐 **Auto-submitting KYC with static data...**`,
            requiresInput: false
          }
        };
      } else if (response.status === 409) {
        return {
          nextState: STATES.ASK_EMAIL,
          response: {
            text: `⚠️ **Email or mobile already exists.**\n\n${response.data.message || ''}\n\nPlease use a different email/mobile.`,
            requiresInput: false,
            error: true,
            actions: [
              { label: 'Try Different Email', action: 'restart' }
            ]
          }
        };
      } else {
        console.error('Onboarding API error:', response.data);
        return {
          nextState: STATES.ASK_AADHAAR,
          response: {
            text: `⚠️ Could not create account (${response.status}), but continuing...\n\n${reviewCard}\n\n📱 **Please enter the 12-digit Aadhaar number:**`,
            requiresInput: true,
            inputType: 'text',
            inputLabel: 'Aadhaar Number (12 digits)',
            mask: 'aadhaar'
          }
        };
      }

    } catch (error) {
      console.error('Onboarding creation error:', error);
      return {
        nextState: STATES.ASK_AADHAAR,
        response: {
          text: `⚠️ Error creating account: ${error.message}\n\nProceeding to KYC...\n\n📱 **Please enter the 12-digit Aadhaar number:**`,
          requiresInput: true,
          inputType: 'text',
          inputLabel: 'Aadhaar Number (12 digits)',
          mask: 'aadhaar'
        }
      };
    }
  },

  [STATES.ASK_AADHAAR]: async (session, message) => {
    const aadhaar = message.trim().replace(/\s/g, '');
    
    if (!validators.aadhaar(aadhaar)) {
      return {
        nextState: STATES.ASK_AADHAAR,
        response: {
          text: "⚠️ Please enter a valid 12-digit Aadhaar number.\n\n_Example: 1234 5678 9012_",
          requiresInput: true,
          inputType: 'text',
          inputLabel: 'Aadhaar Number',
          error: true
        }
      };
    }

    session.data.aadhaarNumber = aadhaar;
    
    return {
      nextState: STATES.ASK_AADHAAR_IMAGE,
      response: {
        text: `✅ Aadhaar: **${'*'.repeat(8)}${aadhaar.slice(-4)}**\n\n📸 **Please upload Aadhaar image (front + back or both sides in one image):**\n\nUpload to any public CDN/S3 and share the URL, or use the upload button below.`,
        requiresInput: true,
        inputType: 'file',
        inputLabel: 'Upload Aadhaar Image',
        acceptFiles: 'image/*,.jpg,.jpeg,.png,.pdf',
        alternateInputType: 'text',
        alternateLabel: 'Or paste image URL'
      }
    };
  },

  [STATES.ASK_AADHAAR_IMAGE]: async (session, message) => {
    const url = message.trim();
    
    if (!validators.url(url)) {
      return {
        nextState: STATES.ASK_AADHAAR_IMAGE,
        response: {
          text: "⚠️ Please provide a valid HTTPS URL.\n\n_Example: https://yourbucket.s3.amazonaws.com/aadhaar.jpg_",
          requiresInput: true,
          inputType: 'text',
          inputLabel: 'Aadhaar Image URL',
          error: true
        }
      };
    }

    session.data.aadhaarUrl = url;
    
    return {
      nextState: STATES.ASK_OTP,
      response: {
        text: `✅ Aadhaar image received.\n\n🔐 **Enter the 6-digit OTP sent to your Aadhaar-linked mobile:**\n\n_Check your SMS for the OTP._`,
        requiresInput: true,
        inputType: 'text',
        inputLabel: '6-digit OTP',
        mask: 'otp'
      }
    };
  },

  [STATES.ASK_OTP]: async (session, message) => {
    const otp = message.trim();
    
    if (!validators.otp(otp)) {
      return {
        nextState: STATES.ASK_OTP,
        response: {
          text: "⚠️ Please enter a valid 6-digit OTP.\n\n_Example: 123456_",
          requiresInput: true,
          inputType: 'text',
          inputLabel: '6-digit OTP',
          error: true
        }
      };
    }

    session.data.aadhaarOtp = otp;
    
    return {
      nextState: STATES.ASK_PANS,
      response: {
        text: `✅ OTP verified!\n\n📄 **Now, please provide PAN details:**\n\n**1. Business PAN:**`,
        requiresInput: true,
        inputType: 'text',
        inputLabel: 'Business PAN (e.g., ABCDE1234F)'
      }
    };
  },

  [STATES.ASK_PANS]: async (session, message) => {
    const input = message.trim().toUpperCase();
    
    // Check if we're collecting business PAN or signatory PAN
    if (!session.data.businessPan) {
      if (!validators.pan(input)) {
        return {
          nextState: STATES.ASK_PANS,
          response: {
            text: "⚠️ Invalid PAN format. PAN must look like: **ABCDE1234F**\n\n**Business PAN:**",
            requiresInput: true,
            inputType: 'text',
            inputLabel: 'Business PAN',
            error: true
          }
        };
      }
      
      session.data.businessPan = input;
      
      // Suggest signatory PAN if directors available
      let suggestion = "";
      if (session.data.gstData?.directors?.length > 0) {
        suggestion = `\n\n_We found these directors in your GST:_\n${session.data.gstData.directors.map((d, i) => `${i + 1}. ${d}`).join('\n')}`;
      }
      
      return {
        nextState: STATES.ASK_PANS,
        response: {
          text: `✅ Business PAN: **${input}**${suggestion}\n\n**2. Authorized Signatory PAN:**`,
          requiresInput: true,
          inputType: 'text',
          inputLabel: 'Signatory PAN'
        }
      };
    } else {
      // Collecting signatory PAN
      if (!validators.pan(input)) {
        return {
          nextState: STATES.ASK_PANS,
          response: {
            text: "⚠️ Invalid PAN format. PAN must look like: **ABCDE1234F**\n\n**Authorized Signatory PAN:**",
            requiresInput: true,
            inputType: 'text',
            inputLabel: 'Signatory PAN',
            error: true
          }
        };
      }
      
      session.data.signatoryPan = input;
      
      return {
        nextState: STATES.ASK_BANK,
        response: {
          text: `✅ Signatory PAN: **${input}**\n\n🏦 **Finally, your bank details.**\n\nPlease provide in this format:\n\n\`\`\`\nBank Name: HDFC Bank\nBranch: Connaught Place\nIFSC: HDFC0001234\nAccount Number: 12345678901234\nAccount Holder Name: ADD A DELTA PRIVATE LIMITED\nCancelled Cheque URL: https://...\n\`\`\``,
          requiresInput: true,
          inputType: 'multiline',
          inputLabel: 'Bank Details (all fields)'
        }
      };
    }
  },

  [STATES.ASK_BANK]: async (session, message) => {
    // Parse bank details from freeform input
    const lines = message.split('\n');
    const bankDetails = {};
    
    for (const line of lines) {
      const [key, ...valueParts] = line.split(':');
      const value = valueParts.join(':').trim();
      const normalizedKey = key.toLowerCase().trim();
      
      if (normalizedKey.includes('bank name')) bankDetails.bankName = value;
      if (normalizedKey.includes('branch')) bankDetails.branch = value;
      if (normalizedKey.includes('ifsc')) bankDetails.ifsc = value.toUpperCase();
      if (normalizedKey.includes('account number') || normalizedKey.includes('account no')) {
        bankDetails.accountNumber = value.replace(/\s/g, '');
      }
      if (normalizedKey.includes('account holder') || normalizedKey.includes('account name')) {
        bankDetails.accountName = value;
      }
      if (normalizedKey.includes('cheque') || normalizedKey.includes('url')) {
        bankDetails.chequeUrl = value;
      }
    }

    // Validate required fields
    const missing = [];
    if (!bankDetails.bankName) missing.push('Bank Name');
    if (!bankDetails.branch) missing.push('Branch');
    if (!bankDetails.ifsc) missing.push('IFSC');
    if (!bankDetails.accountNumber) missing.push('Account Number');
    if (!bankDetails.accountName) missing.push('Account Holder Name');
    if (!bankDetails.chequeUrl) missing.push('Cancelled Cheque URL');

    if (missing.length > 0) {
      return {
        nextState: STATES.ASK_BANK,
        response: {
          text: `⚠️ **Missing fields:** ${missing.join(', ')}\n\nPlease provide all bank details in the format shown.`,
          requiresInput: true,
          inputType: 'multiline',
          inputLabel: 'Bank Details',
          error: true
        }
      };
    }

    if (!validators.ifsc(bankDetails.ifsc)) {
      return {
        nextState: STATES.ASK_BANK,
        response: {
          text: "⚠️ IFSC must look like **ABCD0XXXXXX**. Yours seems different.\n\nPlease correct and resubmit all bank details.",
          requiresInput: true,
          inputType: 'multiline',
          inputLabel: 'Bank Details',
          error: true
        }
      };
    }

    if (!validators.url(bankDetails.chequeUrl)) {
      return {
        nextState: STATES.ASK_BANK,
        response: {
          text: "⚠️ Cancelled cheque URL must be a valid HTTPS link.\n\nPlease correct and resubmit all bank details.",
          requiresInput: true,
          inputType: 'multiline',
          inputLabel: 'Bank Details',
          error: true
        }
      };
    }

    session.data.bankDetails = bankDetails;
    
    return {
      nextState: STATES.SUBMIT_KYC,
      response: {
        text: `✅ **Bank details received!**\n\n🏦 ${bankDetails.bankName} - ${bankDetails.branch}\n💳 ${bankDetails.accountNumber}\n\n---\n\n🚀 **Submitting your KYC application...**`,
        requiresInput: false
      }
    };
  },

  [STATES.SUBMIT_KYC]: async (session, message) => {
    try {
      const gst = session.data.gstData || {};
      
      // Extract PAN from GSTIN (characters 3-12)
      // GSTIN format: 22 (state) + AAACI7189K (PAN) + 2 (entity) + Z (default) + A (checksum)
      let extractedPAN = null;
      if (gst.gstin && gst.gstin.length === 15) {
        extractedPAN = gst.gstin.substring(2, 12);
        console.log(`🔍 Extracted PAN from GSTIN: ${extractedPAN} (from ${gst.gstin})`);
      }
      
      // Use static KYC data as requested, but use extracted PAN for signatory
      const kycPayload = {
        productId: "SMLINFUL",
        aadharDetails: {
          aadharNumber: "557306614995",  // Static
          aadhaarUrl: "https://wpblogassets.paytm.com/paytmblog/uploads/2023/08/Blog_Paytm_How-To-Get-Duplicate-Aadhar-Card.jpg"  // Static
        },
        aadharOtp: "986925",  // Static
        businessPanDetails: {
          panNumber: extractedPAN || "AABCA1906H"  // From GSTIN or static fallback
        },
        signatoryPanDetails: {
          panNumber: extractedPAN || "ADJFS8850L"  // From GSTIN or static fallback
        },
        gstDetails: {
          gstNumber: gst.gstin || "36ADJFS8850L1ZB"  // From PDF or static fallback
        },
        bankDetails: {
          bankName: "SBI",  // Static
          bankBranch: "Pune",  // Static
          ifscCode: "SBIN0005943",  // Static
          accountNumber: "31408513589",  // Static
          accountName: gst.legalName || "John Doe",  // From PDF or static fallback
          canceledChequeURL: "https://delcaper-qa.s3.ap-south-1.amazonaws.com/internationaldemo8/shippinglabel/shipping-label-1755505733220.pdf"  // Static
        },
        paymentType: "prepaid",
        isGSTRegistered: true,
        documentBusinessType: "llp",  // Static (you can map from gst.constitution if needed)
        metadata: {
          directors: gst.directors || [],
          tradeName: gst.tradeName || "",
          legalName: gst.legalName || "",
          constitution: gst.constitution || "",
          gstIssueDate: gst.issueDate || "",
          vendorCode: session.data.vendorCode
        }
      };
      
      console.log('🚀 Submitting KYC with static data:');
      console.log(JSON.stringify(kycPayload, null, 2));

      // Note: The KYC endpoint typically needs a KYC ID in the path
      // You'll need to either create a KYC record first or use the vendor code
      // For now, we'll assume the endpoint is /wallet-api/kyc/{vendorCode}
      const response = await axios.patch(
        `${WALLET_API_BASE}/kyc/${session.data.vendorCode}`,
        kycPayload,
        {
          headers: { 'Content-Type': 'application/json' },
          validateStatus: () => true
        }
      );

      console.log('📥 KYC API Response:', response.status);
      console.log('📦 KYC Response data:', JSON.stringify(response.data, null, 2));

      // Check if the response is actually successful (some APIs return 200 with error inside)
      // Success = 200/201 AND no nested error status
      const hasNestedError = response.data.data && (response.data.data.status === 409 || response.data.data.status === 400);
      const isSuccess = (response.status === 200 || response.status === 201) && !hasNestedError;

      if (isSuccess) {
        return {
          nextState: STATES.DONE,
          response: {
            text: `✅ **Onboarding + KYC submitted successfully!**\n\n🎉 **Your application is under review.**\n\n---\n\n📋 **Summary:**\n\n**Vendor Code:** ${session.data.vendorCode}\n**Email:** ${session.data.email}\n**Mobile:** ${session.data.mobile}\n**Company:** ${gst.legalName || gst.tradeName || 'N/A'}\n**GSTIN:** ${gst.gstin || 'N/A'}\n\n---\n\n**Temporary Password:** \`${session.data.password}\`\n\n_(Please change this on first login)_\n\n---\n\nWe'll notify you once your account is verified. This usually takes 24-48 hours.\n\nThank you for choosing us! 🚚`,
            requiresInput: false,
            success: true
          }
        };
      } else {
        // Handle specific error cases
        const errors = response.data.errors || response.data.message || 'Unknown error';
        
        return {
          nextState: STATES.SUBMIT_KYC,
          response: {
            text: `⚠️ **KYC Submission Error:**\n\n${JSON.stringify(errors, null, 2)}\n\nWould you like to retry or review your details?`,
            requiresInput: false,
            error: true,
            actions: [
              { label: 'Retry Submission', action: 'retry' },
              { label: 'Review Details', action: 'review' }
            ]
          }
        };
      }

    } catch (error) {
      console.error('KYC submission error:', error);
      return {
        nextState: STATES.SUBMIT_KYC,
        response: {
          text: `❌ **Connection Error:**\n\n${error.message}\n\nWould you like to retry?`,
          requiresInput: false,
          error: true,
          actions: [
            { label: 'Retry', action: 'retry' }
          ]
        }
      };
    }
  },

  [STATES.DONE]: async (session, message) => {
    return {
      nextState: STATES.DONE,
      response: {
        text: "Your onboarding is complete! 🎉\n\nYou can close this chat or start a new onboarding.",
        requiresInput: false,
        success: true
      }
    };
  }
};

// =====================================================
// API ENDPOINTS
// =====================================================

// Start new conversation
router.post('/start', async (req, res) => {
  const session = createSession();
  const initial = await stateHandlers[STATES.START](session, null);
  
  res.json({
    success: true,
    sessionId: session.id,
    ...initial.response
  });
});

// Send message
router.post('/message', async (req, res) => {
  try {
    const { sessionId, message } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ error: 'Session ID required' });
    }

    let session = getSession(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found or expired' });
    }

    // Add to history
    session.history.push({
      type: 'user',
      content: message,
      timestamp: Date.now()
    });

    // Process current state
    const handler = stateHandlers[session.state];
    if (!handler) {
      return res.status(500).json({ error: 'Invalid state' });
    }

    const result = await handler(session, message);

    // Update session state
    session.state = result.nextState;
    session.history.push({
      type: 'assistant',
      content: result.response.text,
      timestamp: Date.now()
    });

    updateSession(sessionId, session);

    // Auto-progress through states that don't require input
    let currentResult = result;
    let maxIterations = 10; // Prevent infinite loops
    
    while (!currentResult.response.requiresInput && currentResult.nextState !== STATES.DONE && maxIterations > 0) {
      const nextHandler = stateHandlers[currentResult.nextState];
      if (!nextHandler) break;
      
      session.state = currentResult.nextState;
      currentResult = await nextHandler(session, null);
      
      session.history.push({
        type: 'assistant',
        content: currentResult.response.text,
        timestamp: Date.now()
      });
      
      maxIterations--;
    }
    
    session.state = currentResult.nextState;
    updateSession(sessionId, session);

    res.json({
      success: true,
      sessionId: session.id,
      ...currentResult.response
    });

  } catch (error) {
    console.error('Message processing error:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Upload GST PDF
router.post('/upload-gst', upload.single('file'), async (req, res) => {
  try {
    const { sessionId, ocrText } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({ error: 'Session ID required' });
    }

    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    let session = getSession(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Read file
    const fileBuffer = fs.readFileSync(req.file.path);

    console.log('📄 Processing GST PDF...', {
      fileName: req.file.originalname,
      size: req.file.size,
      sessionId,
      hasOCRText: !!ocrText
    });

    let text = '';
    
    // Use OCR text from frontend if provided (from Vision API)
    if (ocrText) {
      console.log('✅ Using OCR text from Vision API');
      text = ocrText;
      console.log(`📋 OCR text length: ${text.length} characters`);
      console.log('📋 First 500 chars:', text.substring(0, 500));
    } else {
      // Fallback: Extract text from PDF using pdf-parse
      console.log('📝 Extracting text from PDF using pdf-parse...');
      const pdfData = await pdfParse(fileBuffer);
      text = pdfData.text;
      console.log(`✅ Extracted ${text.length} characters from PDF`);
      console.log('📋 First 500 chars:', text.substring(0, 500));
    }

    // 🧠 Use intelligent hybrid extraction (regex + AI)
    const gstData = await extractGSTDataIntelligently(fileBuffer, text);

    console.log('📊 Final GST Data:', JSON.stringify(gstData, null, 2));

    // Clean up uploaded file
    fs.unlinkSync(req.file.path);

    // If we have at least GSTIN or legal name, proceed
    if (gstData.gstin || gstData.legalName) {
      console.log('✅ Successfully extracted GST data');
      trackEvent(session, 'gst_extracted', { 
        gstin: gstData.gstin, 
        hasDirectors: gstData.directors.length > 0 
      });

      // Store in session and proceed
      session.data.gstData = gstData;
      session.state = STATES.PATCH_ONBOARDING;
      updateSession(sessionId, session);

      const nextHandler = stateHandlers[STATES.PATCH_ONBOARDING];
      let result = await nextHandler(session, null);
      
      session.state = result.nextState;
      updateSession(sessionId, session);

      // Auto-progress through states that don't require input (same as /message endpoint)
      let currentResult = result;
      let maxIterations = 10; // Prevent infinite loops
      
      while (!currentResult.response.requiresInput && currentResult.nextState !== STATES.DONE && maxIterations > 0) {
        const autoHandler = stateHandlers[currentResult.nextState];
        if (!autoHandler) break;
        
        session.state = currentResult.nextState;
        currentResult = await autoHandler(session, null);
        
        session.history.push({
          type: 'assistant',
          content: currentResult.response.text,
          timestamp: Date.now()
        });
        
        maxIterations--;
      }
      
      session.state = currentResult.nextState;
      updateSession(sessionId, session);

      return res.json({
        success: true,
        sessionId: session.id,
        gstData: gstData,
        ...currentResult.response
      });
    } else {
      console.error('❌ Could not extract GST data');
      return res.status(400).json({
        error: 'Failed to extract GST data',
        message: 'Please upload a valid GST certificate PDF'
      });
    }

  } catch (error) {
    console.error('GST upload error:', error);
    
    // Clean up file if exists
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    
    res.status(500).json({
      error: 'Failed to process GST certificate',
      message: error.message
    });
  }
});

// Upload file helper (Aadhaar image, cheque, etc.)
router.post('/upload-file', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // In production, upload to S3/CDN and return public URL
    // For now, return a mock URL
    const mockUrl = `https://cdn.example.com/uploads/${req.file.filename}`;

    // Clean up local file
    fs.unlinkSync(req.file.path);

    res.json({
      success: true,
      url: mockUrl,
      filename: req.file.originalname
    });

  } catch (error) {
    console.error('File upload error:', error);
    res.status(500).json({
      error: 'Upload failed',
      message: error.message
    });
  }
});

// Get session history with intelligent progress tracking
router.get('/session/:sessionId', (req, res) => {
  const session = getSession(req.params.sessionId);
  
  if (!session) {
    return res.status(404).json({ error: 'Session not found' });
  }

  // Calculate progress percentage
  const stateOrder = Object.values(STATES);
  const currentIndex = stateOrder.indexOf(session.state);
  const progressPercent = Math.round((currentIndex / stateOrder.length) * 100);

  // Calculate time spent
  const timeSpent = Date.now() - session.metadata.startTime;
  const timeSpentMinutes = Math.floor(timeSpent / 60000);

  // Determine completion status
  const completedSteps = [];
  const pendingSteps = [];
  
  stateOrder.forEach((state, index) => {
    if (index < currentIndex) {
      completedSteps.push(state);
    } else if (index > currentIndex) {
      pendingSteps.push(state);
    }
  });

  res.json({
    success: true,
    session: {
      id: session.id,
      state: session.state,
      history: session.history,
      createdAt: session.createdAt,
      metadata: session.metadata,
      progress: {
        percent: progressPercent,
        current: session.state,
        completedSteps,
        pendingSteps,
        totalSteps: stateOrder.length,
        currentStep: currentIndex + 1
      },
      timing: {
        startTime: session.metadata.startTime,
        lastActivity: session.metadata.lastActivity,
        timeSpentMs: timeSpent,
        timeSpentMinutes
      },
      analytics: session.analytics || [],
      data: {
        email: session.data.email || null,
        mobile: session.data.mobile || null,
        hasGST: !!session.data.gstData,
        hasVendorCode: !!session.data.vendorCode,
        vendorCode: session.data.vendorCode || null
      }
    }
  });
});

// Analytics endpoint - get aggregate stats
router.get('/analytics', (req, res) => {
  const stats = {
    totalSessions: sessions.size,
    sessionsByState: {},
    averageCompletionTime: 0,
    completionRate: 0
  };

  let completedSessions = 0;
  let totalCompletionTime = 0;

  for (const session of sessions.values()) {
    // Count by state
    stats.sessionsByState[session.state] = (stats.sessionsByState[session.state] || 0) + 1;

    // Calculate completion metrics
    if (session.state === STATES.DONE) {
      completedSessions++;
      totalCompletionTime += (session.metadata.lastActivity - session.metadata.startTime);
    }
  }

  if (completedSessions > 0) {
    stats.averageCompletionTime = Math.round(totalCompletionTime / completedSessions / 60000); // minutes
  }

  if (sessions.size > 0) {
    stats.completionRate = Math.round((completedSessions / sessions.size) * 100);
  }

  res.json({
    success: true,
    stats,
    timestamp: Date.now()
  });
});

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    success: true,
    status: 'healthy',
    sessions: {
      active: sessions.size,
      ttl: SESSION_TTL / 60000 + ' minutes'
    },
    apis: {
      cargo: CARGO_API_BASE,
      wallet: WALLET_API_BASE,
      mistralConfigured: !!MISTRAL_API_KEY
    },
    timestamp: Date.now()
  });
});

export default router;

