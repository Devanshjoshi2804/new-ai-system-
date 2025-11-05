import axios from 'axios';

const API_BASE = 'http://localhost:3000/api/onboarding';
const CARGO_API = 'https://qaapis2.delcaper.com/cargo-api';

async function testRealAPI() {
  console.log('🧪 Testing Real API Integration\n');

  try {
    // Step 1: Start session
    console.log('1️⃣ Starting session...');
    let response = await axios.post(`${API_BASE}/start`);
    const sessionId = response.data.sessionId;
    console.log(`✅ Session ID: ${sessionId}\n`);

    // Step 2: Send email
    console.log('2️⃣ Sending email...');
    const testEmail = `test${Date.now()}@delcaper.com`;
    response = await axios.post(`${API_BASE}/message`, {
      sessionId,
      message: testEmail
    });
    console.log(`✅ Email accepted: ${testEmail}\n`);

    // Step 3: Send mobile
    console.log('3️⃣ Sending mobile...');
    const testMobile = `98${String(Date.now()).slice(-8)}`; // Generate unique mobile
    response = await axios.post(`${API_BASE}/message`, {
      sessionId,
      message: testMobile
    });
    console.log(`✅ Mobile accepted: ${testMobile}\n`);

    // At this point, user should upload GST
    console.log('4️⃣ Simulating GST extraction...');
    
    // Mock GST data (as if extracted from PDF)
    const timestamp = Date.now();
    const mockGSTData = {
      gstin: '09AASCA7501M2Z4',
      legalName: `TEST COMPANY ${timestamp} PRIVATE LIMITED`,
      tradeName: `TEST COMPANY ${timestamp}`,
      constitution: 'Private Limited Company',
      address: {
        line1: 'Test Building, Floor 1',
        line2: 'Test Area',
        city: 'Mumbai',
        state: 'Maharashtra',
        pincode: '400001',
        country: 'India'
      },
      directors: ['TEST DIRECTOR 1', 'TEST DIRECTOR 2'],
      issueDate: '01/01/2024',
      validityDate: 'Not Applicable'
    };

    console.log('📋 Mock GST Data:', JSON.stringify(mockGSTData, null, 2));
    console.log('');

    // Step 4: Test direct Cargo API call
    console.log('5️⃣ Testing Direct Cargo API Call...');
    
    const onboardingPayload = {
      type: "SELLER",
      vendorType: "SELLER",
      name: mockGSTData.directors[0],
      email: testEmail,
      mobile: testMobile,
      password: "Test@12345",
      companyName: mockGSTData.legalName,
      addresses: [
        {
          type: "Billing",
          line1: mockGSTData.address.line1,
          line2: mockGSTData.address.line2,
          city: mockGSTData.address.city,
          state: mockGSTData.address.state,
          postalCode: mockGSTData.address.pincode,
          country: "India"
        }
      ]
    };

    console.log('📤 Payload to Cargo API:');
    console.log(JSON.stringify(onboardingPayload, null, 2));
    console.log('');

    const cargoResponse = await axios.post(
      `${CARGO_API}/onboarding`,
      onboardingPayload,
      {
        headers: { 'Content-Type': 'application/json' },
        validateStatus: () => true
      }
    );

    console.log(`📥 Cargo API Response Status: ${cargoResponse.status}`);
    console.log('📥 Response Data:');
    console.log(JSON.stringify(cargoResponse.data, null, 2));
    console.log('');

    if (cargoResponse.status === 201 || cargoResponse.status === 200) {
      const vendorCode = cargoResponse.data.data?.vendorCode || cargoResponse.data.vendorCode || cargoResponse.data.id;
      console.log(`✅ SUCCESS! Vendor Code: ${vendorCode}`);
      console.log('');
      console.log('🎉 Complete Onboarding Data:');
      console.log(`   Email: ${testEmail}`);
      console.log(`   Mobile: ${testMobile}`);
      console.log(`   Company: ${mockGSTData.legalName}`);
      console.log(`   GSTIN: ${mockGSTData.gstin}`);
      console.log(`   Vendor Code: ${vendorCode}`);
      console.log('');
      console.log('✅ Next Step: Use this vendorCode for KYC API');
    } else if (cargoResponse.status === 409) {
      console.log('⚠️ CONFLICT: Email or mobile already exists');
      console.log('💡 This is expected if you run the test multiple times');
      console.log('💡 The onboarding chat handles this gracefully');
    } else {
      console.log('❌ ERROR: Unexpected response');
      console.log('Response:', cargoResponse.data);
    }

  } catch (error) {
    console.error('❌ Test Failed:', error.message);
    if (error.response) {
      console.error('Response Status:', error.response.status);
      console.error('Response Data:', error.response.data);
    }
  }
}

// Run the test
console.log('='.repeat(60));
console.log('   REAL API INTEGRATION TEST');
console.log('='.repeat(60));
console.log('');

testRealAPI().then(() => {
  console.log('');
  console.log('='.repeat(60));
  console.log('Test completed!');
  console.log('='.repeat(60));
  process.exit(0);
}).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});

