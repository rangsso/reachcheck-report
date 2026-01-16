"""
Supabase Client Module for ReachCheck

This module provides Supabase client initialization with dual client architecture:
- Regular client (anon key): For general read operations
- Admin client (service_role key): For RAG operations requiring write/modify permissions
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global client instances
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the regular Supabase client using ANON_KEY.
    
    This client is used for general read operations and respects
    Row Level Security (RLS) policies.
    
    Returns:
        Client: Initialized Supabase client
        
    Raises:
        ValueError: If required environment variables are missing
    """
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError(
                "Missing required environment variables: SUPABASE_URL and/or SUPABASE_ANON_KEY"
            )
        
        _supabase_client = create_client(url, key)
        print(f"✓ Supabase regular client initialized: {url}")
    
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get or create the admin Supabase client using SERVICE_ROLE_KEY.
    
    This client has elevated permissions and bypasses Row Level Security (RLS).
    Use this client for RAG operations that require document insertion,
    modification, or deletion.
    
    ⚠️ WARNING: This client has full database access. Use with caution.
    
    Returns:
        Client: Initialized Supabase admin client
        
    Raises:
        ValueError: If required environment variables are missing
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError(
                "Missing required environment variables: SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY"
            )
        
        _supabase_admin_client = create_client(url, key)
        print(f"✓ Supabase admin client initialized: {url}")
    
    return _supabase_admin_client


def test_connection() -> dict:
    """
    Test both Supabase client connections.
    
    Returns:
        dict: Connection test results
    """
    results = {
        "regular_client": False,
        "admin_client": False,
        "errors": []
    }
    
    try:
        client = get_supabase_client()
        # Simple health check - attempt to get storage buckets
        client.storage.list_buckets()
        results["regular_client"] = True
    except Exception as e:
        results["errors"].append(f"Regular client error: {str(e)}")
    
    try:
        admin_client = get_supabase_admin_client()
        # Simple health check - attempt to get storage buckets
        admin_client.storage.list_buckets()
        results["admin_client"] = True
    except Exception as e:
        results["errors"].append(f"Admin client error: {str(e)}")
    
    return results


if __name__ == "__main__":
    """Test the Supabase client connections"""
    print("Testing Supabase connections...\n")
    
    results = test_connection()
    
    print("\n=== Connection Test Results ===")
    print(f"Regular Client: {'✓ Connected' if results['regular_client'] else '✗ Failed'}")
    print(f"Admin Client: {'✓ Connected' if results['admin_client'] else '✗ Failed'}")
    
    if results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  - {error}")
    else:
        print("\n✓ All connections successful!")
