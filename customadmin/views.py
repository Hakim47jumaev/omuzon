import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from courses.models import Course, Module, Task, TestCase, Enrollment
from .forms import (
    DashboardLoginForm,
    CourseForm,
    ModuleForm,
    TaskForm,
    TaskCreateForm,
    TestCaseForm,
    TestCaseFormSet,
)


class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('customadmin:login')
        return super().dispatch(request, *args, **kwargs)


class CourseListView(StaffRequiredMixin, ListView):
    model = Course
    template_name = 'customadmin/course_list.html'
    context_object_name = 'courses'
    ordering = ['-start_time']


class CourseCreateView(StaffRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'customadmin/course_form.html'
    context_object_name = 'course'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Course created successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('customadmin:course_detail', kwargs={'pk': self.object.pk})


class CourseDetailView(StaffRequiredMixin, DetailView):
    model = Course
    template_name = 'customadmin/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        return Course.objects.prefetch_related('modules')


class CourseEnrollmentsView(StaffRequiredMixin, View):
    def get_course(self, pk):
        return get_object_or_404(Course, pk=pk)

    def get(self, request, pk):
        course = self.get_course(pk)
        enrollments = course.enrollments.all().select_related('user').order_by('-enrolled_at')
        return render(request, 'customadmin/course_enrollments.html', {
            'course': course,
            'enrollments': enrollments,
        })

    def post(self, request, pk):
        course = self.get_course(pk)
        selected_ids = request.POST.getlist('selected_enrollments')
        action = request.POST.get('bulk_action')

        if selected_ids and action in ('approved', 'rejected', 'pending'):
            updated = Enrollment.objects.filter(id__in=selected_ids, course=course).update(status=action)
            messages.success(request, f'{updated} enrollment(s) updated to "{action}".')
        elif not selected_ids:
            messages.error(request, 'No enrollments selected.')

        return redirect('customadmin:course_enrollments', pk=pk)


class CourseUpdateView(StaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'customadmin/course_form.html'
    context_object_name = 'course'

    def get_success_url(self):
        messages.success(self.request, 'Course updated successfully.')
        return reverse_lazy('customadmin:course_detail', kwargs={'pk': self.object.pk})


class ModuleDetailView(StaffRequiredMixin, DetailView):
    model = Module
    template_name = 'customadmin/module_detail.html'
    context_object_name = 'module'

    def get_queryset(self):
        return Module.objects.select_related('course').prefetch_related('tasks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['module_tasks'] = self.object.tasks.all().order_by('order')
        return context


@method_decorator(require_POST, name='dispatch')
class ModuleTasksReorderView(StaffRequiredMixin, View):
    def post(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        try:
            payload = json.loads(request.body.decode() or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid JSON')
        ids = payload.get('order')
        if not isinstance(ids, list) or not ids:
            return JsonResponse({'ok': False, 'error': 'order must be a non-empty list'}, status=400)
        if len(ids) != len(set(ids)):
            return JsonResponse({'ok': False, 'error': 'duplicate task ids'}, status=400)
        expected = set(module.tasks.values_list('id', flat=True))
        if set(ids) != expected:
            return JsonResponse({'ok': False, 'error': 'task list does not match module'}, status=400)
        with transaction.atomic():
            for index, tid in enumerate(ids, start=1):
                Task.objects.filter(pk=tid, module_id=module.pk).update(order=index)
        return JsonResponse({'ok': True})


class ModuleUpdateView(StaffRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = 'customadmin/module_form.html'
    context_object_name = 'module'

    def get_success_url(self):
        messages.success(self.request, 'Module updated successfully.')
        return reverse_lazy('customadmin:module_detail', kwargs={'pk': self.object.pk})


class ModuleCreateView(StaffRequiredMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = 'customadmin/module_form.html'

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs['course_pk'])

    def form_valid(self, form):
        form.instance.course = self.get_course()
        messages.success(self.request, 'Module added successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('customadmin:course_detail', kwargs={'pk': self.kwargs['course_pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.get_course()
        return context


class TaskDetailView(StaffRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'customadmin/task_detail.html'
    context_object_name = 'task'

    def get_queryset(self):
        return Task.objects.select_related('module__course').prefetch_related('testcases')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        module = task.module
        
        # Получаем все задачи модуля для навигации
        context['all_tasks'] = module.tasks.all().order_by('order')
        
        if self.request.method == 'POST':
            context['testcase_formset'] = TestCaseFormSet(self.request.POST, instance=task, prefix='testcases')
        else:
            context['testcase_formset'] = TestCaseFormSet(instance=task, prefix='testcases')
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if 'save_task' in request.POST:
            # Сохранение задачи
            if form.is_valid():
                self.object = form.save()
                messages.success(request, 'Task saved successfully.')
                return redirect('customadmin:task_detail', pk=self.object.pk)
            else:
                return self.form_invalid(form)
        
        elif 'save_testcases' in request.POST:
            # Сохранение TestCases
            testcase_formset = TestCaseFormSet(request.POST, instance=self.object, prefix='testcases')
            if testcase_formset.is_valid():
                testcase_formset.save()
                messages.success(request, 'TestCases saved successfully.')
                return redirect('customadmin:task_detail', pk=self.object.pk)
            else:
                context = self.get_context_data()
                context['testcase_formset'] = testcase_formset
                return self.render_to_response(context)
        
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class TaskDeleteView(StaffRequiredMixin, DeleteView):
    model = Task
    template_name = 'customadmin/task_confirm_delete.html'
    
    def get_success_url(self):
        module_pk = self.object.module.pk
        messages.success(self.request, 'Task deleted successfully.')
        return reverse_lazy('customadmin:module_detail', kwargs={'pk': module_pk})


class TestCaseUpdateView(StaffRequiredMixin, UpdateView):
    model = TestCase
    form_class = TestCaseForm
    template_name = 'customadmin/testcase_form.html'
    context_object_name = 'testcase'

    def get_success_url(self):
        task_pk = self.object.task.pk
        messages.success(self.request, 'TestCase updated successfully.')
        return reverse_lazy('customadmin:task_detail', kwargs={'pk': task_pk})


class TestCaseDeleteView(StaffRequiredMixin, DeleteView):
    model = TestCase
    template_name = 'customadmin/testcase_confirm_delete.html'
    
    def get_success_url(self):
        task_pk = self.object.task.pk
        messages.success(self.request, 'TestCase deleted successfully.')
        return reverse_lazy('customadmin:task_detail', kwargs={'pk': task_pk})


class TaskCreateView(StaffRequiredMixin, CreateView):
    model = Task
    form_class = TaskCreateForm
    template_name = 'customadmin/task_form.html'

    def get_module(self):
        return get_object_or_404(Module, pk=self.kwargs['module_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module = self.get_module()
        context['module'] = module
        
        # Получаем все задачи модуля для навигации
        context['all_tasks'] = module.tasks.all().order_by('order')
        
        if self.request.method == 'POST':
            context['testcase_formset'] = TestCaseFormSet(self.request.POST, prefix='testcases')
        else:
            context['testcase_formset'] = TestCaseFormSet(prefix='testcases')
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        module = self.get_module()
        
        if 'save_task' in request.POST:
            testcase_formset = TestCaseFormSet(request.POST, prefix='testcases')
            
            if form.is_valid():
                if testcase_formset.is_valid():
                    with transaction.atomic():
                        max_order = module.tasks.aggregate(m=Max('order'))['m'] or 0
                        next_order = max_order + 1
                        form.instance.module = module
                        form.instance.order = next_order
                        form.instance.title = f'task{next_order}'
                        form.instance.description = 'description'
                        self.object = form.save()
                        testcase_formset.instance = self.object
                        testcase_formset.save()
                        messages.success(request, 'Task and TestCases added successfully.')
                        return redirect('customadmin:task_detail', pk=self.object.pk)
                else:
                    # Форма задачи валидна, но TestCases нет
                    context = self.get_context_data()
                    context['form'] = form
                    context['testcase_formset'] = testcase_formset
                    return self.render_to_response(context)
            else:
                # Форма задачи невалидна
                return self.form_invalid(form)
        
        return self.form_invalid(form)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy('customadmin:task_detail', kwargs={'pk': self.object.pk})


class DashboardLoginView(View):
    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('customadmin:course_list')
        form = DashboardLoginForm()
        return render(request, 'customadmin/login.html', {'form': form})

    def post(self, request):
        form = DashboardLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('customadmin:course_list')
        return render(request, 'customadmin/login.html', {'form': form})


class DashboardLogoutView(View):
    def post(self, request):
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('customadmin:login')
    
    def get(self, request):
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('customadmin:login')
