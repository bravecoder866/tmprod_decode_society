"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



import os
#import uuid
import logging
import re
import nltk
from nltk.tokenize import sent_tokenize
from pymilvus import MilvusClient, connections, db, Collection, CollectionSchema, FieldSchema, DataType
from .milvus_llm_utils import generate_embeddings
from .milvus_connection_utils import ensure_milvus_connection, ensure_connection
from functools import wraps
from django.conf import settings

logger = logging.getLogger(__name__)


#clean and chunk text
def clean_text(text):
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r"[^a-zA-Z0-9\s,.!?'-]", '', text)  # Remove special characters (you can adjust this based on requirements)
    text = text.strip()  # Remove leading/trailing whitespace
    return text


def chunk_text(text, max_length=550):
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    sentences = sent_tokenize(text)  # Split text into sentences
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        #sentence = sentence.strip()

        # If a single sentence is too long, split it into smaller parts
        #if len(sentence) > max_length:
        #    for i in range(0, len(sentence), max_length):
        #        chunks.append(sentence[i:i + max_length])  # Split at max_length
        #else:
            # Check if adding the sentence exceeds the max length
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())  # Save the current chunk
            current_chunk = sentence  # Start a new chunk with the current sentence

    # Append any remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def process_text(file_path):
    try:
        # Read the entire file content as a single string
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        raise IOError(f"Failed to read file {file_path}") from e
    
    
    # Clean and chunk
    cleaned_text = clean_text(text)
    cleaned_text_chunks = chunk_text(cleaned_text)
    
    return cleaned_text_chunks


      
# Function to create a collection in Milvus (for both development and production);uncomment later.
@ensure_connection
def create_milvus_kb_collection(milvus_client=None):
    if milvus_client is None:
        raise ConnectionError("Milvus client not provided by decorator.") # Safeguard
    
    #milvus_client = ensure_milvus_connection()
    
    collection_name = "kb_embeddings_collection"

    existing_collections = milvus_client.list_collections()

    if collection_name not in existing_collections:

    #if collection_name in existing_collections:
    #    milvus_client.drop_collection(collection_name)
    #    print(f"Dropped existing collection '{collection_name}' to apply schema changes.")      
              
        # Create schema
        schema = milvus_client.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )

        # Add fields to schema
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="factor_vector", datatype=DataType.FLOAT_VECTOR, dim=384)
        schema.add_field(field_name="factor_text", datatype=DataType.VARCHAR, max_length=2000)

        # Create collection
        milvus_client.create_collection(
        collection_name=collection_name, 
        schema=schema, 
        )

        print(f"Collection '{collection_name}' created successfully!")
    else:
        print(f"Collection '{collection_name}' already exists.")


    # create index
    index_params = milvus_client.prepare_index_params()

    index_params.add_index(
        field_name="id",
        index_type="AUTOINDEX"
    )

    index_params.add_index(
        field_name="factor_vector",
        metric_type="COSINE",
        index_type="IVF_FLAT",
        index_name="vector_index",
        params={ "nlist": 128 }
    )

    milvus_client.create_index(
        collection_name=collection_name,
        index_params=index_params,
        sync=True # Whether to wait for index creation to complete before returning. Defaults to True.
    )
            
    print(f"Index created successfully for '{collection_name}'!")




#def generate_uuid():
#    """Generates a UUID for each entry."""
#    return uuid.uuid4().int >> 64


# Generate and insert kb embeddings into the kb collection
@ensure_connection
def generate_insert_kb_embeddings_into_milvus(cleaned_factor_texts, milvus_client=None):
    if milvus_client is None:
        raise ConnectionError("Milvus client not provided by decorator.") # Safeguard
    
    # milvus_client = ensure_milvus_connection()
    
    try:
        #step 1: generate embeddings
        kb_embeddings = generate_embeddings(cleaned_factor_texts)

        #step 2: generate unique IDs
        #ids = [generate_uuid() for _ in range(len(cleaned_factor_texts))]
    
        #step 3: create collection if it doesn't exist
        create_milvus_kb_collection()

        #step 4: load the collection (not necessary for data insertion, only required for search/query)
        #milvus_client.load_collection("kb_embeddings_collection")

        #step 5: prepare data for insertion    
        data_to_insert = [{
                # "id":i,
                "factor_vector": kb_embeddings[i], # List of embeddings
                "factor_text": cleaned_factor_texts[i] # List of original text paragraphs
        }
        for i in range(len(kb_embeddings))
        ]
   
        
        #step 6: insert the data into the collection
        milvus_client.insert("kb_embeddings_collection", data_to_insert)
    
        logging.info(f"Inserted {len(cleaned_factor_texts)} records into 'kb_embeddings_collection'")

    except Exception as e:
        logging.error(f"Error during Milvus insertion: {e}")
        raise
        