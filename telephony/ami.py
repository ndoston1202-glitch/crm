"""Asterisk Manager Interface (AMI) uchun minimal klient — faqat Originate (bir bosishda qo'ng'iroq)."""
import socket

from django.conf import settings


class AmiError(Exception):
    pass


def _read_message(sock_file):
    lines = {}
    while True:
        line = sock_file.readline()
        if not line:
            raise AmiError("AMI ulanishi uzildi")
        line = line.decode(errors="replace").strip()
        if not line:
            if lines:
                return lines
            continue
        key, _, value = line.partition(":")
        lines[key.strip()] = value.strip()


def _send(sock, **fields):
    data = "".join(f"{k}: {v}\r\n" for k, v in fields.items()) + "\r\n"
    sock.sendall(data.encode())


def originate(extension, phone, variables=None):
    """Avval operatorning ichki raqamini chaqiradi, u javob bergach mijoz raqamini teradi."""
    cfg = settings.ASTERISK
    if not cfg["AMI_HOST"]:
        raise AmiError("ASTERISK_AMI_HOST sozlanmagan")
    try:
        sock = socket.create_connection((cfg["AMI_HOST"], cfg["AMI_PORT"]), timeout=cfg["AMI_TIMEOUT"])
    except OSError as exc:
        raise AmiError(f"AMI serverga ulanib bo'lmadi: {exc}") from exc
    with sock:
        f = sock.makefile("rb")
        f.readline()  # "Asterisk Call Manager/x.y" salomlashuvi
        _send(sock, Action="Login", Username=cfg["AMI_USER"], Secret=cfg["AMI_SECRET"], Events="off", ActionID="login")
        resp = _read_message(f)
        if resp.get("Response") != "Success":
            raise AmiError(resp.get("Message", "AMI login xatosi"))
        fields = {
            "Action": "Originate",
            "ActionID": "crm-originate",
            "Channel": cfg["CHANNEL_TEMPLATE"].format(extension=extension),
            "Context": cfg["OUTBOUND_CONTEXT"],
            "Exten": phone,
            "Priority": 1,
            "CallerID": f"CRM <{phone}>",
            "Timeout": cfg["ORIGINATE_TIMEOUT"] * 1000,
            "Async": "true",
        }
        lines = "".join(f"Variable: {k}={v}\r\n" for k, v in (variables or {}).items())
        data = "".join(f"{k}: {v}\r\n" for k, v in fields.items()) + lines + "\r\n"
        sock.sendall(data.encode())
        resp = _read_message(f)
        _send(sock, Action="Logoff")
        if resp.get("Response") != "Success":
            raise AmiError(resp.get("Message", "Originate xatosi"))
        return resp
