"""
Utility script to extract and view data stored in ChromaDB
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.search_providers import SearchProviderFactory

def print_separator(title=""):
    """Print a formatted separator line"""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")
    else:
        print(f"{'=' * 70}")

def get_database_stats():
    """Get statistics about the database"""
    try:
        search_config = {
            'SEARCH_PROVIDER': 'chromadb',
            'CHROMADB_DATA_DIR': '/home/myid/ps47974/ezcommonapp/full-web-app-1123/ezcommon-backend/data/chroma_data',
            'CHROMADB_COLLECTION_NAME': 'document_chunks'
        }
        search_provider = SearchProviderFactory.create(search_config)
        search_provider.initialize()
        
        stats = search_provider.get_stats()
        info = search_provider.get_provider_info()
        
        print_separator("DATABASE STATISTICS")
        print(f"Provider: {info['provider_name']}")
        print(f"Data Directory: {info['data_dir']}")
        print(f"Collection: {info['collection']}")
        print(f"Total Documents: {stats.get('documents', 0)}")
        
        return search_provider
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_user_chunks(search_provider, user_id):
    """Get all chunks for a specific user"""
    try:
        chunks = search_provider.get_all_chunks_for_user(user_id)
        
        print_separator(f"CHUNKS FOR USER: {user_id}")
        print(f"✓ Found {len(chunks)} chunks\n")
        
        if chunks:
            # Group by source file
            by_file = {}
            for chunk in chunks:
                source = chunk.get('source_file', 'unknown')
                if source not in by_file:
                    by_file[source] = []
                by_file[source].append(chunk)
            
            # Display by file
            for source_file, file_chunks in by_file.items():
                print(f"\n📄 {source_file}: {len(file_chunks)} chunks")
                print(f"   File Type: {file_chunks[0].get('file_type', 'unknown')}")
                print(f"   Section: {file_chunks[0].get('section', 'unknown')}")
                print(f"   Category: {file_chunks[0].get('category', 'unknown')}")
                
                # Show chunk preview
                for i, chunk in enumerate(file_chunks[:2], 1):
                    content = chunk.get('content', '')
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"     Chunk {i}: {preview}")
        
        return chunks
    except Exception as e:
        print(f"❌ Error retrieving chunks: {e}")
        import traceback
        traceback.print_exc()
        return []

def export_chunks_to_json(search_provider, user_id, output_file):
    """Export all chunks for a user to JSON file"""
    try:
        chunks = search_provider.get_all_chunks_for_user(user_id)
        
        output_data = {
            "user_id": user_id,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print_separator(f"EXPORT COMPLETE")
        print(f"✓ Exported {len(chunks)} chunks to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error exporting: {e}")
        import traceback
        traceback.print_exc()

def search_chunks_by_content(search_provider, user_id, keyword):
    """Search chunks by keyword"""
    try:
        chunks = search_provider.get_all_chunks_for_user(user_id)
        
        matching_chunks = []
        for chunk in chunks:
            content = chunk.get('content', '').lower()
            if keyword.lower() in content:
                matching_chunks.append(chunk)
        
        print_separator(f"SEARCH RESULTS: '{keyword}'")
        print(f"✓ Found {len(matching_chunks)} matching chunks\n")
        
        for i, chunk in enumerate(matching_chunks, 1):
            print(f"Match {i}:")
            print(f"  Source: {chunk.get('source_file', 'unknown')}")
            print(f"  Category: {chunk.get('category', 'unknown')}")
            content = chunk.get('content', '')
            print(f"  Content: {content[:150]}...")
            print()
        
        return matching_chunks
        
    except Exception as e:
        print(f"❌ Error searching: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Main function"""
    print_separator("ChromaDB Data Extraction Utility")
    
    # Get database stats
    search_provider = get_database_stats()
    if not search_provider:
        return
    
    user_id = "test_user_001"
    
    # Option 1: View chunks in console
    print("\n1️⃣  Viewing chunks in console...")
    chunks = get_user_chunks(search_provider, user_id)
    
    # Option 2: Export to JSON
    print("\n2️⃣  Exporting to JSON...")
    output_file = f"/home/myid/ps47974/ezcommonapp/full-web-app-1123/ezcommon-backend/simple_tests_v2/exported_chunks_{user_id}.json"
    export_chunks_to_json(search_provider, user_id, output_file)
    
    # Option 3: Search by keyword
    print("\n3️⃣  Searching for keyword 'education'...")
    search_chunks_by_content(search_provider, user_id, "education")
    
    print_separator("Done!")

if __name__ == "__main__":
    main()
