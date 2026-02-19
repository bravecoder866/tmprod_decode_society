"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django.db import models
from django.contrib.auth.models import User
from django.conf import settings  # For dynamic user model import

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
#   image = models.ImageField(default='default.jpg', upload_to='profile_pics')
#   bio = models.TextField(max_length=500, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the profile is created
    update_date = models.DateTimeField(auto_now=True)  # Automatically set the date when the profile is updated
    
    def __str__(self):
        return f'{self.user.username} Profile'

   
   
class UserFreeTrial(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    has_used_free_trial = models.BooleanField(default=False)  # Tracks if the user has used the free trial
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    scenario_creation_attempts = models.PositiveIntegerField(default=0)
    # first_usage_reported = models.BooleanField(default=False)# For usage-based subscription

    def __str__(self):
        return f"{self.user.username}'s Free Trial - {'Used' if self.has_used_free_trial else 'Not Used'}"

    def activate_free_trial(self):
        
        if not self.has_used_free_trial:
            self.has_used_free_trial = True
            self.used_at = timezone.now()
            self.save()
            return True
        return False



class UserFreeTrialQuickSolution(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    has_used_free_trial = models.BooleanField(default=False)  # Tracks if the user has used the free trial
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    scenario_creation_attempts = models.PositiveIntegerField(default=0)
    # first_usage_reported = models.BooleanField(default=False) # For usage-based subscription

    def __str__(self):
        return f"{self.user.username}'s Free Trial - {'Used' if self.has_used_free_trial else 'Not Used'}"

    def activate_free_trial(self):
        
        if not self.has_used_free_trial:
            self.has_used_free_trial = True
            self.used_at = timezone.now()
            self.save()
            return True
        return False


class UserFreeTrialScenarioMining(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    has_used_free_trial = models.BooleanField(default=False)  # Tracks if the user has used the free trial
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    scenario_creation_attempts = models.PositiveIntegerField(default=0)
    # first_usage_reported = models.BooleanField(default=False) # For usage-based subscription

    def __str__(self):
        return f"{self.user.username}'s Free Trial - {'Used' if self.has_used_free_trial else 'Not Used'}"

    def activate_free_trial(self):
        
        if not self.has_used_free_trial:
            self.has_used_free_trial = True
            self.used_at = timezone.now()
            self.save()
            return True
        return False


