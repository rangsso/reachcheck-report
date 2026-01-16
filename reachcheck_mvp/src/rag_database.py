"""
RAG Database Module for ReachCheck

This module provides database access layer for RAG-related operations,
including document storage, retrieval, and vector similarity search using pgvector.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import Client
from .supabase_client import get_supabase_admin_client, get_supabase_client


class RAGDatabase:
    """
    Database access layer for RAG operations.
    
    This class provides methods for:
    - Inserting documents with embeddings
    - Searching documents by similarity
    - Managing document lifecycle
    """
    
    def __init__(self, use_admin: bool = True):
        """
        Initialize RAG database access.
        
        Args:
            use_admin: If True, use admin client for write operations.
                      If False, use regular client (read-only).
        """
        self.client: Client = get_supabase_admin_client() if use_admin else get_supabase_client()
        self.table_name = "documents"
    
    def insert_document(
        self,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Insert a document with its embedding into the database.
        
        Args:
            content: The text content of the document
            embedding: Vector embedding of the document (e.g., from OpenAI)
            metadata: Optional metadata (JSON object)
            source: Source identifier (e.g., 'google_reviews', 'naver_place')
            document_type: Type of document (e.g., 'review', 'business_info')
        
        Returns:
            dict: Inserted document data
            
        Raises:
            Exception: If insertion fails
        """
        document_data = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "source": source,
            "document_type": document_type,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = self.client.table(self.table_name).insert(document_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            raise Exception(f"Failed to insert document: {str(e)}")
    
    def insert_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Insert multiple documents in a single batch operation.
        
        Args:
            documents: List of document dictionaries with keys:
                      - content (str)
                      - embedding (List[float])
                      - metadata (dict, optional)
                      - source (str, optional)
                      - document_type (str, optional)
        
        Returns:
            list: Inserted document data
            
        Raises:
            Exception: If batch insertion fails
        """
        # Add timestamps to all documents
        for doc in documents:
            doc.setdefault("created_at", datetime.utcnow().isoformat())
            doc.setdefault("metadata", {})
        
        try:
            response = self.client.table(self.table_name).insert(documents).execute()
            return response.data if response.data else []
        except Exception as e:
            raise Exception(f"Failed to insert documents batch: {str(e)}")
    
    def search_similar_documents(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query embedding using pgvector.
        
        Args:
            query_embedding: Vector embedding of the query
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0-1)
            filters: Optional filters (e.g., {'source': 'google_reviews'})
        
        Returns:
            list: List of similar documents with similarity scores
            
        Note:
            This method requires a pgvector similarity search function
            to be created in your Supabase database. See RAG_ARCHITECTURE.md
            for setup instructions.
        """
        try:
            # Use Supabase RPC to call the vector similarity function
            # This assumes you have created a function like 'match_documents' in Supabase
            query_params = {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit
            }
            
            # Add filters if provided
            if filters:
                query_params.update(filters)
            
            response = self.client.rpc("match_documents", query_params).execute()
            return response.data if response.data else []
        except Exception as e:
            # If the RPC function doesn't exist yet, return empty list with warning
            print(f"Warning: Vector search not available yet. Error: {str(e)}")
            return []
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID.
        
        Args:
            document_id: The document ID
        
        Returns:
            dict or None: Document data if found
        """
        try:
            response = self.client.table(self.table_name).select("*").eq("id", document_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error retrieving document: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            document_id: The document ID to delete
        
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.client.table(self.table_name).delete().eq("id", document_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            return False
    
    def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents with optional filtering.
        
        Args:
            filters: Optional filters (e.g., {'source': 'google_reviews'})
            limit: Maximum number of results
            offset: Number of results to skip (for pagination)
        
        Returns:
            list: List of documents
        """
        try:
            query = self.client.table(self.table_name).select("*")
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # Apply pagination
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error listing documents: {str(e)}")
            return []


# Convenience function for quick access
def get_rag_db(use_admin: bool = True) -> RAGDatabase:
    """
    Get a RAGDatabase instance.
    
    Args:
        use_admin: If True, use admin client for write operations
    
    Returns:
        RAGDatabase: Initialized database access object
    """
    return RAGDatabase(use_admin=use_admin)


if __name__ == "__main__":
    """Test the RAG database connection"""
    print("Testing RAG Database connection...\n")
    
    try:
        # Initialize with admin client
        db = get_rag_db(use_admin=True)
        print("✓ RAG Database initialized successfully")
        
        # Try to list documents (this will work even if table doesn't exist yet)
        print("\nAttempting to list documents...")
        docs = db.list_documents(limit=5)
        print(f"✓ Found {len(docs)} documents in database")
        
        if docs:
            print("\nSample document:")
            print(f"  ID: {docs[0].get('id')}")
            print(f"  Type: {docs[0].get('document_type')}")
            print(f"  Source: {docs[0].get('source')}")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("\nNote: If the 'documents' table doesn't exist yet, you'll need to create it in Supabase.")
        print("See RAG_ARCHITECTURE.md for database setup instructions.")
