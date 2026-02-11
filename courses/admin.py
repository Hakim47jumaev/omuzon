from django.contrib import admin
from django.db import models
from django.forms import Textarea
from .models import Course, Module, Task, Enrollment, TestCase

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ('input_data', 'expected_output', 'is_active', 'order')
    ordering = ('order',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 40})},
    }

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')
    list_filter = ('module', 'module__course')
    search_fields = ('title', 'module__title', 'module__course__title', 'task_text')
    inlines = [TestCaseInline]
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 60})},
    }

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ('title', 'order', 'task_text')
    ordering = ('order',)
    show_change_link = True
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 40})},
    }

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title', 'description')
    inlines = [TaskInline]

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ('title', 'order', 'description')
    ordering = ('order',)
    show_change_link = True
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2, 'cols': 60})},
    }

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'start_time', 'enrolled_count', 'is_active')
    list_filter = ('owner', 'start_time' )
    search_fields = ('title', 'description', 'owner__username')
    inlines = [ModuleInline]

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "course",
        "status",
        "enrolled_at",
         
    )
    list_filter = ("status", "course")
    search_fields = ("user__username", "course__title")
    autocomplete_fields = ("user", "course" )

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('task', 'order', 'is_active')
    list_filter = ('task', 'task__module', 'task__module__course', 'is_active')
    search_fields = ('task__title', 'task__module__title', 'task__module__course__title', 'input_data', 'expected_output')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 40})},
    }
