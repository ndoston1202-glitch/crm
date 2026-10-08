"""Lid yoki xizmat buyurtmasi xodimga biriktirilganda bildirishnoma yuboradi.

Ko'rinishlar (views) obyektga `_actor_id` qo'yadi — xodim o'zini o'zi biriktirsa, bildirishnoma kelmaydi.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from crm.models import Lead, ServiceOrder

from .services import notify


def _remember_old(sender, instance, field):
    old = None
    if instance.pk:
        old = sender.objects.filter(pk=instance.pk).values_list(field, flat=True).first()
    instance._old_assignee_id = old


@receiver(pre_save, sender=Lead)
def lead_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, "operator_id")


@receiver(pre_save, sender=ServiceOrder)
def order_pre_save(sender, instance, **kwargs):
    _remember_old(sender, instance, "assignee_id")


def _changed_to(instance, field):
    new = getattr(instance, field)
    if new and new != getattr(instance, "_old_assignee_id", None) and new != getattr(instance, "_actor_id", None):
        return new
    return None


@receiver(post_save, sender=Lead)
def lead_post_save(sender, instance, **kwargs):
    if _changed_to(instance, "operator_id"):
        notify(
            instance.operator,
            "lead",
            _("Sizga yangi lid biriktirildi: %(name)s") % {"name": instance.full_name},
            text=instance.phone,
            url=reverse("crm:lead_detail", args=[instance.pk]),
        )


@receiver(post_save, sender=ServiceOrder)
def order_post_save(sender, instance, **kwargs):
    if _changed_to(instance, "assignee_id"):
        sale = instance.sale
        when = f" · {instance.scheduled_at:%d.%m %H:%M}" if instance.scheduled_at else ""
        notify(
            instance.assignee,
            "order",
            _("Yangi xizmat buyurtmasi #%(n)s") % {"n": instance.pk},
            text=f"{sale.lead.full_name} · {sale.service}{when}",
            url=reverse("crm:order_edit", args=[instance.pk]),
        )
