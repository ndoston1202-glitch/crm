from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Call, Lead, Sale, Service, ServiceOrder

User = get_user_model()


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)


DATETIME_WIDGET = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class LeadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["full_name", "phone", "extra_phone", "region", "source", "status", "operator", "next_call_at", "comment"]
        widgets = {"next_call_at": DATETIME_WIDGET, "comment": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["operator"].queryset = User.objects.filter(role=User.Role.OPERATOR, is_active=True)
        if user is not None and not user.is_manager:
            # Operator lidni boshqaga biriktira olmaydi
            del self.fields["operator"]


class CallForm(BootstrapMixin, forms.ModelForm):
    new_status = forms.ChoiceField(label=_("Lid holati"), choices=Lead.Status.choices)
    next_call_at = forms.DateTimeField(label=_("Keyingi qo'ng'iroq"), required=False, widget=DATETIME_WIDGET)

    class Meta:
        model = Call
        fields = ["result", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2})}


class SaleForm(BootstrapMixin, forms.ModelForm):
    assignee = forms.ModelChoiceField(label=_("Mas'ul xodim"), queryset=User.objects.none(), required=False)
    scheduled_at = forms.DateTimeField(label=_("Xizmat vaqti"), required=False, widget=DATETIME_WIDGET)
    address = forms.CharField(label=_("Manzil"), required=False)

    class Meta:
        model = Sale
        fields = ["service", "amount", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["assignee"].queryset = User.objects.filter(role=User.Role.SERVICE, is_active=True)
        self.fields["assignee"].widget.attrs["class"] = "form-select"


class ServiceOrderForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = ["assignee", "status", "scheduled_at", "address", "note"]
        widgets = {"scheduled_at": DATETIME_WIDGET, "note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = User.objects.filter(role=User.Role.SERVICE, is_active=True)
        if user is not None and not user.is_manager:
            del self.fields["assignee"]


class LeadImportForm(forms.Form):
    file = forms.FileField(
        label=_("CSV fayl"),
        help_text=_("Ustunlar: full_name, phone, source, region, comment (birinchi qator — sarlavha)"),
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )
    operator = forms.ModelChoiceField(
        label=_("Operatorga biriktirish"),
        queryset=User.objects.filter(role=User.Role.OPERATOR, is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
