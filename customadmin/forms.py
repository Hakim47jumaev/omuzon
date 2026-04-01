from django import forms
from django.contrib.auth import authenticate
from accounts.models import User
from courses.models import Course, Task, Module, TestCase
from django.forms import inlineformset_factory


class DashboardLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            # Попытка найти пользователя по username или email
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    raise forms.ValidationError('Invalid username/email or password.')

            # Проверка пароля
            user = authenticate(username=user.username, password=password)
            if user is None:
                raise forms.ValidationError('Invalid username/email or password.')

            # Проверка is_staff
            if not user.is_staff:
                raise forms.ValidationError('Access denied. Staff access required.')

            # Проверка is_active
            if not user.is_active:
                raise forms.ValidationError('This account is inactive.')

            cleaned_data['user'] = user
        return cleaned_data


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%dT%H:%M')
        super().__init__(*args, **kwargs)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'start_time', 'end_time', 'show', 'is_exam', 'is_olimpiad', 'owner']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'start_time': DateTimeLocalInput(attrs={'class': 'form-control'}),
            'end_time': DateTimeLocalInput(attrs={'class': 'form-control'}),
            'show': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_exam': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_olimpiad': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'owner': forms.Select(attrs={'class': 'form-control'}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'task_text', 'show_count']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'show_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['show_count'].initial = 2


class TaskCreateForm(forms.ModelForm):
    """Создание задачи: только условие и show_count; title/description/order выставляются в view."""

    class Meta:
        model = Task
        fields = ['task_text', 'show_count']
        widgets = {
            'task_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'show_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['show_count'].initial = 2


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output', 'is_active', 'order']
        widgets = {
            'input_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expected_output': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


TestCaseFormSet = inlineformset_factory(
    Task,
    TestCase,
    form=TestCaseForm,
    extra=1,
    can_delete=True,
    fields=['input_data', 'expected_output', 'is_active', 'order']
)
