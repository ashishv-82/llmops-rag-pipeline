"""Service for processing and indexing documents into the vector store."""

from api.utils.chunking import chunk_text
from api.services.vector_store import vector_store


async def ingest_document(filename: str, content: str, metadata: dict):
    """
    Ingest a document by chunking, embedding, and storing it.

    Args:
        filename: Name of the file
        content: Text content of the document
        metadata: Additional metadata (e.g. content_type)

    Returns:
        Number of chunks indexed
    """
    # Split document into manageable chunks
    chunks = chunk_text(content)

    # Generate unique IDs and metadata for each chunk
    ids = [f"{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{**metadata, "chunk_index": i} for i in range(len(chunks))]

    # Add chunks to vector store with embeddings
    vector_store.add_documents(documents=chunks, metadatas=metadatas, ids=ids)
    return len(chunks)
