"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""





from django.urls import path, include, re_path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', views.custom_login_view, name='login'),
    path('social-login-error/', views.social_login_error, name='social_login_error'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.EditProfileView.as_view(), name='edit_profile'),
    # path('password-reset/', views.CustomPasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    # path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    # path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    # re_path(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', views.CustomPasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    # path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # path('', include('django.contrib.auth.urls')),
   
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html', 
        email_template_name='registration/password_reset_email.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    # re_path(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ),  name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),    
]

