"""Debug script to test LLM provider initialization"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set API key
OPENAI_API_KEY = "REDACTED_API_KEY"
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

print("=" * 60)
print("DEBUG: LLM Provider Initialization")
print("=" * 60)

print(f"\n1. OpenAI API Key set: {bool(os.environ.get('OPENAI_API_KEY'))}")
print(f"   Key preview: {OPENAI_API_KEY[:20]}...")

try:
    print("\n2. Importing LLMProviderFactory...")
    from services.llm_providers import LLMProviderFactory
    print("   ✓ Import successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

try:
    print("\n3. Creating LLM config...")
    llm_config = {
        'LLM_PROVIDER': 'openai',
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'OPENAI_MODEL': 'gpt-4o-mini',
        'OPENAI_VISION_MODEL': 'gpt-4o',
        'OPENAI_TRANSCRIBE_MODEL': 'whisper-1',
    }
    print(f"   Config: {llm_config}")
except Exception as e:
    print(f"   ✗ Config creation failed: {e}")
    sys.exit(1)

try:
    print("\n4. Creating LLM provider with factory...")
    llm_provider = LLMProviderFactory.create(llm_config)
    print("   ✓ Provider created successfully")
except Exception as e:
    print(f"   ✗ Provider creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n5. Checking provider methods...")
    if hasattr(llm_provider, 'vision_analysis'):
        print("   ✓ vision_analysis method exists")
    else:
        print("   ✗ vision_analysis method NOT found")
    
    if hasattr(llm_provider, '_initialized'):
        print(f"   ✓ Provider initialized: {llm_provider._initialized}")
    else:
        print("   ? _initialized property not found")
except Exception as e:
    print(f"   ✗ Method check failed: {e}")

print("\n" + "=" * 60)
print("✓ LLM Provider initialization successful!")
print("=" * 60)
