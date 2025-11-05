import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 🧪 SIMPLE TEST: Use Chatbot Flow with Real PDF
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * This test uses the chatbot's existing flow which already:
 * 1. Converts PDF to images
 * 2. Calls Vision API
 * 3. Parses the data
 * 
 * We just need to verify the extracted data is correct!
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 */

const LOCAL_API = 'http://localhost:3000/api';
const CARGO_API = 'https://qaapis2.delcaper.com/cargo-api';

async function testSimple() {
  console.log('╔═══════════════════════════════════════════════════════════════╗');
  console.log('║   🧪 SIMPLE TEST WITH CHATBOT FLOW                           ║');
  console.log('╚═══════════════════════════════════════════════════════════════╝');
  console.log('');

  try {
    const timestamp = Date.now();
    const email = `test.simple.${timestamp}@delcaper.com`;
    const mobile = `98${String(timestamp).slice(-8)}`;

    // Step 1: Start session
    console.log('📝 Starting session...');
    const startResp = await axios.post(`${LOCAL_API}/onboarding/start`, {});
    const sessionId = startResp.data.sessionId;
    console.log(`✅ Session: ${sessionId}\n`);

    // Step 2: Send email
    console.log(`📧 Sending email: ${email}`);
    await axios.post(`${LOCAL_API}/onboarding/message`, {
      sessionId,
      message: email
    });
    console.log('✅ Email sent\n');

    // Step 3: Send mobile
    console.log(`📱 Sending mobile: ${mobile}`);
    await axios.post(`${LOCAL_API}/onboarding/message`, {
      sessionId,
      message: mobile
    });
    console.log('✅ Mobile sent\n');

    // Step 4: Get session data to see what happened
    console.log('📊 Checking session data...');
    const sessionResp = await axios.get(`${LOCAL_API}/onboarding/session/${sessionId}`);
    const session = sessionResp.data;

    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('SESSION DATA:');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(JSON.stringify(session, null, 2));
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('');

    // Check if we have GST data
    if (session.data?.gstData) {
      const gst = session.data.gstData;
      
      console.log('✅ GST DATA FOUND!');
      console.log('');
      console.log('📋 Extracted Data:');
      console.log(`   GSTIN: ${gst.gstin || '❌ MISSING'}`);
      console.log(`   Legal Name: ${gst.legalName || '❌ MISSING'}`);
      console.log(`   Trade Name: ${gst.tradeName || '❌ MISSING'}`);
      console.log(`   Constitution: ${gst.constitution || '❌ MISSING'}`);
      console.log(`   Address: ${gst.address?.line1 || '❌ MISSING'}`);
      console.log(`   City: ${gst.address?.city || '❌ MISSING'}`);
      console.log(`   State: ${gst.address?.state || '❌ MISSING'}`);
      console.log(`   Pincode: ${gst.address?.pincode || '❌ MISSING'}`);
      console.log(`   Directors: ${gst.directors?.length || 0} found`);
      if (gst.directors && gst.directors.length > 0) {
        gst.directors.forEach((d, i) => console.log(`      ${i + 1}. ${d}`));
      }
      console.log('');

      // Check what's missing
      const issues = [];
      if (!gst.gstin) issues.push('GSTIN');
      if (!gst.directors || gst.directors.length === 0) issues.push('Directors');

      if (issues.length > 0) {
        console.log('⚠️  ISSUES FOUND:');
        issues.forEach(issue => console.log(`   ❌ ${issue} not extracted`));
        console.log('');
        console.log('💡 This means the regex patterns need more work!');
      } else {
        console.log('✅ ALL DATA EXTRACTED SUCCESSFULLY!');
      }
    } else {
      console.log('⚠️  No GST data in session yet');
      console.log('💡 You need to upload GST.pdf via the chatbot first');
    }

    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║                  ✅ TEST COMPLETE                             ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');

  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
    throw error;
  }
}

testSimple()
  .then(() => process.exit(0))
  .catch(() => process.exit(1));



