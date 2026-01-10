#!/usr/bin/env python3
import requests
import sys
import os
import time
import argparse
from pathlib import Path

def wait_for_api(api_url: str, timeout: int = 60):
    """Block until API is healthy"""
    print(f"⏳ Waiting for API at {api_url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{api_url}/health")
            if response.status_code == 200:
                print("✅ API is ready!")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    
    print("❌ API failed to become ready.")
    sys.exit(1)

def seed_data(file_path: str, domain: str = "history", api_url: str = "http://localhost:8000"):
    """Upload document to RAG API"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
        
    print(f"📤 Seeding data from {path.name} (Domain: {domain})...")
    
    with open(path, 'rb') as f:
        files = {'file': (path.name, f, 'application/pdf')}
        params = {'domain': domain}
        
        try:
            response = requests.post(f"{api_url}/documents/upload", files=files, params=params)
            
            if response.status_code == 200:
                print(f"✅ Successfully ingested {path.name}!")
                print(f"👉 S3 Key: {response.json().get('s3_key')}")
                print(f"👉 Status: {response.json().get('status')}")
            else:
                print(f"❌ Upload failed: {response.text}")
                sys.exit(1)
        
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed RAG with initial documents")
    parser.add_argument("file_path", help="Path to PDF/TXT file to upload")
    parser.add_argument("--domain", default="history", help="Domain tag for the document")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    wait_for_api(args.url)
    seed_data(args.file_path, args.domain, args.url)
