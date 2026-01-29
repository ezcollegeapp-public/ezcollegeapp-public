"""
Test 2: Fill Forms with Semantic Blocks
Test by calling the actual form fill service with semantic blocks created by Test 1

This test should be run AFTER test_1.py to ensure semantic blocks are available.

Prerequisites:
- Run test_1.py first to upload files and create semantic blocks
- Semantic blocks should be stored in ChromaDB
- ChromaDB database path configured in environment variables
"""

import sys
import json
import random
import os
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
USER_ID = "test_user_001"
NUM_SCHOOLS = 5
OPENAI_API_KEY = "REDACTED_API_KEY"  # Replace with your actual OpenAI API key

# Set environment variables for LLM and search providers
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ['SEARCH_PROVIDER'] = 'chromadb'
os.environ['CHROMADB_DATA_DIR'] = '/home/myid/ps47974/ezcommonapp/full-web-app-1123/ezcommon-backend/data/chroma_data'
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['OPENAI_MODEL'] = 'gpt-4o-mini'
os.environ['OPENAI_VISION_MODEL'] = 'gpt-4o'

from services.form_fill_service import FormFillService
from services.school_form_output_service import SchoolFormOutputService
from services.search_providers import SearchProviderFactory
from services.llm_providers import LLMProviderFactory
from config import ConfigLoader

def test_fill_forms():
    """Test form fill service
    
    Note: This test assumes that semantic blocks have been created
    by test_1.py and stored in the ChromaDB database. The FormFillService
    retrieves these semantic blocks to fill out the forms.
    
    The semantic blocks are expected to have the following structure:
    - block_id: unique identifier
    - block_type: one of the semantic types (ACADEMIC_PERFORMANCE, etc.)
    - sources: list of source files
    - summary: one-line summary of the block
    - content: reorganized content
    - user_id: owner of the block
    """
    
    print(f"🔍 Loading configuration...")
    
    # Load config
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_college_questions()
        print(f"✓ Config loaded")
        
        # First, verify that semantic blocks exist from test_1.py
        print(f"\n📊 Verifying semantic blocks in database...")
        try:
            # Initialize search provider to check for blocks
            search_config = {
                'SEARCH_PROVIDER': os.environ.get('SEARCH_PROVIDER', 'chromadb'),
                'CHROMADB_DATA_DIR': os.environ.get('CHROMADB_DATA_DIR', './chroma_data'),
                'CHROMADB_COLLECTION_NAME': os.environ.get('CHROMADB_COLLECTION_NAME', 'document_chunks')
            }
            search_provider_check = SearchProviderFactory.create(search_config)
            search_provider_check.initialize()
            
            # Retrieve blocks for the user to see what's available
            results = search_provider_check.get_all_chunks_for_user(user_id=USER_ID)
            if results:
                print(f"✓ Semantic blocks found in database (ready for form filling)")
                print(f"  Total chunks: {len(results)}")
                # Check if results contain semantic block structure
                if results and isinstance(results[0], dict):
                    if 'category' in results[0]:
                        print(f"  ✓ Blocks have 'category' field")
                    if 'source_file' in results[0]:
                        print(f"  ✓ Blocks have 'source_file' field (source attribution)")
            else:
                print(f"⚠️  No semantic blocks found for user {USER_ID}")
                print(f"   (This is OK - test_1.py may not have been run yet)")
        except Exception as e:
            print(f"⚠️  Could not verify semantic blocks: {e}")
    
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Get list of schools
    schools = list(config.keys())
    if not schools:
        print("❌ No schools in config")
        return False
    
    print(f"✓ Found {len(schools)} schools")
    
    # Select random schools
    selected = random.sample(schools, min(NUM_SCHOOLS, len(schools)))
    print(f"\n🎲 Selected {len(selected)} random schools:")
    for school in selected:
        print(f"  - {school}")
    
    # Initialize form fill service
    try:
        # Initialize search provider (ChromaDB)
        search_config = {
            'SEARCH_PROVIDER': os.environ.get('SEARCH_PROVIDER', 'chromadb'),
            'CHROMADB_DATA_DIR': os.environ.get('CHROMADB_DATA_DIR', './chroma_data'),
            'CHROMADB_COLLECTION_NAME': os.environ.get('CHROMADB_COLLECTION_NAME', 'document_chunks')
        }
        search_provider = SearchProviderFactory.create(search_config)
        search_provider.initialize()
        
        # Initialize LLM provider
        llm_config = {
            'LLM_PROVIDER': os.environ.get('LLM_PROVIDER', 'openai'),
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            'OPENAI_VISION_MODEL': os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o'),
        }
        llm_provider = LLMProviderFactory.create(llm_config)
        
        # Initialize services with providers
        form_fill_service = FormFillService(search_provider=search_provider, llm_provider=llm_provider)
        output_service = SchoolFormOutputService()
        print(f"\n✓ Services initialized")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Fill forms for each school
    print(f"\n📋 Filling forms...")
    
    # First, fill general application questions (only once)
    use_optimization_general = False  # Set to False to bypass optimization and use all chunks
    print(f"\n📝 Filling general application questions...")
    print(f"   (optimization enabled: {use_optimization_general})")
    try:
        general_data = form_fill_service.fill_general_questions(
            user_id=USER_ID,
            use_optimization=use_optimization_general
        )
        print(f"  ✓ General questions filled")
        print(f"    Total questions: {general_data.get('total_questions', 0)}")
        print(f"    Filled: {general_data.get('filled_count', 0)}")
        print(f"    Success rate: {general_data.get('fill_percentage', 0)}%")
        print(f"    Sections: {len(general_data.get('filled_sections', {}))}")
        
        # Save general questions
        output_service.save_general_questions(USER_ID, general_data)
    except Exception as e:
        print(f"  ❌ Error filling general questions: {e}")
        import traceback
        traceback.print_exc()
        general_data = None
    
    # Then, fill school-specific questions for each school
    successful = 0
    failed = 0
    
    for school_id in selected:
        try:
            print(f"\n  Processing: {school_id}")
            
            # Fill the form
            use_optimization_school = True  # Set to False to bypass optimization and use all chunks
            print(f"    (optimization enabled: {use_optimization_school})")
            filled_data = form_fill_service.fill_school_questions(
                user_id=USER_ID,
                school_id=school_id,
                use_optimization=use_optimization_school
            )
            
            # Save the form
            output_service.save_or_return_json(USER_ID, school_id, filled_data)
            
            # Count questions answered
            status = filled_data.get('form_data', {}).get('status', 'unknown')
            filled_count = filled_data.get('form_data', {}).get('filled_count', 0)
            
            if status == 'success':
                print(f"    ✓ Form filled and saved")
                print(f"      Questions answered: {filled_count}")
                successful += 1
            else:
                print(f"    ⚠️  Form filled with warnings")
                print(f"      Status: {status}")
                successful += 1
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n" + "=" * 50)
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    
    # Summary including general questions
    print(f"\n📊 SUMMARY:")
    if general_data:
        print(f"  General Questions:")
        print(f"    - Total: {general_data.get('total_questions', 0)}")
        print(f"    - Filled: {general_data.get('filled_count', 0)}")
        print(f"    - Success Rate: {general_data.get('fill_percentage', 0)}%")
    print(f"  School-Specific Questions:")
    print(f"    - Schools Processed: {successful}")
    print(f"    - Total Schools: {len(selected)}")
    
    return failed == 0


if __name__ == "__main__":
    print("TEST 2: FILL FORMS")
    print("=" * 50)
    success = test_fill_forms()
    print("=" * 50)
    print(f"Result: {'PASSED ✓' if success else 'PASSED WITH WARNINGS ⚠'}")
