"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import Profile
from django.utils import translation
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

User = get_user_model() 

class SignUpForm(UserCreationForm):
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    username = forms.CharField(max_length=150, required=True, help_text=_('Required.'), widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your username')}),)
    email = forms.EmailField(required=True, help_text=_('Required. Enter a valid email address.'), widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Enter your email')}),)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'captcha')  # Include captcha field
        widgets = {
            #'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your username')}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Enter your password')}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Confirm your password')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure the captcha field is correctly labeled.
        self.fields['captcha'].label = _("Captcha")

        # Set the language for the reCAPTCHA widget.
        #current_language = translation.get_language()
        #if current_language == 'zh-hans':  # Simplified Chinese
        #    self.fields['captcha'].widget.attrs['data-lang'] = 'zh-CN'
        #else:  # Default to English or any other language
        #    self.fields['captcha'].widget.attrs['data-lang'] = 'en' #explicitly set to en


    def clean_email(self):
        email = self.cleaned_data.get("email").lower()  # Normalize email
        #if User.objects.filter(email=email).exists():
        #    raise forms.ValidationError(_("A user with that email already exists."))
        #return email

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if existing_user.is_active:
                raise forms.ValidationError(_("A user with that email already exists."))
            else:
                # User exists but not verified yet, allow proceeding
                self.existing_user = existing_user  # store user for later reference
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            if existing_user.is_active:
                raise forms.ValidationError(_("A user with that username already exists."))
            else:
                self.existing_user_by_username = existing_user
        return username

    def validate_unique(self):
        # Override default unique validation completely
        pass

    def save(self, commit=True):
        existing_user = getattr(self, 'existing_user', None)
        existing_user_by_username = getattr(self, 'existing_user_by_username', None)

        user = existing_user or existing_user_by_username

        if user:
        #if hasattr(self, 'existing_user'):
        #   user = self.existing_user  # reuse existing inactive user
            user.username = self.cleaned_data['username']  # Optionally update username
            user.email = self.cleaned_data['email'].lower()
            user.set_password(self.cleaned_data['password1']) # update password
            user.is_active = False 
        else:
            user = super().save(commit=False)
            user.email = self.cleaned_data['email'].lower()  # Normalize email
            user.is_active = False  # Deactivate user until OTP is verified
        
        if commit:
            user.save()
        return user
        

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

#class ProfileUpdateForm(forms.ModelForm):
#    class Meta:
#       model = Profile
#       fields = ['image', 'bio']


class CustomLoginForm(forms.Form):
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your username or email')}),
        label=_("Username or Email"),
        max_length=255,
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Enter your password')}),
        label=_("Password"),
        required=True
    )

    def clean(self):
        username_or_email = self.cleaned_data.get("username_or_email")
        password = self.cleaned_data.get("password")
        
        user = None

        if username_or_email and password:
            # Try to find user by username first
            user = authenticate(username=username_or_email, password=password)

            if not user:
                # If not found, try looking up by email
                try:
                    user_obj = User.objects.get(email__iexact=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if not user or not user.is_active:
                raise forms.ValidationError(_("Invalid username/email or password"))

            self.user = user  # Save for login() method
                   

        return self.cleaned_data

    def login(self, request):
        return getattr(self, 'user', None)



#class CustomLoginForm(forms.Form):
#    username_or_email = forms.CharField(
#        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your username or email')}),
#        label=_("Username or Email"),
#        max_length=255,
#        required=True
#    )
#    password = forms.CharField(
#        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Enter your password')}),
#        label=_("Password"),
#        required=True
#    )

#    def clean(self):
#        username_or_email = self.cleaned_data.get("username_or_email")
#        password = self.cleaned_data.get("password")
        
        
#        if username_or_email and password:
#            user = authenticate(username=username_or_email, password=password)
        
#            if not user or not user.is_active:
#                raise forms.ValidationError(_("Invalid username/email or password"))
        
        # if not user.is_active:
        #            error_message = "Your account is inactive. Please contact support."
        
#        return self.cleaned_data

#    def login(self, request):
#        username_or_email = self.cleaned_data.get('username_or_email')
#        password = self.cleaned_data.get('password')
#        user = authenticate(username=username_or_email, password=password)
#        return user