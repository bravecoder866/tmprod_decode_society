"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""




import random
from django.core.mail import send_mail
from django.views import View
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Profile, UserFreeTrial, UserFreeTrialScenarioMining, UserFreeTrialQuickSolution
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
)
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView
from django.views.generic.edit import UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from .forms import SignUpForm, UserUpdateForm, CustomLoginForm #ProfileUpdateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone  # Import timezone for Django's timezone-aware datetime
from datetime import timedelta  # Import timedelta for time calculations
from django.utils.translation import gettext as _
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from .otp_utils import generate_and_send_otp

User = get_user_model()

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'accounts/signup.html'  

    def form_valid(self, form):
        # Create inactive user until OTP verified
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        self.object = user  # important for CreateView consistency

        #user = form.save()
        
        generate_and_send_otp(self.request, user)

        # Redirect to OTP verification page
        messages.info(self.request, _("A verification code has been sent to your email."))
        
        return redirect('verify_otp')

        # This calls get_success_url()
        #return super().form_valid(form)  

    #def get_success_url(self):
        """
        After signup, always go to OTP verification page.
        Do not carry forward any ?next= from signup.
        """
    #    return reverse('verify_otp')
        
        """
        Redirect to OTP verification page and carry forward ?next=...
        """
        #next_url = self.request.POST.get("next") or self.request.GET.get("next")
        #verify_url = reverse('verify_otp')
        #if next_url and next_url not in [reverse("signup"), reverse("login")]:
        #    verify_url += f"?next={next_url}"
        #return verify_url



class VerifyOTPView(View):
    template_name = 'accounts/verify_otp.html'

    def get(self, request):
        """Render OTP verification page."""
        return render(request, self.template_name)

        #next_url = request.GET.get("next")
        #return render(request, self.template_name, {"next": next_url})

    def post(self, request):

        # Check if session data exists
        #if not self.request.session.get('user_id'):
        #    messages.error(self.request, _("Your session has expired. Please sign up again."))
        #    return redirect('signup')

        pending_user_id = request.session.get('pending_user_id')
        stored_otp = request.session.get('otp_code')
        otp_expires_at = request.session.get('otp_expires_at')
        entered_otp = request.POST.get("otp")
        #user_id = request.session.get('user_id')
        
        #next_url = request.POST.get("next") or request.GET.get("next")
        
        # Validate session data
        #if not stored_otp or not user_id or not otp_expires_at:
        if not pending_user_id or not stored_otp or not otp_expires_at:
            messages.error(request, _("Session expired. Please sign up again."))
            return redirect('signup')
        
         # Check OTP expiration
        if timezone.now().timestamp() > otp_expires_at:
            self.clear_otp_session(request)
            messages.error(request, _("OTP expired. Please request a new one."))
            return redirect('signup')
           
        # Validate OTP
        if entered_otp and str(entered_otp) == str(stored_otp):

            user = User.objects.get(id=pending_user_id)

            # Activate & ensure related objects
            user.is_active = True
            user.save()

            # Clear session data
            #self.clear_otp_session(request)

            # Retrieve the user
            #user = User.objects.get(id=user_id)

            # Ensure Profile exists
            Profile.objects.get_or_create(user=user)

            # Ensure UserFreeTrial exists
            UserFreeTrial.objects.get_or_create(user=user)
            UserFreeTrialQuickSolution.objects.get_or_create(user=user)
            UserFreeTrialScenarioMining.objects.get_or_create(user=user)

            # Clear OTP session data BEFORE login
            self.clear_otp_session(request)
            
            # Activate the user
            #user.is_active = True 
            #user.save()

            # Log the user in
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            
            #messages.success(request, _("Account created!"))           

            # Redirect back where user came from, or default to scenario mining page.
            # Prefer next, fallback to new_scenario_mining
            #if next_url and url_has_allowed_host_and_scheme(
            #    url=next_url,
            #    allowed_hosts={request.get_host()},
            #):
            #    return redirect(next_url)

            return redirect(reverse_lazy("home"))
    
        #else:
        # Bad OTP
        messages.error(request, _("Invalid OTP. Please try again."))
        return render(request, self.template_name)

    def clear_otp_session(self, request):
        for k in ('otp_code', 'otp_expires_at', 'pending_user_id'):
            request.session.pop(k, None)

        """Helper function to clear OTP-related session data."""
        #request.session.pop('otp_code', None)
        #request.session.pop('otp_expires_at', None)
        #request.session.pop('user_id', None)


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

class EditProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'accounts/edit_profile.html'
    form_class = UserUpdateForm

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['u_form'] = UserUpdateForm(self.request.POST, instance=self.request.user)
           #context['p_form'] = ProfileUpdateForm(self.request.POST, self.request.FILES, instance=self.request.user.profile)
        else:
            context['u_form'] = UserUpdateForm(instance=self.request.user)
           #context['p_form'] = ProfileUpdateForm(instance=self.request.user.profile)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        u_form = context['u_form']
       #p_form = context['p_form']
        if u_form.is_valid(): #and p_form.is_valid()
            u_form.save()
           #p_form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('profile')  # Dynamic redirection logic can be added here
           

# Login View
def custom_login_view(request):
    form = CustomLoginForm()  # Always initialize an empty form first (no validation)
    
    if request.method == "POST":  # Only validate if the form was submitted
        form = CustomLoginForm(request.POST)  
        if form.is_valid():
            user = form.login(request)
            if user:
                login(request, user)

                # Prefer next, fallback to new_scenario_mining
                redirect_to = request.POST.get("next") or request.GET.get("next")
                if redirect_to and url_has_allowed_host_and_scheme(
                    url=redirect_to,
                    allowed_hosts={request.get_host()},
                ):
                    return redirect(redirect_to)

                # Fallback
                return redirect(reverse_lazy("new_scenario_mining"))
    
    return render(request, "registration/login.html", {
        "form": form,
        "next": request.GET.get("next"),
    })


def social_login_error(request):
        return render(request, 'accounts/social_login_error.html', {})


# Logout View
class CustomLogoutView(LogoutView):
    def get_next_page(self):
        return reverse_lazy('home')  # Dynamically resolve the URL



@csrf_exempt  # Don't try to CSRF-protect the error page itself
def csrf_failure(request, reason=""):
    return render(request, "accounts/csrf_failure.html", status=403)