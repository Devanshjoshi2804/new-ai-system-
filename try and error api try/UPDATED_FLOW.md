# ✅ Updated Onboarding Flow (Simplified)

## New Flow Overview

```
1. Ask Email + Phone → Store Locally (no API call yet)
2. Upload GST PDF → Extract all data (name, company, address, directors)
3. POST Onboarding API → Send complete payload (GST data + email + phone)
4. Get Vendor Code from response
5. Continue with KYC → Use Vendor Code + GST data
```

---

## Complete Step-by-Step Flow

### **Step 1: Ask Email**
```
Bot: "What's your official email for onboarding?"
User: accounts@addadelta.com

✓ Validate email
✓ Store in session.data.email
```

### **Step 2: Ask Mobile**
```
Bot: "What's your mobile number?"
User: 9876543210

✓ Validate 10-13 digits
✓ Store in session.data.mobile
✓ Auto-generate password → session.data.password
```

### **Step 3: Request GST Upload** (No API call yet!)
```
Bot: "📄 Now, upload your GST certificate (PDF).
      I'll extract your company name, address, and all other details automatically!"

User: [Uploads GST.pdf]
```

### **Step 4: Extract GST Data** (Mistral Vision API)
```
Extracted:
{
  "gstin": "09AASCA7501M2Z4",
  "legalName": "ADD A DELTA PRIVATE LIMITED",
  "tradeName": "ADD A DELTA PRIVATE LIMITED",
  "constitution": "Private Limited Company",
  "address": {
    "line1": "B-17, Sector-3, fourth floor",
    "line2": "",
    "city": "Noida",
    "state": "Uttar Pradesh",
    "pincode": "201301",
    "country": "India"
  },
  "directors": ["ANSHUL GARG", "ANKIT GARG", "VIPIN SAINI", "PANKAJ DUDEJA"]
}

✓ Store in session.data.gstData
```

### **Step 5: POST Onboarding API** (Now with complete data!)
```javascript
POST https://qaapis2.delcaper.com/cargo-api/onboarding

Payload:
{
  "type": "SELLER",
  "vendorType": "SELLER",
  "name": "ANSHUL GARG",                    // ← From GST (first director)
  "email": "accounts@addadelta.com",        // ← Asked in Step 1
  "mobile": "9876543210",                   // ← Asked in Step 2
  "password": "Auto_Gen_Pass123",           // ← Auto-generated
  "companyName": "ADD A DELTA PRIVATE LIMITED", // ← From GST
  "addresses": [
    {
      "type": "Billing",
      "line1": "B-17, Sector-3, fourth floor", // ← From GST
      "line2": "",
      "city": "Noida",                          // ← From GST
      "state": "Uttar Pradesh",                 // ← From GST
      "postalCode": "201301",                   // ← From GST
      "country": "India"
    }
  ]
}

Response (201):
{
  "vendorCode": "SELLER12345",
  ...
}

✓ Store session.data.vendorCode = "SELLER12345"
```

### **Step 6: Show Review Card**
```
Bot: "✅ Account created successfully!

      Vendor Code: SELLER12345

      📋 Company Details (from GST):
      Legal Name: ADD A DELTA PRIVATE LIMITED
      GSTIN: 09AASCA7501M2Z4
      Address: B-17, Sector-3, fourth floor, Noida, UP 201301
      Directors: ANSHUL GARG, ANKIT GARG, VIPIN SAINI, PANKAJ DUDEJA

      ---

      🔐 Now let's complete KYC verification.
      📱 Please enter the 12-digit Aadhaar number:"
```

### **Step 7-11: KYC Flow** (Same as before)
- Aadhaar number
- Aadhaar image upload
- OTP
- Business PAN
- Signatory PAN
- Bank details

### **Step 12: PATCH KYC API**
```javascript
PATCH https://qaapis2.delcaper.com/wallet-api/kyc/SELLER12345

Payload:
{
  "productId": "SMLINFUL",
  "aadharDetails": {
    "aadharNumber": "123456789012",
    "aadhaarUrl": "https://..."
  },
  "aadharOtp": "123456",
  "businessPanDetails": { "panNumber": "AASCA7501M" },
  "signatoryPanDetails": { "panNumber": "ABCDE1234F" },
  "gstDetails": { 
    "gstNumber": "09AASCA7501M2Z4"  // ← From GST
  },
  "bankDetails": { ... },
  "paymentType": "prepaid",
  "isGSTRegistered": true,
  "documentBusinessType": "pvt_ltd",  // ← From GST constitution
  "metadata": {
    "directors": ["ANSHUL GARG", "ANKIT GARG", ...],  // ← From GST
    "tradeName": "ADD A DELTA PRIVATE LIMITED",        // ← From GST
    "legalName": "ADD A DELTA PRIVATE LIMITED",        // ← From GST
    "vendorCode": "SELLER12345"
  }
}
```

---

## Key Changes from Previous Version

### ❌ Before (Old Flow)
```
1. Ask email + mobile
2. POST Onboarding API (with empty name/company/address)
3. Get vendorCode
4. Upload GST
5. PATCH Onboarding API (update with GST data)
6. Continue KYC
```

### ✅ After (New Flow)
```
1. Ask email + mobile → Store locally
2. Upload GST → Extract data
3. POST Onboarding API (with complete GST + email + mobile)
4. Get vendorCode
5. Continue KYC (no PATCH needed)
```

---

## Payload Comparison

### Your Exact Format (From Screenshot)
```javascript
{
  name: "dev",                           // ← From GST (first director)
  email: "hisdbcwshb@gmail.com",         // ← Asked by chatbot
  password: "devanshj1",                 // ← Auto-generated
  mobile: "7777777763",                  // ← Asked by chatbot
  companyName: "bhdcjwchbpvt",           // ← From GST (legalName)
  type: "SELLER",
  vendorType: "SELLER",
  addresses: [
    {
      type: "Billing",
      line1: "test",                     // ← From GST
      line2: "test",                     // ← From GST
      city: "Pune",                      // ← From GST
      state: "Maharashtra",              // ← From GST
      postalCode: "411014",              // ← From GST
      country: "India"
    }
  ]
}
```

### Our Implementation (Matches Your Format)
```javascript
{
  type: "SELLER",
  vendorType: "SELLER",
  name: gst.directors?.[0] || gst.legalName || "",      // First director or legal name
  email: session.data.email,                             // From chatbot
  mobile: session.data.mobile,                           // From chatbot
  password: session.data.password,                       // Auto-generated
  companyName: gst.legalName || gst.tradeName || "",    // From GST
  addresses: [
    {
      type: "Billing",
      line1: gst.address?.line1 || "",                   // From GST
      line2: gst.address?.line2 || "",                   // From GST
      city: gst.address?.city || "",                     // From GST
      state: gst.address?.state || "",                   // From GST
      postalCode: gst.address?.pincode || "",            // From GST
      country: "India"
    }
  ]
}
```

✅ **Perfect match!**

---

## Data Sources Summary

| Field | Source | When |
|-------|--------|------|
| `email` | User input (chatbot) | Step 1 |
| `mobile` | User input (chatbot) | Step 2 |
| `password` | Auto-generated | Step 2 |
| `name` | GST (first director) | Step 4 (extracted) |
| `companyName` | GST (legalName) | Step 4 (extracted) |
| `addresses[0].line1` | GST address | Step 4 (extracted) |
| `addresses[0].line2` | GST address | Step 4 (extracted) |
| `addresses[0].city` | GST address | Step 4 (extracted) |
| `addresses[0].state` | GST address | Step 4 (extracted) |
| `addresses[0].postalCode` | GST pincode | Step 4 (extracted) |

---

## Timeline Visualization

```
User Perspective                     System Actions
──────────────────────────────────────────────────────────────

👤 Enter email
                                     → Store in session

👤 Enter mobile
                                     → Store in session
                                     → Generate password

👤 Upload GST PDF
                                     → Call Mistral Vision API
                                     → Extract: name, company, address
                                     → POST /cargo-api/onboarding
                                        {
                                          email,
                                          mobile,
                                          password,
                                          name (from GST),
                                          companyName (from GST),
                                          addresses (from GST)
                                        }
                                     → Get vendorCode

✅ See review card with all details

👤 Continue with KYC...
```

---

## Testing the New Flow

### 1. Start Chat
```
http://localhost:3000/onboarding.html
```

### 2. Input Sequence
```
Email: test@addadelta.com
Mobile: 9876543210
GST PDF: [Your GST certificate]
```

### 3. Expected Result
```
✅ Account created successfully!
Vendor Code: SELLER12345

📋 Company Details:
Legal Name: ADD A DELTA PRIVATE LIMITED
GSTIN: 09AASCA7501M2Z4
...
```

### 4. Check Console Logs
```javascript
Creating onboarding with complete data: {
  type: "SELLER",
  vendorType: "SELLER",
  name: "ANSHUL GARG",
  email: "test@addadelta.com",
  mobile: "9876543210",
  password: "Auto_Gen_Pass123",
  companyName: "ADD A DELTA PRIVATE LIMITED",
  addresses: [...]
}
```

---

## API Endpoint Called

**Single POST request only:**

```
POST https://qaapis2.delcaper.com/cargo-api/onboarding

Headers:
  Content-Type: application/json

Body:
  {
    "type": "SELLER",
    "vendorType": "SELLER",
    "name": "...",           // From GST
    "email": "...",          // From user
    "mobile": "...",         // From user
    "password": "...",       // Auto-generated
    "companyName": "...",    // From GST
    "addresses": [...]       // From GST
  }

Expected Response (201):
  {
    "vendorCode": "SELLER12345",
    ...
  }
```

**No PATCH needed!** All data sent in one go.

---

## Benefits of This Approach

✅ **Single API call** (POST only, no PATCH)  
✅ **Complete data upfront** (no partial then update)  
✅ **User only types 2 things** (email + mobile)  
✅ **Everything else from GST** (name, company, address)  
✅ **Matches your exact payload format**  
✅ **Cleaner flow** (no intermediate states)  

---

## What Happens If GST Extraction Fails?

```javascript
if (!gst) {
  // Fallback: Ask user manually
  return {
    nextState: STATES.ASK_NAME,  // New state (can be added)
    response: {
      text: "⚠️ Couldn't read GST PDF. Please enter your name:"
    }
  };
}
```

**For MVP:** Continue with empty fields or stop and ask user to re-upload better quality PDF.

---

## Ready to Test! 🚀

Start the server:
```bash
npm start
```

Open chat:
```
http://localhost:3000/onboarding.html
```

Flow:
1. Enter email
2. Enter mobile
3. Upload GST PDF
4. ✅ Account created with vendorCode
5. Continue KYC...

---

**All changes saved in `onboarding-kyc-flow.js`**  
**Flow now matches your exact requirements!** ✅





