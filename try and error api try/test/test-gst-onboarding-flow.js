import axios from 'axios';

// ═══════════════════════════════════════════════════════════════════════════
// 🧪 COMPLETE GST ONBOARDING FLOW TEST
// ═══════════════════════════════════════════════════════════════════════════
// 
// This test simulates:
// 1. Chatbot asks for email and phone
// 2. User uploads GST PDF (we use pre-extracted OCR data)
// 3. System extracts company info from GST
// 4. Auto-generates random password
// 5. Calls onboarding API with all data
// 6. Stores vendor code for KYC
// 
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = 'http://localhost:3000/api/onboarding';
const CARGO_API = 'https://qaapis2.delcaper.com/cargo-api';

// Mock GST OCR Data (from your provided GST certificate)
// Note: Company name is made unique per test run to avoid conflicts
function getMockGSTData() {
  const timestamp = Date.now();
  const uniqueSuffix = String(timestamp).slice(-6);
  
  return {
    gstin: '09AASC7501M2Z4',
    legalName: `ADD A DELTA TEST ${uniqueSuffix} PRIVATE LIMITED`,
    tradeName: `ADD A DELTA TEST ${uniqueSuffix} PRIVATE LIMITED`,
    constitution: 'Private Limited Company',
    address: {
      line1: 'Fourth floor, B-17, Sector-3',
      line2: 'Noida',
      city: 'Noida',
      state: 'Uttar Pradesh',
      pincode: '201301',
      country: 'India'
    },
    directors: [
      'ANSHUL GARG',
      'ANKIT GARG',
      'VIPIN SAINI',
      'PANKAJ DUDEJA'
    ],
    district: 'Gautambudhna Nagar',
    registrationType: 'Regular',
    issueDate: '11/07/2023',
    validityDate: 'Not Applicable'
  };
}

// Generate random password (12 characters with special chars)
function generateRandomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
  let password = '';
  for (let i = 0; i < 12; i++) {
    password += chars[Math.floor(Math.random() * chars.length)];
  }
  return password;
}

// Simulate chatbot interaction
async function simulateChatbotFlow() {
  console.log('╔═══════════════════════════════════════════════════════════════╗');
  console.log('║   🤖 GST ONBOARDING FLOW - COMPLETE TEST                     ║');
  console.log('╚═══════════════════════════════════════════════════════════════╝');
  console.log('');

  try {
    // Get unique GST data for this test run
    const MOCK_GST_OCR_DATA = getMockGSTData();
    
    // ═══════════════════════════════════════════════════════════════
    // STEP 1: Chatbot asks for email
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 1: Chatbot Asks for Email                             │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    console.log('🤖 Bot: "What\'s your official email for onboarding?"');
    console.log('');
    
    // Generate unique email for testing
    const timestamp = Date.now();
    const userEmail = `test.gst.${timestamp}@delcaper.com`;
    
    console.log(`👤 User: "${userEmail}"`);
    console.log('✅ Email collected\n');

    // ═══════════════════════════════════════════════════════════════
    // STEP 2: Chatbot asks for phone number
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 2: Chatbot Asks for Phone Number                      │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    console.log('🤖 Bot: "What\'s the best contact number for OTP and alerts?"');
    console.log('');
    
    // Generate unique phone number for testing
    const userPhone = `98${String(timestamp).slice(-8)}`;
    
    console.log(`👤 User: "${userPhone}"`);
    console.log('✅ Phone number collected\n');

    // ═══════════════════════════════════════════════════════════════
    // STEP 3: Auto-generate password
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 3: Auto-Generate Random Password                      │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    const autoPassword = generateRandomPassword();
    
    console.log('🔐 Generating secure password...');
    console.log(`✅ Password: ${autoPassword}`);
    console.log('💡 This will be shared with the user for login\n');

    // ═══════════════════════════════════════════════════════════════
    // STEP 4: Simulate GST PDF upload and OCR extraction
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 4: GST PDF Upload & OCR Extraction                    │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    console.log('🤖 Bot: "Now, upload your GST certificate (PDF)"');
    console.log('');
    console.log('👤 User: [Uploads GST PDF]');
    console.log('');
    console.log('📄 Processing GST certificate...');
    console.log('🔍 Running OCR extraction...');
    console.log('');
    
    // Display extracted data
    console.log('✅ GST Data Extracted Successfully!');
    console.log('');
    console.log('📊 Extracted Information:');
    console.log('─────────────────────────────────────────────────────────────');
    console.log(`   GSTIN:           ${MOCK_GST_OCR_DATA.gstin}`);
    console.log(`   Legal Name:      ${MOCK_GST_OCR_DATA.legalName}`);
    console.log(`   Trade Name:      ${MOCK_GST_OCR_DATA.tradeName}`);
    console.log(`   Constitution:    ${MOCK_GST_OCR_DATA.constitution}`);
    console.log(`   Registration:    ${MOCK_GST_OCR_DATA.registrationType}`);
    console.log('');
    console.log('   Address:');
    console.log(`   ${MOCK_GST_OCR_DATA.address.line1}`);
    console.log(`   ${MOCK_GST_OCR_DATA.address.line2}`);
    console.log(`   ${MOCK_GST_OCR_DATA.address.city}, ${MOCK_GST_OCR_DATA.address.state} ${MOCK_GST_OCR_DATA.address.pincode}`);
    console.log('');
    console.log('   Directors/Partners:');
    MOCK_GST_OCR_DATA.directors.forEach((director, i) => {
      console.log(`   ${i + 1}. ${director}`);
    });
    console.log('─────────────────────────────────────────────────────────────');
    console.log('');

    // ═══════════════════════════════════════════════════════════════
    // STEP 5: Prepare onboarding payload
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 5: Prepare Onboarding API Payload                     │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    const onboardingPayload = {
      type: "SELLER",
      subTypes: [],
      email: userEmail,
      name: MOCK_GST_OCR_DATA.directors[0], // Use first director as name
      companyName: MOCK_GST_OCR_DATA.legalName,
      mobile: userPhone,
      password: autoPassword,
      transporterIds: {
        air: "string",
        surface: "string",
        rail: "string"
      },
      addresses: [
        {
          type: "billing",
          line1: MOCK_GST_OCR_DATA.address.line1,
          line2: MOCK_GST_OCR_DATA.address.line2,
          city: MOCK_GST_OCR_DATA.address.city,
          state: MOCK_GST_OCR_DATA.address.state,
          postalCode: MOCK_GST_OCR_DATA.address.pincode,
          country: MOCK_GST_OCR_DATA.address.country
        }
      ],
      serviceAreas: [
        {
          city: "Mumbai",
          state: "Maharashtra",
          pincode: "400001",
          isActive: true
        },
        {
          city: "Delhi",
          state: "Delhi",
          pincode: "110001",
          isActive: true
        }
      ],
      logoUrl: "https://example.com/logo.png",
      metadata: [
        {
          key: "GSTIN",
          value: MOCK_GST_OCR_DATA.gstin
        },
        {
          key: "CONSTITUTION",
          value: MOCK_GST_OCR_DATA.constitution
        },
        {
          key: "DIRECTORS",
          value: JSON.stringify(MOCK_GST_OCR_DATA.directors)
        }
      ]
    };

    console.log('📤 Onboarding Payload:');
    console.log('─────────────────────────────────────────────────────────────');
    console.log(JSON.stringify(onboardingPayload, null, 2));
    console.log('─────────────────────────────────────────────────────────────');
    console.log('');

    // ═══════════════════════════════════════════════════════════════
    // STEP 6: Call Cargo Onboarding API
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 6: Call Cargo Onboarding API                          │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    console.log('🚀 Calling Cargo API...');
    console.log(`📡 Endpoint: ${CARGO_API}/onboarding`);
    console.log('');

    const cargoResponse = await axios.post(
      `${CARGO_API}/onboarding`,
      onboardingPayload,
      {
        headers: { 
          'Content-Type': 'application/json',
          'accept': '*/*'
        },
        validateStatus: () => true // Accept all status codes
      }
    );

    console.log(`📥 Response Status: ${cargoResponse.status}`);
    console.log('');

    // ═══════════════════════════════════════════════════════════════
    // STEP 7: Handle response and extract vendor code
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 7: Process Response & Extract Vendor Code             │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');

    if (cargoResponse.status === 201 || cargoResponse.status === 200) {
      const responseData = cargoResponse.data;
      const vendorCode = responseData.data?.vendorCode || responseData.vendorCode;
      const tenantId = responseData.data?.prayogData?.tenantId;
      const userId = responseData.data?.prayogData?.userId;

      console.log('✅ SUCCESS! Onboarding completed successfully!');
      console.log('');
      console.log('╔═══════════════════════════════════════════════════════════════╗');
      console.log('║                  📋 ONBOARDING SUMMARY                        ║');
      console.log('╚═══════════════════════════════════════════════════════════════╝');
      console.log('');
      console.log('👤 User Information:');
      console.log(`   Email:           ${userEmail}`);
      console.log(`   Phone:           ${userPhone}`);
      console.log(`   Password:        ${autoPassword}`);
      console.log('');
      console.log('🏢 Company Information:');
      console.log(`   Company Name:    ${MOCK_GST_OCR_DATA.legalName}`);
      console.log(`   GSTIN:           ${MOCK_GST_OCR_DATA.gstin}`);
      console.log(`   Primary Contact: ${MOCK_GST_OCR_DATA.directors[0]}`);
      console.log('');
      console.log('🎫 System Generated IDs:');
      console.log(`   Vendor Code:     ${vendorCode}`);
      console.log(`   Tenant ID:       ${tenantId}`);
      console.log(`   User ID:         ${userId}`);
      console.log('');
      console.log('📍 Address:');
      console.log(`   ${MOCK_GST_OCR_DATA.address.line1}`);
      console.log(`   ${MOCK_GST_OCR_DATA.address.line2}`);
      console.log(`   ${MOCK_GST_OCR_DATA.address.city}, ${MOCK_GST_OCR_DATA.address.state} ${MOCK_GST_OCR_DATA.address.pincode}`);
      console.log('');
      console.log('─────────────────────────────────────────────────────────────');
      console.log('');
      console.log('💡 Next Steps:');
      console.log('   1. Use Vendor Code for KYC API calls');
      console.log('   2. Share credentials with user via email/SMS');
      console.log('   3. User can login with email and password');
      console.log('   4. Complete KYC verification process');
      console.log('');
      console.log('🔐 KYC API Endpoint:');
      console.log(`   PATCH https://qaapis2.delcaper.com/wallet-api/kyc/${vendorCode}`);
      console.log('');

      // Store for KYC reference
      const onboardingResult = {
        vendorCode,
        tenantId,
        userId,
        email: userEmail,
        mobile: userPhone,
        password: autoPassword,
        companyName: MOCK_GST_OCR_DATA.legalName,
        gstin: MOCK_GST_OCR_DATA.gstin,
        directors: MOCK_GST_OCR_DATA.directors,
        address: MOCK_GST_OCR_DATA.address,
        timestamp: new Date().toISOString()
      };

      console.log('💾 Stored Data for KYC (JSON):');
      console.log('─────────────────────────────────────────────────────────────');
      console.log(JSON.stringify(onboardingResult, null, 2));
      console.log('─────────────────────────────────────────────────────────────');
      console.log('');

      // Display full API response
      console.log('📦 Full API Response:');
      console.log('─────────────────────────────────────────────────────────────');
      console.log(JSON.stringify(responseData, null, 2));
      console.log('─────────────────────────────────────────────────────────────');
      console.log('');

      console.log('╔═══════════════════════════════════════════════════════════════╗');
      console.log('║              ✅ TEST COMPLETED SUCCESSFULLY! 🎉               ║');
      console.log('╚═══════════════════════════════════════════════════════════════╝');
      console.log('');

      return onboardingResult;

    } else if (cargoResponse.status === 409) {
      console.log('⚠️  CONFLICT: Email or mobile already exists');
      console.log('');
      console.log('Response:', JSON.stringify(cargoResponse.data, null, 2));
      console.log('');
      console.log('💡 This is expected if you run the test multiple times.');
      console.log('   The system prevents duplicate registrations.');
      console.log('');
      console.log('🔄 To test again, the script generates new unique email/phone.');
      console.log('');

    } else {
      console.log('❌ ERROR: Unexpected response status');
      console.log('');
      console.log('Status:', cargoResponse.status);
      console.log('Response:', JSON.stringify(cargoResponse.data, null, 2));
      console.log('');
    }

  } catch (error) {
    console.error('');
    console.error('╔═══════════════════════════════════════════════════════════════╗');
    console.error('║                    ❌ TEST FAILED                             ║');
    console.error('╚═══════════════════════════════════════════════════════════════╝');
    console.error('');
    console.error('Error:', error.message);
    
    if (error.response) {
      console.error('');
      console.error('Response Status:', error.response.status);
      console.error('Response Data:', JSON.stringify(error.response.data, null, 2));
    }
    
    if (error.code === 'ECONNREFUSED') {
      console.error('');
      console.error('💡 Make sure the server is running:');
      console.error('   npm start');
    }
    
    console.error('');
    throw error;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// RUN THE TEST
// ═══════════════════════════════════════════════════════════════════════════

console.log('');
console.log('═══════════════════════════════════════════════════════════════');
console.log('  Starting GST Onboarding Flow Test');
console.log('  ' + new Date().toLocaleString());
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

simulateChatbotFlow()
  .then((result) => {
    if (result) {
      console.log('');
      console.log('═══════════════════════════════════════════════════════════════');
      console.log('  Test completed successfully!');
      console.log('  Vendor Code:', result.vendorCode);
      console.log('═══════════════════════════════════════════════════════════════');
      console.log('');
    }
    process.exit(0);
  })
  .catch((err) => {
    console.error('');
    console.error('═══════════════════════════════════════════════════════════════');
    console.error('  Fatal error:', err.message);
    console.error('═══════════════════════════════════════════════════════════════');
    console.error('');
    process.exit(1);
  });
