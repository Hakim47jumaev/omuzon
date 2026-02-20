# submissions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    # Список
    list_display = (
        "id",
        "user_link",
        "task_link",
        "lang",
        "status_badge",
        "created_at",
        "code_preview",
        "errors_count",
    )
    list_display_links = ("id",)
    list_filter = ("status", "lang", "created_at", "task",'user')
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Поиск
    search_fields = (
        "id",
        "user__username",
        "user__email",
        "task__title",
        "task__id",
        "lang",
        "status",
        "feedback",
        "code",
    )

    # Автокомплит (если User/Task большие)
    autocomplete_fields = ("user", "task")

    # Редактирование
    readonly_fields = (
        "created_at",
        "code_formatted",
        "errors_formatted",
        "short_feedback",
    )
    fieldsets = (
        ("Основное", {
            "fields": ("user", "task", "lang", "status", "created_at")
        }),
        ("Код", {
            "fields": ("code_formatted", "code"),
            "description": "Сверху — красиво отформатированный предпросмотр, снизу — исходное поле (для копирования/редактирования).",
        }),
        ("Результат", {
            "fields": ("short_feedback", "feedback", "errors_formatted", "errors"),
        }),
    )

    # Удобство
    list_per_page = 50
    save_on_top = True

    actions = ("mark_pending", "mark_accepted", "mark_rejected", "clear_errors")

    # ---------------- UI helpers ----------------

    @admin.display(description="User", ordering="user__username")
    def user_link(self, obj: Submission):
        u = obj.user
        return format_html("{} ({})", u.username, getattr(u, "email", "") or "-")

    @admin.display(description="Task", ordering="task__title")
    def task_link(self, obj: Submission):
        t = obj.task
        return format_html("{} (id={})", t.title, t.pk)

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj: Submission):
        s = obj.status
        style = {
            "pending": "background:#fff3cd;color:#664d03;border:1px solid #ffecb5",
            "accepted": "background:#d1e7dd;color:#0f5132;border:1px solid #badbcc",
            "rejected": "background:#f8d7da;color:#842029;border:1px solid #f5c2c7",
            "error": "background:#e2e3e5;color:#41464b;border:1px solid #d3d6d8",
        }.get(s, "background:#e2e3e5;color:#41464b;border:1px solid #d3d6d8")

        label = dict(Submission.STATUS_CHOICES).get(s, s)
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:12px;font-weight:600;{}">{}</span>',
            style,
            label,
        )

    @admin.display(description="Code")
    def code_preview(self, obj: Submission):
        text = (obj.code or "").replace("\n", " ")
        return Truncator(text).chars(80)

    @admin.display(description="Errors")
    def errors_count(self, obj: Submission):
        try:
            return len(obj.errors or [])
        except Exception:
            return 0

    @admin.display(description="Code (preview)")
    def code_formatted(self, obj: Submission):
        code = (obj.code or "").strip()
        if not code:
            return "-"
        return format_html(
            '<pre style="white-space:pre;overflow:auto;max-height:420px;padding:12px;border-radius:8px;border:1px solid #ddd;background:#fafafa;">{}</pre>',
            code,
        )

    @admin.display(description="Errors (preview)")
    def errors_formatted(self, obj: Submission):
        errs = obj.errors or []
        if not errs:
            return "-"
        # Безопасный вывод JSON как текста
        import json
        txt = json.dumps(errs, ensure_ascii=False, indent=2)
        return format_html(
            '<pre style="white-space:pre;overflow:auto;max-height:320px;padding:12px;border-radius:8px;border:1px solid #ddd;background:#fafafa;">{}</pre>',
            txt,
        )

    @admin.display(description="Feedback (short)")
    def short_feedback(self, obj: Submission):
        fb = (obj.feedback or "").strip()
        if not fb:
            return "-"
        return Truncator(fb).chars(200)

    # ---------------- Actions ----------------

    @admin.action(description="Mark as pending")
    def mark_pending(self, request, queryset):
        queryset.update(status="pending")

    @admin.action(description="Mark as accepted")
    def mark_accepted(self, request, queryset):
        queryset.update(status="accepted")

    @admin.action(description="Mark as rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(status="rejected")

    @admin.action(description="Clear errors")
    def clear_errors(self, request, queryset):
        queryset.update(errors=[])
