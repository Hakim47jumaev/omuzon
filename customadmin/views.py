from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, DetailView
from django.contrib.auth.views import LogoutView
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory
from courses.models import Course, Module, Task, TestCase
from .forms import (
    CourseForm, ModuleForm, TaskForm, TestCaseForm, DashboardLoginForm,
    ModuleInlineFormSet, TaskInlineFormSet, TestCaseInlineFormSet,
    TaskInlineForm, TestCaseInlineForm, TaskAddFormSet, TestCaseAddFormSet
)


class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('customadmin:login')
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DashboardLoginView(View):
    template_name = 'customadmin/login.html'
    
    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('customadmin:course_list')
        form = DashboardLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = DashboardLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('customadmin:course_list')
        return render(request, self.template_name, {'form': form})


class DashboardLogoutView(LogoutView):
    next_page = reverse_lazy('customadmin:login')


class CourseListView(StaffRequiredMixin, ListView):
    model = Course
    template_name = 'customadmin/course_list.html'
    context_object_name = 'courses'


class CourseCreateView(StaffRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:course_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Course'
        context['model_name'] = 'Course'
        context['cancel_url'] = reverse_lazy('customadmin:course_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Course created successfully.')
        return super().form_valid(form)


class CourseDetailView(StaffRequiredMixin, DetailView):
    model = Course
    template_name = 'customadmin/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        return Course.objects.select_related('owner').prefetch_related('modules')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        if self.request.method == 'POST':
            formset = ModuleInlineFormSet(self.request.POST, instance=course)
        else:
            formset = ModuleInlineFormSet(instance=course)
        context['formset'] = formset
        return context

    def post(self, request, *args, **kwargs):
        course = self.get_object()
        formset = ModuleInlineFormSet(request.POST, instance=course)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Modules updated successfully.')
            return redirect('customadmin:course_detail', pk=course.pk)
        return self.render_to_response(self.get_context_data(formset=formset))


class CourseUpdateView(StaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:course_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Course'
        context['model_name'] = 'Course'
        context['cancel_url'] = reverse_lazy('customadmin:course_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Course updated successfully.')
        return super().form_valid(form)


class CourseDeleteView(StaffRequiredMixin, DeleteView):
    model = Course
    template_name = 'customadmin/confirm_delete.html'
    success_url = reverse_lazy('customadmin:course_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Course'
        context['model_name'] = 'Course'
        context['cancel_url'] = reverse_lazy('customadmin:course_list')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Course deleted successfully.')
        return super().delete(request, *args, **kwargs)


class ModuleListView(StaffRequiredMixin, ListView):
    model = Module
    template_name = 'customadmin/module_list.html'
    context_object_name = 'modules'


class ModuleCreateView(StaffRequiredMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:module_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Module'
        context['model_name'] = 'Module'
        context['cancel_url'] = reverse_lazy('customadmin:module_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Module created successfully.')
        return super().form_valid(form)


class ModuleDetailView(StaffRequiredMixin, DetailView):
    model = Module
    template_name = 'customadmin/module_detail.html'
    context_object_name = 'module'

    def get_queryset(self):
        return Module.objects.select_related('course').prefetch_related('tasks__testcases')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module = self.get_object()
        
        selected_task_id = self.request.GET.get('task_id')
        show_add_form = self.request.GET.get('add') == '1'
        
        if show_add_form:
            # Для добавления новой задачи - только одна форма
            if self.request.method == 'POST':
                task_formset = TaskAddFormSet(
                    self.request.POST, 
                    instance=module, 
                    prefix='tasks',
                    queryset=Task.objects.none()
                )
            else:
                task_formset = TaskAddFormSet(
                    instance=module, 
                    prefix='tasks',
                    queryset=Task.objects.none()
                )
        else:
            # Для редактирования существующих задач
            if self.request.method == 'POST':
                task_formset = TaskInlineFormSet(self.request.POST, instance=module, prefix='tasks')
            else:
                task_formset = TaskInlineFormSet(instance=module, prefix='tasks')
        
        task_testcase_pairs = []
        add_testcase_count = int(self.request.GET.get('add_testcase', 0))
        
        # Для выбранной задачи создаем formset тесткейсов
        selected_task = None
        selected_task_testcase_formset = None
        if selected_task_id and selected_task_id.isdigit():
            try:
                selected_task = Task.objects.get(pk=int(selected_task_id), module=module)
                prefix = 'selected_task_testcases'
                
                if self.request.method == 'POST':
                    extra_count = 1 + add_testcase_count
                    TestCaseAddFormSetDynamic = inlineformset_factory(
                        Task,
                        TestCase,
                        form=TestCaseInlineForm,
                        extra=extra_count,
                        can_delete=True,
                        fields=['input_data', 'expected_output', 'is_active', 'order']
                    )
                    selected_task_testcase_formset = TestCaseAddFormSetDynamic(
                        self.request.POST,
                        instance=selected_task,
                        prefix=prefix,
                        queryset=TestCase.objects.none()
                    )
                else:
                    extra_count = 1 + add_testcase_count
                    TestCaseAddFormSetDynamic = inlineformset_factory(
                        Task,
                        TestCase,
                        form=TestCaseInlineForm,
                        extra=extra_count,
                        can_delete=True,
                        fields=['input_data', 'expected_output', 'is_active', 'order']
                    )
                    selected_task_testcase_formset = TestCaseAddFormSetDynamic(
                        instance=selected_task,
                        prefix=prefix,
                        queryset=TestCase.objects.none()
                    )
            except Task.DoesNotExist:
                pass
        
        for i, task_form in enumerate(task_formset):
            task = task_form.instance if task_form.instance.pk else None
            prefix = f'testcases-{i}'
            
            if show_add_form and task_form.instance.pk is None:
                # Для новой задачи используем TestCaseAddFormSet с возможностью добавления
                extra_count = 1 + add_testcase_count
                TestCaseAddFormSetDynamic = inlineformset_factory(
                    Task,
                    TestCase,
                    form=TestCaseInlineForm,
                    extra=extra_count,
                    can_delete=True,
                    fields=['input_data', 'expected_output', 'is_active', 'order']
                )
                
                if self.request.method == 'POST':
                    testcase_formset = TestCaseAddFormSetDynamic(
                        self.request.POST,
                        instance=task,
                        prefix=prefix
                    )
                else:
                    testcase_formset = TestCaseAddFormSetDynamic(
                        instance=task,
                        prefix=prefix
                    )
            else:
                # Для существующих задач используем обычный formset
                if self.request.method == 'POST':
                    testcase_formset = TestCaseInlineFormSet(
                        self.request.POST,
                        instance=task,
                        prefix=prefix
                    )
                else:
                    testcase_formset = TestCaseInlineFormSet(
                        instance=task,
                        prefix=prefix
                    )
            
            task_testcase_pairs.append((task_form, testcase_formset))
        
        context['task_formset'] = task_formset
        context['task_testcase_pairs'] = task_testcase_pairs
        context['selected_task_id'] = int(selected_task_id) if selected_task_id and selected_task_id.isdigit() else None
        context['show_add_form'] = show_add_form
        context['add_testcase_count'] = add_testcase_count
        context['selected_task'] = selected_task
        context['selected_task_testcase_formset'] = selected_task_testcase_formset
        return context

    def post(self, request, *args, **kwargs):
        module = self.get_object()
        show_add_form = request.GET.get('add') == '1'
        selected_task_id = request.GET.get('task_id')
        add_testcase_count = int(request.GET.get('add_testcase', 0))
        
        # Обработка добавления тесткейсов к выбранной задаче
        if selected_task_id and selected_task_id.isdigit():
            try:
                selected_task = Task.objects.get(pk=int(selected_task_id), module=module)
                prefix = 'selected_task_testcases'
                extra_count = 1 + add_testcase_count
                TestCaseAddFormSetDynamic = inlineformset_factory(
                    Task,
                    TestCase,
                    form=TestCaseInlineForm,
                    extra=extra_count,
                    can_delete=True,
                    fields=['input_data', 'expected_output', 'is_active', 'order']
                )
                testcase_formset = TestCaseAddFormSetDynamic(
                    request.POST,
                    instance=selected_task,
                    prefix=prefix,
                    queryset=TestCase.objects.none()
                )
                
                if testcase_formset.is_valid():
                    testcase_formset.save()
                    messages.success(request, 'TestCases added successfully.')
                    return redirect(f'customadmin:module_detail', pk=module.pk, task_id=selected_task_id)
                else:
                    # Если форма невалидна, показываем ошибки
                    context = self.get_context_data()
                    return self.render_to_response(context)
            except Task.DoesNotExist:
                pass
        
        if show_add_form:
            # Для добавления новой задачи - только одна форма
            task_formset = TaskAddFormSet(
                request.POST, 
                instance=module, 
                prefix='tasks',
                queryset=Task.objects.none()
            )
        else:
            # Для редактирования существующих задач
            task_formset = TaskInlineFormSet(request.POST, instance=module, prefix='tasks')
        
        if task_formset.is_valid():
            with transaction.atomic():
                tasks = task_formset.save()
                
                all_valid = True
                testcase_formsets_data = []
                
                for i, (task_form, task) in enumerate(zip(task_formset.forms, tasks)):
                    if task_form.cleaned_data.get('DELETE', False):
                        continue
                    
                    prefix = f'testcases-{i}'
                    testcase_formset = TestCaseInlineFormSet(
                        request.POST,
                        instance=task,
                        prefix=prefix
                    )
                    
                    if not testcase_formset.is_valid():
                        all_valid = False
                    
                    testcase_formsets_data.append((task, testcase_formset))
                
                if all_valid:
                    for task, testcase_formset in testcase_formsets_data:
                        testcase_formset.save()
                    
                    messages.success(request, 'Tasks and TestCases updated successfully.')
                    return redirect('customadmin:module_detail', pk=module.pk)
        
        context = self.get_context_data()
        return self.render_to_response(context)


class ModuleUpdateView(StaffRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:module_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Module'
        context['model_name'] = 'Module'
        context['cancel_url'] = reverse_lazy('customadmin:module_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Module updated successfully.')
        return super().form_valid(form)


class ModuleDeleteView(StaffRequiredMixin, DeleteView):
    model = Module
    template_name = 'customadmin/confirm_delete.html'
    success_url = reverse_lazy('customadmin:module_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Module'
        context['model_name'] = 'Module'
        context['cancel_url'] = reverse_lazy('customadmin:module_list')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Module deleted successfully.')
        return super().delete(request, *args, **kwargs)


class TaskListView(StaffRequiredMixin, ListView):
    model = Task
    template_name = 'customadmin/task_list.html'
    context_object_name = 'tasks'


class TaskCreateView(StaffRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Task'
        context['model_name'] = 'Task'
        context['cancel_url'] = reverse_lazy('customadmin:task_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Task created successfully.')
        return super().form_valid(form)


class TaskDetailView(StaffRequiredMixin, DetailView):
    model = Task
    template_name = 'customadmin/task_detail.html'
    context_object_name = 'task'

    def get_queryset(self):
        return Task.objects.select_related('module__course').prefetch_related('testcases')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        add_testcase_count = int(self.request.GET.get('add_testcase', 0))
        
        if self.request.method == 'POST':
            # При POST используем formset с существующими тесткейсами
            formset = TestCaseInlineFormSet(self.request.POST, instance=task)
        else:
            # При GET показываем только новые формы для добавления
            extra_count = 1 + add_testcase_count
            TestCaseAddFormSetDynamic = inlineformset_factory(
                Task,
                TestCase,
                form=TestCaseInlineForm,
                extra=extra_count,
                can_delete=True,
                fields=['input_data', 'expected_output', 'is_active', 'order']
            )
            formset = TestCaseAddFormSetDynamic(instance=task, queryset=TestCase.objects.none())
        
        context['formset'] = formset
        context['add_testcase_count'] = add_testcase_count
        return context

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        formset = TestCaseInlineFormSet(request.POST, instance=task)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'TestCases updated successfully.')
            return redirect('customadmin:task_detail', pk=task.pk)
        return self.render_to_response(self.get_context_data(formset=formset))


class TaskUpdateView(StaffRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'customadmin/form.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('customadmin:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Task'
        context['model_name'] = 'Task'
        next_url = self.request.GET.get('next')
        context['cancel_url'] = next_url if next_url else reverse_lazy('customadmin:task_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Task updated successfully.')
        return super().form_valid(form)


class TaskDeleteView(StaffRequiredMixin, DeleteView):
    model = Task
    template_name = 'customadmin/confirm_delete.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('customadmin:task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Task'
        context['model_name'] = 'Task'
        next_url = self.request.GET.get('next')
        context['cancel_url'] = next_url if next_url else reverse_lazy('customadmin:task_list')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Task deleted successfully.')
        return super().delete(request, *args, **kwargs)


class TestCaseListView(StaffRequiredMixin, ListView):
    model = TestCase
    template_name = 'customadmin/testcase_list.html'
    context_object_name = 'testcases'


class TestCaseCreateView(StaffRequiredMixin, CreateView):
    model = TestCase
    form_class = TestCaseForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:testcase_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create TestCase'
        context['model_name'] = 'TestCase'
        context['cancel_url'] = reverse_lazy('customadmin:testcase_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'TestCase created successfully.')
        return super().form_valid(form)


class TestCaseUpdateView(StaffRequiredMixin, UpdateView):
    model = TestCase
    form_class = TestCaseForm
    template_name = 'customadmin/form.html'
    success_url = reverse_lazy('customadmin:testcase_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update TestCase'
        context['model_name'] = 'TestCase'
        context['cancel_url'] = reverse_lazy('customadmin:testcase_list')
        return context

    def form_valid(self, form):
        messages.success(self.request, 'TestCase updated successfully.')
        return super().form_valid(form)


class TestCaseDeleteView(StaffRequiredMixin, DeleteView):
    model = TestCase
    template_name = 'customadmin/confirm_delete.html'
    success_url = reverse_lazy('customadmin:testcase_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete TestCase'
        context['model_name'] = 'TestCase'
        context['cancel_url'] = reverse_lazy('customadmin:testcase_list')
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'TestCase deleted successfully.')
        return super().delete(request, *args, **kwargs)
