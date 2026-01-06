import boto3
from api.config import settings

""" Service for managing document storage in AWS S3 """

class S3Service:
    # Initialize S3 client and target bucket
    def __init__(self):
        self.client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket = settings.documents_bucket
    
    # Upload binary content to specific S3 key
    def upload_file(self, content: bytes, key: str):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content
        )
    
    # Retrieve file content from S3 as bytes
    def download_file(self, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key
        )
        return response['Body'].read()

# Shared instance for S3 operations
s3_service = S3Service()