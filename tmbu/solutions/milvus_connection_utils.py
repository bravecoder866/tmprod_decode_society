"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""

from pymilvus import MilvusClient
from functools import wraps
from django.conf import settings

#Function to connect to Milvus. For production, connect to Milvus Standalone using URI and token
def ensure_milvus_connection():
    try:
        milvus_client = MilvusClient(uri=settings.MILVUS_URI, token=settings.MILVUS_TOKEN)
        print("Connected to Milvus Standalone")
        return milvus_client

    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        raise

def ensure_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        milvus_client = None # Initialize to None in case connection fails immediately
        
        try:
            milvus_client = ensure_milvus_connection()

            # Pass the milvus_client as a keyword argument to the decorated function
            return func(*args, milvus_client=milvus_client, **kwargs)
        finally:
            if milvus_client:  # Check if milvus_client is not None
                try:
                    milvus_client.close()
                except Exception as e:
                    print(f"Error closing Milvus connection: {e}")    
    return wrapper