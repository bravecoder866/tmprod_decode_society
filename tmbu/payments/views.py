"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""

import stripe
from stripe.error import StripeError
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import UserSubscription
from accounts.models import Profile, UserFreeTrial
from solutions.models import Scenario
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _, get_language, get_language_from_request
from django.contrib import messages
from datetime import datetime, timedelta, timezone as dt_timezone
from calendar import monthrange
import logging
import json
import time



logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def subscription_plan(request):
    return render(request, 'payments/subscription_plan.html')

# For usage-based subscription
#def get_next_month_first_day_timestamp():
#    current_time = timezone.now()
#    next_month = (current_time.month % 12) + 1
#    year = current_time.year + (1 if current_time.month == 12 else 0)
#    first_day_next_month = datetime(year, next_month, 1, tzinfo=timezone.get_current_timezone(),)
#    return int(first_day_next_month.timestamp())


@login_required
def create_checkout_session(request):
    stripe_price_id = settings.STRIPE_PRICE_ID
    user = request.user

    # Get the latest subscription, if any
    subscription = UserSubscription.objects.filter(user=user).order_by('-updated_at').first()


    # If the subscription exists and is "active", prevent a new checkout
    if subscription and subscription.subscription_status == "active":
        messages.info(request, _("You already have an active subscription."))
        return redirect(request.META.get("HTTP_REFERER", "subscription_plan")) 


    user_language = get_language()  # Detect user language

    # Map Django language codes to Stripe's supported locale values
    stripe_locale_map = {
        "en": "en",
        "zh-hans": "zh",    # Map Simplified Chinese (Django) → Stripe's "zh"
    }

    # Use mapped locale if available, otherwise default to 'auto'
    locale = stripe_locale_map.get(user_language, "auto")


    try:
        # For usage-based subscription
        # billing_cycle_anchor = get_next_month_first_day_timestamp()
        
        # Use existing customer ID if available, otherwise let Stripe create a new one
        if subscription:
            customer_id = subscription.customer_id
        else:
            customer_id = None
        
        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            customer=customer_id,
            line_items=[
                {
                    'price': stripe_price_id,
                    'quantity': 1,
                },
            ],

            billing_address_collection="required",
            
            # For usage-based subscription
            #subscription_data={
            #    'billing_cycle_anchor': billing_cycle_anchor,
            #    'proration_behavior': 'create_prorations',  
            #},

            #success_url=request.build_absolute_uri(reverse('subscribe_success')) + '?session_id={CHECKOUT_SESSION_ID}', 
            #cancel_url=request.build_absolute_uri(reverse('subscribe_cancel')),
            success_url=request.build_absolute_uri(reverse('checkout_redirect')) + '?status=success&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('checkout_redirect')) + '?status=cancel',
            
            automatic_tax={'enabled': True},
            metadata={'user_id': request.user.id},
            locale=locale,
        )
    
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return JsonResponse({'error': _('An error occurred while creating the checkout session')}, status=500)

    return redirect(checkout_session.url, code=303)


def checkout_redirect(request):
    language = get_language_from_request(request)
    status = request.GET.get("status", "success")
    session_id = request.GET.get("session_id") 

    if status == "cancel":
        return redirect(reverse("subscribe_cancel"))
    return redirect(f"{reverse('subscribe_success')}?session_id={session_id}")


@login_required
def subscribe_success(request):
    session_id = request.GET.get('session_id')  # Retrieve session ID from the URL

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        subscription_id = session.subscription

        subscription = stripe.Subscription.retrieve(subscription_id)
                   
        if subscription.status != "active":
            return render(request, 'payments/subscribe_cancel.html')
    
    except stripe.error.StripeError as e:
        # log Stripe errors clearly
        logger.error(f"Stripe Error: {e}")
        return render(request, "payments/subscribe_cancel.html")
    
    except Exception as e:
        # handle unexpected errors clearly
        logger.error(f"Unexpected Error: {e}")
        return render(request, "payments/subscribe_cancel.html")

    return render(request, "payments/subscribe_success.html")


@login_required
def subscribe_cancel(request):
    return render(request, 'payments/subscribe_cancel.html')


#@login_required
#def check_subscription_status(request):
#    session_id = request.GET.get('session_id')

#    if not session_id:
#        logger.warning("Missing session_id in request.")
#       return JsonResponse({"status": "missing_session_id"}, status=400)

#    try:
#        checkout_session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
#        stripe_subscription_id = checkout_session.subscription.id
#        user_subscription = UserSubscription.objects.get(subscription_id=stripe_subscription_id, user=request.user)
        
#        logger.info(f"Subscription status for session {session_id}: {user_subscription.subscription_status}")
#        return JsonResponse({"status": user_subscription.subscription_status})

#    except stripe.error.StripeError as e:
#        logger.error(f"Stripe error for session {session_id}: {str(e)}")
#        return JsonResponse({"status": "error", "message": str(e)}, status=500) #add status code.
#    except UserSubscription.DoesNotExist:
#        logger.warning(f"UserSubscription not found for session {session_id}.")
#        return JsonResponse({"status": "no_subscription"}, status=404) #add status code.
#    except Exception as e:
#        logger.error(f"Unexpected error for session {session_id}: {str(e)}")
#        return JsonResponse({"status": "error", "message": "An unexpected error occurred."}, status=500)


@csrf_exempt
def stripe_webhooks(request):
    if request.method == 'POST':
        payload = request.body
        #sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        sig_header = request.headers.get('stripe-signature')
        try:
        
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        

            # Handle specific event types
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                session_id = session["id"]

                logger.info(f"Received checkout session: {session_id}")  # Debugging

                # Check if important data is missing (e.g., customer or subscription ID)
                if not session.get("customer") or not session.get("subscription"):
                    try:
                        session = stripe.checkout.Session.retrieve(session_id)  
                        logger.info(f"Fetched session from Stripe API: {session}")
                    except stripe.error.InvalidRequestError as e:
                        logger.error(f"Stripe API Error: {e}")
                        return JsonResponse({"error": f"Invalid session ID: {session_id}"}, status=400)


                handle_checkout_session_completed(session)

            elif event['type'] == 'invoice.payment_succeeded':
                invoice = event['data']['object']
                handle_invoice_payment_succeeded(invoice)
            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                handle_invoice_payment_failed(invoice)
            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                handle_subscription_deleted(subscription)

            return JsonResponse({'status': 'success'}, status=200)


        except ValueError:
            # Invalid payload
            return JsonResponse({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            return JsonResponse({'error': 'Invalid signature'}, status=400)

    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)



def handle_checkout_session_completed(session):
    
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')

    if not customer_id or not subscription_id:
        logger.error("Checkout session is missing customer or subscription ID.")
        return

    try:
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve subscription from Stripe: {e}")
        return
    
    subscription_item_id = stripe_subscription['items']['data'][0]['id']
    status = stripe_subscription['status']

    user_id = session.get('metadata', {}).get('user_id')
    if not user_id:
        logger.error("Checkout session missing user_id in metadata.")
        return

    try:
        user_id = int(user_id)  # Ensure it's an integer
        user = User.objects.get(id=user_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id format: {user_id}")
        return
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found.")
        return
    

    # Create a new UserSubscription record
    try:
        UserSubscription.objects.create(
                user=user,
                subscription_id=subscription_id,
                subscription_item_id=subscription_item_id,
                subscription_status=status,
                customer_id=customer_id,
                # created_at=timezone.now(),
                # updated_at=timezone.now(),
        )
        logger.info(f"Created new subscription for user {user.username} (ID: {user_id}).")
    except Exception as e:
        logger.error(f"Error creating new subscription for user {user.username} (ID: {user_id}): {e}")



def handle_invoice_payment_succeeded(invoice):
    
    subscription_id = invoice.get('subscription')

    if not subscription_id:
        logger.error("Invoice does not contain a subscription ID.")
        return

    logger.info(f"Invoice payment succeeded for subscription_id: {subscription_id}.")
    return


#    retries = 3
#    delay = 3  # seconds

#    for i in range(retries):

#        try:
            # Fetch the latest subscription status from Stripe
#            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
#            stripe_status = stripe_subscription.get("status")

#            user_subscription = UserSubscription.objects.get(subscription_id=subscription_id)
#            user_subscription.subscription_status = stripe_status  # Ensure subscription remains active
#            user_subscription.updated_at = timezone.now()
#            user_subscription.save()
#            logger.info(f"UserSubscription updated for subscription_id: {subscription_id}")
#            return # success

#        except UserSubscription.DoesNotExist:
#            logger.error(f"No UserSubscription found for subscription_id: {subscription_id}")
#        except Exception as e:
#            logger.error(f"Error updating UserSubscription: {e}")
#            return

#    logger.error(f"Failed to update UserSubscription after {retries} retries for subscription_id: {subscription_id}")


def handle_invoice_payment_failed(invoice):
    
    subscription_id = invoice.get('subscription')

    retries = 3
    base_delay = 3  # seconds

    for i in range(retries):

        try:
            user_subscription = UserSubscription.objects.get(subscription_id=subscription_id)
            user_subscription.subscription_status = 'canceled'  # Suspend the subscription
            user_subscription.save()
            logger.info(f"UserSubscription status updated to 'canceled' for subscription_id: {subscription_id}")
            return  # Success

        except UserSubscription.DoesNotExist:
            logger.error(f"No UserSubscription found for subscription_id: {subscription_id}")
        except Exception as e:
            logger.error(f"Error updating UserSubscription: {e}")
            return
        
    logger.error(f"Failed to update UserSubscription after {retries} retries for subscription_id: {subscription_id}")


def handle_subscription_deleted(subscription):
    
    subscription_id = subscription.get('id')
    status = subscription.get('status')

    if not subscription_id or not status:
        logger.error("Subscription event missing subscription ID, or customer ID or status.")
        return

    # Find the corresponding user subscription
    try:
        user_subscription = UserSubscription.objects.get(subscription_id=subscription_id)    
    
        user_subscription.subscription_status = status
        user_subscription.save(update_fields=["subscription_status"])

        logger.info(f"Subscription {subscription_id} canceled for user {user_subscription.user.username}.")

        # Report usage for this user only for usage-based subscription
        #user = user_subscription.user
        #report_usage_to_stripe(user, user_subscription)

    except UserSubscription.DoesNotExist:
        logger.error(f"No UserSubscription found for subscription_id: {subscription_id}")
    except Exception as e:
        logger.error(f"Error updating UserSubscription: {e}")



@login_required
def manage_subscription(request):
    return render(request, 'accounts/profile.html')


@login_required
def stripe_customer_portal(request):
    if request.method == "POST":
        try:
            user_subscription = UserSubscription.objects.filter(user=request.user, subscription_status='active').order_by('-updated_at').first()
            
            if user_subscription is None:  # Check if user_subscription is None
                logger.warning(f"User {request.user.username} tried to access the portal without a subscription.")
                messages.info(request, _("You do not have an active subscription. Please subscribe to access your portal."))
                return redirect('subscription_plan')
            
            stripe_customer_id = user_subscription.customer_id
            
            if not stripe_customer_id:
                logger.error(f"Missing customer ID for user {request.user.username}")
                messages.error(request, "Stripe customer ID is missing. Please contact support.")
                return redirect('subscription_plan')

            user_language = get_language() 

            # Map Django language codes to Stripe's supported locale values
            stripe_locale_map = {
                "en": "en",
                "zh-hans": "zh",    # Map Simplified Chinese (Django) → Stripe's "zh"
            }

            # Use mapped locale if available, otherwise default to 'auto'
            locale = stripe_locale_map.get(user_language, "auto")


            # Create a session for the customer portal
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=request.build_absolute_uri(reverse('manage_subscription')),
                locale=locale 
            )
            return redirect(session.url)
            
        except StripeError as e:
            logger.error(f"Stripe error for user {request.user.username}: {str(e)}")
            messages.error(request, _("An error occurred while connecting to Stripe. Please try again later."))
            return redirect('subscription_plan')
    
    return redirect('home')  # Redirect if accessed via a non-POST method


# For usage-based subscription
# def get_previous_month_date_range():
   
    # Get the current date and time in the current timezone
#    now = timezone.now()
    
    # Find the first day of the current month
#    first_day_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate the last day of the previous month
#    last_day_previous_month = first_day_current_month - timezone.timedelta(days=1)
    
    # Get the start and end of the previous month
#    month_start = last_day_previous_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
#    month_end = last_day_previous_month.replace(day=monthrange(last_day_previous_month.year, last_day_previous_month.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    
#    return month_start, month_end


# For usage-based subscription
# def count_scenarios_previous_month(user):
#    
#    month_start, month_end = get_previous_month_date_range()
#    return Scenario.objects.filter(
#        user=user,
#        scenario_input_time__gte=start_date,
#        scenario_input_time__lte=end_date
#    ).count()

# For usaged-based subscription
#def count_scenarios_previous_billing_period(user, user_subscription):
#    try:
        # user_subscription = UserSubscription.objects.filter(user=user).order_by('-updated_at').first()
        
#        subscription_id = user_subscription.subscription_id

        # Retrieve Stripe subscription object
#        stripe_subscription = stripe.Subscription.retrieve(subscription_id)

        # Get billing period start and end from Stripe
#        start_date_timestamp = stripe_subscription['current_period_start']
#        end_date_timestamp = stripe_subscription['current_period_end']

        # Convert timestamps to datetime objects (aware of UTC)
#        period_start = datetime.fromtimestamp(start_date_timestamp, tz=dt_timezone.utc)
#        period_end = datetime.fromtimestamp(end_date_timestamp, tz=dt_timezone.utc)

        # Query scenarios
#        return Scenario.objects.filter(
#            user=user,
#            scenario_input_time__gte=period_start,
#            scenario_input_time__lte=period_end,
#        ).count()
        
        
#    except stripe.error.StripeError as e:
        # Handle Stripe API errors
#        print(f"Stripe API error: {e}")
#        return 0

# For usage-based subscription
#def report_usage_to_stripe(user, user_subscription=None):
    
#    if user_subscription is None:
#        user_subscription = UserSubscription.objects.filter(user=user, subscription_status='active').order_by('-updated_at').first()


#    if not user_subscription:
#        logger.warning(f"No active subscription found for user {user.username}")
#        return

    #subscription_item_id = user_subscription.subscription_item_id

#    customer_id = user_subscription.customer_id

#    usage_count = count_scenarios_previous_billing_period(user, user_subscription)
    
#    try:
#        user_free_trial = UserFreeTrial.objects.get(user=user)
    
        # Deduct 1 scenario if this is the first usage report
#        if not user_free_trial.first_usage_reported:
#            usage_count = max(0, usage_count - 1)  # Ensure usage_count doesn't go below 0
#            user_free_trial.first_usage_reported = True
#            user_free_trial.save(update_fields=["first_usage_reported"])
#    except UserFreeTrial.DoesNotExist:
#        logger.warning(f"No UserFreeTrial found for user {user.username}")
    
#    try:
        #stripe.subscriptionItems.createUsageRecord(
        #    subscription_item=subscription_item_id,
        #    quantity=usage_count,
        #    timestamp=int(timezone.now().timestamp()),  # Current time
        #    action='set',  # Replace previous usage count for the current period
        #)

#        stripe.billing.MeterEvent.create(
#        event_name="scenario_input_count",
#        payload={"stripe_customer_id": customer_id, "number_of_scenarios": str(usage_count)},
#        )


#        logger.info(f"Reported {usage_count} scenarios for user {user.username}")
#    except stripe.error.StripeError as e:
#        logger.error(f"Stripe Error: {e}")

# For usage-based subscription
#def report_usage_for_all_users():
#    users_with_active_subscription = User.objects.filter(
#        subscription__subscription_status='active'
#    ).distinct()

#    for user in users_with_active_subscription:
#        try:
#            report_usage_to_stripe(user)
#        except Exception as e:
#            logger.error(f"Failed to report usage for user {user.id}: {e}")



