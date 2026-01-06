import chromadb
from chromadb.config import Settings
from api.services.embedding_service import embedding_service
from rank_bm25 import BM25Okapi
import numpy as np

class VectorStore:
    def __init__(self, host="vectordb-service", port=8000):
        self.host = host
        self.port = port
        self._client = None
        self._collection = None
        self.bm25 = None
        self.documents_cache = []
    
    @property
    def client(self):
        """Lazy connection to ChromaDB"""
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(
                    host=self.host, 
                    port=self.port,
                    settings=Settings(allow_reset=True, anonymized_telemetry=False)
                )
            except Exception as e:
                print(f"Warning: Could not connect to ChromaDB at {self.host}:{self.port} - {e}")
                raise
        return self._client
    
    @property
    def collection(self):
        """Lazy collection initialization"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection("rag_docs")
        return self._collection
    
    def add_documents(self, documents: list, metadatas: list, ids: list):
        # Generate embeddings in batch
        embeddings = [embedding_service.generate_embedding(doc) for doc in documents]
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Update BM25 index
        self._rebuild_bm25_index()
    
    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from all documents"""
        all_docs = self.collection.get()
        self.documents_cache = all_docs['documents']
        
        if not self.documents_cache:
            self.bm25 = None
            return

        tokenized_docs = [doc.lower().split() for doc in self.documents_cache]
        self.bm25 = BM25Okapi(tokenized_docs)
    
    def hybrid_search(self, query: str, top_k=5, filter=None, alpha=0.5):
        """
        Hybrid search combining vector similarity and BM25.
        alpha: weight for vector search (1-alpha for BM25)
        """
        # Vector search
        query_embedding = embedding_service.generate_embedding(query)
        vector_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get more candidates
            where=filter
        )
        
        # BM25 search
        if self.bm25 is None:
            self._rebuild_bm25_index()
        
        if self.bm25 is None:
            # Fallback to vector-only results if BM25 not available
            return self.collection.get(ids=vector_results['ids'][0])

        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Combine scores using Reciprocal Rank Fusion
        combined_scores = {}
        
        # Add vector scores
        for idx, (doc_id, distance) in enumerate(zip(
            vector_results['ids'][0], 
            vector_results['distances'][0]
        )):
            # Convert distance to similarity (lower is better)
            similarity = 1 / (1 + distance)
            combined_scores[doc_id] = alpha * similarity
        
        # Add BM25 scores
        for idx, (doc_id, score) in enumerate(zip(
            vector_results['ids'][0],
            bm25_scores
        )):
            if doc_id in combined_scores:
                combined_scores[doc_id] += (1 - alpha) * score
        
        # Sort and return top_k
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Fetch full results
        final_ids = [doc_id for doc_id, _ in sorted_ids]
        return self.collection.get(ids=final_ids)
    
    def search(self, query: str, top_k=5, filter=None):
        """Fallback to vector-only search"""
        query_embedding = embedding_service.generate_embedding(query)
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter
        )

vector_store = VectorStore()