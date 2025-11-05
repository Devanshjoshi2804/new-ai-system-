# 🎯 Onboarding + KYC Flow Diagram

## Complete Conversation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER JOURNEY                                   │
└─────────────────────────────────────────────────────────────────────────┘

START
  │
  ├─────► 📧 "What's your email?"
  │       User: accounts@addadelta.com
  │       ✓ Validate email format
  │
  ├─────► 📱 "What's your mobile?"
  │       User: 9876543210
  │       ✓ Validate 10-13 digits
  │
  ├─────► 🔐 (Silent) Generate password: Auto_Gen_Pass123
  │
  ├─────► 🌐 POST /cargo-api/onboarding
  │       {
  │         type: "SELLER",
  │         email: "accounts@addadelta.com",
  │         mobile: "9876543210",
  │         password: "Auto_Gen_Pass123",
  │         name: "",
  │         companyName: ""
  │       }
  │       ✓ Response: vendorCode = "SELLER12345"
  │
  ├─────► 📄 "Upload your GST certificate (PDF)"
  │       User: [Uploads GST.pdf]
  │
  ├─────► 🤖 Mistral Vision API
  │       Extract from PDF:
  │       ┌─────────────────────────────────────────┐
  │       │ GSTIN: 09AASCA7501M2Z4                  │
  │       │ Legal Name: ADD A DELTA PRIVATE LIMITED │
  │       │ Trade Name: ADD A DELTA PRIVATE LIMITED │
  │       │ Constitution: Private Limited Company   │
  │       │ Address:                                │
  │       │   - Line1: B-17, Sector-3, fourth floor │
  │       │   - City: Noida                         │
  │       │   - State: Uttar Pradesh                │
  │       │   - Pincode: 201301                     │
  │       │ Directors:                              │
  │       │   1. ANSHUL GARG                        │
  │       │   2. ANKIT GARG                         │
  │       │   3. VIPIN SAINI                        │
  │       │   4. PANKAJ DUDEJA                      │
  │       └─────────────────────────────────────────┘
  │
  ├─────► 🌐 PATCH /cargo-api/onboarding/SELLER12345
  │       {
  │         onboardingData: {
  │           organizationName: "ADD A DELTA PRIVATE LIMITED",
  │           ownerName: "ANSHUL GARG",
  │           pincode: "201301",
  │           metadata: [
  │             { key: "gstin", value: "09AASCA7501M2Z4" },
  │             { key: "constitution", value: "Private Limited Company" },
  │             { key: "tradeName", value: "ADD A DELTA PRIVATE LIMITED" }
  │           ]
  │         }
  │       }
  │       ✓ Profile updated
  │
  ├─────► 📋 Show review card:
  │       "✅ Company Details (from GST):
  │        Legal Name: ADD A DELTA PRIVATE LIMITED
  │        GSTIN: 09AASCA7501M2Z4
  │        Address: B-17, Sector-3, fourth floor, Noida, UP 201301
  │        Directors: ANSHUL GARG, ANKIT GARG, VIPIN SAINI, PANKAJ DUDEJA"
  │
  ├─────► 🔐 "Now let's complete KYC. Enter your 12-digit Aadhaar:"
  │       User: 123456789012
  │       ✓ Validate 12 digits
  │
  ├─────► 📸 "Upload Aadhaar image (front + back):"
  │       User: [Uploads aadhaar.jpg → S3]
  │       → URL: https://s3.amazonaws.com/bucket/aadhaar.jpg
  │
  ├─────► 🔢 "Enter the 6-digit OTP sent to your Aadhaar-linked mobile:"
  │       User: 123456
  │       ✓ Validate 6 digits
  │
  ├─────► 📄 "Please provide PAN details. First, Business PAN:"
  │       User: AASCA7501M
  │       ✓ Validate PAN format (5 letters + 4 digits + 1 letter)
  │
  ├─────► 📄 "Now, Authorized Signatory PAN:"
  │       User: ABCDE1234F
  │       ✓ Validate PAN format
  │
  ├─────► 🏦 "Finally, your bank details in this format:
  │       Bank Name: HDFC Bank
  │       Branch: Connaught Place
  │       IFSC: HDFC0001234
  │       Account Number: 12345678901234
  │       Account Holder Name: ADD A DELTA PRIVATE LIMITED
  │       Cancelled Cheque URL: https://..."
  │
  │       User: [Pastes bank details]
  │       ✓ Parse freeform text → structured data
  │       ✓ Validate IFSC format (ABCD0XXXXXX)
  │       ✓ Validate URL is HTTPS
  │
  ├─────► 🌐 PATCH /wallet-api/kyc/SELLER12345
  │       {
  │         productId: "SMLINFUL",
  │         aadharDetails: {
  │           aadharNumber: "123456789012",
  │           aadhaarUrl: "https://s3.../aadhaar.jpg"
  │         },
  │         aadharOtp: "123456",
  │         businessPanDetails: { panNumber: "AASCA7501M" },
  │         signatoryPanDetails: { panNumber: "ABCDE1234F" },
  │         gstDetails: { gstNumber: "09AASCA7501M2Z4" },
  │         bankDetails: {
  │           bankName: "HDFC Bank",
  │           bankBranch: "Connaught Place",
  │           ifscCode: "HDFC0001234",
  │           accountNumber: "12345678901234",
  │           accountName: "ADD A DELTA PRIVATE LIMITED",
  │           canceledChequeURL: "https://..."
  │         },
  │         paymentType: "prepaid",
  │         isGSTRegistered: true,
  │         documentBusinessType: "pvt_ltd",
  │         metadata: {
  │           directors: ["ANSHUL GARG", "ANKIT GARG", "VIPIN SAINI", "PANKAJ DUDEJA"],
  │           tradeName: "ADD A DELTA PRIVATE LIMITED",
  │           legalName: "ADD A DELTA PRIVATE LIMITED",
  │           vendorCode: "SELLER12345"
  │         }
  │       }
  │       ✓ KYC submitted
  │
  └─────► 🎉 DONE
          "✅ Onboarding + KYC submitted successfully!
          
          📋 Summary:
          - Vendor Code: SELLER12345
          - Email: accounts@addadelta.com
          - Mobile: 9876543210
          - Company: ADD A DELTA PRIVATE LIMITED
          - GSTIN: 09AASCA7501M2Z4
          
          Temporary Password: Auto_Gen_Pass123
          (Please change this on first login)
          
          We'll notify you once your account is verified (24-48 hours)."
```

---

## State Machine Diagram

```
┌──────┐
│START │
└──┬───┘
   │
   ▼
┌────────────┐
│ ASK_EMAIL  │ ◄────┐
└──┬─────────┘      │ (Validation failed)
   │                │
   ▼                │
┌────────────┐      │
│ ASK_MOBILE │ ◄────┤
└──┬─────────┘      │
   │                │
   ▼                │
┌─────────────────┐ │
│CREATE_PASSWORD  │ │ (Auto, no user input)
└──┬──────────────┘ │
   │                │
   ▼                │
┌──────────────────┐│
│CALL_ONBOARDING   ││ (POST Cargo API)
└──┬───────────────┘│
   │                │
   ├─ 409 Conflict ─┘
   │
   ▼
┌──────────────────┐
│ASK_GST_UPLOAD    │ (File upload)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│   PARSE_GST      │ (Mistral Vision API)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│PATCH_ONBOARDING  │ (PATCH Cargo API)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│  ASK_AADHAAR     │
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│ASK_AADHAAR_IMAGE │ (File upload)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│    ASK_OTP       │
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│   ASK_PANS       │ (Business → Signatory)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│   ASK_BANK       │ (Freeform parse)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│  SUBMIT_KYC      │ (PATCH Wallet API)
└──┬───────────────┘
   │
   ▼
┌──────────────────┐
│      DONE        │ ✅
└──────────────────┘
```

---

## API Integration Points

```
┌─────────────────┐
│  Onboarding     │
│  Flow Engine    │
└────────┬────────┘
         │
         ├─────────────────────┐
         │                     │
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  Mistral Vision  │  │   Cargo API      │
│      API         │  │  (Delcaper)      │
└──────────────────┘  └──────────────────┘
         │                     │
         │                     ├─► POST /onboarding
         │                     │   (Create vendor)
         │                     │
         ▼                     ├─► PATCH /onboarding/{vendorCode}
    Extract GST ──────────────►│   (Update profile)
    - GSTIN                    │
    - Legal Name               │
    - Address                  │
    - Directors                │
                               │
                               ▼
                    ┌──────────────────┐
                    │   Wallet API     │
                    │  (Delcaper)      │
                    └──────────────────┘
                               │
                               ├─► PATCH /kyc/{vendorCode}
                               │   (Submit KYC)
                               │   - Aadhaar
                               │   - PANs
                               │   - GST
                               │   - Bank
                               │
                               ▼
                            ✅ Done
```

---

## Data Flow: GST → APIs

```
┌──────────────────────────────────────────────────────────────┐
│                      GST CERTIFICATE (PDF)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ GSTIN: 09AASCA7501M2Z4                                 │  │
│  │ Legal Name: ADD A DELTA PRIVATE LIMITED                │  │
│  │ Trade Name: ADD A DELTA PRIVATE LIMITED                │  │
│  │ Constitution: Private Limited Company                  │  │
│  │ Address: B-17, Sector-3, fourth floor, Noida, UP...    │  │
│  │ Directors: ANSHUL GARG, ANKIT GARG, VIPIN SAINI...     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Mistral Vision API   │
            │ (pixtral-12b-2409)   │
            └──────────┬───────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Extracted JSON │
              └────┬───────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌───────────────┐    ┌───────────────────┐
│ Cargo API     │    │ Wallet API        │
│ (Onboarding)  │    │ (KYC)             │
├───────────────┤    ├───────────────────┤
│ orgName       │◄───│ gstNumber         │
│ ownerName     │    │ documentBusinessType
│ pincode       │    │ metadata.directors│
│ metadata.gst  │    │ metadata.tradeName│
└───────────────┘    └───────────────────┘
```

**Field Mapping:**

| GST Certificate | Session Data | Cargo API | Wallet API |
|-----------------|--------------|-----------|------------|
| GSTIN | `gstData.gstin` | `metadata[key=gstin]` | `gstDetails.gstNumber` |
| Legal Name | `gstData.legalName` | `organizationName` | `metadata.legalName` |
| Trade Name | `gstData.tradeName` | `metadata[key=tradeName]` | `metadata.tradeName` |
| Constitution | `gstData.constitution` | `metadata[key=constitution]` | `documentBusinessType` (enum) |
| Address | `gstData.address` | `pincode` | — |
| Directors | `gstData.directors[]` | `ownerName` (first) | `metadata.directors` |

---

## User Input Timeline

```
Time  │ User Action              │ System Response
──────┼──────────────────────────┼────────────────────────────────────
0:00  │ Opens /onboarding.html   │ "Welcome! What's your email?"
      │                          │
0:10  │ Types email              │ "✓ Got it! Mobile number?"
      │                          │
0:20  │ Types mobile             │ "✓ Creating account..."
      │                          │ [Auto: Generate password]
      │                          │ [Auto: POST Onboarding API]
      │                          │ "✓ Account created! Upload GST PDF"
      │                          │
0:40  │ Uploads GST PDF          │ "⏳ Extracting data..."
      │                          │ [Auto: Mistral Vision API]
      │                          │ [Auto: PATCH Onboarding API]
      │                          │ "✓ Company: ADD A DELTA PRIVATE LIMITED"
      │                          │ "✓ GSTIN: 09AASCA7501M2Z4"
      │                          │ "✓ Directors: ANSHUL GARG, ANKIT GARG..."
      │                          │ "Enter your Aadhaar number:"
      │                          │
1:10  │ Types Aadhaar            │ "✓ Upload Aadhaar image:"
      │                          │
1:30  │ Uploads Aadhaar image    │ "✓ Enter 6-digit OTP:"
      │                          │
1:40  │ Types OTP                │ "✓ Business PAN:"
      │                          │
1:50  │ Types Business PAN       │ "✓ Signatory PAN:"
      │                          │
2:00  │ Types Signatory PAN      │ "✓ Bank details:"
      │                          │
2:30  │ Pastes bank details      │ "⏳ Submitting KYC..."
      │                          │ [Auto: PATCH KYC API]
      │                          │ "🎉 Success!"
      │                          │ "Vendor Code: SELLER12345"
      │                          │ "Temp Password: Auto_Gen_Pass123"
──────┴──────────────────────────┴────────────────────────────────────

Total Time: ~2.5 minutes (vs 15+ for traditional forms!)
```

---

## Error Handling Flow

```
┌────────────────┐
│  User Input    │
└───────┬────────┘
        │
        ▼
   ┌─────────┐
   │Validator│
   └────┬────┘
        │
    ┌───┴───┐
    │ Valid?│
    └───┬───┘
        │
    ┌───┴───────────┐
    │               │
    ▼ YES           ▼ NO
┌─────────┐    ┌─────────────┐
│ Process │    │ Show Error  │
└────┬────┘    │ + Re-ask    │
     │         └──────┬──────┘
     ▼                │
┌─────────┐           │
│API Call │           │
└────┬────┘           │
     │                │
 ┌───┴────────┐       │
 │  Status?   │       │
 └───┬────────┘       │
     │                │
 ┌───┴──────────┐     │
 │              │     │
 ▼ 200/201      ▼ 400/409/500
┌──────┐    ┌────────────┐
│ Next │    │ Show Error │
│State │    │ + Retry    │
└──────┘    └─────┬──────┘
                  │
                  └──────► Back to input
```

**Error Examples:**

| Status | Scenario | Action |
|--------|----------|--------|
| 400 | Invalid email format | Re-ask email with error: "Email format looks off" |
| 409 | Email already exists | Show: "Email exists. [Login] or [Try Another]" |
| 400 | Invalid PAN format | Re-ask: "PAN must look like ABCDE1234F" |
| 400 | Invalid IFSC | Re-ask: "IFSC must look like HDFC0001234" |
| 500 | API timeout | Show: "Connection error. [Retry]" |
| Parse | GST extraction failed | Fallback: "Couldn't read PDF. Enter company name manually" |

---

## UI Component Hierarchy

```
onboarding.html
│
├─ chat-container
│  │
│  ├─ chat-header
│  │  ├─ h1: "Delcaper Onboarding"
│  │  └─ p: "Let's get you set up in minutes!"
│  │
│  ├─ chat-messages (scrollable)
│  │  │
│  │  ├─ message.assistant
│  │  │  ├─ message-avatar: 🤖
│  │  │  └─ message-content
│  │  │     ├─ text (formatted: **bold**, `code`, _italic_)
│  │  │     └─ message-actions (buttons)
│  │  │
│  │  ├─ message.user
│  │  │  ├─ message-avatar: 👤
│  │  │  └─ message-content
│  │  │
│  │  └─ typing-indicator
│  │     └─ typing-dots (animated)
│  │
│  └─ chat-input-area
│     ├─ input-label
│     ├─ chat-input (dynamic: text/tel/file/multiline)
│     ├─ file-selected (preview)
│     └─ input-actions
│        ├─ file-button
│        └─ send-button
│
└─ JavaScript
   ├─ initChat()
   ├─ addMessage()
   ├─ sendMessage()
   ├─ uploadFile()
   └─ updateInputArea()
```

---

## Session Data Structure

```javascript
{
  id: "abc123...",
  state: "ask_aadhaar",
  data: {
    // Step 1-2: User input
    email: "accounts@addadelta.com",
    mobile: "9876543210",
    password: "Auto_Gen_Pass123",
    
    // Step 3: API response
    vendorCode: "SELLER12345",
    onboardingResponse: { ... },
    
    // Step 4: GST extraction
    gstData: {
      gstin: "09AASCA7501M2Z4",
      legalName: "ADD A DELTA PRIVATE LIMITED",
      tradeName: "ADD A DELTA PRIVATE LIMITED",
      constitution: "Private Limited Company",
      address: {
        line1: "B-17, Sector-3, fourth floor",
        city: "Noida",
        state: "Uttar Pradesh",
        pincode: "201301"
      },
      directors: ["ANSHUL GARG", "ANKIT GARG", "VIPIN SAINI", "PANKAJ DUDEJA"]
    },
    
    // Step 5-9: KYC input
    aadhaarNumber: "123456789012",
    aadhaarUrl: "https://s3.../aadhaar.jpg",
    aadhaarOtp: "123456",
    businessPan: "AASCA7501M",
    signatoryPan: "ABCDE1234F",
    bankDetails: {
      bankName: "HDFC Bank",
      branch: "Connaught Place",
      ifsc: "HDFC0001234",
      accountNumber: "12345678901234",
      accountName: "ADD A DELTA PRIVATE LIMITED",
      chequeUrl: "https://..."
    }
  },
  history: [
    { type: "assistant", content: "Welcome! Email?", timestamp: 1234567890 },
    { type: "user", content: "accounts@addadelta.com", timestamp: 1234567891 },
    ...
  ],
  createdAt: 1234567890
}
```

---

## Validation Matrix

| Field | Format | Valid Example | Invalid Example |
|-------|--------|---------------|-----------------|
| Email | RFC 5322 | `user@company.com` | `user@` |
| Mobile | 10-13 digits | `9876543210` | `123` |
| GSTIN | 15 alphanumeric | `09AASCA7501M2Z4` | `ABC123` |
| PAN | 5L+4D+1L | `ABCDE1234F` | `ABC1234` |
| Aadhaar | 12 digits | `123456789012` | `12345` |
| IFSC | 4L+0+6AN | `HDFC0001234` | `HDFC1234` |
| OTP | 6 digits | `123456` | `12` |
| URL | HTTPS | `https://...` | `http://...` |

**Validation Functions:**
```javascript
validators = {
  email: (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e),
  mobile: (m) => /^(\+91)?[6-9]\d{9}$/.test(m.replace(/[\s\-\(\)]/g, '')),
  gstin: (g) => /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(g),
  pan: (p) => /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(p),
  aadhaar: (a) => /^\d{12}$/.test(a.replace(/\s/g, '')),
  ifsc: (i) => /^[A-Z]{4}0[A-Z0-9]{6}$/.test(i),
  otp: (o) => /^\d{6}$/.test(o),
  url: (u) => u.startsWith('https://')
}
```

---

## Quick Reference: URLs

| Page | URL | Purpose |
|------|-----|---------|
| **Main UI** | http://localhost:3000/ | Landing page with links |
| **Onboarding Chat** | http://localhost:3000/onboarding.html | User-facing chat interface |
| **API Test Suite** | http://localhost:3000/test-onboarding.html | Developer testing tools |
| **Health Check** | http://localhost:3000/api/health | Server status |
| **Start Session** | POST http://localhost:3000/api/onboarding/start | Initialize chat |
| **Send Message** | POST http://localhost:3000/api/onboarding/message | User input |
| **Upload GST** | POST http://localhost:3000/api/onboarding/upload-gst | GST PDF |
| **Upload File** | POST http://localhost:3000/api/onboarding/upload-file | Images |

---

**🎉 That's the complete flow! Every step documented, every error handled, every field validated.**

**Start testing:** http://localhost:3000/onboarding.html





