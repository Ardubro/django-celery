from django.test import TestCase
from mixer.backend.django import mixer

import lessons.models as lessons
import products.models as products
from elk.utils.test import mock_request, test_customer, test_teacher
from hub.exceptions import CannotBeScheduled, CannotBeUnscheduled
from hub.models import Class, Subscription
from timeline.models import Entry as TimelineEntry


class BuySubscriptionTestCase(TestCase):
    fixtures = ('crm', 'lessons', 'products')
    TEST_PRODUCT_ID = 1

    def setUp(self):
        self.customer = test_customer()

    def test_buy_a_single_subscription(self):
        """
        When buing a subscription, all lessons in it should become beeing
        available to the customer
        """

        # TODO: Clean this up
        def _get_lessons_count(product):
            cnt = 0
            for lesson_type in product.LESSONS:
                cnt += getattr(product, lesson_type).all().count()
            return cnt

        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150,
        )
        s.request = mock_request(self.customer)
        s.save()

        active_lessons_count = Class.objects.filter(subscription_id=s.pk).count()
        active_lessons_in_product_count = _get_lessons_count(product)

        self.assertEqual(active_lessons_count, active_lessons_in_product_count, 'When buying a subscription should add all of its available lessons')  # two lessons with natives and four with curators

    test_second_time = test_buy_a_single_subscription  # let's test for the second time :-)

    def test_store_class_source(self):
        """
        When buying a subcription, every bought class should have a sign
        about that it's bought buy subscription.
        """

        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150
        )
        s.request = mock_request(self.customer)
        s.save()

        for c in s.classes.all():
            self.assertEqual(c.buy_source, 1)  # 1 is defined in the model

    def test_disabling_subscription(self):
        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150,
        )
        s.request = mock_request(self.customer)
        s.save()

        for lesson in s.classes.all():
            self.assertEqual(lesson.active, 1)

        # now, disable the subscription for any reason
        s.active = 0
        s.save()
        for lesson in s.classes.all():
            self.assertEqual(lesson.active, 0, 'Every lesson in subscription should become inactive now')


class ScheduleTestCase(TestCase):
    fixtures = ('crm', 'lessons')

    def setUp(self):
        self.host = test_teacher()
        self.customer = test_customer()

    def _buy_a_lesson(self, lesson):
        c = Class(
            customer=self.customer,
            lesson=lesson
        )
        c.request = mock_request(self.customer)
        c.save()
        return c

    def test_unschedule_of_non_scheduled_lesson(self):
        bought_class = self._buy_a_lesson(products.OrdinaryLesson.get_default())
        with self.assertRaises(CannotBeUnscheduled):
            bought_class.unschedule()

    def test_schedule_simple(self):
        """
        Generic test to schedule and unschedule a class
        """
        lesson = products.OrdinaryLesson.get_default()

        entry = mixer.blend(TimelineEntry, slots=1, lesson=lesson)
        bought_class = self._buy_a_lesson(lesson)

        self.assertFalse(bought_class.is_scheduled)
        self.assertTrue(entry.is_free)

        bought_class.schedule(entry)  # schedule a class
        bought_class.save()

        self.assertTrue(bought_class.is_scheduled)
        self.assertFalse(entry.is_free)

        bought_class.unschedule()
        self.assertFalse(bought_class.is_scheduled)
        self.assertTrue(entry.is_free)

    def test_schedule_master_class(self):
        """
        Buy a master class and then schedule it
        """
        lesson = mixer.blend(lessons.MasterClass, host=self.host)

        timeline_entry = mixer.blend(TimelineEntry,
                                     lesson=lesson,
                                     teacher=self.host,
                                     )

        timeline_entry.save()

        bought_class = self._buy_a_lesson(lesson=lesson)
        bought_class.save()

        bought_class.schedule(timeline_entry)
        bought_class.save()

        self.assertTrue(bought_class.is_scheduled)
        self.assertEqual(timeline_entry.taken_slots, 1)

        bought_class.unschedule()
        self.assertEqual(timeline_entry.taken_slots, 0)

    def schedule_2_people_to_a_paired_lesson(self):
        customer1 = test_customer()
        customer2 = test_customer()

        paired_lesson = mixer.blend(lessons.PairedLesson, slots=2)

        customer1_class = mixer.blend(Class, customer=customer1, lesson=paired_lesson)
        customer2_class = mixer.blend(Class, customer=customer2, lesson=paired_lesson)

        timeline_entry = mixer.blend(TimelineEntry, lesson=paired_lesson, teacher=self.host)

        customer1_class.schedule(timeline_entry)
        customer2_class.schedule(timeline_entry)

        self.assertTrue(customer1_class.is_scheduled)
        self.assertTrue(customer2_class.is_scheduled)
        self.assertEqual(timeline_entry.taken_slots, 2)

        customer2_class.unschedule()
        self.assertEqual(timeline_entry.taken_slots, 1)

    def test_schedule_lesson_of_a_wrong_type(self):
        """
        Try to schedule bought master class lesson to a paired lesson event
        """
        paired_lesson = mixer.blend(lessons.PairedLesson, slots=2)
        paired_lesson_entry = mixer.blend(TimelineEntry, lesson=paired_lesson, teacher=self.host, active=1)

        paired_lesson_entry.save()

        bought_class = self._buy_a_lesson(mixer.blend(lessons.MasterClass, host=self.host))
        bought_class.save()

        with self.assertRaises(CannotBeScheduled):
            bought_class.schedule(paired_lesson_entry)

        self.assertFalse(bought_class.is_scheduled)


class testBuyableProduct(TestCase):
    fixtures = ('crm', 'lessons', 'products')
    TEST_PRODUCT_ID = 1

    def setUp(self):
        self.customer = test_customer()

    def test_subscription_name(self):
        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150,
        )
        s.request = mock_request(self.customer)
        s.save()

        self.assertEqual(s.name_for_user, product.name)

    def test_single_class_name(self):
        lesson = products.OrdinaryLesson.get_default()
        c = Class(
            customer=self.customer,
            lesson=lesson
        )
        c.request = mock_request(self.customer)
        c.save()

        self.assertEqual(c.name_for_user, lesson.name)


class TestAvailableLessons(TestCase):
    fixtures = ('crm', 'lessons', 'products')
    TEST_PRODUCT_ID = 1

    def setUp(self):
        self.customer = test_customer()
        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150,
        )
        s.request = mock_request()
        s.save()

    def test_available_lesson_types(self):
        lesson_types = self.customer.classes.bought_lesson_types()
        self.assertEquals(len(lesson_types), 5)

        self.assertIn(lessons.OrdinaryLesson.contenttype(), lesson_types)


class TryToSchedule(TestCase):
    fixtures = ('lessons', 'products')
    TEST_PRODUCT_ID = 1

    def setUp(self):
        self.customer = test_customer()
        self.host = test_teacher()

    def _buy_a_lesson(self, lesson):
        c = Class(
            customer=self.customer,
            lesson=lesson
        )
        c.request = mock_request(self.customer)
        c.save()
        return c

    def _buy_a_subscription(self):
        product = products.Product1.objects.get(pk=self.TEST_PRODUCT_ID)
        s = Subscription(
            customer=self.customer,
            product=product,
            buy_price=150,
        )
        s.request = mock_request(self.customer)
        s.save()
        return s

    def test_find_class(self):
        res = Class.objects.find_class(
            customer=self.customer,
            lesson_type=lessons.OrdinaryLesson.contenttype()
        )
        self.assertFalse(res['result'])
        self.assertEquals(res['error'], 'E_CLASS_NOT_FOUND')
        self.assertIn('curated session', res['text'])  # err text should contain name of the lesson

        self._buy_a_lesson(lessons.OrdinaryLesson.get_default())
        res = Class.objects.find_class(
            customer=self.customer,
            lesson_type=lessons.OrdinaryLesson.contenttype()
        )
        self.assertTrue(res['result'])  # should find now
        self.assertIsInstance(res['class'], Class)

    def test_find_only_active_classes(self):
        lesson = lessons.OrdinaryLesson.get_default()
        entry = mixer.blend(TimelineEntry, lesson=lesson, teacher=self.host, active=1)
        c = self._buy_a_lesson(lesson)

        c.schedule(entry)
        c.save()

        res = Class.objects.find_class(
            customer=self.customer,
            lesson_type=lessons.OrdinaryLesson.contenttype()
        )
        self.assertFalse(res['result'])  # we already have scheduled the only class we could

    def test_find_the_subscription_class_first(self):
        """
        Return subscription lessons first.

        Buy a single lesson, than buy a subscription an check, that find_class()
        would return a subscription lesson.
        """
        self._buy_a_lesson(lessons.OrdinaryLesson.get_default())
        subscription = self._buy_a_subscription()

        first_lesson_by_subscription = Class.objects.order_by('buy_date', 'id').filter(subscription=subscription)[0]

        res = Class.objects.find_class(
            customer=self.customer,
            lesson_type=lessons.OrdinaryLesson.contenttype()
        )
        self.assertTrue(res['result'])
        self.assertEquals(res['class'], first_lesson_by_subscription)
