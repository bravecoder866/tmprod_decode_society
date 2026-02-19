import random
from django.utils import timezone
from datetime import timedelta  # Import timedelta for time calculations
from django.core.mail import send_mail
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import translation

def generate_and_send_otp(request, user):
    otp_code = random.randint(100000, 999999)  # Generate 6-digit OTP
    otp_expiration = timezone.now() + timedelta(minutes=30)

    request.session['otp_code'] = otp_code  # Store OTP in session
    request.session['pending_user_id'] = user.id
    #request.session['user_id'] = user.id    # Store user ID in session   
    request.session['otp_expires_at'] = otp_expiration.timestamp()  # Expiration

    # Send OTP via email
    subject = _("Your Verification Code")
    message = _(
        "Hi {username},\n\n"
        "Your OTP code is: {otp_code}\n\n"
        "This code is valid for 30 minutes.\n\n"
        "Thank you for signing up!\n\n"
        "Xtembusu Support Team"
        ).format(username=user.username, otp_code=otp_code)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

