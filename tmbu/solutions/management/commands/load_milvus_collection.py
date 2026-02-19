"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""


from django.core.management.base import BaseCommand
from pymilvus import MilvusClient
from django.conf import settings

class Command(BaseCommand):
    help = "Loads the kb_embeddings_collection into Milvus memory"

    def handle(self, *args, **options):
        milvus_client = MilvusClient(uri=settings.MILVUS_URI, token=settings.MILVUS_TOKEN)
        milvus_client.load_collection("kb_embeddings_collection")
        self.stdout.write(self.style.SUCCESS("Milvus collection loaded and ready!"))
