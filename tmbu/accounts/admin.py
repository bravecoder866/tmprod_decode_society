"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django.contrib import admin
from .models import Profile, UserFreeTrial, UserFreeTrialScenarioMining, UserFreeTrialQuickSolution

# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'create_date', 'update_date')
    

admin.site.register(UserFreeTrial)
admin.site.register(UserFreeTrialScenarioMining)
admin.site.register(UserFreeTrialQuickSolution)