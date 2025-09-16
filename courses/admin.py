from django.contrib import admin
from .models import Course, Module, Task, Enrollment

# ----------------- Task Inline -----------------
class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ('title', 'order', 'task_text')
    ordering = ('order',)

# ----------------- Module Inline -----------------
class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ('title', 'order', 'description')
    ordering = ('order',)

# ----------------- Course Admin -----------------
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'start_time', 'enrolled_count', 'is_active')
    list_filter = ('start_time', 'owner')
    search_fields = ('title', 'description', 'owner__username')
    inlines = [ModuleInline]  # Модули будут внутри курса

# ----------------- Module Admin -----------------
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    inlines = [TaskInline]  # Задачи будут внутри модуля

# ----------------- Task Admin -----------------
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')
    list_filter = ('module',)
    search_fields = ('title', 'module__title')

# ----------------- Enrollment Admin -----------------
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'progress')
    list_filter = ('course', 'user')
    search_fields = ('user__username', 'course__title')
