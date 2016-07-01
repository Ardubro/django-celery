from django.contrib import admin

from .models import OrdinaryLesson, LessonWithNative, PairedLesson, HappyHour, MasterClass
from .models import Event as LessonEvent


@admin.register(LessonEvent)
class LessonEventAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'host')


class LessonAdmin(admin.ModelAdmin):
    """
    Abstract admin for the lessons.
    """
    list_display = ('internal_name', 'duration')


@admin.register(OrdinaryLesson)
class OrdinaryLessonAdmin(LessonAdmin):
    pass


@admin.register(LessonWithNative)
class LessonWithNativeAdmin(LessonAdmin):
    pass


@admin.register(PairedLesson)
class PairedLessonAdmin(LessonAdmin):
    pass


@admin.register(HappyHour)
class HappyHourAdmin(LessonAdmin):
    pass


@admin.register(MasterClass)
class MasterClassAdmin(LessonAdmin):
    pass
