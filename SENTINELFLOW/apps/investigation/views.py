from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.core.permissions import RolePermissionMixin
from .forms import CaseCreateForm, CaseNoteForm, CaseUpdateForm
from .models import InvestigationCase
from .services import add_note, close_case


class CaseListView(RolePermissionMixin, ListView):
    model = InvestigationCase
    template_name = "investigation/case_list.html"
    context_object_name = "cases"
    paginate_by = 25

    def get_queryset(self):
        qs = InvestigationCase.objects.select_related("subject", "assigned_to", "alert").all()
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            qs = qs.filter(subject=self.request.user)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Investigation Cases"
        ctx["statuses"] = InvestigationCase._meta.get_field("status").choices
        return ctx


class CaseDetailView(RolePermissionMixin, DetailView):
    model = InvestigationCase
    template_name = "investigation/case_detail.html"
    context_object_name = "case"

    def get_queryset(self):
        return InvestigationCase.objects.select_related("subject", "assigned_to", "opened_by", "alert")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Case {self.object.short_id}"
        ctx["update_form"] = kwargs.get("update_form") or CaseUpdateForm(instance=self.object)
        ctx["note_form"] = kwargs.get("note_form") or CaseNoteForm()
        ctx["activities"] = self.object.activities.select_related("detection").order_by("-timestamp")[:40]
        ctx["timeline"] = self.object.case_notes.select_related("author").all()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action", "note")
        if action == "note":
            form = CaseNoteForm(request.POST)
            if form.is_valid() and form.cleaned_data["note"].strip():
                add_note(self.object, request.user, form.cleaned_data["note"])
                messages.success(request, "Case note added.")
            else:
                messages.error(request, "Note cannot be empty.")
            return redirect("investigation:detail", pk=self.object.pk)
        form = CaseUpdateForm(request.POST, instance=self.object)
        if not form.is_valid():
            ctx = self.get_context_data(update_form=form)
            messages.error(request, "Please correct the errors below.")
            return self.render_to_response(ctx)
        if action == "close":
            close_case(self.object, actor=request.user, conclusion=form.cleaned_data.get("conclusion", ""))
            messages.success(request, "Case closed and linked alert resolved.")
        else:
            form.save()
            messages.success(request, "Case updated.")
        return redirect("investigation:detail", pk=self.object.pk)


class CaseCreateView(RolePermissionMixin, CreateView):
    model = InvestigationCase
    form_class = CaseCreateForm
    template_name = "investigation/case_form.html"

    def form_valid(self, form):
        case = form.save(commit=False)
        case.opened_by = self.request.user
        case.assigned_to = self.request.user
        case.save()
        form.save_m2m()
        messages.success(self.request, f"Case {case.short_id} created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("investigation:detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Open Investigation Case"
        return ctx
