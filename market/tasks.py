from elk.celery import app as celery
from market.signals import subscription_unused

from .models import Subscription


@celery.task
def notify_subscription_unused_for_a_week():
    """
    Remind a customer with active subscription to take classes if he hasn't taken them for a week.
    """
    for s in Subscription.objects.unused_for_a_week().filter(unused_subscription_notification_date=None).select_related('customer'):
        if s.customer.classes.nearest_scheduled() is None:
            subscription_unused.send(sender=notify_subscription_unused_for_a_week, instance=s)
