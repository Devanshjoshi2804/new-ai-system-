import axios from 'axios';

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * 🔐 KYC SUBMISSION AFTER ONBOARDING TEST
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * This test demonstrates:
 * 1. How to extract data from onboarding metadata
 * 2. How to transform it into KYC dedicated fields
 * 3. How to submit complete KYC verification
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 */

const WALLET_API = 'https://qaapis2.delcaper.com/wallet-api';

// Constitution mapping (from metadata to KYC enum)
// Based on the API spec, valid values are: proprietorship, partnership, llp, pvt_ltd, public_ltd, other
const CONSTITUTION_MAP = {
  'Private Limited Company': 'proprietorship', // Using proprietorship as fallback
  'Public Limited Company': 'proprietorship',
  'Limited Liability Partnership': 'llp',
  'Partnership': 'partnership',
  'Proprietorship': 'proprietorship',
  'Others': 'proprietorship'
};

/**
 * Extract metadata value by key
 */
function getMetadataValue(metadata, key) {
  const item = metadata.find(m => m.key === key);
  return item ? item.value : null;
}

/**
 * Transform onboarding response to KYC payload
 */
function transformOnboardingToKYC(onboardingData, additionalKYCData) {
  console.log('🔄 Transforming onboarding data to KYC payload...');
  console.log('');
  
  // Extract from metadata
  const gstin = getMetadataValue(onboardingData.metadata, 'GSTIN');
  const constitution = getMetadataValue(onboardingData.metadata, 'CONSTITUTION');
  const directors = getMetadataValue(onboardingData.metadata, 'DIRECTORS');
  
  // Parse directors if it's a JSON string
  let directorsList = [];
  try {
    directorsList = JSON.parse(directors || '[]');
  } catch (e) {
    console.log('⚠️ Could not parse directors from metadata');
  }
  
  // Get address from onboarding
  const address = onboardingData.addresses?.[0] || {};
  
  console.log('📊 Extracted from Onboarding:');
  console.log(`   GSTIN: ${gstin}`);
  console.log(`   Constitution: ${constitution}`);
  console.log(`   Directors: ${directorsList.join(', ')}`);
  console.log(`   Address: ${address.line1}, ${address.city}, ${address.state} ${address.postalCode}`);
  console.log('');
  
  // Map constitution to KYC enum
  const documentBusinessType = CONSTITUTION_MAP[constitution] || 'other';
  
  console.log(`✅ Constitution mapped: "${constitution}" → "${documentBusinessType}"`);
  console.log('');
  
  // Build KYC payload
  const kycPayload = {
    productId: additionalKYCData.productId || "SMLINFUL",
    
    // Aadhaar details (from user input)
    aadharDetails: {
      aadharNumber: additionalKYCData.aadharNumber,
      aadhaarUrl: additionalKYCData.aadhaarUrl
    },
    aadharOtp: additionalKYCData.aadharOtp,
    
    // Business PAN (from user input)
    businessPanDetails: {
      panNumber: additionalKYCData.businessPan
    },
    
    // Signatory PAN (from user input)
    signatoryPanDetails: {
      panNumber: additionalKYCData.signatoryPan
    },
    
    // GST details (from onboarding metadata → dedicated field)
    gstDetails: {
      gstNumber: gstin
    },
    
    // Bank details (from user input)
    bankDetails: {
      bankName: additionalKYCData.bankName,
      bankBranch: additionalKYCData.bankBranch,
      ifscCode: additionalKYCData.ifscCode,
      accountNumber: additionalKYCData.accountNumber,
      accountName: additionalKYCData.accountName || onboardingData.personalDetails?.companyName,
      canceledChequeURL: additionalKYCData.canceledChequeURL
    },
    
    // Payment type
    paymentType: "prepaid",
    
    // GST registration status
    isGSTRegistered: !!gstin,
    
    // Constitution type (from metadata → enum)
    documentBusinessType: documentBusinessType,
    
    // Optional metadata for reference
    metadata: {
      directors: directorsList,
      tradeName: onboardingData.personalDetails?.companyName,
      legalName: onboardingData.personalDetails?.companyName,
      constitution: constitution,
      vendorCode: onboardingData.vendorCode,
      onboardingAddress: address
    }
  };
  
  return kycPayload;
}

/**
 * Main test function
 */
async function testKYCAfterOnboarding() {
  console.log('╔═══════════════════════════════════════════════════════════════╗');
  console.log('║   🔐 KYC SUBMISSION AFTER ONBOARDING TEST                    ║');
  console.log('╚═══════════════════════════════════════════════════════════════╝');
  console.log('');
  
  try {
    // ═══════════════════════════════════════════════════════════════
    // STEP 1: Simulate onboarding response (from previous test)
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 1: Use Data from Onboarding Response                  │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    // This would come from your previous onboarding API call
    const onboardingResponse = {
      vendorCode: "ADD0",
      personalDetails: {
        email: "test.gst.1759643648962@delcaper.com",
        name: "ANSHUL GARG",
        companyName: "ADD A DELTA TEST 648962 PRIVATE LIMITED",
        mobile: "9843648962"
      },
      metadata: [
        {
          key: "GSTIN",
          value: "09AASC7501M2Z4"
        },
        {
          key: "CONSTITUTION",
          value: "Private Limited Company"
        },
        {
          key: "DIRECTORS",
          value: "[\"ANSHUL GARG\",\"ANKIT GARG\",\"VIPIN SAINI\",\"PANKAJ DUDEJA\"]"
        }
      ],
      addresses: [
        {
          type: "billing",
          line1: "Fourth floor, B-17, Sector-3",
          line2: "Noida",
          city: "Noida",
          state: "Uttar Pradesh",
          postalCode: "201301",
          country: "India"
        }
      ]
    };
    
    console.log('📦 Onboarding Response:');
    console.log(`   Vendor Code: ${onboardingResponse.vendorCode}`);
    console.log(`   Company: ${onboardingResponse.personalDetails.companyName}`);
    console.log(`   Email: ${onboardingResponse.personalDetails.email}`);
    console.log('');
    
    // ═══════════════════════════════════════════════════════════════
    // STEP 2: Collect additional KYC data from user
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 2: Collect Additional KYC Data                        │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    // These would be collected from user via chatbot/form
    const additionalKYCData = {
      productId: "SMLINFUL",
      
      // Aadhaar
      aadharNumber: "557306614995",
      aadhaarUrl: "https://wpblogassets.paytm.com/paytmblog/uploads/2023/08/Blog_Paytm_How-To-Get-Duplicate-Aadhar-Card.jpg",
      aadharOtp: "986925",
      
      // PAN cards
      businessPan: "AABCA1906H",
      signatoryPan: "ADJFS8850L",
      
      // Bank details
      bankName: "SBI",
      bankBranch: "Noida Sector 18",
      ifscCode: "SBIN0005943",
      accountNumber: "31408513589",
      accountName: "ADD A DELTA TEST 648962 PRIVATE LIMITED",
      canceledChequeURL: "https://delcaper-qa.s3.ap-south-1.amazonaws.com/internationaldemo8/shippinglabel/shipping-label-1755505733220.pdf"
    };
    
    console.log('📋 Additional KYC Data Collected:');
    console.log(`   Aadhaar: ${'*'.repeat(8)}${additionalKYCData.aadharNumber.slice(-4)}`);
    console.log(`   Business PAN: ${additionalKYCData.businessPan}`);
    console.log(`   Signatory PAN: ${additionalKYCData.signatoryPan}`);
    console.log(`   Bank: ${additionalKYCData.bankName} - ${additionalKYCData.bankBranch}`);
    console.log(`   IFSC: ${additionalKYCData.ifscCode}`);
    console.log('');
    
    // ═══════════════════════════════════════════════════════════════
    // STEP 3: Transform metadata to dedicated fields
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 3: Transform Metadata → Dedicated Fields              │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    const kycPayload = transformOnboardingToKYC(onboardingResponse, additionalKYCData);
    
    console.log('📤 Final KYC Payload:');
    console.log('─────────────────────────────────────────────────────────────');
    console.log(JSON.stringify(kycPayload, null, 2));
    console.log('─────────────────────────────────────────────────────────────');
    console.log('');
    
    // ═══════════════════════════════════════════════════════════════
    // STEP 4: Submit KYC to Wallet API
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 4: Submit KYC to Wallet API                           │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    const vendorCode = onboardingResponse.vendorCode;
    const kycEndpoint = `${WALLET_API}/kyc/${vendorCode}`;
    
    console.log(`🚀 Calling KYC API...`);
    console.log(`📡 Endpoint: PATCH ${kycEndpoint}`);
    console.log('');
    
    const kycResponse = await axios.patch(
      kycEndpoint,
      kycPayload,
      {
        headers: {
          'accept': '*/*',
          'Content-Type': 'application/json'
        },
        validateStatus: () => true // Accept all status codes
      }
    );
    
    console.log(`📥 Response Status: ${kycResponse.status}`);
    console.log('');
    
    // ═══════════════════════════════════════════════════════════════
    // STEP 5: Handle response
    // ═══════════════════════════════════════════════════════════════
    console.log('┌─────────────────────────────────────────────────────────────┐');
    console.log('│ STEP 5: Process KYC Response                               │');
    console.log('└─────────────────────────────────────────────────────────────┘');
    console.log('');
    
    if (kycResponse.status === 200 || kycResponse.status === 201) {
      console.log('✅ SUCCESS! KYC submitted successfully!');
      console.log('');
      
      const customerData = kycResponse.data.data?.customerData;
      
      if (customerData) {
        console.log('╔═══════════════════════════════════════════════════════════════╗');
        console.log('║                  📋 KYC VERIFICATION SUMMARY                  ║');
        console.log('╚═══════════════════════════════════════════════════════════════╝');
        console.log('');
        console.log('🎫 Customer Information:');
        console.log(`   Customer ID: ${customerData.customerId}`);
        console.log(`   Name: ${customerData.name}`);
        console.log(`   KYC Status: ${customerData.kycStatus}`);
        console.log(`   Payment Type: ${customerData.payment_type}`);
        console.log('');
        console.log('📄 Verification Status:');
        console.log(`   GST: ${customerData.kyc?.gstStatus || 'pending'}`);
        console.log(`   Business PAN: ${customerData.kyc?.businessPanStatus || 'pending'}`);
        console.log(`   Signatory PAN: ${customerData.kyc?.signatoryPanStatus || 'pending'}`);
        console.log(`   Aadhaar: ${customerData.kyc?.aadharStatus || 'pending'}`);
        console.log('');
        console.log('🏢 Verified Details:');
        console.log(`   Name as per GST: ${customerData.kyc?.nameasPerGst || 'N/A'}`);
        console.log(`   GST Address: ${customerData.kyc?.addressAsperGst?.gstAddressLine1 || 'N/A'}`);
        console.log('');
      }
      
      console.log('📦 Full Response:');
      console.log('─────────────────────────────────────────────────────────────');
      console.log(JSON.stringify(kycResponse.data, null, 2));
      console.log('─────────────────────────────────────────────────────────────');
      console.log('');
      
    } else if (kycResponse.status === 409) {
      console.log('⚠️  CONFLICT: GST/PAN/Aadhaar already used');
      console.log('');
      console.log('Response:', JSON.stringify(kycResponse.data, null, 2));
      console.log('');
      
      if (kycResponse.data.data?.kycData?.customerlist) {
        console.log('📋 Existing Customers with Same Details:');
        kycResponse.data.data.kycData.customerlist.forEach((customer, i) => {
          console.log(`   ${i + 1}. Aadhaar: ${customer.aadhar}, PAN: ${customer.signatoryPan}`);
          customer.customerV2s?.forEach(c => {
            console.log(`      - ${c.customerid}: ${c.name} (${c.productName})`);
          });
        });
        console.log('');
      }
      
    } else {
      console.log('❌ ERROR: Unexpected response');
      console.log('');
      console.log('Status:', kycResponse.status);
      console.log('Response:', JSON.stringify(kycResponse.data, null, 2));
      console.log('');
    }
    
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║              ✅ TEST COMPLETED! 🎉                            ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log('');
    
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
    
    console.error('');
    throw error;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// RUN THE TEST
// ═══════════════════════════════════════════════════════════════════════════

console.log('');
console.log('═══════════════════════════════════════════════════════════════');
console.log('  Starting KYC After Onboarding Test');
console.log('  ' + new Date().toLocaleString());
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

testKYCAfterOnboarding()
  .then(() => {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  Test completed!');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('');
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
