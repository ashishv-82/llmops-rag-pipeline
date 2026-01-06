from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from api.services.ingestion_service import ingest_document
from api.services.s3_service import s3_service
import PyPDF2
import io

""" Router for document upload and processing """

router = APIRouter()

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Check size (FastAPI doesn't provide size directly, check in memory)
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

def parse_document(file: UploadFile, content_bytes: bytes) -> str:
    """Parse document based on file type"""
    ext = file.filename.split('.')[-1].lower()
    
    if ext == 'txt':
        return content_bytes.decode('utf-8')
    
    elif ext == 'pdf':
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif ext == 'docx':
        # TODO: Implement DOCX parsing with python-docx
        raise HTTPException(status_code=501, detail="DOCX parsing not yet implemented")
    
    return ""

@router.post("/upload")
async def upload_document(
    file: UploadFile, 
    background_tasks: BackgroundTasks,
    domain: str = "general"
):
    # Validate file
    validate_file(file)
    
    # Read content
    content_bytes = await file.read()
    
    # Parse document
    text_content = parse_document(file, content_bytes)
    
    # Upload to S3
    s3_key = f"documents/{domain}/{file.filename}"
    s3_service.upload_file(content_bytes, s3_key)
    
    # Process in background (async)
    background_tasks.add_task(
        ingest_document, 
        file.filename, 
        text_content, 
        {
            "domain": domain, 
            "source": "web_upload",
            "s3_key": s3_key
        }
    )
    
    return {
        "status": "processing", 
        "filename": file.filename,
        "s3_key": s3_key
    }