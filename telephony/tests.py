import shutil
import socketserver
import tempfile
import threading

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Call, Lead

from .models import PhoneCall
from .utils import normalize_phone

User = get_user_model()
TOKEN = "secret-token"
MEDIA = tempfile.mkdtemp()


class FakeAmiHandler(socketserver.StreamRequestHandler):
    received = []

    def handle(self):
        self.wfile.write(b"Asterisk Call Manager/7.0\r\n")
        block = []
        while True:
            line = self.rfile.readline()
            if not line:
                return
            line = line.decode().strip()
            if line:
                block.append(line)
                continue
            if not block:
                continue
            FakeAmiHandler.received.append(block)
            action = block[0].split(": ", 1)[1]
            block = []
            if action == "Logoff":
                return
            self.wfile.write(b"Response: Success\r\nMessage: OK\r\n\r\n")


def asterisk_settings(port=0):
    return {
        "AMI_HOST": "127.0.0.1" if port else "",
        "AMI_PORT": port,
        "AMI_USER": "crm",
        "AMI_SECRET": "x",
        "AMI_TIMEOUT": 2,
        "CHANNEL_TEMPLATE": "PJSIP/{extension}",
        "OUTBOUND_CONTEXT": "crm-outbound",
        "ORIGINATE_TIMEOUT": 30,
        "WEBHOOK_TOKEN": TOKEN,
    }


@override_settings(ASTERISK=asterisk_settings(), MEDIA_ROOT=MEDIA)
class TelephonyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.op = User.objects.create_user("op", password="x", role=User.Role.OPERATOR, sip_extension="101")
        self.op2 = User.objects.create_user("op2", password="x", role=User.Role.OPERATOR, sip_extension="102")
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)

    def hook(self, **params):
        return self.client.get(reverse("telephony:webhook"), {"token": TOKEN, **params})

    def test_normalize(self):
        self.assertEqual(normalize_phone("+998 (90) 123-45-67"), "901234567")
        self.assertEqual(normalize_phone("901234567"), "901234567")

    def test_bad_token(self):
        resp = self.client.get(reverse("telephony:webhook"), {"token": "no", "event": "ring", "phone": "1"})
        self.assertEqual(resp.status_code, 403)

    def test_incoming_new_number_creates_lead_and_popup(self):
        self.assertEqual(self.hook(event="ring", uniqueid="u1", phone="+998901112233").status_code, 200)
        lead = Lead.objects.get(phone_norm="901112233")
        self.assertEqual(lead.source, Lead.Source.CALL)

        self.client.force_login(self.op)
        calls = self.client.get(reverse("telephony:poll")).json()["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], reverse("crm:lead_detail", args=[lead.pk]))

        self.hook(event="answer", uniqueid="u1", extension="101")
        lead.refresh_from_db()
        self.assertEqual(lead.operator, self.op)
        # boshqa operatorga endi oyna chiqmaydi
        self.client.force_login(self.op2)
        self.assertEqual(self.client.get(reverse("telephony:poll")).json()["calls"], [])

        self.hook(event="hangup", uniqueid="u1", disposition="ANSWER", duration="75")
        call = PhoneCall.objects.get(uniqueid="u1")
        self.assertEqual((call.status, call.duration, call.operator), (PhoneCall.Status.ANSWERED, 75, self.op))

    def test_incoming_existing_lead_matched(self):
        lead = Lead.objects.create(full_name="Vali", phone="+998 90 111-22-33", operator=self.op2)
        self.hook(event="ring", uniqueid="u2", phone="901112233")
        self.assertEqual(PhoneCall.objects.get().lead, lead)
        self.assertEqual(Lead.objects.count(), 1)

    def test_missed_call(self):
        self.hook(event="ring", uniqueid="u3", phone="901112233")
        self.hook(event="hangup", uniqueid="u3", disposition="NOANSWER", duration="0")
        self.assertEqual(PhoneCall.objects.get().status, PhoneCall.Status.NO_ANSWER)

    def test_recording_upload_and_listen(self):
        lead = Lead.objects.create(full_name="Vali", phone="901112233", operator=self.op)
        self.hook(event="ring", uniqueid="u4", phone="901112233")
        self.hook(event="answer", uniqueid="u4", extension="101")
        self.hook(event="hangup", uniqueid="u4", disposition="ANSWER", duration="12")
        audio = SimpleUploadedFile("u4.mp3", b"ID3fake-audio", content_type="audio/mpeg")
        resp = self.client.post(reverse("telephony:upload_recording"), {"token": TOKEN, "uniqueid": "u4", "file": audio})
        self.assertEqual(resp.status_code, 200, resp.content)
        call = PhoneCall.objects.get()
        self.assertTrue(call.recording.name.endswith(".mp3"))

        # operator natija yozadi -> izoh shu qo'ng'iroqqa bog'lanadi
        self.client.force_login(self.op)
        self.client.post(reverse("crm:call_add", args=[lead.pk]), {"result": "answered", "note": "Narxni so'radi", "new_status": "interested"})
        self.assertEqual(Call.objects.get().phone_call, call)

        page = self.client.get(reverse("crm:lead_detail", args=[lead.pk]))
        self.assertContains(page, reverse("telephony:recording", args=[call.pk]))
        self.assertContains(page, "Narxni so&#x27;radi")
        resp = self.client.get(reverse("telephony:recording", args=[call.pk]))
        self.assertEqual(b"".join(resp.streaming_content), b"ID3fake-audio")
        self.assertEqual(resp["Content-Type"], "audio/mpeg")

        # begona operator eshita olmaydi
        self.client.force_login(self.op2)
        self.assertEqual(self.client.get(reverse("telephony:recording", args=[call.pk])).status_code, 404)

    def test_upload_requires_token(self):
        audio = SimpleUploadedFile("x.wav", b"x")
        resp = self.client.post(reverse("telephony:upload_recording"), {"token": "bad", "uniqueid": "u", "file": audio})
        self.assertEqual(resp.status_code, 403)

    def test_click_to_call_without_ami(self):
        lead = Lead.objects.create(full_name="Vali", phone="901112233", operator=self.op)
        self.client.force_login(self.op)
        resp = self.client.post(reverse("telephony:click_to_call", args=[lead.pk]))
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(PhoneCall.objects.get().status, PhoneCall.Status.FAILED)

    def test_click_to_call_via_ami(self):
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeAmiHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        FakeAmiHandler.received = []
        lead = Lead.objects.create(full_name="Vali", phone="+998 90 111-22-33", operator=self.op)
        self.client.force_login(self.op)
        with self.settings(ASTERISK=asterisk_settings(server.server_address[1])):
            resp = self.client.post(reverse("telephony:click_to_call", args=[lead.pk]))
        self.assertEqual(resp.status_code, 200, resp.content)
        call = PhoneCall.objects.get()
        originate = next(b for b in FakeAmiHandler.received if "Action: Originate" in b)
        self.assertIn("Channel: PJSIP/101", originate)
        self.assertIn("Exten: 998901112233", originate)
        self.assertIn(f"Variable: CRM_CALL_ID={call.pk}", originate)

        # Asterisk call_id bilan hodisa yuboradi
        self.hook(event="answer", call_id=call.pk)
        self.hook(event="hangup", call_id=call.pk, disposition="ANSWER", duration="30")
        call.refresh_from_db()
        self.assertEqual((call.status, call.duration), (PhoneCall.Status.ANSWERED, 30))

    def test_reports_show_phone_stats(self):
        self.hook(event="ring", uniqueid="u5", phone="901112233", extension="101")
        self.hook(event="hangup", uniqueid="u5", disposition="NOANSWER")
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("crm:reports"))
        self.assertEqual(resp.context["phone"]["missed"], 1)
