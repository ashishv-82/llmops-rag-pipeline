import boto3
import requests
import argparse
from pathlib import Path

def sync_documents(files_list: str, bucket: str, api_url: str):
    s3 = boto3.client('s3')
    
    with open(files_list, 'r') as f:
        files = [line.strip() for line in f if line.strip()]
    
    for file_path in files:
        path = Path(file_path)
        
        # Determine domain from directory structure
        # e.g., data/documents/legal/policy.pdf -> domain=legal
        parts = path.parts
        domain = parts[2] if len(parts) > 2 else 'general'
        
        # Upload to S3
        s3_key = f"documents/{domain}/{path.name}"
        print(f"Uploading {file_path} to s3://{bucket}/{s3_key}")
        
        s3.upload_file(str(path), bucket, s3_key)
        
        # Trigger API ingestion
        with open(file_path, 'rb') as file_data:
            response = requests.post(
                f"{api_url}/documents/upload",
                files={'file': file_data},
                params={'domain': domain}
            )
            
            if response.status_code == 200:
                print(f"✅ {path.name} processed successfully")
            else:
                print(f"❌ {path.name} failed: {response.text}")
                raise Exception(f"Upload failed for {path.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', required=True)
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--api-url', required=True)
    args = parser.parse_args()
    
    sync_documents(args.files, args.bucket, args.api_url)