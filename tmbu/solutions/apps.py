"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""

from django.apps import AppConfig

class SolutionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'solutions'

    def ready(self):
        #import solutions.signals
        pass

        


    