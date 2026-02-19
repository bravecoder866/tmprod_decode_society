"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



import os
import logging
from django.contrib import admin
from .models import Scenario, CorekbUpload, ScenarioForMining, ScenarioActors, ScenarioDynamics, ScenarioNeeds, ScenarioSkillsResources, ScenarioAnalysisPrediction, ScenarioQuickSolution, Actors, IndividualTraits, GroupTraits, IndividualProfile, GroupProfile, Interactions, InteractionRelations, GlobalActorsProfiles, SocialNetworkGraphCache, GeneratedSimulation, LiveSimulation
from django.contrib import messages
from .corekb_milvus_setup_utils import process_text, generate_insert_kb_embeddings_into_milvus
from .milvus_connection_utils import ensure_connection
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.html import format_html
from pymilvus import MilvusClient

logger = logging.getLogger(__name__)


# Register your models here.
admin.site.register(Scenario)
admin.site.register(ScenarioQuickSolution)
admin.site.register(ScenarioForMining)
admin.site.register(ScenarioActors)
admin.site.register(ScenarioDynamics)
admin.site.register(ScenarioNeeds)
admin.site.register(ScenarioSkillsResources)
admin.site.register(ScenarioAnalysisPrediction)
admin.site.register(Actors)
admin.site.register(IndividualTraits)
admin.site.register(GroupTraits)
admin.site.register(IndividualProfile)
admin.site.register(GroupProfile)
admin.site.register(Interactions)
admin.site.register(InteractionRelations)
admin.site.register(GlobalActorsProfiles)
admin.site.register(SocialNetworkGraphCache)
admin.site.register(GeneratedSimulation)
admin.site.register(LiveSimulation)



#@ensure_connection
@admin.register(CorekbUpload)
class CorekbUploadAdmin(admin.ModelAdmin):
    list_display = ('name', 'upload_date', 'is_inserted', 'file_link')
    readonly_fields = ('is_inserted',)

    # Add a custom link to view the file
    def file_link(self, obj):
        if obj.file:
            return format_html("<a href='{}' target='_blank'>{}</a>", obj.file.url, obj.file.name)
        return "No file uploaded"
    file_link.short_description = "Uploaded File"

    # Override save_model to process the file
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)  # Save the uploaded file

        # Process the uploaded file if not already processed
        if not obj.is_inserted and obj.file:
            try:
                # Use obj.file.path to get the absolute file path
                file_path = obj.file.path
                          
                # Ensure the file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"The file {file_path} does not exist.")
               
                # Step 1: Process text from uploaded files
                cleaned_factor_texts = process_text(file_path)
                
                # Step 2: Generate and insert embeddings to the collection
                generate_insert_kb_embeddings_into_milvus(cleaned_factor_texts)
                
                # Step 3: Mark the file as inserted
                obj.is_inserted = True
                obj.save()
            
                self.message_user(request, f"File {obj.file.name} processed successfully.", level="success")
            except Exception as e:
                logging.error(f"Error processing file {obj.file.name}: {e}")
                self.message_user(request, f"Error processing file: {e}", level="error")


#@ensure_connection
@admin.action(description="Retry processing unembedded uploads")
def retry_unprocessed_uploads(modeladmin, request, queryset):
    
    unprocessed_uploads = queryset.filter(is_inserted=False)
    if not unprocessed_uploads.exists():
        modeladmin.message_user(request, "No uninserted uploads to process.", level="info")
        return

    success_count = 0
    errors = []

    for upload in unprocessed_uploads:
        try:
            
            file_path = upload.file.path
    
            # Step 1: Process text from uploaded files
            cleaned_factor_texts = process_text(file_path)
                
            # Step 2: Generate and insert embeddings to the collection
            generate_insert_kb_embeddings_into_milvus(cleaned_factor_texts)
                
            upload.is_inserted = True
            success_count += 1
        except Exception as e:
            error_message(f"{upload.file.name}: {e}")
            errors.append(error_message)
            logging.error(error_message)

    if success_count:
        modeladmin.message_user(request, f"Successfully processed {success_count} uploads.", level="success")
    if errors:
        modeladmin.message_user(request, f"Errors occurred: {', '.join(errors)}", level="error")
