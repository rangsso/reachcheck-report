"""
Example: Using Supabase RAG Database for ReachCheck

This example demonstrates how to integrate the RAG database into
the ReachCheck workflow for storing and retrieving review data.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import our modules
from src.rag_database import get_rag_db
from src.supabase_client import test_connection

# Load environment variables
load_dotenv()


def example_embedding_generation(text: str) -> List[float]:
    """
    Generate a mock embedding for demonstration.
    
    In production, use OpenAI's text-embedding-ada-002:
    
    from openai import OpenAI
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding
    """
    # Mock embedding (1536 dimensions for ada-002)
    # This is just for demonstration - use real embeddings in production!
    import random
    random.seed(hash(text) % (2**32))
    return [random.random() for _ in range(1536)]


def example_store_reviews():
    """
    Example: Store reviews in the RAG database with embeddings
    """
    print("=== Example: Storing Reviews ===\n")
    
    # Initialize RAG database with admin client
    db = get_rag_db(use_admin=True)
    
    # Sample reviews
    sample_reviews = [
        {
            "text": "떡볶이가 정말 맛있어요! 최고입니다.",
            "rating": 5,
            "source": "google_reviews"
        },
        {
            "text": "직원분들이 친절하고 매장이 깨끗해요",
            "rating": 4,
            "source": "naver_reviews"
        },
        {
            "text": "가격대비 양이 많고 맛도 좋습니다",
            "rating": 5,
            "source": "google_reviews"
        }
    ]
    
    # Store each review (in production, you'd generate real embeddings)
    for review in sample_reviews:
        try:
            # Generate embedding (mock for now)
            embedding = example_embedding_generation(review["text"])
            
            # Store in database
            result = db.insert_document(
                content=review["text"],
                embedding=embedding,
                metadata={
                    "rating": review["rating"],
                    "business_id": "example_business_123"
                },
                source=review["source"],
                document_type="review"
            )
            
            print(f"✓ Stored review: '{review['text'][:50]}...'")
            print(f"  Document ID: {result.get('id')}")
            print()
            
        except Exception as e:
            print(f"✗ Error storing review: {str(e)}")
            print(f"  Note: Make sure you've created the 'documents' table in Supabase")
            print(f"  See RAG_ARCHITECTURE.md for setup instructions")
            break


def example_search_similar_reviews():
    """
    Example: Search for similar reviews using vector similarity
    """
    print("\n=== Example: Searching Similar Reviews ===\n")
    
    # Initialize RAG database
    db = get_rag_db(use_admin=False)  # read-only operations
    
    # Query text
    query = "음식이 맛있나요?"
    
    try:
        # Generate query embedding (mock for now)
        query_embedding = example_embedding_generation(query)
        
        # Search for similar documents
        similar_docs = db.search_similar_documents(
            query_embedding=query_embedding,
            limit=5,
            threshold=0.5
        )
        
        print(f"Query: '{query}'")
        print(f"Found {len(similar_docs)} similar reviews:\n")
        
        for i, doc in enumerate(similar_docs, 1):
            print(f"{i}. {doc.get('content')}")
            print(f"   Similarity: {doc.get('similarity', 'N/A')}")
            print(f"   Source: {doc.get('source')}")
            print()
            
    except Exception as e:
        print(f"✗ Search error: {str(e)}")
        print(f"  Note: Vector search requires the 'match_documents' function")
        print(f"  See RAG_ARCHITECTURE.md for setup instructions")


def example_list_recent_documents():
    """
    Example: List recent documents
    """
    print("\n=== Example: Listing Recent Documents ===\n")
    
    db = get_rag_db(use_admin=False)
    
    try:
        docs = db.list_documents(limit=5)
        
        print(f"Found {len(docs)} recent documents:\n")
        
        for doc in docs:
            print(f"• {doc.get('content', 'N/A')[:60]}...")
            print(f"  Type: {doc.get('document_type')} | Source: {doc.get('source')}")
            print(f"  ID: {doc.get('id')}")
            print()
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")


def main():
    """
    Run all examples
    """
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     Supabase RAG Integration Examples for ReachCheck     ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    # Test connection first
    print("Testing Supabase connection...\n")
    results = test_connection()
    
    if not results["regular_client"] or not results["admin_client"]:
        print("✗ Connection test failed!")
        if results["errors"]:
            for error in results["errors"]:
                print(f"  {error}")
        return
    
    print("✓ Both clients connected successfully!\n")
    print("-" * 60)
    
    # List existing documents
    example_list_recent_documents()
    
    print("-" * 60)
    
    # Note about database setup
    print("\n📝 Next Steps:")
    print("1. Create the 'documents' table in Supabase using the SQL from RAG_ARCHITECTURE.md")
    print("2. Uncomment the store and search examples below")
    print("3. Replace mock embeddings with real OpenAI embeddings")
    print("4. Integrate into collector.py and analyzer.py workflows\n")
    
    # Uncomment these when your database is ready:
    # example_store_reviews()
    # example_search_similar_reviews()


if __name__ == "__main__":
    main()
