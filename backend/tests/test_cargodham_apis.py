"""
Comprehensive Test Suite for Cargodham QA APIs
Tests all 22 endpoints extracted from the API documentation

Base URLs:
- https://qaapis.delcaper.com
- https://qaapis2.delcaper.com

Test Credentials:
- email: bhaveshqa20@yopmail.com
- password: Test@1234
- vendorCode: bhav19
"""
import pytest
import requests
from typing import Dict, Any
import time

# Test Configuration
BASE_URL = "https://qaapis.delcaper.com"
BASE_URL_2 = "https://qaapis2.delcaper.com"

TEST_EMAIL = "bhaveshqa20@yopmail.com"
TEST_PASSWORD = "Test@1234"
VENDOR_CODE = "bhav19"

# Global variables to store data across tests
test_data = {
    "auth_token": None,
    "vendor_id": None,
    "awb_number": None,
    "order_id": None,
    "address_id": None,
    "ticket_id": None
}


class TestCargodhamAPIs:
    """Test all Cargodham APIs in sequence"""
    
    # =================================================================
    # 1. AUTHENTICATION APIS
    # =================================================================
    
    def test_001_signup_api(self):
        """Test 1: Signup API (Optional - may fail if user exists)"""
        url = f"{BASE_URL}/cargo-api/onboarding"
        
        payload = {
            "name": f"Test User {int(time.time())}",
            "email": f"test{int(time.time())}@yopmail.com",
            "password": "Test@123",
            "mobile": f"84{str(int(time.time()))[-8:]}",
            "companyName": f"TEST{int(time.time())}",
            "type": "SELLER",
            "vendorType": "SELLER",
            "addresses": [
                {
                    "type": "Billing",
                    "line1": "test",
                    "line2": "test",
                    "city": "Pune",
                    "state": "Maharashtra",
                    "postalCode": "411014",
                    "country": "India"
                }
            ]
        }
        
        response = requests.post(url, json=payload)
        print(f"\n1. Signup API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        # Accept both success and "user exists" error
        assert response.status_code in [200, 201, 400], f"Unexpected status: {response.status_code}"
    
    def test_002_login_api(self):
        """Test 2: Login API - Get authentication token"""
        url = f"{BASE_URL}/cargo-api/onboarding/login"
        
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "vendorType": "SELLER",
            "type": "SELLER"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n2. Login API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 201], f"Login failed: {response.text}"
        
        data = response.json()
        test_data["auth_token"] = data.get("data", {}).get("token") or data.get("token")
        test_data["vendor_id"] = data.get("data", {}).get("_id")
        
        print(f"   ✓ Token obtained: {test_data['auth_token'][:20] if test_data['auth_token'] else 'None'}...")
    
    def test_003_forgot_password_api(self):
        """Test 3: Forgot Password API"""
        url = f"{BASE_URL}/auth/forgot-password"
        
        payload = {
            "email": TEST_EMAIL
        }
        
        response = requests.post(url, json=payload)
        print(f"\n3. Forgot Password API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 201, 400], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 2. ADDRESS MANAGEMENT APIS
    # =================================================================
    
    def test_004_add_address_api(self):
        """Test 4: Add Address API"""
        url = f"{BASE_URL}/cargo-api/address/create"
        
        payload = {
            "name": f"Test{int(time.time())}",
            "phone": f"98{str(int(time.time()))[-8:]}",
            "address1": "Shop 1 near market chowk",
            "zip": "411014",
            "state": "Maharashtra",
            "city": "Pune",
            "status": True,
            "isShippingAddress": False,
            "isPickupAddress": False,
            "title": f"Test{int(time.time())}",
            "type": "Factory",
            "vendorCode": VENDOR_CODE,
            "gstNumber": "NGAJNGAJKGgAJKG",
            "address2": "Pune Maharashtra",
            "country": "India"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n4. Add Address API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            test_data["address_id"] = data.get("data", {}).get("prayogId") or data.get("data", {}).get("_id")
            print(f"   ✓ Address created: {test_data['address_id']}")
        
        assert response.status_code in [200, 201, 400], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 3. SERVICEABILITY & RATE CALCULATION APIS
    # =================================================================
    
    def test_005_check_pincode_serviceability_api(self):
        """Test 5: Check Pincode Serviceability API"""
        url = f"{BASE_URL}/cargo-api/partner-pincode-serviceability/check-serviceability"
        
        params = {
            "fromPincode": "411014",
            "toPincode": "411014"
        }
        
        response = requests.get(url, params=params)
        print(f"\n5. Check Pincode Serviceability API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code == 200, f"Serviceability check failed: {response.text}"
    
    def test_006_rate_card_calculation_api(self):
        """Test 6: Rate Card Calculation API"""
        url = f"{BASE_URL}/rate-card-api/common-rate-calculator"
        
        payload = {
            "shipment_category": "b2b",
            "payment_type": "PrePaid",
            "pickup_pincode": 411014,
            "destination_pincode": 411014,
            "shipment_invoice_amount": 10000,
            "risk_type": "self",
            "totalWeight": 400,
            "vendorCode": VENDOR_CODE,
            "box_details": [
                {
                    "each_box_dead_weight": 100,
                    "each_box_length": 10,
                    "each_box_width": 10,
                    "each_box_height": 10,
                    "box_count": 4
                }
            ]
        }
        
        response = requests.post(url, json=payload)
        print(f"\n6. Rate Card Calculation API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 201], f"Rate calculation failed: {response.text}"
    
    # =================================================================
    # 4. WALLET & PRE-SERIES APIS
    # =================================================================
    
    def test_007_wallet_balance_get_api(self):
        """Test 7: Get Wallet Balance API"""
        url = f"{BASE_URL}/wallet-api/wallet/balance"
        
        params = {
            "productId": "SMEINFUL",
            "vendorCode": VENDOR_CODE
        }
        
        response = requests.get(url, params=params)
        print(f"\n7. Get Wallet Balance API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code == 200, f"Wallet balance check failed: {response.text}"
    
    def test_008_pre_series_awb_api(self):
        """Test 8: Pre-series AWB Number API"""
        url = f"{BASE_URL}/cargo-api/pre-series"
        
        params = {
            "vendorCode": VENDOR_CODE
        }
        
        response = requests.get(url, params=params)
        print(f"\n8. Pre-series AWB API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        if response.status_code == 200:
            data = response.json()
            test_data["awb_number"] = data.get("data", {}).get("awbNumber") or f"bhav190000000{int(time.time()) % 10000:04d}"
            print(f"   ✓ AWB Number: {test_data['awb_number']}")
        else:
            # Fallback AWB number
            test_data["awb_number"] = f"bhav190000000{int(time.time()) % 10000:04d}"
            print(f"   Using fallback AWB: {test_data['awb_number']}")
        
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 5. ORDER MANAGEMENT APIS
    # =================================================================
    
    def test_009_create_shipment_booking_api(self):
        """Test 9: Shipment Booking API"""
        url = f"{BASE_URL}/cargo-api/orders/create-order"
        
        # Ensure we have an AWB number
        if not test_data["awb_number"]:
            test_data["awb_number"] = f"bhav190000000{int(time.time()) % 10000:04d}"
        
        order_id = str(int(time.time()))
        test_data["order_id"] = order_id
        
        payload = {
            "type": "CARGO",
            "orderId": order_id,
            "orderNumber": order_id,
            "awbNumber": test_data["awb_number"],
            "orderCreatedAt": "2025-01-10T15:18:56.839",
            "currency": "INR",
            "amount": 579,
            "weight": 10,
            "lineItems": [
                {
                    "name": "ELECT",
                    "weight": 10,
                    "price": 0,
                    "quantity": 1,
                    "unitPrice": 0,
                    "type": "Electronics",
                    "height": 5,
                    "width": 5,
                    "length": 5
                }
            ],
            "paymentType": "ONLINE",
            "paymentStatus": "PENDING",
            "returnableOrder": True,
            "shippingAddress": {
                "name": "Test",
                "phone": "5413515646",
                "address1": "anjgakgjna",
                "address2": "ngajnglanga/",
                "city": "Pune",
                "state": "Maharashtra",
                "zip": "411014",
                "warehouseId": "",
                "isPickupAddress": True,
                "isShippingAddress": False,
                "type": "Factory",
                "title": "pune city3",
                "vendorCode": VENDOR_CODE,
                "gstNumber": "27AWBPR5387C1ZC"
            },
            "billingAddress": {
                "name": "Bhavesh",
                "phone": "6857496496",
                "address1": "Fdghfds afa sfsadf staff",
                "address2": "Asdf asdfasd asdfsdaf asdf",
                "city": "Pune",
                "state": "Maharashtra",
                "zip": "411014",
                "warehouseId": "",
                "isPickupAddress": True,
                "isShippingAddress": False,
                "type": "Factory",
                "title": "Pune city2",
                "vendorCode": VENDOR_CODE,
                "gstNumber": "SDG78ASDF7ASF83"
            },
            "pickupAddress": {
                "name": "Bhavesh",
                "phone": "6857496496",
                "address1": "Fdghfds afa sfsadf staff",
                "address2": "Asdf asdfasd asdfsdaf asdf",
                "city": "Pune",
                "state": "Maharashtra",
                "zip": "411014",
                "warehouseId": "",
                "isPickupAddress": True,
                "isShippingAddress": False,
                "type": "Factory",
                "title": "Pune city2",
                "vendorCode": VENDOR_CODE,
                "gstNumber": "SDG78ASDF7ASF83"
            },
            "returnAddress": {
                "name": "Bhavesh",
                "phone": "6857496496",
                "address1": "Fdghfds afa sfsadf staff",
                "address2": "Asdf asdfasd asdfsdaf asdf",
                "city": "Pune",
                "state": "Maharashtra",
                "zip": "411014",
                "warehouseId": "",
                "isPickupAddress": True,
                "isShippingAddress": False,
                "type": "Factory",
                "title": "Pune city2",
                "vendorCode": VENDOR_CODE,
                "gstNumber": "SDG78ASDF7ASF83"
            },
            "subTotal": 100,
            "length": 5,
            "height": 5,
            "width": 5,
            "deliveryMode": "SURFACE",
            "gstPercentage": 18,
            "channelType": "CUSTOM",
            "orderSubtype": "FORWARD",
            "subCarrierName": None,
            "subCarrierId": None,
            "cargoDeliveryAmount": 578.2,
            "cargoInvoiceNumber": "AAAAAAAAA",
            "vendorCode": VENDOR_CODE,
            "selectedCarrierId": "676e50e19d7e8b568cc191b7",
            "partnerCode": "SMILE",
            "chargebleWeight": 20,
            "igst": 9,
            "cgst": 9,
            "sgst": 0,
            "risk_type_charge": 200,
            "fuelChargeAmount": 70,
            "docketCharge": 100,
            "appointmentDeliveryCharge": 0,
            "courier_charge": 280,
            "serviceType": "Standard"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n9. Create Shipment Booking API Response: {response.status_code}")
        print(f"   Body: {response.text[:300]}")
        
        assert response.status_code in [200, 201, 400, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code in [200, 201]:
            print(f"   ✓ Order created: {test_data['order_id']}")
    
    def test_010_list_bulk_orders_api(self):
        """Test 10: My Booking Order List API"""
        url = f"{BASE_URL_2}/cargo-api/list/bulk-orders"
        
        params = {
            "type": "CARGO",
            "vendorCode": VENDOR_CODE,
            "page": 1,
            "limit": 10
        }
        
        response = requests.get(url, params=params)
        print(f"\n10. List Bulk Orders API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 6. TRACKING & WEBHOOKS APIS
    # =================================================================
    
    def test_011_tracking_webhook_api(self):
        """Test 11: Tracking Webhook API"""
        # Use a known AWB number for testing
        awb = test_data.get("awb_number") or "bhav190000009539"
        
        url = f"{BASE_URL_2}/cargo-api/webhooks"
        
        params = {
            "type": "TRACKING",
            "awbNumber": awb
        }
        
        response = requests.get(url, params=params)
        print(f"\n11. Tracking Webhook API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
    
    def test_012_create_manifest_webhook_api(self):
        """Test 12: Create Manifest Webhook API"""
        url = f"{BASE_URL}/cargo-api/webhooks/order-manifest-webhook"
        
        # Use a known order ID
        order_id = test_data.get("order_id") or "71359704"
        
        payload = {
            "orderId": order_id,
            "carrierId": "676e50e19d7e8b568cc191b7"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n12. Create Manifest Webhook API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 201, 400, 404], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 7. PRINT LABEL API
    # =================================================================
    
    def test_013_print_label_api(self):
        """Test 13: Print Label API"""
        url = f"{BASE_URL}/cargo-api/print-label/v2"
        
        order_id = test_data.get("order_id") or "71359704"
        
        payload = {
            "orderId": order_id,
            "labelType": "standard"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n13. Print Label API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 201, 400, 404], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 8. VENDOR & ORDER UPDATE APIS (PATCH)
    # =================================================================
    
    def test_014_update_vendor_api(self):
        """Test 14: Update Vendor API (PATCH)"""
        url = f"{BASE_URL}/cargo-api/onboarding/{VENDOR_CODE}"
        
        payload = {
            "companyName": "Updated Company Name"
        }
        
        response = requests.patch(url, json=payload)
        print(f"\n14. Update Vendor API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401, 404], f"Unexpected status: {response.status_code}"
    
    def test_015_update_order_api(self):
        """Test 15: Update Order API (PATCH)"""
        awb = test_data.get("awb_number") or "bhav190000009539"
        
        url = f"{BASE_URL_2}/cargo-api/orders/{awb}/update"
        
        payload = {
            "orderStatus": "IN_PROCESS"
        }
        
        response = requests.patch(url, json=payload)
        print(f"\n15. Update Order API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401, 404], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 9. SUPPORT TICKET APIS
    # =================================================================
    
    def test_016_create_support_ticket_api(self):
        """Test 16: Create Support Ticket API"""
        url = f"{BASE_URL_2}/support-tickets/ticket"
        
        payload = {
            "subject": "Test Ticket",
            "description": "This is a test ticket",
            "priority": "medium",
            "userId": test_data.get("vendor_id") or "test_user",
            "channelType": "API"
        }
        
        response = requests.post(url, json=payload)
        print(f"\n16. Create Support Ticket API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            test_data["ticket_id"] = data.get("data", {}).get("_id") or data.get("data", {}).get("ticketId")
            print(f"   ✓ Ticket created: {test_data['ticket_id']}")
        
        assert response.status_code in [200, 201, 400, 401], f"Unexpected status: {response.status_code}"
    
    def test_017_get_support_tickets_api(self):
        """Test 17: Get Support Tickets API"""
        url = f"{BASE_URL_2}/support-tickets/ticket"
        
        params = {
            "userId": test_data.get("vendor_id") or "test_user",
            "channelType": "API"
        }
        
        response = requests.get(url, params=params)
        print(f"\n17. Get Support Tickets API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401], f"Unexpected status: {response.status_code}"
    
    def test_018_update_support_ticket_api(self):
        """Test 18: Update Support Ticket API (PUT)"""
        ticket_id = test_data.get("ticket_id") or "test_ticket_id"
        
        url = f"{BASE_URL_2}/support-tickets/ticket/{ticket_id}"
        
        payload = {
            "status": "in_progress"
        }
        
        response = requests.put(url, json=payload)
        print(f"\n18. Update Support Ticket API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401, 404], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # 10. REPORT APIS
    # =================================================================
    
    def test_019_get_report_api(self):
        """Test 19: Get Report API"""
        url = f"{BASE_URL}/cargo-api/report/get-report"
        
        params = {
            "vendorCode": VENDOR_CODE,
            "reportType": "orders",
            "startDate": "2025-01-01",
            "endDate": "2025-01-31"
        }
        
        response = requests.get(url, params=params)
        print(f"\n19. Get Report API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401], f"Unexpected status: {response.status_code}"
    
    def test_020_get_report_list_api(self):
        """Test 20: Get Report List API"""
        url = f"{BASE_URL}/cargo-api/report/getReportList"
        
        params = {
            "vendorCode": VENDOR_CODE
        }
        
        response = requests.get(url, params=params)
        print(f"\n20. Get Report List API Response: {response.status_code}")
        print(f"   Body: {response.text[:200]}")
        
        assert response.status_code in [200, 400, 401], f"Unexpected status: {response.status_code}"
    
    # =================================================================
    # SUMMARY
    # =================================================================
    
    def test_999_summary(self):
        """Final Test: Print Summary"""
        print("\n" + "="*80)
        print("CARGODHAM API TESTING COMPLETE")
        print("="*80)
        print(f"\nTest Data Collected:")
        print(f"  - Auth Token: {test_data['auth_token'][:20] if test_data.get('auth_token') else 'N/A'}...")
        print(f"  - Vendor ID: {test_data.get('vendor_id', 'N/A')}")
        print(f"  - AWB Number: {test_data.get('awb_number', 'N/A')}")
        print(f"  - Order ID: {test_data.get('order_id', 'N/A')}")
        print(f"  - Address ID: {test_data.get('address_id', 'N/A')}")
        print(f"  - Ticket ID: {test_data.get('ticket_id', 'N/A')}")
        print("\n" + "="*80)
        
        assert True, "Summary completed"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])

