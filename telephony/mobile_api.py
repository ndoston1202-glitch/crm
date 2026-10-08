"""Android ilova uchun API: kirish va telefonning o'z yozuvchisi yozgan qo'ng'iroq yozuvlarini yuklash."""
import secrets
import shutil
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from crm.models import Lead

from .audio import ConversionError, to_mp3
from .models import PhoneCall
from .utils import normalize_phone

User = get_user_model()


def token_required(view):
    @csrf_exempt
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[6:].strip() if header.startswith("Token ") else ""
        user = User.objects.filter(api_token=token, is_active=True).first() if token else None
        if user is None:
            return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)
        request.user = user
        return view(request, *args, **kwargs)

    return wrapper


@csrf_exempt
@require_POST
def login(request):
    user = authenticate(request, username=request.POST.get("username", ""), password=request.POST.get("password", ""))
    if user is None or not user.is_active:
        return JsonResponse({"ok": False, "error": _("Login yoki parol noto'g'ri")}, status=401)
    if not user.can("phone_app"):
        return JsonResponse({"ok": False, "error": _("Ilova faqat operatorlar uchun")}, status=403)
    if not user.api_token:
        user.api_token = secrets.token_urlsafe(32)
        user.save(update_fields=["api_token"])
    return JsonResponse({"ok": True, "token": user.api_token, "name": str(user)})


@token_required
def me(request):
    return JsonResponse({"ok": True, "name": str(request.user)})


@token_required
@require_POST
def logout(request):
    request.user.api_token = None
    request.user.save(update_fields=["api_token"])
    return JsonResponse({"ok": True})


def save_recording(call, upload):
    name, mp3, tmpdir = to_mp3(upload)
    try:
        if call.recording:
            call.recording.delete(save=False)
        call.recording.save(f"{call.pk}_{name}", mp3, save=True)
    finally:
        if tmpdir:
            mp3.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


@token_required
@require_POST
def upload(request):
    """multipart: file, phone, direction (in|out), started_at (epoch ms), duration (s), client_id."""
    user = request.user
    upload_file = request.FILES.get("file")
    phone = "".join(ch for ch in request.POST.get("phone", "") if ch.isdigit() or ch == "+")
    client_id = request.POST.get("client_id", "")[:120] or None
    if not upload_file or len(normalize_phone(phone)) < 7:
        return JsonResponse({"ok": False, "error": "file and phone required"}, status=400)
    if client_id and PhoneCall.objects.filter(client_id=client_id).exists():
        return JsonResponse({"ok": True, "duplicate": True})

    started = timezone.now()
    started_ms = request.POST.get("started_at", "")
    if started_ms.isdigit():
        started = datetime.fromtimestamp(int(started_ms) / 1000, tz=dt_timezone.utc)
    duration = request.POST.get("duration", "")
    duration = int(duration) if duration.isdigit() else 0

    lead = Lead.objects.filter(phone_norm=normalize_phone(phone)).order_by("-created_at").first()
    if lead is None:
        lead = Lead(
            full_name=phone,
            phone=phone,
            source=Lead.Source.CALL,
            operator=user if user.is_operator else None,
            comment=_("Telefon ilovasi orqali qo'ng'iroqdan avtomatik yaratildi"),
        )
        lead._actor_id = user.pk
        lead.save()

    try:
        call = PhoneCall.objects.create(
            source=PhoneCall.Source.MOBILE,
            client_id=client_id,
            direction=PhoneCall.Direction.OUTGOING if request.POST.get("direction") == "out" else PhoneCall.Direction.INCOMING,
            status=PhoneCall.Status.ANSWERED,
            phone=phone,
            lead=lead,
            operator=user,
            duration=duration,
        )
    except IntegrityError:  # parallel ikkinchi yuklash
        return JsonResponse({"ok": True, "duplicate": True})
    # started_at auto_now_add — haqiqiy qo'ng'iroq vaqtini alohida yozamiz (obyektda ham, keyingi save uchun)
    call.started_at = call.answered_at = started
    call.ended_at = started + timedelta(seconds=duration)
    PhoneCall.objects.filter(pk=call.pk).update(started_at=call.started_at, answered_at=started, ended_at=call.ended_at)
    try:
        save_recording(call, upload_file)
    except ConversionError as exc:
        call.delete()
        return JsonResponse({"ok": False, "error": f"mp3 conversion failed: {exc}"}, status=500)
    return JsonResponse({"ok": True, "call_id": call.pk, "lead_id": lead.pk})


# ---------- Ilovaning o'zini yangilashi ----------
RELEASE_DIR = settings.BASE_DIR / "mobile" / "release"


def _release_info():
    import json

    try:
        info = json.loads((RELEASE_DIR / "version.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (RELEASE_DIR / "CRM-yozuvlar.apk").is_file():
        return None
    return info


@token_required
def app_version(request):
    info = _release_info()
    if info is None:
        return JsonResponse({"ok": False, "error": "no release"}, status=404)
    return JsonResponse({"ok": True, **info})


def app_download(request):
    """APK: telefon ilovasi (token) yoki CRM'ga kirgan foydalanuvchi (brauzer) yuklab oladi."""
    from django.http import FileResponse, Http404

    header = request.headers.get("Authorization", "")
    token = header[6:].strip() if header.startswith("Token ") else ""
    allowed = (token and User.objects.filter(api_token=token, is_active=True).exists()) or (
        request.user.is_authenticated
    )
    if not allowed:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path())
    apk = RELEASE_DIR / "CRM-yozuvlar.apk"
    if not apk.is_file():
        raise Http404
    return FileResponse(open(apk, "rb"), as_attachment=True, filename="CRM-yozuvlar.apk",
                        content_type="application/vnd.android.package-archive")
