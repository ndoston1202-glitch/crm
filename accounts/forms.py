from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from .models import User
from .permissions import MODULES, PRIVILEGED


class UserAccessForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Parol"), required=False, widget=forms.PasswordInput(render_value=False),
        help_text=_("Tahrirlashda bo'sh qoldirilsa, parol o'zgarmaydi"),
    )
    modules = forms.MultipleChoiceField(
        label=_("Ruxsat berilgan bo'limlar"), choices=MODULES, required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "username", "role", "phone", "sip_extension", "is_active",
            "full_access", "modules", "data_scope",
        ]
        widgets = {"data_scope": forms.RadioSelect(attrs={"class": "form-check-input"})}
        labels = {"first_name": _("Ism"), "last_name": _("Familiya"), "username": _("Login"), "is_active": _("Faol")}
        help_texts = {"username": _("Lotin harflari, raqamlar va @ . + - _ belgilari")}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            field.widget.attrs.setdefault("class", "form-select" if isinstance(field.widget, forms.Select) else "form-control")
        self.fields["full_access"].widget.attrs["class"] = "form-check-input"
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
        if self.instance.pk is None:
            self.fields["password"].required = True
            self.fields["password"].help_text = ""
        self.limited_editor = editor is not None and not editor.has_full_access
        if self.limited_editor:
            # Cheklangan foydalanuvchi boshqaga o'zida bo'lmagan yoki imtiyozli huquq bera olmaydi
            self.fields["full_access"].disabled = True
            self.fields["modules"].choices = [
                (k, v) for k, v in MODULES if k not in PRIVILEGED and editor.can(k)
            ]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned = super().clean()
        if self.limited_editor:
            if self.instance.pk and self.instance.has_full_access:
                raise forms.ValidationError(_("To'liq dostupli foydalanuvchini faqat to'liq dostupli admin o'zgartira oladi"))
            # Cheklangan editor ko'rmaydigan imtiyozli modullar o'z holicha qoladi
            kept = [m for m in (self.instance.modules or []) if m in PRIVILEGED]
            cleaned["modules"] = list(dict.fromkeys(list(cleaned.get("modules", [])) + kept))
        if self.editor and self.instance.pk == self.editor.pk:
            # O'zini o'zi qulflab qo'ymasligi uchun
            if not cleaned.get("is_active"):
                raise forms.ValidationError(_("O'zingizni o'chira olmaysiz"))
            if self.editor.has_full_access and not cleaned.get("full_access"):
                raise forms.ValidationError(_("O'zingizdan to'liq dostupni olib qo'ya olmaysiz"))
            if not cleaned.get("full_access") and "users" not in cleaned.get("modules", []):
                raise forms.ValidationError(_("O'zingizdan foydalanuvchilarni boshqarish huquqini olib qo'ya olmaysiz"))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.modules = list(self.cleaned_data.get("modules") or [])
        user._explicit_access = True
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
