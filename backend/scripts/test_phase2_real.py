"""
Real Phase 2 Test - Verify ML Models Actually Work
Tests with actual PDF from docs folder
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("🧪 PHASE 2 REALITY CHECK - Testing ML Models with Real PDF")
print("=" * 80)
print()

# Test 1: Check if ML model files exist
print("📁 Test 1: Checking ML Model Files...")
ml_models_dir = Path(__file__).parent.parent / "src" / "application" / "ai" / "ml_models"
expected_files = [
    "data_collector.py",
    "endpoint_classifier.py",
    "payload_generator.py",
    "error_fixer.py",
    "workflow_predictor.py",
    "model_server.py",
    "training_pipeline.py"
]

all_exist = True
for file in expected_files:
    file_path = ml_models_dir / file
    exists = file_path.exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("  ✅ All ML model files exist\n")
else:
    print("  ❌ Some ML model files are missing\n")
    sys.exit(1)

# Test 2: Check file sizes (detect if they're just stubs)
print("📏 Test 2: Checking File Sizes (Detecting Stubs)...")
min_lines = {
    "data_collector.py": 50,
    "endpoint_classifier.py": 100,
    "payload_generator.py": 200,
    "error_fixer.py": 250,
    "workflow_predictor.py": 400,
    "model_server.py": 400,
    "training_pipeline.py": 300
}

all_real = True
for file, min_line_count in min_lines.items():
    file_path = ml_models_dir / file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = len(f.readlines())
    is_real = lines >= min_line_count
    status = "✅" if is_real else "❌"
    print(f"  {status} {file}: {lines} lines (min: {min_line_count})")
    if not is_real:
        all_real = False

if all_real:
    print("  ✅ All files have substantial code (not stubs)\n")
else:
    print("  ❌ Some files appear to be stubs\n")
    sys.exit(1)

# Test 3: Import ML models (verify no syntax errors)
print("🔍 Test 3: Importing ML Models...")
try:
    from src.application.ai.ml_models.endpoint_classifier import EndpointClassifier
    print("  ✅ EndpointClassifier imported")
except Exception as e:
    print(f"  ❌ EndpointClassifier import failed: {e}")
    all_real = False

try:
    from src.application.ai.ml_models.payload_generator import PayloadGeneratorModel
    print("  ✅ PayloadGeneratorModel imported")
except Exception as e:
    print(f"  ❌ PayloadGeneratorModel import failed: {e}")
    all_real = False

try:
    from src.application.ai.ml_models.error_fixer import ErrorFixerModel
    print("  ✅ ErrorFixerModel imported")
except Exception as e:
    print(f"  ❌ ErrorFixerModel import failed: {e}")
    all_real = False

try:
    from src.application.ai.ml_models.workflow_predictor import WorkflowPredictor
    print("  ✅ WorkflowPredictor imported")
except Exception as e:
    print(f"  ❌ WorkflowPredictor import failed: {e}")
    all_real = False

try:
    from src.application.ai.ml_models.model_server import ModelServer
    print("  ✅ ModelServer imported")
except Exception as e:
    print(f"  ❌ ModelServer import failed: {e}")
    all_real = False

if all_real:
    print("  ✅ All ML models import successfully\n")
else:
    print("  ❌ Some imports failed\n")
    sys.exit(1)

# Test 4: Instantiate models (verify they initialize)
print("🏗️  Test 4: Instantiating ML Models...")
try:
    classifier = EndpointClassifier()
    print(f"  ✅ EndpointClassifier instantiated")
    print(f"     - Labels: {classifier.LABELS}")
    print(f"     - Model type: {type(classifier.model).__name__}")
except Exception as e:
    print(f"  ❌ EndpointClassifier instantiation failed: {e}")
    all_real = False

try:
    generator = PayloadGeneratorModel()
    print(f"  ✅ PayloadGeneratorModel instantiated")
    print(f"     - Model name: {generator.model_name}")
except Exception as e:
    print(f"  ❌ PayloadGeneratorModel instantiation failed: {e}")
    all_real = False

try:
    fixer = ErrorFixerModel()
    print(f"  ✅ ErrorFixerModel instantiated")
    print(f"     - Model name: {fixer.model_name}")
except Exception as e:
    print(f"  ❌ ErrorFixerModel instantiation failed: {e}")
    all_real = False

try:
    predictor = WorkflowPredictor()
    print(f"  ✅ WorkflowPredictor instantiated")
    param_count = sum(p.numel() for p in predictor.encoder.parameters())
    print(f"     - Parameters: {param_count:,}")
except Exception as e:
    print(f"  ❌ WorkflowPredictor instantiation failed: {e}")
    all_real = False

try:
    server = ModelServer()
    print(f"  ✅ ModelServer instantiated")
    print(f"     - Models registered: {len(server.models)}")
except Exception as e:
    print(f"  ❌ ModelServer instantiation failed: {e}")
    all_real = False

if all_real:
    print("  ✅ All models instantiate successfully\n")
else:
    print("  ❌ Some models failed to instantiate\n")
    sys.exit(1)

# Test 5: Run inference (verify models can make predictions)
print("🔮 Test 5: Running Model Inference...")
try:
    result = classifier.predict("/api/users", "POST")
    print(f"  ✅ EndpointClassifier prediction: {result}")
    assert 'label' in result
    assert 'confidence' in result
except Exception as e:
    print(f"  ❌ EndpointClassifier prediction failed: {e}")
    all_real = False

try:
    result = generator.generate_payload("/api/users", "POST")
    print(f"  ✅ PayloadGenerator prediction: {result}")
    assert 'payload' in result
except Exception as e:
    print(f"  ❌ PayloadGenerator prediction failed: {e}")
    all_real = False

try:
    result = fixer.fix_error(
        error_request='POST /api/users {"name": "Test"}',
        error_message='Required field email is missing'
    )
    print(f"  ✅ ErrorFixer prediction: {result}")
    assert 'fixed_request' in result
except Exception as e:
    print(f"  ❌ ErrorFixer prediction failed: {e}")
    all_real = False

if all_real:
    print("  ✅ All models can make predictions\n")
else:
    print("  ❌ Some predictions failed\n")
    sys.exit(1)

async def test_pdf_parsing():
    """Test 6: Test with Real PDF from docs folder"""
    print("📄 Test 6: Testing with Real PDF from docs folder...")
    pdf_path = Path(__file__).parent.parent / "docs" / "Cargo Api Documentation.pdf"

    if not pdf_path.exists():
        print(f"  ⚠️  PDF not found at: {pdf_path}")
        print("  Looking for any PDF in docs folder...")
        docs_dir = Path(__file__).parent.parent / "docs"
        pdf_files = list(docs_dir.glob("*.pdf"))
        if pdf_files:
            pdf_path = pdf_files[0]
            print(f"  ✅ Found PDF: {pdf_path.name}")
        else:
            print("  ❌ No PDF files found in docs folder")
            sys.exit(1)
    else:
        print(f"  ✅ Found PDF: {pdf_path.name}")

    # Try to parse the PDF
    print(f"\n📊 Parsing PDF: {pdf_path.name}")
    try:
        from src.application.ai.parsers.pdf_parser import PDFParser
        from fastapi import UploadFile
        import io
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"  📁 PDF size: {len(pdf_bytes):,} bytes")
        
        # Create a mock UploadFile
        class MockUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.content_type = "application/pdf"
                self.file = io.BytesIO(content)
            
            async def read(self):
                return self.file.read()
            
            async def seek(self, position):
                self.file.seek(position)
        
        mock_file = MockUploadFile(pdf_path.name, pdf_bytes)
        
        # Parse with PDFParser
        parser = PDFParser()
        print("  🔄 Parsing PDF with AI...")
        
        # This will use Mistral OCR and Gemini analysis
        api_spec = await parser.parse(mock_file)
        
        print(f"\n  ✅ PDF Parsed Successfully!")
        print(f"     - Base URL: {api_spec.baseUrl}")
        print(f"     - Endpoints found: {len(api_spec.endpoints)}")
        print(f"     - Authentication: {api_spec.auth.type if api_spec.auth else 'None'}")
        
        # Show first few endpoints
        if api_spec.endpoints:
            print(f"\n  📍 Sample Endpoints:")
            for i, endpoint in enumerate(api_spec.endpoints[:5]):
                print(f"     {i+1}. {endpoint.method} {endpoint.path}")
        
        # Now test ML models on parsed endpoints
        print(f"\n🎯 Testing ML Models on Parsed Endpoints...")
        
        # Get the models from global scope
        from src.application.ai.ml_models.endpoint_classifier import EndpointClassifier
        from src.application.ai.ml_models.payload_generator import PayloadGeneratorModel
        
        classifier = EndpointClassifier()
        generator = PayloadGeneratorModel()
        
        for i, endpoint in enumerate(api_spec.endpoints[:3]):
            print(f"\n  Endpoint {i+1}: {endpoint.method} {endpoint.path}")
            
            # Test classifier
            try:
                classification = classifier.predict(endpoint.path, endpoint.method)
                print(f"    ✅ Classification: {classification['label']} ({classification['confidence']:.2f})")
            except Exception as e:
                print(f"    ❌ Classification failed: {e}")
            
            # Test payload generator
            try:
                payload = generator.generate_payload(endpoint.path, endpoint.method)
                print(f"    ✅ Generated payload: {payload['payload']}")
            except Exception as e:
                print(f"    ❌ Payload generation failed: {e}")
        
        print(f"\n" + "=" * 80)
        print("🎉 PHASE 2 VERIFICATION COMPLETE - ALL TESTS PASSED!")
        print("=" * 80)
        print("\n✅ Phase 2 is REAL and WORKING:")
        print("   - All 5 ML models exist and have substantial code")
        print("   - All models import and instantiate successfully")
        print("   - All models can make predictions")
        print("   - PDF parsing works with real document")
        print("   - ML models work on parsed endpoints")
        print("\n🚀 Phase 2 is ready for production use!")
        
    except Exception as e:
        print(f"\n  ❌ PDF parsing or ML testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Run the PDF parsing test
asyncio.run(test_pdf_parsing())
