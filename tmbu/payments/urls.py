"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('subscription-plan/', views.subscription_plan, name='subscription_plan'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('subscribe-success/', views.subscribe_success, name='subscribe_success'),
    path('subscribe-cancel/', views.subscribe_cancel, name='subscribe_cancel'),
    path('manage-subscription/', views.manage_subscription, name='manage_subscription'),
    path('customer-portal/', views.stripe_customer_portal, name='stripe_customer_portal'),
    #path('check-subscription/', views.check_subscription_status, name='check_subscription_status'),
]
