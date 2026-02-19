"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, UserFreeTrial, UserFreeTrialScenarioMining, UserFreeTrialQuickSolution


#Create a user profile when a new user is created and active
@receiver(post_save, sender=User)
def create_user_profile_on_activation(sender, instance, created, **kwargs):
    if not created and instance.is_active:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Ensure the Profile is saved whenever the User is saved, if it exists.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


#Create user free trial when its user profile is created.
@receiver(post_save, sender=Profile)
def create_free_trial_for_new_user(sender, instance, created, **kwargs):
   
    if created:
        UserFreeTrial.objects.create(user=instance.user)
        UserFreeTrialQuickSolution.objects.create(user=instance.user)
        UserFreeTrialScenarioMining.objects.create(user=instance.user)  
        
