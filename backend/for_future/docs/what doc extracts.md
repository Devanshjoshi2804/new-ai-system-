Welcome to CargoDham AI 🚀
Let's get your logistics API integrated in minutes!

Company Info
Tell us about your company
Upload Docs
Upload API documentation
OCR Extract
Extract text from PDF
Review OCR
Review extracted text
5
AI Analysis
AI finds endpoints
6
API Testing
Test all endpoints
7
Activate
Activate integration
Integration Ready!
Review what the AI discovered and activate your integration

Discovered APIs
Base URL

https://qaapis.delcaper.com

Endpoints Found

23

Workflows

0

OCR Text Extracted
Pages Processed

0

Characters Extracted

64,583

✅ OCR extraction completed successfully! View extracted text below:

=== Document 02178c97-f8b2-4334-b081-2cdd1866283f (PyMuPDF4LLM) ===

--- Page 1 ---

CARGODHAM QA DOCUMENT
Use only QA ID and password - Prepaid/Postpaid Account type both​

email: "bhaveshqa20@yopmail.com"

password: "Test@1234"

The fields are Case Sensitive, Please follow the requested body format only.
1. Signup API
Purpose
The Signup API is used to register a new vendor user by collecting necessary details such as name, email, password, and company information.

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/onboarding

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Vendortype and address is necessary for signup, Kindly use vendorType as SELLER​ Request Body Format - use new ID to test the same
{ "name": "Maadhav", "email": "Test1234567@yopmail.com", "password": "Test@123", "mobile": "8491153123", "companyName": "TEST312", "type": "SELLER", "vendorType": "SELLER",

--- Page 2 ---

"addresses": [ { "type": "Billing", "line1": "test",

"line2": "test",

"city": "Pune", "state": "Maharashtra", "postalCode": "411014", "country": "India" } ] }

Required & Optional Fields Breakdown

Variable

Name

Data

Required Description Type

name string ✅ Yes Full name of the user.

email string ✅ Yes Email address for user identification.

User's phone number for contact and mobile string ✅ Yes verification.

password string ✅ Yes Password for account security.

createdDate string ❌ No Date when the user was created.

vendorType string ✅ Yes Type of vendor.

channelCode string ❌ No Code representing the sales channel.

storeCode string ❌ No Code representing the store.

companyNa

me

string ✅ Yes The name of the company (if applicable).

address string ✅ Yes Address of the company/vendor.

vendorCode string ✅ Yes A unique code assigned to the vendor.

--- Page 3 ---

Success Response (200 OK)
{ "data": { "_id": "68d0f098a57f130bad056137" },

"status": 200

}

Error Response (400/401/500)
If users already exists

{

"status": 400,

"trace": {

"name": "HttpException",

"error": "User already exists"

},

"message": "User already exists"

}

Status Codes
Code Meaning

200 Signup successful

400 Invalid input or user exists

401 Unauthorized

500 Internal server error

--- Page 4 ---

- 2. Login API user id and password (created by you)
Purpose
The Login API is used to authenticate a user and generate a token that can be used for accessing protected endpoints within the system.

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/onboarding/login

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

vendorType is mandatory in, Please use vendorType: SELLER Request Body Format
{ "email": "bhaveshqa20@yopmail.com", "password": "Test@1234", "vendorType": "SELLER", "type": "SELLER" }

--- Page 5 ---

Request Body Field Description
Field Type Required Description

email String ✅ Yes The registered email of the user

password String ✅ Yes The user's password

vendorType String ✅ Yes Type of vendor (e.g., SELLER, BUYER) remember Uppercase

Success Response (201 OK)
{ "status": 201, "message": "Onboarding login successfully", "data": { "_id": "68bf30ff9c2c185ce3bf8dfb", "personalDetails": { "email": "bhaveshqa20@yopmail.com", "name": "string", "companyName": "bhavesh qa 20 pvt ltd",

"mobile": "6854985484"

}, "type": "SELLER",

"vendorCode": "bhav19"

}

No authorisation token is required. Error Response (400/401/500)
{ "status": false,

"message": "Invalid email or password" }

Status Codes
--- Page 6 ---

Code Meaning

200 Login successful

400 Invalid input or credentials

401 Unauthorized (invalid credentials)

500 Internal server error

3. Forgot Password API
Purpose
The Forgot Password API is used for initiating the password reset process by sending a password reset link to the user's registered email address.

API Method
POST

Endpoint
https://qaapis.delcaper.com/auth/forgot-password

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Request Body Format
{ "email": "demoqaprashant@yopmail.com" }

Request Body Field Description
Field Type Required Description

--- Page 7 ---

email String ✅ Yes The email address of the user requesting password reset

Success Response (200 OK)
{

"data": true,

"status": 200

}

Error Response (400/401/500)
If user not exists

{

"status": 400,

"trace": {

"name": "HttpException",

"error": {}

},

"message": "User with this email / mobile does not exists"

}

Status Codes
Code Meaning

200 Password reset link sent successfully

400 Invalid input/validation error

500 Internal server error

--- Page 8 ---

4. Add Address API
Purpose
The Create Address API is used in the logistics system to add or update pickup and delivery addresses of a user. These addresses are essential for managing various logistics operations such as product pickup, shipment delivery, and location-based service configuration.​Note: After adding the address using Add Address API you will get a prayog ID in the success response body which is a unique ID, Please store it in your system according to your convenience

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/address/create

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Request Body Format
{ "name": "Test456456",

"phone": "9864569561", "address1": "Shop 1 near market chowk", "zip": "411014",

--- Page 9 ---

"state": "Maharashtra",

"city": "Pune", "status": true, "isShippingAddress": false, "isPickupAddress": false, "title": "Test1234",

"type": "Factory", "vendorCode": "bhav19", "gstNumber": "NGAJNGAJKGgAJKG", "address2": "Pune Maharashtra",

"country": "India" }

Request Body Field Description
Field Type Required Description

name String ✅ Yes Contact or entity name

phone String ✅ Yes 10-digit mobile number

address1 String ✅ Yes Main address line

address2 String ❌ No Additional address info

zip String ✅ Yes Postal (PIN) code

state String ✅ Yes State name in uppercase

city String ✅ Yes City name

status Boolean ✅ Yes Whether the address is active

isShippingAddress Boolean ❌ No Marks as shipping address

isPickupAddress Boolean ❌ No Marks as pickup location

title String ❌ No Friendly label for internal use

type String ✅ Yes Address type (e.g., Factory, Office)

vendorCode String ✅ Yes Unique identifier for the vendor

gstNumber String ❌ No GSTIN (15 characters)

--- Page 10 ---

Success Response (200 OK)
{ "status": 201, "data": { "vendorCode": "bhav19",

"title": "Test1234",

"name": "Test456456",

"phone": "9864569561", "address1": "Shop 1 near market chowk", "address2": "Pune Maharashtra",

"city": "Pune", "state": "Maharashtra",

"country": "India", "zip": "411014", "status": true,

"type": "Factory", "gstNumber": "NGAJNGAJKGgAJKG", "isActive": true,

"createdDate": "2025-10-03T08:55:28.716Z",

"updatedDate": "2025-10-03T08:55:28.716Z", "prayogId": "270d71d6-cc06-4a7e-83f1-4a4e93125eb2", "source": "api", "_id": "68df8f802faf3d85044abe2a", "createdAt": "2025-10-03T08:55:28.717Z",

"updatedAt": "2025-10-03T08:55:28.717Z", "__v": 0 } }

Error Response (400/401/500)
{ "status": false,

"message": "Validation error", "errors": { "phone": "Invalid phone number" } }

Status Codes
--- Page 11 ---

Code Meaning

200 Address created successfully

400 Invalid input/validation error

401 Unauthorized (missing/invalid JWT)

500 Internal server error

5. Check Pincode Serviceability API
Purpose
Please note that QA pincode to check this functionality and they are different then Production Pincode.​This API is help us to check whether the first mile pincode is serviceable or last mile pincode is serviceable, and by which partner. ​In Response body Partner code refers as the service available, as in this case it is “SMILE” i.e Shree

Maruti.

fromPincode and toPincode is used to check whether we are serviceable in that particular pincode or not.

NOTE: If you want a particular partner for your shipment the FirstMile and LastMile conditions should

be true.

--- Page 12 ---

API Method
GET

Endpoint
https://qaapis.delcaper.com/cargo-api/partner-pincode-serviceability/check-serviceability?fromPi

ncode=411014&toPincode=411014

Query Parameters
Parameter Required Type Description

fromPincode ✅ Yes String Source pincode

toPincode ✅ Yes String Destination pincode

Success Response (200 OK)
{

"status": 200,

"data": [ { "fromPincode": 411014,

"toPincode": 411014,

"activePartners": [ { "partnerCode": "SMILE", "isActive": true,

"partnerData": { "email": "smileqa@shreemaruti.com",

"name": "SMILe",

"companyName": "smile pvt. ltd.",

"mobile": "9585491101"

}, "city": "MUMBAI", "cityName": "MUMBAI", "districtname": "",

"status": "Serviceable",

"zone": "West 2",

"firstMile": true,

"lastMile": true,

--- Page 13 ---

"hubCode": "91",

"cod": false,

"toPay": false, "surface": true,

"air": true,

"rail": true,

"activedate": "2025-09-22T04:27:39.116Z"

}, { "partnerCode": "bhavesh_qa_32", "isActive": true,

"partnerData": { "email": "bhaveshqa32@yopmail.com", "name": "Bhavesh Qa 32", "companyName": "bhavesh qa 32 pvt. ltd.",

"mobile": "7867594852"

}, "city": "MUMBAI", "cityName": "MUMBAI", "districtname": "",

"status": "ODA",

"zone": "N2",

"firstMile": true,

"lastMile": true,

"hubCode": "91",

"cod": false,

"toPay": false, "surface": true,

"air": true,

"rail": true,

"activedate": "2025-09-19T05:26:33.572Z"

} ] } ] }

Error Response (400/500)
{ "statusCode": 400,

--- Page 14 ---

"message": [ "toPincode must be a number conforming to the specified constraints" ] }

Status Codes
Code Meaning

200 Service available

400 Invalid input

500 Internal server error

6. Rate Card Calculation API
Purpose
The Rate Card Calculation API is used to compute the shipping rate based on shipment parameters such as weight, pin codes, invoice amount, and vendor configuration.

Basic purpose to understand the charges we would charge you for upcoming orders.

The Invoice amount is in INR,​

The Total weight is in Kilograms (KG)

The Dimensions are in CM

Shipment Invoice amount is referred as the invoice value of the goods being shipped in INR.

API Method
POST

Endpoint
https://qaapis.delcaper.com/rate-card-api/common-rate-calculator

Headers
Name Required Type Description

--- Page 15 ---

Content-Type ✅ Yes String Must be application/json

Request Body Format
{ "shipment_category": "b2b", "payment_type": "PrePaid", "pickup_pincode": 411014, "destination_pincode": 411014, "shipment_invoice_amount": 10000, "risk_type": "self", "totalWeight": 400, "vendorCode": "bhav19",

"box_details": [ { "each_box_dead_weight": 100, "each_box_length": 10, "each_box_width": 10, "each_box_height": 10, "box_count": 4 } ] }

Request Body Field Description
Field Type Required Description

shipment_category String ✅ Yes Category of shipment (e.g., b2b)

payment_type String ✅ Yes Mode of payment (PrePaid or COD)

pickup_pincode Number ✅ Yes Pickup location pincode

destination_pincode Number ✅ Yes Destination pincode

shipment_invoice_amount Number ✅ Yes Invoice amount in currency

risk_type String ✅ Yes Risk handling type (self, carrier)

totalWeight Number ✅ Yes Total shipment weight in kilograms

--- Page 16 ---

vendorCode String ✅ Yes Vendor identifier

box_details Array ✅ Yes Array of box dimension and weight details

each_box_dead_weight Number ✅ Yes Dead weight per box

each_box_length Number ✅ Yes Length per box in cm

each_box_width Number ✅ Yes Width per box in cm

each_box_height Number ✅ Yes Height per box in cm

box_count Number ✅ Yes Number of such boxes

Success Response (201)
{

"status": 201,

"data": [ { "courier_name": "SMILe Delivery", "courier_type": "surface", "zone": null,

"tat": 11,

"validTat": 4,

"billable_weight": 400, "risk_type_name": "self", "total_shipping_charges": 5498.8, "courier_charge": 3600, "actualCharge": 4160, "GST": {

"cGST": "9",

"iGST": "9"

}, "other_additional_charges": { "risk_type_charge": 500, "lr_cost": 0, "green_tax": 0, "handling_charge": 0, "to_pay": 0, "warai_charge": 0, "state_tax": 0, "odc_charge": 0,

--- Page 17 ---

"pickup_charge": 0, "fuelChargeAmount": 360, "docketCharge": 200, "odacharge": 0, "appointmentDeliveryCharge": 400, "platformFee": 0 }, "smileCharges": { "perKgPrice": 9, "maxLiability": 200, "minimumWeight": 20, "fuelChargePer": 10, "minimumFreight": 4000, "oda": 0,

"volumetricWeight": 0.8888888888888888, "gstAmount": 838.8 }, "partnerCode": "SMILE", "partnerName": "SMILe", "carrierName": "SMILE",

"isAppointment": true }, { "courier_name": "SMILe Air", "courier_type": "air", "zone": null,

"tat": 21,

"validTat": 4,

"billable_weight": 400, "risk_type_name": "self", "total_shipping_charges": 8217.52, "courier_charge": 6000, "actualCharge": 6963, "GST": {

"cGST": "9",

"iGST": "9"

}, "other_additional_charges": { "risk_type_charge": 0, "lr_cost": 0, "green_tax": 0, "handling_charge": 0,

--- Page 18 ---

"to_pay": 0, "warai_charge": 0, "state_tax": 0, "odc_charge": 0, "pickup_charge": 0, "fuelChargeAmount": 720, "docketCharge": 243, "odacharge": 0, "appointmentDeliveryCharge": 120, "platformFee": 1 }, "smileCharges": { "perKgPrice": 15, "maxLiability": 300, "minimumWeight": 10, "fuelChargePer": 12, "minimumFreight": 340, "oda": 0,

"volumetricWeight": 1.4814814814814814, "gstAmount": 1253.52 }, "partnerCode": "SMILE", "partnerName": "SMILe", "carrierName": "SMILE",

"isAppointment": true }, { "courier_name": "supplier test21 Delivery", "courier_type": "surface", "zone": null,

"tat": null,

"validTat": 4,

"billable_weight": 400, "risk_type_name": "self", "total_shipping_charges": 6744.88, "courier_charge": 4800, "actualCharge": 5706, "GST": {

"cGST": "9",

"iGST": "9"

}, "other_additional_charges": {

--- Page 19 ---

"risk_type_charge": 0, "lr_cost": 0, "green_tax": 0, "handling_charge": 0, "to_pay": 0, "warai_charge": 0, "state_tax": 0, "odc_charge": 0, "pickup_charge": 0, "fuelChargeAmount": 672.0000000000001, "docketCharge": 234, "odacharge": 0, "appointmentDeliveryCharge": 300, "platformFee": 10 }, "smileCharges": { "perKgPrice": 12, "maxLiability": 523, "minimumWeight": 12, "fuelChargePer": 14, "minimumFreight": 480, "oda": 0,

"volumetricWeight": 1.4814814814814814, "gstAmount": 1028.8799999999999 }, "partnerCode": "supplier_test21", "partnerName": "supplier test21", "transporterId": null, "carrierName": "supplier_test21", "isAppointment": true } ] }

Error Response (400/401/500)
{ "status": false,

"message": "Validation error", "errors": {

--- Page 20 ---

"pickup_pincode": "Invalid pincode" // check pincode is serviceable list shared with you for QA

account

} }

Status Codes
Code Meaning

200 Rate calculated successfully

400 Invalid input/validation error

401

404

Unauthorized (missing/invalid JWT)

Cannot Post/ Not Found

500 Internal server error

7. My Booking Order List API
Purpose
The My Booking Order List API is used to fetch a list of booked cargo orders for a specific vendor. It supports pagination and can filter based on whether the orders are parent orders. Call orders in pagination

50 orders

This API when called gives us the list of the orders booked by the user. Identified by the vendorCode, Please use vendorCode=bhav19 only.

API Method
GET

Endpoint
https://qaapis2.delcaper.com/cargo-api/list/bulk-orders?type=CARGO&vendorCode=bhav19&page=1&li

mit=10

Headers
--- Page 21 ---

Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Query Parameters
Parameter Required Type Description

isParentOrder ✅ Yes Boolean Whether to filter for parent orders

type ✅ Yes String Type of shipment (e.g., CARGO)

vendorCode ✅ Yes String Vendor identifier

page ✅ Yes Number Page number for pagination

limit ✅ Yes Number Number of results per page

Success Response (200 OK)
{

"status": 200,

"message": "Order list", "data": { "ordersList": [ { "_id": "68ac6613e32dcafb90899f08", "vendorCode": "bhav19",

"originalOrderId": "71359704", "type": "CARGO", "originalOrderNumber": "71359704", "orderCreatedAt": "2025-08-25T13:33:07.724Z",

"orderUpdatedAt": "2025-08-25T13:33:07.724Z", "currency": "INR", "paymentType": "ONLINE", "paymentStatus": "PAID",

"amount": 767,

"weight": 1, "length": 1, "width": 1,

--- Page 22 ---

"height": 1, "orderStatus": "IN_PROCESS", "shippingType": "FORWARD", "remarks": "No Remarks",

"deliveryVerification": false, "orderCreatedFrom": "API",

"shippingAddress": { "_id": "6773f2ab2c8759abdddf20dc", "id": null,

"name": "demo aakurdi user",

"phone": "9823456784", "address1": "asdsadsdasd sad as title updated again", "address2": "",

"zip": "400001", "state": "Maharashtra",

"city": "Mumbai", "latitude": 0,

"longitude": 0,

"status": true,

"isShippingAddress": null, "isPickupAddress": null, "title": "demo aakurdia updated", "type": "Warehourse", "vendorCode": "bhav19",

"warehouseId": null,

"createdDate": "2024-12-31T13:33:31.273Z",

"updatedDate": "2025-08-19T08:20:14.249Z", "createdById": "6773f2ab2c8759abdddf20db", "updatedById": "68a433be6d529ef173a37f9c", "createdBy": "Demo QA Prashant", "updatedBy": "Demo QA Prashant Edit", "innoCity": "Ahmedabad", "innoState": "GUJARAT",

"owner": "INNOFULFIL",

"gstNumber": "27AWBPR5387C1ZC", "serviceType": "CARGO" }, "sellerName": "Demo QA Prashant Edit", "channelType": "API", "channelId": "6324262c9a3f345e2a985874",

"gstProductLevel": false, "selectedCarriers": [

--- Page 23 ---

{ "_id": "676e50e19d7e8b568cc191b7", "name": "Smile",

"image": "", "isActive": true,

"shortName": "SMILE",

"createdDate": "2024-03-13T05:37:13.203Z",

"updatedDate": "2024-03-13T05:37:13.203Z" } ], "carrierName": "SMILE",

"carrierId": "676e50e19d7e8b568cc191b7",

"cAwbNumber": "bhav190000009539",

"cargoDeliveryAmount": 767, "cargoInvoiceUrl": "", "cargoInvoiceNumber": "ASD/23/ASD/123123", "isParentOrder": true,

"smileAwbNumber": "bhav190000009539",

"awbNumber": "bhav190000009539",

"pickupAddress": { "_id": "6773f2ab2c8759abdddf20dc", "id": null,

"name": "demo aakurdi user",

"phone": "9823456784", "address1": "asdsadsdasd sad as title updated again", "address2": "",

"zip": "400001", "state": "Maharashtra",

"city": "Mumbai", "latitude": 0,

"longitude": 0,

"status": true,

"isShippingAddress": null, "isPickupAddress": null, "title": "demo aakurdia updated", "type": "Warehourse", "vendorCode": "bhav19",

"warehouseId": null,

"createdDate": "2024-12-31T13:33:31.273Z",

"updatedDate": "2025-08-19T08:20:14.249Z", "createdById": "6773f2ab2c8759abdddf20db", "updatedById": "68a433be6d529ef173a37f9c",

--- Page 24 ---

"createdBy": "Demo QA Prashant", "updatedBy": "Demo QA Prashant Edit", "innoCity": "Ahmedabad", "innoState": "GUJARAT",

"owner": "INNOFULFIL",

"gstNumber": "27AWBPR5387C1ZC", "serviceType": "CARGO" }, "billingAddress": { "_id": "6773f2ab2c8759abdddf20dc", "id": null,

"name": "demo aakurdi user",

"phone": "9823456784", "address1": "asdsadsdasd sad as title updated again", "address2": "",

"zip": "400001", "state": "Maharashtra",

"city": "Mumbai", "latitude": 0,

"longitude": 0,

"status": true,

"isShippingAddress": null, "isPickupAddress": null, "title": "demo aakurdia updated", "type": "Warehourse", "vendorCode": "bhav19",

"warehouseId": null,

"createdDate": "2024-12-31T13:33:31.273Z",

"updatedDate": "2025-08-19T08:20:14.249Z", "createdById": "6773f2ab2c8759abdddf20db", "updatedById": "68a433be6d529ef173a37f9c", "createdBy": "Demo QA Prashant", "updatedBy": "Demo QA Prashant Edit", "innoCity": "Ahmedabad", "innoState": "GUJARAT",

"owner": "INNOFULFIL",

"gstNumber": "27AWBPR5387C1ZC", "serviceType": "CARGO" }, "returnAddress": { "_id": "6773f2ab2c8759abdddf20dc", "id": null,

--- Page 25 ---

"name": "demo aakurdi user",

"phone": "9823456784", "address1": "asdsadsdasd sad as title updated again", "address2": "",

"zip": "400001", "state": "Maharashtra",

"city": "Mumbai", "latitude": 0,

"longitude": 0,

"status": true,

"isShippingAddress": null, "isPickupAddress": null, "title": "demo aakurdia updated", "type": "Warehourse", "vendorCode": "bhav19",

"warehouseId": null,

"createdDate": "2024-12-31T13:33:31.273Z",

"updatedDate": "2025-08-19T08:20:14.249Z", "createdById": "6773f2ab2c8759abdddf20db", "updatedById": "68a433be6d529ef173a37f9c", "createdBy": "Demo QA Prashant", "updatedBy": "Demo QA Prashant Edit", "innoCity": "Ahmedabad", "innoState": "GUJARAT",

"owner": "INNOFULFIL",

"gstNumber": "27AWBPR5387C1ZC", "serviceType": "CARGO" }, "deliveryMode": "SURFACE", "appointmentDate": "", "isDocket": true,

"chargebleWeight": 20, "igst": 9, "cgst": 9, "sgst": 0, "gst": 117, "gstPercentage": 18, "volumetricWeight": 0.29333333333333333,

"tat": 7,

"chargesData": { "risk_type_charge": 200, "fuelChargeAmount": 70,

--- Page 26 ---

"docketCharge": 100, "appointmentDeliveryCharge": 750, "courier_charge": 280 }, "serviceType": "Standard", "channel": { "type": "COMPANY", "storeCode": "bhav19",

"storeName": "Demo QA Prashant Pvt Ltd" }, "orderedAt": "2025-08-25T08:03:07.540Z",

"subTotal": 5000,

"sellerInfo": { "id": "676d2b6491375a44b29b15c3",

"name": "Demo QA Prashant Edit",

"mobile": "9809808989",

"companyName": "Demo QA Prashant Pvt Ltd" }, "shipperOrderId": "bhav19-bhav190000009539", "createdDate": "2025-08-25T13:33:07.950Z",

"updatedDate": "2025-08-25T13:33:07.950Z", "createdById": "676d2b6491375a44b29b15c1", "updatedById": "676d2b6491375a44b29b15c1", "createdBy": "Demo QA Prashant Edit", "updatedBy": "Demo QA Prashant Edit", "updatedAt": "2025-08-25T13:33:09.002Z" } ], "page": 1, "limit": 1,

"total": 10660,

"searchHints": [] } }

Error Response (400/401/500)
{ "status": false,

"message": "Validation error or Unauthorized access" }

--- Page 27 ---

Status Codes
Code Meaning

200 Order list fetched successfully

400 Invalid input/validation error

401 Unauthorized (missing/invalid JWT)

500 Internal server error

--- Page 28 ---

8. Customer check Wallet Balance API
Purpose
This API is used to fetch the available wallet balance of a specific customer (vendor). Very important to know your wallet balance before placing order or check from rate calculator the order charges and verify before placing order.

The Balance is always shown in INR. There are Two payment Types Prepaid and Postpaid.

API Method

GET

Endpoint
https://qaapis.delcaper.com/wallet-api/wallet/balance

Query Parameters
Name Required Type Description

productId ✅ Yes String The product identifier (e.g., SMEINFUL)

vendorCode ✅ Yes String Vendor code of the customer

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Success Response (200 OK)
{

--- Page 29 ---

"status": 200,

"message": "Customer wallet details", "data": { "balance": 7922792,

"points": 79227.92, "limitBalance": { "creditlimit": 14220000,

"creditbalance": 106454,

"customerId": "SMEINFUL000000000571333",

"paymentType": "prepaid",

"status": "enabled"

}, "walletBalance": { "balance": 7816338,

"points": 78163.38 }, "customerPaymentType": "POSTPAID" } }

Error Response (400/401/500)
{

"status": 400,

"message": "Seller not found" }

Status Codes
Code Meaning

200 Wallet balance fetched successfully

400 Bad Request (e.g., missing parameters)

401 Unauthorized (invalid/missing token)

500 Internal server error

--- Page 30 ---

9. Shipment Booking API
Purpose
The Shipment Booking API is used to create and push a shipment order to the fulfillment system, including detailed shipment, address, and invoice information.

Important :
Try to get all charges from rate-calculator response with non-zero Please use AWB number in series given to you everytime you run the API. In simpler terms use the next number which you used the last time. For example: bhav190000000542 You have to always check your wallet balance. To find out the wallet balance please run the wallet balance API, you can find it later in the document. To Get AWB number use the following API:​EndPoint: https://qaapis.delcaper.com/cargo-api/pre-series

Requested Params:
Vendorcode: bhav19

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/orders/create-order

Headers
Name Required Type Description

--- Page 31 ---

Content-Type ✅ Yes String Must be application/json

Request Body Format
{

"type": "CARGO",

"orderId": "449509082",

"orderNumber": "449509082",

"awbNumber": "bhav190000000042",

"orderCreatedAt": "2025-10-10T15:18:56.839",

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

"returnableOrder": true,

--- Page 32 ---

"shippingAddress": {

"name": "Test",

"phone": "5413515646",

"address1": "anjgakgjna",

"address2": "ngajnglanga/",

"city": "Pune",

"state": "Maharashtra",

"zip": "411014",

"warehouseId": "",

"isPickupAddress": true,

"isShippingAddress": false,

"type": "Factory",

"title": "pune city3",

"vendorCode": "bhav19",

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

"isPickupAddress": true,

"isShippingAddress": false,

"type": "Factory",

--- Page 33 ---

"title": "Pune city2",

"vendorCode": "bhav19",

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

"isPickupAddress": true,

"isShippingAddress": false,

"type": "Factory",

"title": "Pune city2",

"vendorCode": "bhav19",

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

--- Page 34 ---

"warehouseId": "",

"isPickupAddress": true,

"isShippingAddress": false,

"type": "Factory",

"title": "Pune city2",

"vendorCode": "bhav19",

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

"subCarrierName": null,

"subCarrierId": null,

"cargoDeliveryAmount": 578.2,

"cargoInvoiceNumber": "AAAAAAAAA",

"cargoInvoiceUrl": "https://delcaper-qa.s3.ap-south-1.amazonaws.com/blob%3Ahttps%3A//qabooking.cargodham.com/4234 c1ac-303f-4404-9006-177f597b1b60/onboarding_order_flow-1760089729445.png",

"invoiceDate": null,

"cargoSellerPercentageAmount": null,

"isParentOrder": true,

"cargoBoxDetails": null,

"carrierName": "SMILE",

"carrierId": "391af7de-0b75-46cc-b98c-9a4d05d405c1",

--- Page 35 ---

"warehouseId": null,

"ewaybillUrl": null,

"ewaybillNumber": null,

"ewayExpiryDate": null,

"appointmentDate": "",

"chargebleWeight": 12,

"gst": 88.2,

"igst": 9,

"sgst": 0,

"cgst": 9,

"volumetricWeight": 0.046296296296296294,

"ewayBills": null,

"ewayUrls": null,

"cargoEwayExpiryDates": null,

"cargoInvoiceNumbers": null,

"cargoInvoiceUrls": null,

"tat": 8,

"chargesData": {

"fuelChargeAmount": "6.00",

"docketCharge": "234.00",

"platformFee": "10.00",

"freight_charge": 480,

"courier_charge": 36

},

"orderCreatedFrom": "Web",

"companyName": "smile pvt. ltd.",

"metadata": [

{

--- Page 36 ---

"key": "companyName",

"value": "smile pvt. ltd."

}

],

"subType": "PTL",

"vendorCode": "bhav19",

"transporterId": "88AABCM9407D1ZS"

}

Key Field Descriptions
Field Type Required Description

type String ✅ Yes Shipment type (CARGO)

orderId/orderNumber String ✅ Yes Unique order identifiers

currency String ✅ Yes Currency code (INR)

amount Number ✅ Yes Total amount including delivery

lineItems Array ✅ Yes Product/item list with dimensions and price

paymentType String ✅ Yes Payment mode (ONLINE or COD)

shippingAddress Object ✅ Yes Address details of recipient

billingAddress Object ✅ Yes Address for billing

pickupAddress Object ✅ Yes Warehouse/vendor pickup address

returnAddress Object ✅ Yes Address for return (if applicable)

deliveryMode String ✅ Yes Type of transport (SURFACE/AIR)

gstPercentage Number ✅ Yes Applicable GST percentage

--- Page 37 ---

carrierName String ✅ Yes Shipping carrier name

Vendorcode String ✅ Yes Unique identification number of the vendor

volumetricWeight Number ✅ Yes Calculated volume-based weight

cargoInvoiceUrl String Optional URL to cargo invoice PDF

Success Response (200 OK)
{

"status": 200,

"message": "Order Created Successfully", "data": {

"status": "success",

"statusCode": 201,

"message": "order created successfully", "data": { "id": 12383,

"orderId": "2510100953185Q4BBW",

"referenceId": "449509082",

"parcelCategory": "CARGO", "orderDate": "2025-10-10T09:53:17.409Z",

"expectedDeliveryDate": "0001-01-01T00:00:00Z", "eWaybills": [], "returnable": true,

"deliveryMode": "SURFACE", "deliveryPromise": "Standard", "orderStatus": "CONFIRMED",

"carrierName": "SMILE",

"carrierId": "391af7de-0b75-46cc-b98c-9a4d05d405c1",

"vendorCode": "bhav19",

"metadata": { "createdBy": "71739d8a-3051-7043-a2d1-b87908e183eb",

"source": "Web"

}, "createdAt": "2025-10-10T09:53:18.197300525Z",

"updatedAt": "2025-10-10T09:53:18.197300525Z", "addresses": [ { "id": 49144,

"type": "DELIVERY", "zip": "411014",

--- Page 38 ---

"name": "Test",

"phone": "5413515646", "street": "anjgakgjna", "landmark": "ngajnglanga/", "city": "Pune", "state": "Maharashtra",

"country": "India" }, { "id": 49145,

"type": "BILLING", "zip": "411014", "name": "Bhavesh",

"phone": "6857496496", "street": "Fdghfds afa sfsadf staff", "landmark": "Asdf asdfasd asdfsdaf asdf",

"city": "Pune", "state": "Maharashtra",

"country": "India" }, { "id": 49146,

"type": "PICKUP", "zip": "411014", "name": "Bhavesh",

"phone": "6857496496", "street": "Fdghfds afa sfsadf staff", "landmark": "Asdf asdfasd asdfsdaf asdf",

"city": "Pune", "state": "Maharashtra",

"country": "India", "addressName": "Pune city2" }, { "id": 49147,

"type": "RETURN", "zip": "411014", "name": "Bhavesh",

"phone": "6857496496", "street": "Fdghfds afa sfsadf staff", "landmark": "Asdf asdfasd asdfsdaf asdf",

"city": "Pune",

--- Page 39 ---

"state": "Maharashtra",

"country": "India" } ], "documents": [ { "id": 2030,

"type": "invoice", "number": "AAAAAAAAA",

"url":

"https://delcaper-qa.s3.ap-south-1.amazonaws.com/blob%3Ahttps%3A//qabooking.cargodham.com/4234 c1ac-303f-4404-9006-177f597b1b60/onboarding_order_flow-1760089729445.png" } ], "shipments": [ { "id": 93849,

"isParent": true,

"awbNumber": "bhav190000000042",

"dimensions": { "height": 5, "length": 5,

"width": 5

}, "volumetricWeight": 10, "packaging": {

"id": 0

}, "items": [ { "id": 108682,

"name": "ELECT",

"quantity": 1, "weight": 10, "taxes": null,

"discounts": null

} ] } ], "vehicles": null,

"slots": null,

--- Page 40 ---

"payment": { "id": 12162,

"finalAmount": 579,

"type": "ONLINE",

"status": "PENDING",

"currency": "INR", "breakdown": { "id": 2906,

"subTotal": 100,

"taxes": null,

"discounts": null,

"otherCharges": [ { "id": 8380,

"description": "fuelChargeAmount", "chargedAmount": 6 }, { "id": 8381,

"description": "docketCharge", "chargedAmount": 234 }, { "id": 8382,

"description": "platformFee", "chargedAmount": 10 }, { "id": 8383,

"description": "freight_charge", "chargedAmount": 480 }, { "id": 8384,

"description": "courier_charge", "chargedAmount": 36 } ] }, "splitPayments": null }, "taxes": [

--- Page 41 ---

{ "id": 6026,

"description": "GST", "value": 18,

"chargedAmount": 88.2 }, { "id": 6027,

"description": "CGST", "chargedAmount": 9 }, { "id": 6028,

"description": "IGST", "chargedAmount": 9 } ], "discounts": null,

"orderSource": {

"id": 0

} },

"databaseId": "68e8d78d09b43437338403ea"

} }

Status Codes
Code Meaning

200 Shipment order created successfully

400 Invalid input/validation error

401 Unauthorized (token missing/invalid)

500 Internal server error

--- Page 42 ---

10. Wallet Order Balance Update API
Purpose
This API is used to create a wallet transaction corresponding to a product order, adjusting the wallet balance based on the order value and associated charges.

API Method
POST

Endpoint
https://qaapis.delcaper.com/wallet-api/wallet/balance

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Request Body Format
{ "productId": "string", "vendorCode": "string",

"amount": 0,

"productOrderId": "string", "txnType": "string", "redirectURL": "string", "description": "string", "logo": "string", "awbNumber": "string", "paymentType": "string", "freightCharges": 0, "chargebleWeight": 0 }

--- Page 43 ---

Request Body Field Description
Field Type Required Description

productId String ✅ Yes Product identifier, e.g., SMEINFUL

vendorCode String ✅ Yes Code identifying the vendor

amount Number ✅ Yes Total amount to be charged in INR

productOrderId String ✅ Yes Unique ID of the product order

awbNumber String ✅ Yes Airway bill number for tracking

paymentType String ✅ Yes Type or reason for the payment

txnType String ✅ Yes Transaction type: debit or credit

chargebleWeight Number ✅ Yes Chargeable weight of the shipment

freightCharges Number ✅ Yes Freight cost associated with the order

Success Response (200 OK)
{

"status": 200,

"message": "Order inserted successfully", "data": {

"walletOrderId": "DLWA000000003081787"

} }

Status Codes
Code Meaning

200 Wallet updated successfully

400 Validation error

401 Unauthorized (invalid/missing token)

--- Page 44 ---

500 Internal server error

11. Shipment Tracking API
Purpose
This API is used to retrieve tracking information for a specific shipment using its tracking ID.

Ready for Dispatch: Your shipment is packed and ready to be sent out.

Confirmed: The order has been confirmed and is being prepared for pickup.

In-Transit: The shipment is on its way to the delivery location.

Shipped: The package has left the warehouse or origin location.

Out for Delivery: The delivery person is on the way to deliver your shipment.

Delivered: Your shipment has been successfully delivered to the destination. Once delivered you get POD( Proof of delivery) URL.

There can be more additional statuses also,

--- Page 45 ---

API Method

GET

Endpoint
https://qaapis2.delcaper.com/cargo-api/webhooks?type=TRACKING&awbNumber=bhav190000009539

Path Parameters
Name Required Type Description

awbNumber ✅ Yes String The Air Waybill number of the shipment

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Success Response (200 OK)
{

"status": 200,

"data": { "parentOrderWebhook": [ { "trackingId": "bhav190000009539", "status": "ORDER_CONFIRMED", "deliveryPartnerName": "innofulfill", "event": "order placed in system", "cAwbNumber": "bhav190000009539",

"location": "Mumbai",

"statusTimestamp": "", "cpDetails": {}, "daInfo": {}, "pod_links": [],

"createdAt": "2025-08-25T13:33:08.013Z"

}, { "trackingId": "bhav190000009539",

--- Page 46 ---

"status": "ORDER_CONFIRMED", "deliveryPartnerName": "innofulfill", "event": "order placed in system", "cAwbNumber": "bhav190000009539",

"smileAwbNumber": "bhav190000009539",

"location": "Mumbai",

"statusTimestamp": "", "cpDetails": {}, "daInfo": {}, "pod_links": [],

"createdAt": "2025-08-25T13:33:07.959Z"

} ], "childOrderWebhook": [] } }

Status Codes
Code Meaning

200 Tracking details fetched successfully

400 Bad request or missing parameters

401 Unauthorized (invalid/missing token)

404 Shipment not found

500 Internal server error

12. Cancel Booking API
Purpose
This API is used to cancel a booking/order by providing the order ID and a reason for cancellation.

There are different reasons depending on the situation to cancel the order. For example: Incorrect Product Information, Wrong shipment address, Other reasons. In the following request body we have used Other

as the reason. ​

Providing a reason is mandatory to cancel the order.

Please use a valid AWB number, To Get AWB number use the following “GET” API:​EndPoint: https://qaapis.delcaper.com/cargo-api/pre-series

--- Page 47 ---

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/orders/cancel/bulk

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Requested Body (JSON) ​ {
"orders": [

{

"awbNumber": "bhav190000000042",

"reason": "Other"

}

]

}

Query Parameters
Field Type Required Description

​
Awb

number

​
String ✅ Yes The unique AWB number of the shipment.

​
Success Response (200 OK)
{

"status": 200,

"message": "Orders cancelled successfully via Prayog API",

​
--- Page 48 ---

"data": { "cancelledAwbNumbers": [

"bhav190000000042"

], "cancelledOrderIds": [

"2510100953185Q4BBW"

], "totalCancelled": 1,

"externalResponse": {

"status": "success",

"statusCode": 200,

"message": "Bulk cancel operation started successfully", "data": "cancel operation started successfully" }, "localDatabaseUpdated": 1, "refunds": [ { "awbNumber": "bhav190000000042",

"refundStatus": "success",

"refundAmount": 578.2,

"refundResponse": {

"status": 200,

"message": "Order inserted successfully", "data": {

"walletOrderId": "DLWA000000003114970"

} } } ], "apiUsed": "prayog" } }

Error Response (400/401/500)
--- Page 49 ---

{

"status": 401,

"message": "Invalid order ID or unauthorized access" }​Error Response 404​{

"status": 404,

"data": null,

"message": "order not found in our system with orderId 868778103" }

Status Codes
Code Meaning

200 Order canceled successfully

400 Bad request or missing parameters

401 Unauthorized (invalid/missing token)

404 Order not found

500 Internal server error

- 13. Invoice/ Docket/ E Way Bill Upload API
Purpose
This API is used to upload invoice, docket files or e-way bills (PDF, image formats) to the server.

API Method
POST

--- Page 50 ---

Endpoint
https://qaapis.delcaper.com/common/cargo-api/orders/{awbNumber}/update

Headers
Name Required Type Description

Form Data Parameters
Name Required Type Description

path ✅ Yes String Temporary blob path or identifier for client-side file reference

fileType ✅ Yes String Allowed MIME types (e.g., image/png, application/pdf)

files ✅ Yes File The file to be uploaded (e.g., image or PDF file)

Success Response (200 OK)
{

"status": 200,

"message": "Files Uploaded Successfully", "data": [ {

"url":

"https://delcaper-qa.s3.ap-south-1.amazonaws.com/blob%3Ahttps%3A//qabooking.cargodham.com/82e0 782b-1e87-4245-851c-b2f4de3b9f2a/ACFrOgB2duUI4SVEOlOKlhfOV0JOaqiDj6R5jyfnwOfUcN1jFzc hDp5sPf8JgwwaSCYz5_4FG_bH3ueLLSz9vGKvTzf0xzP8NEd5VfGI1bIfo59OFNt7Zc1sGSLY8TWDrz Ku_y3z_xa2jUxAYgqc-2-1746018111316.pdf", "generatedFileName": "ACFrOgB2duUI4SVEOlOKlhfOV0JOaqiDj6R5jyfnwOfUcN1jFzchDp5sPf8JgwwaSCYz5_4FG_bH3u eLLSz9vGKvTzf0xzP8NEd5VfGI1bIfo59OFNt7Zc1sGSLY8TWDrzKu_y3z_xa2jUxAYgqc-2-17460181 11316.pdf", "originalFileName": "ACFrOgB2duUI4SVEOlOKlhfOV0JOaqiDj6R5jyfnwOfUcN1jFzchDp5sPf8JgwwaSCYz5_4FG_bH3u eLLSz9vGKvTzf0xzP8NEd5VfGI1bIfo59OFNt7Zc1sGSLY8TWDrzKu_y3z_xa2jUxAYgqc-2.pdf" } ] }

--- Page 51 ---

Error Response (400/401/500)
{

"status": 400,

"message": "File upload failed" }

Status Codes
Code Meaning

200 File uploaded successfully

400 Bad request or missing parameters

401 Unauthorized (invalid token)

500 Internal server error

14. Cargo Manifest Order API
Purpose
This API is used to create a cargo manifest for a seller's order by specifying the orderId and selected

carrierName.

You will receive order ID from Order details API response of shipment booking. Usually in the 10th line of the response body..

Carrier Name is the name of the partner you have chosen throughout your journey. Please ask your POC to provide Carrier Name. In this order the partner was Shree Maruti and carrier name is

SMILE.

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/webhooks/order-manifest-webhook

--- Page 52 ---

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Request Body
{ "data": { "orderId": "6811e3678a89a8751ae17ccb",

"carrierName": "SMILE"

} }

Request Body Parameters
Field Type Required Description

orderId String ✅ Yes Unique ID of the order

carrierName String ✅ Yes Name of the carrier (e.g., SMILE)

Success Response (200 OK)
{

"status": 201,

"data": { "message": "Manifest webhook received successfully" } }

Error Response (400/401/500)
--- Page 53 ---

{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
Code Meaning

200 Cargo manifest created successfully

400 Bad request or missing fields

401 Unauthorized (invalid/missing token)

500 Internal server error

15. Print Label API
Purpose
This API is used to generate and print the label for a cargo order based on the given Order ID and

Carrier Name.

This API will only run if the order is manifested already . Please refer to the Manifest order API, Just

above.

API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/print-label/v2

Headers
--- Page 54 ---

Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Request Body
Parameter Required Type Description

orderId ✅ Yes String Unique ID of the order

carrierName ✅ Yes String Name of the carrier

Example Request Body
{ "awbNumber": "bhav190000000094",

"carrierName": "SMILE"

}

Success Response (200 OK)
{

"status": 201,

"data": { "shippingLabelUrl": "https://delcaper-qa.s3.ap-south-1.amazonaws.com/bhav19/shippinglabel//shipping-label-1759729008853 -1759729008863.pdf" } }

Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

--- Page 55 ---

Status Codes
Code Meaning

200 Label generated successfully

400 Bad request or missing parameters

401 Unauthorized (invalid/missing token)

404 Order not found

500 Internal server error

16. Transporter ID API
Purpose
This API is used to fetch transporter ID details using a specific order number.

API Method
PATCH

Endpoint
https://qaapis.delcaper.com/cargo-api/onboarding/{vendorCode}

Query Parameters
Name Required Type Description

vendorCode ✅ Yes String Unique Vendor code number. (Eg: DEMO)

Headers
Name Required Type Description

--- Page 56 ---

Content-Type ✅ Yes String Should be set to application/json

Requested Endpoint​
{

"onboardingData": {

"organizationName": "string",

"ownerName": "string",

"pincode": "string",

"source": "string",

"subTypes": [

"PTL",

"FTL"

],

"status": "string",

"logoUrl": "https://example.com/logo.png",

"metadata": [

{

"key": "string",

"value": "string"

}

]

},

"partnerData": {},

--- Page 57 ---

"transporterIds": {

"air": "string",

"surface": "string",

"rail": "string"

},

"serviceAreas": [

{

"city": "Mumbai",

"state": "Maharashtra",

"pincode": "400001",

"isActive": true

}

]

}

Success Response (200 OK)
{ "orderCount": 1,

"orderData": [ { "_id": "6812055f8a89a8751ae199b1", "vendorCode": "bhav19",

"originalOrderId": "868778103", "type": "CARGO", "originalOrderNumber": "868778103", "orderCreatedAt": "2025-04-30T11:11:27.647Z",

"orderUpdatedAt": "2025-05-02T17:08:47.050Z", "currency": "INR", "paymentType": "ONLINE", "paymentStatus": "PAID",

"amount": 512.1,

"weight": 10, "length": 10,

--- Page 58 ---

"width": 10,

"height": 10, "orderStatus": "READY_FOR_DISPATCH", "shippingType": "FORWARD", "remarks": "No Remarks",

"deliveryVerification": false, "orderCreatedFrom": "API",

"shippingAddress": { "name": "pwerf", "phone": "9234567899", "address1": "asdfghjkhhhh", "city": "Pune", "state": "Maharashtra",

"zip": "411014", "warehouseId": "",

"isPickupAddress": true, "isShippingAddress": false, "type": "Factory", "title": "snehal test 4",

"vendorCode": "bhav19",

"gstNumber": "27AWBPR5387C1ZC", "address2": "sdfghj", "innoCity": "Pune",

"innoState": "MAHARASHTRA"

}, "sellerName": "Demo QA Prashant Edit", "channelType": "API", "channelId": "6324262c9a3f345e2a985874",

"gstProductLevel": false, "selectedCarriers": [ { "_id": "676e50e19d7e8b568cc191b7", "name": "Smile",

"image": "", "isActive": true,

"shortName": "SMILE",

"createdDate": "2024-03-13T05:37:13.203Z",

"updatedDate": "2024-03-13T05:37:13.203Z" } ], "carrierName": "SMILE",

"carrierId": "676e50e19d7e8b568cc191b7",

--- Page 59 ---

"cAwbNumber": "24800228026",

"cargoDeliveryAmount": 512.12, "cargoInvoiceUrl": "https://delcaper-qa.s3.ap-south-1.amazonaws.com/blob%3Ahttps%3A//qabooking.cargodham.com/c476 e4d4-7b5c-4c0d-817e-a238c3190486/ACFrOgB2duUI4SVEOlOKlhfOV0JOaqiDj6R5jyfnwOfUcN1jFzc hDp5sPf8JgwwaSCYz5_4FG_bH3ueLLSz9vGKvTzf0xzP8NEd5VfGI1bIfo59OFNt7Zc1sGSLY8TWDrz Ku_y3z_xa2jUxAYgqc-2-1746011452289.pdf", "cargoInvoiceNumber": "123456789", "isParentOrder": true,

"smileAwbNumber": "24800228026",

"awbNumber": "21055184667839",

"pickupAddress": { "name": "prerak", "phone": "9234567898", "address1": "wertyhertyu", "city": "SURAT",

"state": "GUJARAT",

"zip": "394110", "warehouseId": "",

"isPickupAddress": true, "isShippingAddress": false, "type": "Factory", "title": "snehal test 3",

"vendorCode": "bhav19",

"gstNumber": "27AWBPR5387C1ZC", "address2": "asdfghj" }, "billingAddress": { "name": "prerak", "phone": "9234567898", "address1": "wertyhertyu", "city": "SURAT",

"state": "GUJARAT",

"zip": "394110", "warehouseId": "",

"isPickupAddress": true, "isShippingAddress": false, "type": "Factory", "title": "snehal test 3",

"vendorCode": "bhav19",

"gstNumber": "27AWBPR5387C1ZC", "address2": "asdfghj"

--- Page 60 ---

}, "returnAddress": { "name": "prerak", "phone": "9234567898", "address1": "wertyhertyu", "city": "SURAT",

"state": "GUJARAT",

"zip": "394110", "warehouseId": "",

"isPickupAddress": true, "isShippingAddress": false, "type": "Factory", "title": "snehal test 3",

"vendorCode": "bhav19",

"gstNumber": "27AWBPR5387C1ZC", "address2": "asdfghj" }, "deliveryMode": "SURFACE", "appointmentDate": "", "isDocket": true,

"chargebleWeight": 20, "igst": 9, "cgst": 9, "sgst": 0, "gst": 78.12, "gstPercentage": 18, "volumetricWeight": 0.2222222222222222, "channel": { "type": "COMPANY", "storeCode": "bhav19",

"storeName": "Demo QA Prashant Pvt Ltd" }, "timeLine": [ {

"status": "NEW",

"displayLabel": "Ordered", "isAchieved": true,

"displayLabelShowOrNot": true, "historyLabelShowOrNot": true,

"date": "2025-04-30T11:11:27.650Z"

}, {

--- Page 61 ---

"status": "READY_FOR_DISPATCH", "displayLabel": "Manifest", "isAchieved": false,

"displayLabelShowOrNot": true, "historyLabelShowOrNot": true,

"date": null

}, { "status": "IN_TRANSIT", "displayLabel": "In Transit", "isAchieved": false,

"displayLabelShowOrNot": true, "historyLabelShowOrNot": true,

"date": null

}, { "status": "OUT_FOR_DELIVERY", "displayLabel": "Out For Delivery", "isAchieved": false,

"displayLabelShowOrNot": true, "historyLabelShowOrNot": true,

"date": null

}, {

"status": "UNDELIVERED",

"displayLabel": "Attempt 1", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false, "attemptReason": "", "date": null,

"attempts": 0 }, {

"status": "UNDELIVERED",

"displayLabel": "Attempt 2", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false, "attemptReason": "", "date": null,

"attempts": 0

--- Page 62 ---

}, {

"status": "UNDELIVERED",

"displayLabel": "Attempt 3", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false, "attemptReason": "", "date": null,

"attempts": 0 }, {

"status": "UNDELIVERED",

"displayLabel": "Undelivered", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false,

"date": null

}, {

"status": "RTO",

"displayLabel": "RTO", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false,

"date": null

}, { "status": "RTO_IN_TRANSIT", "displayLabel": "RTO In Transit", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false,

"date": null

}, { "status": "RTO_OUT_FOR_DELIVERY", "displayLabel": "RTO Out For Delivery", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false,

"date": null

--- Page 63 ---

}, { "status": "RTO_DELIVERED", "displayLabel": "RTO Delivered", "isAchieved": false,

"displayLabelShowOrNot": false, "historyLabelShowOrNot": false,

"date": null

}, {

"status": "DELIVERED",

"displayLabel": "Delivered", "isAchieved": false,

"displayLabelShowOrNot": true, "historyLabelShowOrNot": true,

"date": null

} ], "orderedAt": "2025-04-30T11:11:27.556Z",

"subTotal": 10000,

"sellerInfo": { "id": "676d2b6491375a44b29b15c3",

"name": "Demo QA Prashant Edit",

"mobile": "9809808989",

"companyName": "Demo QA Prashant Pvt Ltd" }, "shipperOrderId": "bhav19-21055184667839", "lineItems": [ { "name": "testing product", "weight": 10, "price": 0, "quantity": 1, "unitPrice": 0,

"type": "Electronics", "height": 10, "width": 10,

"length": 10,

"childAwbNumber": "21055184667839"

} ], "createdDate": "2025-04-30T11:11:27.824Z",

--- Page 64 ---

"updatedDate": "2025-04-30T11:11:27.824Z", "createdById": "676d2b6491375a44b29b15c1", "updatedById": "676d2b6491375a44b29b15c1", "createdBy": "Demo QA Prashant Edit", "updatedBy": "Demo QA Prashant Edit", "chargesData": { "risk_type_charge": "60.00", "fuelChargeAmount": "33.00", "docketCharge": "110.00", "platformFee": "11.00", "freight_charge": 363 }, "updatedAt": "2025-07-01T09:15:37.399Z", "invoiceDate": "2025-04-30 16:41:27",

"invoiceNo": "ODDGJ/2526/0289",

"invoiceUrl": "https://devuat.prospay.tech/ODDGJ/2526/0289.pdf", "isManifested": true,

"internalStatus": "READY_FOR_DISPATCH", "reason": null,

"shippingLabelUrl": "https://delcaper-qa.s3.ap-south-1.amazonaws.com/public/fulfillment/seller/bhav19/shippinglabel/shippin g-label-1746547683999.pdf" } ] }

Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
Code Meaning

--- Page 65 ---

200 Request successful

400 Bad request or missing parameters

401 Unauthorized (invalid token)

500 Internal server error

- 17. E way Bill API
Purpose
This API is used to fetch E-way bill details using a specific E-way bill number.

This API fetches E-way Bill details for a shipment, including order status, tracking links, and partner information. It provides metadata like delivery type, customer notes, and document URLs. On success, it returns the E-way Bill number, transporter ID, vehicle number, and validity date.The response helps track shipment progress and verify E-way Bill compliance. Use this to integrate logistics and compliance data into your system.

API Method
PATCH

Endpoint
https://qaapis2.delcaper.com/cargo-api/orders/{awbNumber}/update

Path Parameter
Name Required Type Description

--- Page 66 ---

awbNumber ✅ Yes String The E-way bill number to fetch

Headers
Name Required Type Description

Content-Type ✅ Yes String Should be set to application/json

Requested Body (JSON)

{ "orderStatus": "string", "docketUrl": "string", "labelUrl": "string", "podUrl": "string", "expectedDeliveryDate": "string", "partnerDetails": { "awbNumber": "string", "urls": [ { "key": "tracking_url", "value": "https://example.com/track/123" }, { "key": "label_url", "value": "https://example.com/label/123" } ], "metadata": [ { "key": "delivery_type", "value": "express" }, { "key": "special_instructions",

"value": "handle with care"

} ] }, "metadata": [ { "key": "priority",

--- Page 67 ---

"value": "high" }, { "key": "customer_notes", "value": "fragile item" } ], "documents": [ "string" ], "uploadDocuments": {}, "chargesData": {}, "_append": true }

Success Response (200 OK)
{

"status": true,

"message": "E-way bill fetched successfully", "data": { "ewayBillNumber": "251943247012", "transporterId": "TRANS123", "vehicleNumber": "MH12AB1234",

"validUpto": "2025-06-15T23:59:59Z",

...

} }

Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
--- Page 68 ---

Code Meaning

200 Request successful

400 Bad request or missing

parameters

401 Unauthorized (invalid token)

404 E-way bill not found

500 Internal server error

18. Support Ticket Creation API
Purpose
This API is used to create a new support ticket in the system.

API Method
POST

--- Page 69 ---

Endpoint
https://qaapis2.delcaper.com/support-tickets/ticket

Headers
Name Required Type Description

Content-Type ✅ Yes String Should be set to application/json

Request Body (JSON)
Field Required Type Description

title ✅ Yes String Subject or heading of the ticket

message ✅ Yes String Detailed message describing issue

channelType ✅ Yes String Source or channel (e.g., email, app)

userType ✅ Yes String Type of user (e.g., ADMIN)

userId ✅ Yes String Unique identifier for the user

awbNumber ❌ No String Air Waybill number if applicable

userEmail ❌ No String Email address of the user

customerName ❌ No String Name of the customer

orderStatus ❌ No String Status of the order (if relevant)

Error Response (400/401/500)
{

"status": 400,

"message": "Bad Request Exception", "errors": [

--- Page 70 ---

"userType must be one of the following values: ADMIN, CUSTOMER" ] }

Status Codes
Code Meaning

201 Ticket created successfully

400 Bad request / Missing parameters

401 Unauthorized / Invalid credentials

500 Internal server error

19. Get Support Tickets API
Purpose
This API is used to fetch support tickets associated with a specific user ID and ChannelType. If the userId and channelType is not provided, the API will return all support tickets .

API Method
GET

--- Page 71 ---

Endpoint
https://qaapis2.delcaper.com/support-tickets/ticket

Query Parameters
Name Required Type Description

userId ❌ No String Unique ID of the user (e.g., bhav19). Optional; if omitted, returns

all tickets.

channelType ❌ No String Channel through which the ticket was raised (e.g., EMAIL, CHAT). Optional.

Headers
Name Required Type Description

Content-Type ✅ Yes String Should be set to application/json

Success Response (200 OK)
{

"status": 200,

"message": "Success",

"data": {

"count": 8,

"ticket": [ {

"_id": "67e5525474d5bba4d87fc409",

"title": "KYC",

"message": "I am unable to upload my KYC documents.",

--- Page 72 ---

"status": "OPEN",

"ticketNo": "809532",

"channelType": "CARGO",

"userType": "CUSTOMER",

"awbNumber": null,

"userId": "bhav19",

"userEmail": null,

"emailIds": [],

"createdAt": "2025-03-27T13:27:48.942Z",

"updatedAt": "2025-03-27T13:27:48.942Z",

"__v": 0 } ….

]

} }

Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
Code Meaning

--- Page 73 ---

200 Request successful

400 Bad request

401 Unauthorized

404 User not found

500 Internal server error

20. Update Support Ticket Status API
Purpose
This API is used to update the status of an existing support ticket.

API Method
PUT

Endpoint
--- Page 74 ---

https://qaapis2.delcaper.com/support-tickets/ticket/{ticketId}

Path Parameters
Name Required Type Description

ticketId ✅ Yes String Unique identifier of the ticket

Headers
Name Required Type Description

Content-Type ✅ Yes String Should be set to application/json

Request Body
{ "status": "Completed" }

Field Required Type Description

status ✅ Yes String New status of the

ticket

Success Response (200 OK)
{

"status": 200,

"message": "Ticket status updated successfully", "data": { "ticketNo": "754298",

"status": "Completed" } }

--- Page 75 ---

Error Response (400/401/404/500)
{ "message": "Unexpected token 'd', "{\n "status": done\n}" is not valid JSON", "error": "Bad Request",

"statusCode": 400

}

Status Codes
Code Meaning

200 Status update successful

400 Bad request

401 Unauthorized

404 Ticket not found

500 Internal server error

21. Report API
Purpose
This API is used to fetch reports related to cargo orders, transactions or weight reconciliation for a given

vendor.

API Method
GET

Endpoint
https://qaapis.delcaper.com/cargo-api/report/get-report

Query Parameters
Name Required Type Description

reportType ✅ Yes String Type of report to fetch. Use order, transaction or weight

reconciliation.

--- Page 76 ---

vendorCode ✅ Yes String Vendor identifier (e.g., bhav19).

limit ❌ No Number Limits the number of records returned (e.g., 10).

filter ❌ No String Apply filters to the report data.

orderStatus ❌ No String Filter by order status.

carrierName ❌ No String Filter by carrier name.

deliveryMode ❌ No String Filter by delivery mode.

ChannelType ❌ No String Filter by the channel type (e.g., EMAIL, CHAT).

fromDate ❌ No String Filter records from this date (format: YYYY-MM-DD or timestamp).

toDate ❌ No String Filter records up to this date.

search ❌ No String Search term for filtering the records.

isParentOrder ❌ No Boolean If true, returns parent orders only.

paymentType ❌ No String Filter by payment type.

txnType ❌ No String Filter by transaction type.

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json.

Success Response (200 OK)
{

"status": 200,

"data": { "orderCount": 0,

"orderData": [] } }

Error Response (400/401/404/500)
--- Page 77 ---

{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
Code Meaning

200 Request successful

400 Bad request

401 Unauthorized

500 Internal server error

22. Report List API
Purpose
This API is used to fetch reports lists related to cargo orders, transactions or weightreconciliation for a given vendor.

API Method
GET

Endpoint https://qaapis.delcaper.com/cargo-api/report/getReportList
--- Page 78 ---

Query Parameters
Name Required Type Description

reportType ✅ Yes String Type of report to fetch. Use order, transaction or weightreconciliation.

vendorCode ✅ Yes String Vendor identifier (e.g., bhav19).

limit ❌ No Number Limits the number of records returned (e.g., 10).

filter ❌ No String Apply filters to the report data.

orderStatus ❌ No String Filter by order status.

carrierName ❌ No String Filter by carrier name.

deliveryMode ❌ No String Filter by delivery mode.

ChannelType ❌ No String Filter by the channel type (e.g., EMAIL, CHAT).

fromDate ❌ No String Filter records from this date (format: YYYY-MM-DD or timestamp).

toDate ❌ No String Filter records up to this date.

search ❌ No String Search term for filtering the records.

isParentOrder ❌ No Boolean If true, returns parent orders only.

paymentType ❌ No String Filter by payment type.

txnType ❌ No String Filter by transaction type.

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json.

--- Page 79 ---

Success Response (200 OK)
{

"status": 200,

"data": { "orderCount": 0,

"orderData": [] } }

Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

Status Codes
Code Meaning

200 Request successful

400 Bad request

404 Not Found

401 Unauthorized

500 Internal server error

--- Page 80 ---

23. Docket creation API
API Method
POST

Endpoint
https://qaapis.delcaper.com/cargo-api/docket

Headers
Name Required Type Description

Content-Type ✅ Yes String Must be application/json

Cookie ✅ Yes String Session cookie for authentication

Request Body
Parameter Required Type Description

awbNumber ✅ Yes String Air Waybill number (unique ID)

vendorCode ✅ Yes String Vendor code for the shipment

--- Page 81 ---

type ✅ Yes String Shipment type PTL

Success Response (200 OK) { "status": 201, "data": { "url": "https://delcaper-qa.s3.ap-south-1.amazonaws.com/cargodham-docketfile/awb-21055184 667839-1758532753360.pdf", "generatedFileName": "awb-21055184667839-1758532753360.pdf", "originalFileName": "awb-21055184667839.pdf" } } Error Response (400/401/404/500)
{

"status": 401,

"trace": { "name": "UnauthorizedException", "error": {} }, "message": "Unauthorized" }

--- Page 82 ---

Status Codes
Code Meaning

200 Docket generated successfully

400 Bad request or missing parameters

401 Unauthorized (invalid/missing cookie)

404 AWB not found

500 Internal server error

🔄 Fresh Extraction
Processing time: s
API Endpoints
POST
/cargo-api/onboarding
Register a new vendor user
POST
/cargo-api/onboarding/login
Authenticate a user and generate a token
POST
/auth/forgot-password
Initiate the password reset process
POST
/cargo-api/address/create
Add or update pickup and delivery addresses
GET
/cargo-api/partner-pincode-serviceability/check-serviceability
Check whether the first mile pincode is serviceable or last mile pincode is serviceable
POST
/rate-card-api/common-rate-calculator
Compute the shipping rate based on shipment parameters
GET
/cargo-api/list/bulk-orders
Fetch a list of booked cargo orders
GET
/wallet-api/wallet/balance
Fetch the available wallet balance of a specific customer (vendor)
POST
/cargo-api/orders/create-order
Create and push a shipment order to the fulfillment system
POST
/wallet-api/wallet/balance
Create a wallet transaction corresponding to a product order
GET
/cargo-api/webhooks
Get tracking details for a shipment
POST
/cargo-api/orders/cancel/bulk
Cancel a booking/order
POST
/common/cargo-api/orders/{awbNumber}/update
Upload invoice, docket files or e-way bills
POST
/cargo-api/webhooks/order-manifest-webhook
Create a cargo manifest for a seller's order
POST
/cargo-api/print-label/v2
Generate and print the label for a cargo order
PATCH
/cargo-api/onboarding/{vendorCode}
Fetch transporter ID details
PATCH
/cargo-api/orders/{awbNumber}/update
Fetch E-way bill details
POST
/support-tickets/ticket
Create a new support ticket
GET
/support-tickets/ticket
Fetch support tickets
PUT
/support-tickets/ticket/{ticketId}
Update the status of an existing support ticket
GET
/cargo-api/report/get-report
Fetch reports related to cargo orders, transactions or weight reconciliation for a given vendor
GET
/cargo-api/report/getReportList
Fetch reports lists related to cargo orders, transactions or weight reconciliation for a given vendor
POST
/cargo-api/docket
Docket creation API
Back
Activate Integration
🧪 DEV MODE: Authentication bypassed for testing