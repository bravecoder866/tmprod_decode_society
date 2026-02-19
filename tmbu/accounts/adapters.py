from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to manage social signup flow, primarily ensuring a unique 
    username is created automatically from Google data to bypass the signup form.
    """
    
    # 1. Ensure auto-signup is allowed (consistent with SOCIALACCOUNT_AUTO_SIGNUP=True)
    def is_open_for_signup(self, request, sociallogin):
        """Allows all users to proceed with automatic signup."""
        return True

    # 2. Crucial logic: Ensures the user object has a unique username before saving.
    def populate_user(self, request, sociallogin, data):
        """
        Ensures the user object is populated with a unique username derived from 
        the social account data if the field is empty.
        """
        # Call the parent method to populate common fields (email, first/last name, etc.)
        user = super().populate_user(request, sociallogin, data)
        
        # We only need to generate a username if the super() call didn't set one
        # or if the default generated one is not guaranteed to be unique.
        if not user.username:
            # Create a base username from the name or email, slugified for safety
            base_username = (
                data.get("name")
                or data.get("email", "").split("@")[0]
                or "user"
            )
            base_username = slugify(base_username)

            # Ensure uniqueness
            username = base_username
            counter = 1
            
            # Loop until a unique username is found
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Set the unique username on the user object
            user.username = username
            
        return user

    # 3. Streamlined pre_social_login
    # We keep this simple as the main work is done in populate_user, 
    # and the settings handle the rest of the auto-signup process.
    def pre_social_login(self, request, sociallogin):
                       
        """
        Ensures the user object is populated before the signup process begins, 
        making sure the required 'username' field is available for auto-signup.
        """
        # Call populate_user here to ensure the unique username is set 
        # on sociallogin.user *before* allauth attempts to save the user.
        self.populate_user(request, sociallogin, sociallogin.account.extra_data) 
        
        email = sociallogin.user.email

        if email:
            try:
                # Find the existing user account (created via Django form)
                existing_user = User.objects.get(email__iexact=email)

                # Check if the social account is already linked to avoid errors
                if not SocialAccount.objects.filter(user=existing_user, provider=sociallogin.account.provider).exists():
                    # If not linked, link the new social account to the existing user
                    with transaction.atomic():
                        sociallogin.connect(request, existing_user)
                
                # CRITICAL: Mark sociallogin state to skip the entire signup flow and proceed directly to login.
                sociallogin.state["should_auto_signup"] = True
                sociallogin.user = existing_user 
                return
            
            except User.DoesNotExist:

                # We don't need sociallogin.state["should_auto_signup"] = True 
                # because SOCIALACCOUNT_AUTO_SIGNUP = True already covers it.
                pass # Returning None (the default) continues the flow.

        sociallogin.state["should_auto_signup"] = True
