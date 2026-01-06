import uuid
from api.utils.chunking import chunk_text
from api.services.vector_store import vector_store

""" Service for processing and indexing documents into the vector store """

async def ingest_document(filename: str, content: str, metadata: dict):
    # Split document into manageable chunks
    chunks = chunk_text(content)
    
    # Generate unique IDs and metadata for each chunk
    ids = [f"{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{**metadata, "chunk_index": i} for i in range(len(chunks))]
    
    # Add chunks to vector store with embeddings
    vector_store.add_documents(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)