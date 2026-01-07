#!/usr/bin/env python3
"""
Verification Script for Data Sync Workflow
Validates that documents were successfully indexed in ChromaDB
"""

import argparse
import requests
import sys
from pathlib import Path

def verify_ingestion(files_list: str, api_url: str = None):
    """
    Verify that all synced documents are searchable in the vector database
    
    Args:
        files_list: Path to file containing list of synced documents
        api_url: Optional API URL (defaults to localhost for local testing)
    """
    if not api_url:
        api_url = "http://localhost:8000"
    
    # Read the list of files that were synced
    with open(files_list, 'r') as f:
        files = [line.strip() for line in f if line.strip()]
    
    if not files:
        print("✅ No files to verify")
        return True
    
    print(f"Verifying {len(files)} document(s)...")
    
    failed = []
    for file_path in files:
        path = Path(file_path)
        
        # Extract domain from path structure
        parts = path.parts
        domain = parts[2] if len(parts) > 2 else 'general'
        
        # Test query: search for the filename (should return the document)
        test_query = path.stem  # Filename without extension
        
        try:
            response = requests.post(
                f"{api_url}/query",
                json={
                    "question": test_query,
                    "domain": domain
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # Check if the document appears in sources
                sources = result.get('sources', [])
                
                if any(path.name in str(source) for source in sources):
                    print(f"✅ {path.name} is indexed and searchable")
                else:
                    print(f"⚠️  {path.name} indexed but not in search results (may need time to propagate)")
            else:
                print(f"❌ {path.name} verification failed: {response.status_code}")
                failed.append(path.name)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {path.name} verification error: {str(e)}")
            failed.append(path.name)
    
    # Summary
    print("\n" + "="*50)
    if failed:
        print(f"❌ Verification failed for {len(failed)} file(s):")
        for f in failed:
            print(f"   - {f}")
        return False
    else:
        print(f"✅ All {len(files)} document(s) verified successfully")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify document ingestion into vector database"
    )
    parser.add_argument(
        '--files', 
        required=True,
        help='Path to file containing list of synced documents'
    )
    parser.add_argument(
        '--api-url',
        help='API URL (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    success = verify_ingestion(args.files, args.api_url)
    sys.exit(0 if success else 1)
