import os
import shutil
import subprocess
import tempfile

from django.core.files import File


class ConversionError(Exception):
    pass


def to_mp3(upload):
    """Yuklangan yozuvni (wav, gsm, ogg...) MP3 ga aylantiradi. ffmpeg talab qilinadi.

    (fayl_nomi, File) qaytaradi; chaqiruvchi saqlagach vaqtinchalik papkani o'chirish uchun tmpdir ham qaytariladi.
    """
    base = os.path.splitext(os.path.basename(upload.name))[0] or "recording"
    if upload.name.lower().endswith(".mp3"):
        return f"{base}.mp3", upload, None
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ConversionError("ffmpeg o'rnatilmagan")
    tmpdir = tempfile.mkdtemp(prefix="crm-rec-")
    src = os.path.join(tmpdir, "input" + os.path.splitext(upload.name)[1])
    dst = os.path.join(tmpdir, "output.mp3")
    with open(src, "wb") as fh:
        for chunk in upload.chunks():
            fh.write(chunk)
    # Mono, 64 kbit/s — so'zlashuv uchun yetarli va kam joy egallaydi
    result = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k", dst],
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0 or not os.path.getsize(dst):
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ConversionError(result.stderr.decode(errors="replace")[:300])
    return f"{base}.mp3", File(open(dst, "rb")), tmpdir
