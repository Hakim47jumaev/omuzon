from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.contrib.auth import get_user_model
from django.db import models
from courses.models import Course, Module, Task, TestCase

User = get_user_model()


class DashboardLoginForm(forms.Form):
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            try:
                user = User.objects.get(
                    models.Q(username=username) | models.Q(email__iexact=username)
                )
            except User.DoesNotExist:
                raise forms.ValidationError('Invalid username/email or password.')

            if not user.check_password(password):
                raise forms.ValidationError('Invalid username/email or password.')

            if not user.is_active:
                raise forms.ValidationError('This account is disabled.')

            if not user.is_staff:
                raise forms.ValidationError('Access denied. Staff privileges required.')

            cleaned_data['user'] = user
        return cleaned_data


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%dT%H:%M')
        super().__init__(*args, **kwargs)

    def format_value(self, value):
        if value:
            if isinstance(value, str):
                return value
            return value.strftime('%Y-%m-%dT%H:%M')
        return ''


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'start_time', 'owner', 'is_exam', 'is_olimpiad', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_time': DateTimeLocalInput(attrs={'class': 'form-control'}),
            'owner': forms.Select(attrs={'class': 'form-control'}),
            'is_exam': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_olimpiad': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'end_time': DateTimeLocalInput(attrs={'class': 'form-control'}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['course', 'title', 'description', 'order']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['module', 'title', 'description', 'task_text', 'order', 'show_count']
        widgets = {
            'module': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 15, 'style': 'overflow-x: hidden; overflow-y: auto; word-wrap: break-word; white-space: pre-wrap;'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'show_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TaskInlineForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'task_text', 'order', 'show_count']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'task_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'style': 'overflow-x: hidden; overflow-y: auto; word-wrap: break-word; white-space: pre-wrap;'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'show_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['task', 'input_data', 'expected_output', 'is_active', 'order']
        widgets = {
            'task': forms.Select(attrs={'class': 'form-control'}),
            'input_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'expected_output': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TestCaseInlineForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output', 'is_active', 'order']
        widgets = {
            'input_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'expected_output': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


ModuleInlineFormSet = inlineformset_factory(
    Course,
    Module,
    form=ModuleForm,
    extra=3,
    can_delete=True,
    fields=['title', 'description', 'order']
)

TaskInlineFormSet = inlineformset_factory(
    Module,
    Task,
    form=TaskInlineForm,
    extra=3,
    can_delete=True,
    fields=['title', 'description', 'task_text', 'order', 'show_count']
)

TaskAddFormSet = inlineformset_factory(
    Module,
    Task,
    form=TaskInlineForm,
    extra=1,
    can_delete=False,
    fields=['title', 'description', 'task_text', 'order', 'show_count']
)

TestCaseInlineFormSet = inlineformset_factory(
    Task,
    TestCase,
    form=TestCaseInlineForm,
    extra=2,
    can_delete=True,
    fields=['input_data', 'expected_output', 'is_active', 'order']
)

TestCaseAddFormSet = inlineformset_factory(
    Task,
    TestCase,
    form=TestCaseInlineForm,
    extra=1,
    can_delete=True,
    fields=['input_data', 'expected_output', 'is_active', 'order']
)

TestCaseAddFormSet = inlineformset_factory(
    Task,
    TestCase,
    form=TestCaseInlineForm,
    extra=1,
    can_delete=True,
    fields=['input_data', 'expected_output', 'is_active', 'order']
)
