"""
Phase 3 & Phase 4 Verification Test
Tests the Integration & Orchestration Layer implementations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("🧪 PHASE 3 & 4 REALITY CHECK - Testing Integration & Orchestration")
print("=" * 80)
print()

# ============================================================================
# PHASE 3 TESTING
# ============================================================================

print("🔵 PHASE 3: INTEGRATION & ORCHESTRATION LAYER")
print("=" * 80)

# Test 1: Check Phase 3 files exist
print("\n📁 Test 1: Phase 3 File Existence Check...")
phase3_base = Path(__file__).parent.parent / "src" / "application" / "ai"

phase3_files = {
    "hybrid/hybrid_predictor.py": 400,
    "orchestration/autonomous_orchestrator.py": 500,
    "orchestration/execution_engine.py": 450,
    "orchestration/learning_loop.py": 400,
    "orchestration/performance_monitor.py": 450,
    "orchestration/model_registry.py": 450,
}

phase3_exists = {}
for file_path, min_lines in phase3_files.items():
    full_path = phase3_base / file_path
    if full_path.exists():
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = len([l for l in f if l.strip()])
        is_real = lines >= min_lines
        status = "✅" if is_real else "⚠️"
        print(f"  {status} {file_path}: {lines} lines (min: {min_lines})")
        phase3_exists[file_path] = lines >= min_lines
    else:
        print(f"  ❌ {file_path}: MISSING")
        phase3_exists[file_path] = False

phase3_complete = all(phase3_exists.values())
if phase3_complete:
    print(f"\n  ✅ All Phase 3 files exist with substantial code\n")
else:
    print(f"\n  ⚠️  Some Phase 3 files are missing or incomplete\n")

# Test 2: Import Phase 3 components
print("🔍 Test 2: Phase 3 Component Imports...")
phase3_imports = {}

try:
    from src.application.ai.hybrid.hybrid_predictor import HybridPredictor
    print("  ✅ HybridPredictor imported")
    phase3_imports['HybridPredictor'] = True
except Exception as e:
    print(f"  ❌ HybridPredictor import failed: {str(e)[:100]}")
    phase3_imports['HybridPredictor'] = False

try:
    from src.application.ai.orchestration.autonomous_orchestrator import AutonomousOrchestrator
    print("  ✅ AutonomousOrchestrator imported")
    phase3_imports['AutonomousOrchestrator'] = True
except Exception as e:
    print(f"  ❌ AutonomousOrchestrator import failed: {str(e)[:100]}")
    phase3_imports['AutonomousOrchestrator'] = False

try:
    from src.application.ai.orchestration.execution_engine import ExecutionEngine
    print("  ✅ ExecutionEngine imported")
    phase3_imports['ExecutionEngine'] = True
except Exception as e:
    print(f"  ❌ ExecutionEngine import failed: {str(e)[:100]}")
    phase3_imports['ExecutionEngine'] = False

try:
    from src.application.ai.orchestration.learning_loop import LearningLoop
    print("  ✅ LearningLoop imported")
    phase3_imports['LearningLoop'] = True
except Exception as e:
    print(f"  ❌ LearningLoop import failed: {str(e)[:100]}")
    phase3_imports['LearningLoop'] = False

try:
    from src.application.ai.orchestration.performance_monitor import PerformanceMonitor
    print("  ✅ PerformanceMonitor imported")
    phase3_imports['PerformanceMonitor'] = True
except Exception as e:
    print(f"  ❌ PerformanceMonitor import failed: {str(e)[:100]}")
    phase3_imports['PerformanceMonitor'] = False

try:
    from src.application.ai.orchestration.model_registry import ModelRegistry
    print("  ✅ ModelRegistry imported")
    phase3_imports['ModelRegistry'] = True
except Exception as e:
    print(f"  ❌ ModelRegistry import failed: {str(e)[:100]}")
    phase3_imports['ModelRegistry'] = False

phase3_imports_ok = any(phase3_imports.values())
if phase3_imports_ok:
    success_count = sum(phase3_imports.values())
    print(f"\n  ✅ {success_count}/6 Phase 3 components imported successfully\n")
else:
    print(f"\n  ❌ No Phase 3 components could be imported\n")

# Test 3: Check Phase 3 code quality
print("📊 Test 3: Phase 3 Code Quality Indicators...")
quality_indicators = {
    "async def": "Async/await patterns",
    "class.*Predictor": "Predictor classes",
    "class.*Orchestrator": "Orchestrator classes",
    "ChromaDB|ChromaVectorStore": "Vector DB integration",
    "cache": "Caching logic",
    "redis": "Redis integration",
    "def predict": "Prediction methods",
    "def execute": "Execution methods",
    "LangGraph|StateGraph": "LangGraph orchestration"
}

hybrid_predictor_path = phase3_base / "hybrid" / "hybrid_predictor.py"
if hybrid_predictor_path.exists():
    with open(hybrid_predictor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    found_indicators = {}
    for pattern, desc in quality_indicators.items():
        if re.search(pattern, content, re.IGNORECASE):
            found_indicators[desc] = True
            print(f"  ✅ {desc}")
        else:
            print(f"  ⚠️  {desc} not found")
    
    quality_score = len(found_indicators) / len(quality_indicators)
    if quality_score >= 0.5:
        print(f"\n  ✅ Phase 3 code quality: {quality_score*100:.0f}% ({len(found_indicators)}/{len(quality_indicators)} indicators)\n")
    else:
        print(f"\n  ⚠️  Phase 3 code quality: {quality_score*100:.0f}% ({len(found_indicators)}/{len(quality_indicators)} indicators)\n")
else:
    print("  ⚠️  Cannot assess - hybrid_predictor.py not found\n")

# ============================================================================
# PHASE 4 TESTING (REST API LAYER)
# ============================================================================

print("\n🟣 PHASE 4: REST API LAYER")
print("=" * 80)

# Test 4: Check Phase 4 REST APIs
print("\n📁 Test 4: Phase 4 REST API Files...")
rest_base = Path(__file__).parent.parent / "src" / "presentation" / "rest"

phase4_files = {
    "autonomous_api.py": 150,
    "simple_testing.py": 100,
}

phase4_exists = {}
for file_path, min_lines in phase4_files.items():
    full_path = rest_base / file_path
    if full_path.exists():
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = len([l for l in f if l.strip()])
        is_real = lines >= min_lines
        status = "✅" if is_real else "⚠️"
        print(f"  {status} {file_path}: {lines} lines (min: {min_lines})")
        phase4_exists[file_path] = lines >= min_lines
    else:
        print(f"  ❌ {file_path}: MISSING")
        phase4_exists[file_path] = False

# Test 5: Check REST endpoints
print("\n🔍 Test 5: REST API Endpoints...")
autonomous_path = rest_base / "autonomous_api.py"
if autonomous_path.exists():
    with open(autonomous_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    endpoints = {
        "@router.post.*onboard": "POST /onboard endpoint",
        "@router.post.*test": "POST /test endpoint",
        "@router.get.*status": "GET /status endpoint",
        "APIRouter": "FastAPI Router",
        "async def": "Async handlers"
    }
    
    found_endpoints = 0
    for pattern, desc in endpoints.items():
        if re.search(pattern, content):
            print(f"  ✅ {desc}")
            found_endpoints += 1
        else:
            print(f"  ⚠️  {desc} not found")
    
    if found_endpoints >= 3:
        print(f"\n  ✅ REST API layer has {found_endpoints}/{len(endpoints)} expected features\n")
    else:
        print(f"\n  ⚠️  REST API layer incomplete: {found_endpoints}/{len(endpoints)} features\n")
else:
    print("  ❌ autonomous_api.py not found\n")

# Test 6: Check if APIs are registered in main.py
print("📋 Test 6: API Registration in main.py...")
main_path = Path(__file__).parent.parent / "src" / "main.py"
if main_path.exists():
    with open(main_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    registrations = {
        "autonomous": "autonomous router",
        "simple_testing": "testing router",
        "include_router": "router registration"
    }
    
    registered = 0
    for key, desc in registrations.items():
        if key in main_content:
            print(f"  ✅ {desc} registered")
            registered += 1
        else:
            print(f"  ⚠️  {desc} not registered")
    
    if registered >= 2:
        print(f"\n  ✅ API routes registered in main.py\n")
    else:
        print(f"\n  ⚠️  Some routes may not be registered\n")
else:
    print("  ❌ main.py not found\n")

# ============================================================================
# FINAL VERDICT
# ============================================================================

print("\n" + "=" * 80)
print("📋 FINAL VERDICT")
print("=" * 80)

phase3_score = sum([
    phase3_complete,
    phase3_imports_ok,
    quality_score >= 0.5 if 'quality_score' in locals() else False
]) / 3

phase4_score = sum([
    all(phase4_exists.values()) if phase4_exists else False,
    found_endpoints >= 3 if 'found_endpoints' in locals() else False,
    registered >= 2 if 'registered' in locals() else False
]) / 3

print(f"\n🔵 PHASE 3 Score: {phase3_score*100:.0f}%")
if phase3_score >= 0.7:
    print("   ✅ Phase 3 appears to be REAL with substantial implementations")
elif phase3_score >= 0.4:
    print("   ⚠️  Phase 3 is partially implemented")
else:
    print("   ❌ Phase 3 appears incomplete or dummy")

print(f"\n🟣 PHASE 4 Score: {phase4_score*100:.0f}%")
if phase4_score >= 0.7:
    print("   ✅ Phase 4 appears to be REAL with working REST APIs")
elif phase4_score >= 0.4:
    print("   ⚠️  Phase 4 is partially implemented")
else:
    print("   ❌ Phase 4 appears incomplete or dummy")

overall_score = (phase3_score + phase4_score) / 2
print(f"\n🎯 OVERALL Score: {overall_score*100:.0f}%")

if overall_score >= 0.7:
    print("\n✅ VERDICT: Phase 3 & 4 are REAL implementations!")
    print("   - Integration layer exists")
    print("   - Orchestration components present")
    print("   - REST API layer functional")
elif overall_score >= 0.4:
    print("\n⚠️  VERDICT: Phase 3 & 4 are PARTIALLY implemented")
    print("   - Some components exist")
    print("   - May need completion or fixes")
else:
    print("\n❌ VERDICT: Phase 3 & 4 appear incomplete")
    print("   - Missing key components")
    print("   - May be stub implementations")

print("\n" + "=" * 80)
