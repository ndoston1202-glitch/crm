import mimetypes
import os
import shutil
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from crm.models import Lead
from crm.views import visible_leads

from . import ami
from .audio import ConversionError, to_mp3
from .models import PhoneCall
from .utils import normalize_phone

User = get_user_model()

DISPOSITIONS = {
    "ANSWERED": PhoneCall.Status.ANSWERED,
    "ANSWER": PhoneCall.Status.ANSWERED,
    "NO ANSWER": PhoneCall.Status.NO_ANSWER,
    "NOANSWER": PhoneCall.Status.NO_ANSWER,
    "CANCEL": PhoneCall.Status.NO_ANSWER,
    "BUSY": PhoneCall.Status.BUSY,
    "FAILED": PhoneCall.Status.FAILED,
    "CONGESTION": PhoneCall.Status.FAILED,
    "CHANUNAVAIL": PhoneCall.Status.FAILED,
}


@login_required
@require_POST
def click_to_call(request, lead_pk):
    lead = get_object_or_404(visible_leads(request.user), pk=lead_pk)
    extension = request.user.sip_extension
    if not extension:
        return JsonResponse({"ok": False, "error": _("Profilingizda ichki raqam (SIP) ko'rsatilmagan")}, status=400)
    phone = request.POST.get("phone") or lead.phone
    if phone not in (lead.phone, lead.extra_phone):
        return JsonResponse({"ok": False, "error": "bad phone"}, status=400)
    dial = "".join(ch for ch in phone if ch.isdigit())
    call = PhoneCall.objects.create(
        direction=PhoneCall.Direction.OUTGOING, phone=dial, extension=extension, lead=lead, operator=request.user
    )
    try:
        ami.originate(extension, dial, variables={"CRM_CALL_ID": call.pk})
    except ami.AmiError as exc:
        call.status = PhoneCall.Status.FAILED
        call.ended_at = timezone.now()
        call.save()
        return JsonResponse({"ok": False, "error": _("ATS xatosi: %(e)s") % {"e": exc}}, status=502)
    return JsonResponse({"ok": True, "message": _("Telefoningiz jiringlaydi, go'shakni ko'taring")})


def _token_ok(params):
    token = settings.ASTERISK["WEBHOOK_TOKEN"]
    return bool(token) and constant_time_compare(params.get("token", ""), token)


def _find_lead(phone):
    norm = normalize_phone(phone)
    if len(norm) < 5:
        return None
    return Lead.objects.filter(phone_norm=norm).order_by("-created_at").first()


@csrf_exempt
def webhook(request):
    """Asterisk dialplan'dan hodisalar: event=ring|answer|hangup (GET yoki POST parametrlari)."""
    params = request.POST if request.method == "POST" else request.GET
    if not _token_ok(params):
        return HttpResponseForbidden("bad token")

    event = params.get("event", "")
    uniqueid = params.get("uniqueid", "")
    call_id = params.get("call_id", "")
    phone = "".join(ch for ch in params.get("phone", "") if ch.isdigit() or ch == "+")
    extension = params.get("extension", "").strip()
    now = timezone.now()

    call = None
    if call_id.isdigit():
        call = PhoneCall.objects.filter(pk=call_id).first()
    if call is None and uniqueid:
        call = PhoneCall.objects.filter(uniqueid=uniqueid).first()
    if call is None:
        if event not in ("ring", "answer", "hangup") or not phone:
            return JsonResponse({"ok": False, "error": "unknown call"}, status=400)
        direction = params.get("direction", "in")
        call = PhoneCall(
            uniqueid=uniqueid,
            phone=phone,
            direction=PhoneCall.Direction.OUTGOING if direction == "out" else PhoneCall.Direction.INCOMING,
        )
    if uniqueid and not call.uniqueid:
        call.uniqueid = uniqueid

    if extension:
        call.extension = extension
        operator = User.objects.filter(sip_extension=extension, is_active=True).first()
        if operator:
            call.operator = operator

    if call.lead_id is None:
        call.lead = _find_lead(call.phone)
        if call.lead is None and call.direction == PhoneCall.Direction.INCOMING:
            call.lead = Lead.objects.create(
                full_name=call.phone,
                phone=call.phone,
                source=Lead.Source.CALL,
                operator=call.operator if call.operator and call.operator.is_operator else None,
                comment=_("Kiruvchi qo'ng'iroqdan avtomatik yaratildi"),
            )
    if call.lead and call.lead.operator_id is None and call.operator and call.operator.is_operator:
        call.lead.operator = call.operator
        call.lead.save(update_fields=["operator", "updated_at"])

    if event == "answer":
        call.status = PhoneCall.Status.ANSWERED
        call.answered_at = call.answered_at or now
    elif event == "hangup":
        disposition = params.get("disposition", "").upper()
        call.status = DISPOSITIONS.get(disposition, call.status if call.answered_at else PhoneCall.Status.NO_ANSWER)
        duration = params.get("duration", "")
        if duration.isdigit():
            call.duration = int(duration)
        elif call.answered_at:
            call.duration = int((now - call.answered_at).total_seconds())
        call.ended_at = now
    call.save()
    return JsonResponse({"ok": True, "call_id": call.pk, "lead_id": call.lead_id})


@login_required
def poll(request):
    """Brauzer har bir necha soniyada so'raydi: operatorga hozir jiringlayotgan kiruvchi qo'ng'iroqlar."""
    user = request.user
    if not (user.is_operator or user.is_manager) or not user.sip_extension:
        return JsonResponse({"calls": []})
    since = timezone.now() - timedelta(seconds=90)
    calls = (
        PhoneCall.objects.filter(direction=PhoneCall.Direction.INCOMING, started_at__gte=since, ended_at__isnull=True)
        .filter(extension__in=[user.sip_extension, ""])
        .select_related("lead")
    )
    data = []
    for call in calls:
        if call.status == PhoneCall.Status.ANSWERED and call.operator_id not in (None, user.pk):
            continue
        data.append(
            {
                "id": call.pk,
                "phone": call.phone,
                "status": call.status,
                "lead_name": call.lead.full_name if call.lead else "",
                "lead_status": call.lead.get_status_display() if call.lead else "",
                "url": reverse("crm:lead_detail", args=[call.lead_id]) if call.lead_id else "",
            }
        )
    return JsonResponse({"calls": data})


@csrf_exempt
@require_POST
def upload_recording(request):
    """Asterisk MixMonitor yozuvni tugatgach faylni shu yerga yuklaydi (multipart: token, uniqueid yoki call_id, file)."""
    if not _token_ok(request.POST):
        return HttpResponseForbidden("bad token")
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"ok": False, "error": "file required"}, status=400)
    call_id = request.POST.get("call_id", "")
    uniqueid = request.POST.get("uniqueid", "")
    call = None
    if call_id.isdigit():
        call = PhoneCall.objects.filter(pk=call_id).first()
    if call is None and uniqueid:
        call = PhoneCall.objects.filter(uniqueid=uniqueid).first()
    if call is None:
        return JsonResponse({"ok": False, "error": "unknown call"}, status=404)
    try:
        name, mp3, tmpdir = to_mp3(upload)
    except ConversionError as exc:
        return JsonResponse({"ok": False, "error": f"mp3 conversion failed: {exc}"}, status=500)
    try:
        if call.recording:
            call.recording.delete(save=False)
        call.recording.save(f"{call.pk}_{name}", mp3, save=True)
    finally:
        if tmpdir:
            mp3.close()
            shutil.rmtree(tmpdir, ignore_errors=True)
    return JsonResponse({"ok": True, "call_id": call.pk, "file": call.recording.name})


@login_required
def recording(request, pk):
    call = get_object_or_404(PhoneCall, pk=pk)
    user = request.user
    allowed = user.is_manager or call.operator_id == user.pk or (
        call.lead_id and visible_leads(user).filter(pk=call.lead_id).exists()
    )
    if not allowed or not call.recording:
        raise Http404
    try:
        handle = call.recording.open("rb")
    except FileNotFoundError:
        raise Http404
    content_type = mimetypes.guess_type(call.recording.name)[0] or "audio/mpeg"
    # FileResponse Range so'rovlarini qo'llaydi — pleerda oldinga/orqaga surish ishlaydi
    return FileResponse(handle, content_type=content_type, filename=os.path.basename(call.recording.name))
