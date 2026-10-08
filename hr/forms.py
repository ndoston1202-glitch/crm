from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from crm.forms import BootstrapMixin

from .models import Department, Employee, LeaveRequest

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
TIME = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


class EmployeeForm(BootstrapMixin, forms.ModelForm):
    new_department = forms.CharField(label=_("Yoki yangi bo'lim"), required=False)

    class Meta:
        model = Employee
        fields = ["full_name", "phone", "user", "department", "new_department", "position", "hire_date", "birth_date",
                  "salary", "work_start", "work_end", "status", "dismissed_at", "notes"]
        widgets = {"hire_date": DATE, "birth_date": DATE, "dismissed_at": DATE, "work_start": TIME, "work_end": TIME,
                   "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        taken = Employee.objects.exclude(pk=self.instance.pk).exclude(user=None).values("user")
        self.fields["user"].queryset = get_user_model().objects.filter(is_active=True).exclude(pk__in=taken)
        self.fields["user"].help_text = _("Bog'lansa, xodim CRM orqali «Keldim/Ketdim» bosadi va ta'til so'raydi")

    def save(self, commit=True):
        name = self.cleaned_data.get("new_department", "").strip()
        if name:
            self.instance.department, _created = Department.objects.get_or_create(name=name)
        return super().save(commit)


class LeaveRequestForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["kind", "start_date", "end_date", "reason"]
        widgets = {"start_date": DATE, "end_date": DATE, "reason": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["end_date"] < cleaned["start_date"]:
            raise forms.ValidationError(_("Tugash sanasi boshlanishidan oldin bo'lishi mumkin emas"))
        return cleaned


class AttendanceFixForm(forms.Form):
    """HR qo'lda davomatni to'g'irlaydi."""
    employee = forms.ModelChoiceField(label=_("Xodim"), queryset=Employee.objects.filter(status=Employee.Status.ACTIVE),
                                      widget=forms.Select(attrs={"class": "form-select form-select-sm"}))
    date = forms.DateField(label=_("Sana"), widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))
    check_in = forms.TimeField(label=_("Keldi"), required=False, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control form-control-sm"}))
    check_out = forms.TimeField(label=_("Ketdi"), required=False, widget=forms.TimeInput(attrs={"type": "time", "class": "form-control form-control-sm"}))
