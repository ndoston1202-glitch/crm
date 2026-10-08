import io
import shutil
import tempfile
import wave
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Lead

from .models import PhoneCall

User = get_user_model()
MEDIA = tempfile.mkdtemp()


def wav_bytes():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x10" * 8000)
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class MobileApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.op = User.objects.create_user("op", password="pass12345", role=User.Role.OPERATOR)
        self.srv = User.objects.create_user("srv", password="pass12345", role=User.Role.SERVICE)

    def login(self, username="op"):
        return self.client.post(reverse("telephony:mobile_login"), {"username": username, "password": "pass12345"})

    def auth(self):
        return {"HTTP_AUTHORIZATION": "Token " + self.login().json()["token"]}

    def test_login(self):
        self.assertEqual(self.client.post(reverse("telephony:mobile_login"), {"username": "op", "password": "bad"}).status_code, 401)
        self.assertEqual(self.login("srv").status_code, 403)
        headers = self.auth()
        self.assertEqual(self.client.get(reverse("telephony:mobile_me"), **headers).json()["name"], "op")
        self.assertEqual(self.client.get(reverse("telephony:mobile_me"), HTTP_AUTHORIZATION="Token nope").status_code, 401)
        self.client.post(reverse("telephony:mobile_logout"), **headers)
        self.assertEqual(self.client.get(reverse("telephony:mobile_me"), **headers).status_code, 401)

    def upload(self, headers, client_id="42_1000", phone="+998 90 111 22 33", name="rec.mp3", data=b"ID3mp3"):
        return self.client.post(
            reverse("telephony:mobile_upload"),
            {"file": SimpleUploadedFile(name, data), "phone": phone, "direction": "out",
             "started_at": "1790000000000", "duration": "95", "client_id": client_id},
            **headers,
        )

    def test_upload_links_existing_lead_and_dedupes(self):
        lead = Lead.objects.create(full_name="Vali", phone="901112233", operator=self.op)
        headers = self.auth()
        resp = self.upload(headers)
        self.assertEqual(resp.status_code, 200, resp.content)
        call = PhoneCall.objects.get()
        self.assertEqual((call.lead, call.source, call.direction, call.duration), (lead, "mobile", "out", 95))
        self.assertEqual(call.started_at.timestamp(), 1790000000)
        self.assertTrue(call.recording.name.endswith(".mp3"))
        self.assertTrue(self.upload(headers).json()["duplicate"])
        self.assertEqual(PhoneCall.objects.count(), 1)

    def test_upload_unknown_number_creates_lead(self):
        self.upload(self.auth(), phone="935554433")
        lead = Lead.objects.get()
        self.assertEqual((lead.phone_norm, lead.operator, lead.source), ("935554433", self.op, Lead.Source.CALL))

    def test_upload_requires_token_and_phone(self):
        self.assertEqual(self.upload({}).status_code, 401)
        self.assertEqual(self.upload(self.auth(), phone="12").status_code, 400)

    @skipUnless(shutil.which("ffmpeg"), "ffmpeg kerak")
    def test_manual_upload_from_lead_card(self):
        lead = Lead.objects.create(full_name="Vali", phone="901112233", operator=self.op)
        self.client.force_login(self.op)
        resp = self.client.post(
            reverse("telephony:manual_upload", args=[lead.pk]),
            {"file": SimpleUploadedFile("iphone.wav", wav_bytes()), "direction": "in"},
        )
        self.assertEqual(resp.status_code, 302)
        call = PhoneCall.objects.get()
        self.assertEqual((call.source, call.direction), ("manual", "in"))
        self.assertTrue(call.recording.name.endswith("iphone.mp3"))
        self.assertContains(self.client.get(reverse("crm:lead_detail", args=[lead.pk])), reverse("telephony:recording", args=[call.pk]))

    def test_mobile_app_page(self):
        self.client.force_login(self.op)
        resp = self.client.get(reverse("telephony:mobile_app"))
        self.assertContains(resp, "CRM-yozuvlar.apk")
