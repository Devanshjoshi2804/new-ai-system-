# 📊 Metadata vs KYC Data Structure - Explanation

## ❓ Why is GST Data in Metadata?

You're seeing GST information stored in two different places:

### 1. **Onboarding API** - Uses `metadata[]` array
```json
{
  "metadata": [
    {
      "key": "GSTIN",
      "value": "09AASC7501M2Z4"
    },
    {
      "key": "CONSTITUTION",
      "value": "Private Limited Company"
    },
    {
      "key": "DIRECTORS",
      "value": "[\"ANSHUL GARG\",\"ANKIT GARG\",\"VIPIN SAINI\",\"PANKAJ DUDEJA\"]"
    }
  ]
}
```

### 2. **KYC API** - Uses dedicated fields
```json
{
  "customerData": {
    "aadhar": "557306614995",
    "businessPAN": "AABCA1906H",
    "signatoryPAN": "ADJFS8850L",
    "GST": "36ADJFS8850L1ZB",
    "kyc": {
      "nameasPerGst": "SMILE",
      "addressAsperGst": {
        "gstAddressLine1": "...",
        "gstState": "...",
        "gstPinCode": "..."
      }
    }
  }
}
```

## 🔍 Why the Difference?

### Onboarding API (Cargo API)
- **Purpose:** Create seller account quickly
- **Focus:** Basic registration, vendor code generation
- **Flexibility:** `metadata` allows storing ANY custom key-value pairs
- **Use Case:** Initial signup, not full verification

**Advantages of `metadata[]`:**
- ✅ Flexible schema - can add any field without DB changes
- ✅ Quick onboarding - don't need all KYC fields upfront
- ✅ Extensible - can store custom business logic data
- ✅ No strict validation - faster registration

### KYC API (Wallet API)
- **Purpose:** Complete KYC verification for compliance
- **Focus:** Regulatory compliance, financial operations
- **Structure:** Dedicated fields with strict validation
- **Use Case:** Full verification before enabling payments

**Advantages of dedicated fields:**
- ✅ Type safety - each field has specific validation
- ✅ Searchable - can query by GST, PAN, Aadhaar
- ✅ Compliance - meets regulatory requirements
- ✅ Verification status - tracks each document's status

## 📋 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ONBOARDING (Cargo API)                   │
│                                                             │
│  Purpose: Quick Registration                                │
│  Data Storage: metadata[] array                             │
│                                                             │
│  {                                                          │
│    "metadata": [                                            │
│      {"key": "GSTIN", "value": "09AASC7501M2Z4"},          │
│      {"key": "CONSTITUTION", "value": "Pvt Ltd"},          │
│      {"key": "DIRECTORS", "value": "[...]"}                │
│    ]                                                        │
│  }                                                          │
│                                                             │
│  ✅ Vendor Code Generated: "ADD0"                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    [User gets vendor code]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    KYC VERIFICATION (Wallet API)            │
│                                                             │
│  Purpose: Compliance & Verification                         │
│  Data Storage: Dedicated fields                             │
│                                                             │
│  {                                                          │
│    "customerData": {                                        │
│      "GST": "09AASC7501M2Z4",                              │
│      "businessPAN": "AABCA1906H",                          │
│      "signatoryPAN": "ADJFS8850L",                         │
│      "aadhar": "557306614995",                             │
│      "kyc": {                                               │
│        "nameasPerGst": "ADD A DELTA...",                   │
│        "addressAsperGst": {...},                           │
│        "gstStatus": "verified",                            │
│        "businessPanStatus": "verified"                     │
│      }                                                      │
│    }                                                        │
│  }                                                          │
│                                                             │
│  ✅ KYC Status: "verified" or "pending"                    │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 The Correct Approach

### Step 1: Onboarding (Store in metadata)
```javascript
// POST /cargo-api/onboarding
{
  "email": "test@example.com",
  "mobile": "9876543210",
  "companyName": "ADD A DELTA PRIVATE LIMITED",
  "metadata": [
    {
      "key": "GSTIN",
      "value": "09AASC7501M2Z4"
    },
    {
      "key": "CONSTITUTION",
      "value": "Private Limited Company"
    },
    {
      "key": "DIRECTORS",
      "value": "[\"ANSHUL GARG\",\"ANKIT GARG\"]"
    }
  ]
}

// Response:
{
  "vendorCode": "ADD0",
  "metadata": [...] // GST data stored here temporarily
}
```

### Step 2: KYC (Move to dedicated fields)
```javascript
// PATCH /wallet-api/kyc/ADD0
{
  "productId": "SMLINFUL",
  "gstDetails": {
    "gstNumber": "09AASC7501M2Z4"  // ← Now in dedicated field
  },
  "businessPanDetails": {
    "panNumber": "AABCA1906H"
  },
  "signatoryPanDetails": {
    "panNumber": "ADJFS8850L"
  },
  "aadharDetails": {
    "aadharNumber": "557306614995",
    "aadhaarUrl": "https://..."
  },
  "bankDetails": {
    "bankName": "SBI",
    "ifscCode": "SBIN0005943",
    "accountNumber": "31408513589"
  },
  "isGSTRegistered": true,
  "documentBusinessType": "pvt_ltd"  // ← Constitution mapped
}

// Response:
{
  "customerData": {
    "GST": "09AASC7501M2Z4",  // ← Now in dedicated field
    "kyc": {
      "nameasPerGst": "ADD A DELTA PRIVATE LIMITED",
      "addressAsperGst": {
        "gstAddressLine1": "Fourth floor, B-17, Sector-3",
        "gstState": "Uttar Pradesh",
        "gstPinCode": "201301"
      },
      "gstStatus": "verified"  // ← Verification status tracked
    }
  }
}
```

## 🔄 Data Transformation

### From Onboarding Metadata → KYC Dedicated Fields

| Onboarding (metadata) | KYC (dedicated field) | Notes |
|-----------------------|-----------------------|-------|
| `metadata[GSTIN]` | `gstDetails.gstNumber` | Moved to dedicated field |
| `metadata[CONSTITUTION]` | `documentBusinessType` | Mapped to enum value |
| `metadata[DIRECTORS]` | Not directly used | Stored for reference |
| `addresses[0]` | `kyc.addressAsperGst` | Restructured format |
| `companyName` | `kyc.nameasPerGst` | Used for verification |

### Example Transformation Code

```javascript
// Extract from onboarding metadata
const onboardingData = {
  vendorCode: "ADD0",
  metadata: [
    { key: "GSTIN", value: "09AASC7501M2Z4" },
    { key: "CONSTITUTION", value: "Private Limited Company" },
    { key: "DIRECTORS", value: "[\"ANSHUL GARG\",\"ANKIT GARG\"]" }
  ],
  addresses: [
    {
      line1: "Fourth floor, B-17, Sector-3",
      city: "Noida",
      state: "Uttar Pradesh",
      postalCode: "201301"
    }
  ]
};

// Transform to KYC payload
const kycPayload = {
  productId: "SMLINFUL",
  gstDetails: {
    gstNumber: onboardingData.metadata.find(m => m.key === "GSTIN").value
  },
  isGSTRegistered: true,
  documentBusinessType: mapConstitution(
    onboardingData.metadata.find(m => m.key === "CONSTITUTION").value
  ),
  // Add other KYC fields...
};

function mapConstitution(constitution) {
  const map = {
    "Private Limited Company": "pvt_ltd",
    "Limited Liability Partnership": "llp",
    "Proprietorship": "proprietorship",
    "Partnership": "partnership"
  };
  return map[constitution] || "other";
}
```

## 📊 Comparison Table

| Aspect | Onboarding API (metadata) | KYC API (dedicated fields) |
|--------|---------------------------|----------------------------|
| **Purpose** | Quick registration | Full verification |
| **Data Structure** | Flexible key-value pairs | Strict schema |
| **Validation** | Minimal | Comprehensive |
| **Searchability** | Limited | Full-text search enabled |
| **Verification** | Not tracked | Status per document |
| **Compliance** | Basic | Regulatory compliant |
| **Speed** | Fast (no validation) | Slower (full validation) |
| **Use Case** | Initial signup | Payment enablement |

## ✅ Best Practices

### 1. **Use Metadata for Onboarding**
```javascript
// Good: Quick registration with metadata
{
  "email": "user@example.com",
  "metadata": [
    {"key": "GSTIN", "value": "09AASC7501M2Z4"},
    {"key": "CUSTOM_FIELD", "value": "any value"}
  ]
}
```

### 2. **Use Dedicated Fields for KYC**
```javascript
// Good: Proper KYC with validation
{
  "gstDetails": {
    "gstNumber": "09AASC7501M2Z4"
  },
  "businessPanDetails": {
    "panNumber": "AABCA1906H"
  }
}
```

### 3. **Don't Mix Approaches**
```javascript
// Bad: Don't send GST in metadata to KYC API
{
  "metadata": [
    {"key": "GSTIN", "value": "09AASC7501M2Z4"}  // ❌ Wrong
  ]
}

// Good: Use dedicated fields
{
  "gstDetails": {
    "gstNumber": "09AASC7501M2Z4"  // ✅ Correct
  }
}
```

## 🎯 Summary

### Why Metadata in Onboarding?
- ✅ **Flexibility:** Can store any custom data
- ✅ **Speed:** No schema validation delays
- ✅ **Extensibility:** Easy to add new fields
- ✅ **Temporary:** Just for initial registration

### Why Dedicated Fields in KYC?
- ✅ **Compliance:** Meets regulatory requirements
- ✅ **Validation:** Each field properly validated
- ✅ **Searchable:** Can query by GST, PAN, etc.
- ✅ **Status Tracking:** Know verification state
- ✅ **Permanent:** Used for all financial operations

## 🔄 Complete Flow Example

```javascript
// 1. Onboarding - Store in metadata
const onboardingResponse = await axios.post('/cargo-api/onboarding', {
  email: "test@example.com",
  mobile: "9876543210",
  metadata: [
    { key: "GSTIN", value: "09AASC7501M2Z4" }
  ]
});

const vendorCode = onboardingResponse.data.vendorCode; // "ADD0"

// 2. KYC - Use dedicated fields
const kycResponse = await axios.patch(`/wallet-api/kyc/${vendorCode}`, {
  productId: "SMLINFUL",
  gstDetails: {
    gstNumber: "09AASC7501M2Z4"  // ← Now in proper field
  },
  businessPanDetails: {
    panNumber: "AABCA1906H"
  },
  // ... other KYC fields
});

// 3. Check KYC status
const kycStatus = kycResponse.data.customerData.kyc.gstStatus; // "verified"
```

## 💡 Key Takeaway

**Metadata** = Temporary storage for quick onboarding  
**Dedicated Fields** = Permanent storage for verified KYC data

The GST data flows from `metadata` (onboarding) → `gstDetails.gstNumber` (KYC) during the verification process.

This is by design - it separates the **registration phase** (fast, flexible) from the **verification phase** (strict, compliant).
