"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



"""
URL configuration for tmbu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.views.i18n import set_language
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog
from payments.views import stripe_webhooks, checkout_redirect
from solutions.views import transcribe_audio_view



urlpatterns = [
    path('ad-8c7g6c2i-min/', admin.site.urls),
    path("i18n/set_language/", set_language, name="set_language"),  # Explicitly add set_language
    path('stripe-webhooks/', stripe_webhooks, name='stripe_webhooks'), #Include webhooks outside of i18n
    path("checkout-redirect/", checkout_redirect, name="checkout_redirect"),# Include checkout redirect outside of i18n
    path('transcribe-audio/', transcribe_audio_view, name='transcribe_audio'), 
    path('', include('allauth.urls')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
]


urlpatterns += i18n_patterns(
    path("accounts/", include("accounts.urls")),
    path("solutions/", include("solutions.urls")),
    path("payments/", include("payments.urls")),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),  # Landing page 
    path('privacy-policy/', TemplateView.as_view(template_name="privacy_policy.html"), name='privacy_policy'),   
    path('terms-of-use/', TemplateView.as_view(template_name="terms_of_use.html"), name='terms_of_use'),
    path('cookie-policy/', TemplateView.as_view(template_name="cookie_policy.html"), name='cookie_policy'),   
    path('about-us/', TemplateView.as_view(template_name="about_us.html"), name='about_us'),
    path('contact-us/', TemplateView.as_view(template_name="contact_us.html"), name='contact_us'),
    path('mobile-info/', TemplateView.as_view(template_name="mobile_info.html"), name='mobile_info'),
    prefix_default_language=True  # Default language (e.g., English) won't have `/en/` in the URL
)


# urlpatterns = [
#    path('admin/', admin.site.urls),
#    path("accounts/", include("accounts.urls")),
#    path("solutions/", include("solutions.urls")),
#    path("payments/", include("payments.urls")),
#    path("i18n/", include("django.conf.urls.i18n")),  # Enable language features
#    path("set_language/", set_language, name="set_language"),  # Explicitly add set_language
#    path('', TemplateView.as_view(template_name='home.html'), name='home'),  # Landing page 
#    path('privacy-policy/', TemplateView.as_view(template_name="privacy_policy.html"), name='privacy_policy'),   
#    path('terms-of-use/', TemplateView.as_view(template_name="terms_of_use.html"), name='terms_of_use'),
#]