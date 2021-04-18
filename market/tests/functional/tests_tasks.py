from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from freezegun import freeze_time
from mixer.backend.django import mixer

from elk.utils.testing import ClassIntegrationTestCase, create_customer, create_teacher
from market.models import Subscription
from market.tasks import notify_subscription_unused_for_a_week
from products.models import Product1


@freeze_time('2032-12-01 12:00')
class TestNotificationUnusedSubscription(ClassIntegrationTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.product = Product1.objects.get(pk=1)
        cls.product.duration = timedelta(days=42)
        cls.product.save()

        cls.customer = create_customer()

    def setUp(self):
        self.s = Subscription(
            customer=self.customer,
            product=self.product,
            buy_price=150
        )
        self.s.save()

    @patch('market.models.signals.class_scheduled.send')
    def _schedule(self, c, date, *args):
        c.timeline = mixer.blend(
            'timeline.Entry',
            lesson_type=c.lesson_type,
            teacher=create_teacher(),
            start=date,
        )
        c.save()

    def test_customer_notified_if_subscription_unused_for_a_week(self):
        with freeze_time('2032-12-08 12:00'):   # 1 week forward
            self.assertIn(self.s, Subscription.objects.unused_for_a_week())
            self.assertTrue(self.s.unused_subscription_notification_date is None)

            notify_subscription_unused_for_a_week()

            self.s.refresh_from_db()
            self.assertTrue(self.s.unused_subscription_notification_date is not None)
            self.assertEqual(len(mail.outbox), 1)

            out_emails = [outbox.to[0] for outbox in mail.outbox]

            self.assertIn(self.customer.user.email, out_emails)

    def test_customer_notified_only_once(self):
        with freeze_time('2032-12-08 12:00'):   # 1 week forward
            for _ in range(5):
                notify_subscription_unused_for_a_week()

            self.assertEqual(len(mail.outbox), 1)

    def test_customer_not_notified_if_got_scheduled_class(self):
        c = self.s.classes.first()
        date = self.tzdatetime(2032, 12, 9, 13, 33)
        self._schedule(c, date)

        with freeze_time('2032-12-08 12:00'):  # 1 week fwd
            notify_subscription_unused_for_a_week()

            self.assertEqual(len(mail.outbox), 0)

    def test_customer_notified_again_after_taking_class_and_disappearing_for_a_week(self):
        with freeze_time('2032-12-08 12:00'):  # 1 week fwd
            notify_subscription_unused_for_a_week()
            self.assertEqual(len(mail.outbox), 1)

        c = self.s.classes.first()
        date = self.tzdatetime(2032, 12, 10, 12, 00)
        self._schedule(c, date)

        with freeze_time('2032-12-11 12:00'):  # day after class was scheduled
            c.mark_as_fully_used()

        with freeze_time('2032-12-18 12:00'):  # week after class was taken
            notify_subscription_unused_for_a_week()
            self.assertEqual(len(mail.outbox), 2)

    def test_unused_subscription_notification_date_updated(self):
        self.assertTrue(self.s.unused_subscription_notification_date is None)

        with freeze_time('2032-12-08 12:00'):  # 1 week fwd
            notify_subscription_unused_for_a_week()

            self.s.refresh_from_db()
            self.assertTrue(self.s.unused_subscription_notification_date.date().strftime('%Y-%m-%d') == '2032-12-08')
