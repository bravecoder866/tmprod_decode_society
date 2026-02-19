"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription')
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    subscription_item_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_status = models.CharField(
        max_length=50,
        choices=[
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),  # Other Stripe statuses
        ('incomplete_expired', 'Incomplete Expired'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),   
    ],
    blank=True,
    null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Subscription of {self.user.username} - {self.subscription_status}"




