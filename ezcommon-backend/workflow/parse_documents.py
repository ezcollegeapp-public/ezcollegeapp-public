"""
Test 1: Upload Files and Parse
Test by calling the actual document parsing service with the same logic
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.document_parse_service import DocumentParseService
from services.search_providers import SearchProviderFactory
from services.llm_providers import LLMProviderFactory

# Configuration
USER_ID = "test_user_001"
OPENAI_API_KEY = "REDACTED_API_KEY"  # Replace with your actual OpenAI API key

# Set environment variables for LLM and search providers
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
os.environ['SEARCH_PROVIDER'] = 'chromadb'
os.environ['CHROMADB_DATA_DIR'] = '/home/myid/ps47974/ezcommonapp/full-web-app-1123/ezcommon-backend/data/chroma_data'
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['OPENAI_MODEL'] = 'gpt-4o-mini'
os.environ['OPENAI_VISION_MODEL'] = 'gpt-4o'

def test_upload_and_parse():
    """Test document parsing service with files in data/ directory"""
    
    data_dir = Path("/home/myid/ps47974/ezcommonapp/full-web-app-1123/ezcommon-backend/data")
    print(f"🔍 Looking for files at: {data_dir.absolute()}")
    
    if not data_dir.exists():
        print("❌ data/ directory not found")
        return False
    
    files = list(data_dir.glob("*"))
    if not files:
        print("❌ No files in data/ directory")
        return False
    
    print(f"✓ Found {len(files)} files to parse:")
    for f in files:
        print(f"  - {f.name}")
    
    # Initialize search provider (ChromaDB or OpenSearch)
    try:
        search_config = {
            'SEARCH_PROVIDER': os.environ.get('SEARCH_PROVIDER', 'chromadb'),
            'CHROMADB_DATA_DIR': os.environ.get('CHROMADB_DATA_DIR', './chroma_data'),
            'CHROMADB_COLLECTION_NAME': os.environ.get('CHROMADB_COLLECTION_NAME', 'document_chunks')
        }
        search_provider = SearchProviderFactory.create(search_config)
        # IMPORTANT: Call initialize() to set up the connection
        search_provider.initialize()
        print(f"✓ Search provider initialized")
    except Exception as e:
        print(f"⚠ Warning: Search provider init failed: {e}")
        search_provider = None
    
    # Initialize LLM provider (for image processing and vision capabilities)
    llm_provider = None
    try:
        llm_config = {
            'LLM_PROVIDER': os.environ.get('LLM_PROVIDER', 'openai'),
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            'OPENAI_VISION_MODEL': os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o'),
            'OPENAI_TRANSCRIBE_MODEL': os.environ.get('OPENAI_TRANSCRIBE_MODEL', 'whisper-1'),
        }
        llm_provider = LLMProviderFactory.create(llm_config)
        print(f"✓ LLM provider initialized")
    except Exception as e:
        print(f"⚠ Warning: LLM provider init failed: {e}")
        print(f"   (Images will not be processed without LLM provider)")
        llm_provider = None
    
    # Initialize parser service (same as auth_api.py does)
    try:
        parser = DocumentParseService(search_provider=search_provider, llm_provider=llm_provider)
        print(f"✓ DocumentParseService initialized")
    except Exception as e:
        print(f"❌ Failed to initialize parser: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Parse each file using semantic chunking
    print(f"\n📤 Parsing files with SEMANTIC CHUNKING...")
    total_naive_chunks = 0
    total_semantic_blocks = 0
    
    for file_path in files:
        try:
            print(f"\n  Processing: {file_path.name}")
            
            # Determine file type and extract text
            file_ext = file_path.suffix.lower()
            extracted_text = None
            
            if file_ext == '.pdf':
                # Extract text from PDF
                print(f"    📄 Extracting from PDF...")
                try:
                    extracted_text = parser.process_pdf(str(file_path))
                    print(f"    ✓ Extracted text ({len(extracted_text)} chars)")
                except Exception as pdf_error:
                    print(f"    ⚠️  PDF processing skipped")
                    continue
                
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # Process image
                print(f"    🖼️  Processing image...")
                try:
                    import json
                    structured_data = parser.process_image(str(file_path), source_file=file_path.name)
                    extracted_text = json.dumps(structured_data, indent=2)
                    print(f"    ✓ Extracted from image ({len(extracted_text)} chars)")
                except Exception as img_error:
                    print(f"    ⚠️  Image processing skipped: {img_error}")
                    continue
                
            elif file_ext in ['.txt', '.md', '.doc', '.docx']:
                # For text files, read directly
                print(f"    📝 Reading text file...")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = f.read()
                print(f"    ✓ Read {len(extracted_text)} chars")
            else:
                print(f"    ⚠️  Unsupported file type: {file_ext}")
                continue
            
            if not extracted_text:
                print(f"    ❌ No text extracted")
                continue
            
            # Form semantic blocks using LLM
            print(f"    🧠 Forming semantic blocks...")
            raw_texts = [{
                'source_file': file_path.name,
                'file_type': file_ext,
                'content': extracted_text
            }]
            
            semantic_blocks = parser.form_semantic_chunks_for_user(
                user_id=USER_ID,
                section="general",
                raw_texts=raw_texts
            )
            
            if semantic_blocks:
                print(f"    ✓ Created {len(semantic_blocks)} semantic blocks")
                total_semantic_blocks += len(semantic_blocks)
                
                # Store semantic blocks in database
                if search_provider:
                    print(f"    💾 Storing semantic blocks...")
                    # Wrap semantic blocks in the information_chunks format for storage
                    document_id = parser._generate_document_id(file_path.name, USER_ID)
                    document = {
                        "user_id": USER_ID,
                        "source_file": file_path.name,
                        "section": "general",
                        "file_type": file_ext,
                        "information_chunks": semantic_blocks
                    }
                    success = search_provider.store_document(document_id, document)
                    if not success:
                        print(f"    ⚠️  Failed to store semantic blocks")
                    else:
                        print(f"    ✓ Stored {len(semantic_blocks)} semantic blocks")
                else:
                    print(f"    ⚠️  Search provider not available")
            else:
                # Fallback to naive chunking if semantic failed
                print(f"    ⚠️  Semantic chunking failed, using naive chunks as fallback...")
                naive_chunks = parser._create_text_chunks(extracted_text, source_file=file_path.name)
                total_naive_chunks += len(naive_chunks)
                print(f"    ✓ Created {len(naive_chunks)} naive chunks (fallback)")
                
                # Store fallback chunks in database
                if search_provider and naive_chunks:
                    print(f"    💾 Storing fallback naive chunks...")
                    document_id = parser._generate_document_id(file_path.name, USER_ID)
                    parser._store_document_chunks(
                        document_id=document_id,
                        source_file=file_path.name,
                        chunks=naive_chunks,
                        processor_name="DocumentParseService",
                        file_type=file_ext,
                        user_id=USER_ID,
                        section="general"
                    )
                    print(f"    ✓ Stored {len(naive_chunks)} fallback chunks")
                elif not search_provider:
                    print(f"    ⚠️  Search provider not available, skipping storage")
                else:
                    print(f"    ⚠️  No naive chunks to store")
        
        except Exception as e:
            print(f"    ❌ Error parsing file: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*50}")
    print(f"✓ Results:")
    print(f"  - Semantic blocks created: {total_semantic_blocks}")
    print(f"  - Fallback naive chunks: {total_naive_chunks}")
    
    if total_semantic_blocks == 0 and total_naive_chunks == 0:
        print("⚠ Warning: No chunks were extracted from any files")
        return False
    
    return True


if __name__ == "__main__":
    print("TEST 1: UPLOAD FILES AND PARSE")
    print("=" * 50)
    success = test_upload_and_parse()
    print("=" * 50)
    print(f"Result: {'PASSED ✓' if success else 'FAILED ✗'}")
