# -*- coding: utf-8 -*-
"""
גיבוי לימים שבהם שירות הקול של edge-tts לא עונה: בונה את הפרקים בקול העברי
שמותקן ב-Windows (Microsoft Asaf), בלי רשת.

  cd podcast && python build_local.py          # כל הפרקים
  python build_local.py 03                     # פרק מסוים

במה זה שונה מ-build.py:
  * קוראים את התסריטים הלא מנוקדים (scripts/plain/), ומורידים מהם גם ניקוד ידני. הקול
    המקומי קורא טוב יותר כתיב מלא בלי ניקוד (נבדק בתמלול: עם ניקוד, „לטווח״ נשמע „לטווחה״).
  * יש רק קול אחד, גברי. שורות המראיינת (ש:) עוברות הגבהה של גובה הצליל, כדי שיהיה ברור
    מי מדבר.
  * נכתב הקובץ mp3/LOCAL_VOICE, ודף הנגן מציין שזו גרסה זמנית. build.py מוחק אותו כשהוא
    בונה מחדש את כל הפרקים בקולות הרגילים.
"""
import os
import re
import subprocess
import sys

import build as B

PLAIN = os.path.join(B.SCRIPTS, "plain")
PS1 = os.path.join(B.HERE, "tts_local.ps1")
MARK = os.path.join(B.OUT, "LOCAL_VOICE")
SPEAKER = {v: k for k, v in B.VOICES.items()}        # שם הקול של edge -> אות הדובר
FILTER = {"א": None, "ש": "rubberband=pitch=1.2"}    # המראיינת: אותו קול, גבוה יותר
NIKUD = re.compile("[֑-ׇ]")

# איות לקול המקומי, אחרי הורדת הניקוד. נבדק בתמלול (faster-whisper) של משפטים קצרים:
# בלי ההחלפה, „חוק ובר״ נשמע „עובר״, „התקה״ נשמע „התקעה״, „בעוצמה״ נשמע „בעובצמה״,
# „כהנמן״ נשמע „קונמן״, ו„איי בי אם״ נשמע „IBM״. מילה מנוקדת בכתיב מלא נקראת נכון.
RESPELL = [
    ("חוק ובר", "חוק וֶבֶּר"),
    ("כהנמן", "כַּהֲנֶמָן"),
    ("איי בי אם", "אֵיי בִּי אֶם"),
    ("בעוצמה", "בְּעוֹצְמָה"),
    ("התקה", "הַתָּקָה"),
    ("אינרציה", "אִינֶרְצְיָה"),
]


def local_text(text):
    text = NIKUD.sub("", text)
    for old, new in RESPELL:
        text = text.replace(old, new)
    return text


def pieces_for(path, jobs):
    """מחזיר (כותרת, מספר, רשימת קטעים). קטע דיבור שעוד אין לו WAV נוסף ל-jobs."""
    title, parts = B.parse(path)
    num = re.match(r"^(\d+)", os.path.basename(path)).group(1)
    out = []
    for p in parts:
        if p[0] == "gap":
            out.append(("gap", p[1]))
            continue
        who, text = SPEAKER[p[1]], local_text(p[2])
        base = B.cache_path("loc", who + "|" + str(FILTER[who]) + "|" + text)[:-4]     # בלי הסיומת
        if not os.path.exists(base + ".mp3") and not os.path.exists(base + ".wav"):
            jobs.append((base + ".wav", text))
        out.append(("say", who, base))
    return title, num, out


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    os.makedirs(B.CACHE, exist_ok=True)
    os.makedirs(B.OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(PLAIN) if f.endswith(".txt"))
    if only:
        files = [f for f in files if any(f.startswith(o) for o in only)]
    if not files:
        sys.exit("לא נמצאו תסריטים ב-scripts/plain/")

    jobs, episodes = [], []
    for f in files:
        episodes.append(pieces_for(os.path.join(PLAIN, f), jobs))

    if jobs:
        print(f"מסנתז {len(jobs)} שורות בקול המקומי…")
        jobfile = os.path.join(B.CACHE, "local_jobs.tsv")
        with open(jobfile, "w", encoding="utf-8") as fh:
            for wav, text in dict(jobs).items():
                fh.write(wav + "\t" + text + "\n")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", PS1, "-Jobs", jobfile], capture_output=True)
        if r.returncode:
            sys.exit("הסינתזה המקומית נכשלה:\n" + (r.stdout + r.stderr).decode("utf-8", "replace")[-1500:])

    for title, num, parts in episodes:
        listed = []
        for p in parts:
            if p[0] == "gap":
                listed.append(B.silence(p[1]))
                continue
            _, who, base = p
            if not os.path.exists(base + ".mp3"):
                af = ["-af", FILTER[who]] if FILTER[who] else []
                B.sh(["ffmpeg", "-v", "error", "-y", "-i", base + ".wav", *af, *B.AUDIO_ARGS, base + ".mp3"])
                os.remove(base + ".wav")
            listed.append(base + ".mp3")

        out = os.path.join(B.OUT, f"{num} - {title}.mp3")
        for old in os.listdir(B.OUT):
            if old.startswith(num + " - ") and old != os.path.basename(out):
                os.remove(os.path.join(B.OUT, old))
        listfile = os.path.join(B.CACHE, f"list_{num}.txt")
        with open(listfile, "w", encoding="utf-8") as fh:
            for p in listed:
                fh.write("file '" + p.replace("\\", "/").replace("'", r"'\''") + "'\n")
        B.sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
              "-i", listfile, *B.AUDIO_ARGS,
              "-metadata", f"title={num} · {title}",
              "-metadata", f"album={B.ALBUM}",
              "-metadata", f"artist={B.COURSE}",
              "-metadata", f"track={int(num)}",
              "-metadata", "genre=Education",
              "-id3v2_version", "3",
              out])
        d = B.duration(out)
        print(f"▸ {os.path.basename(out)}  {int(d // 60)}:{int(d % 60):02d}")

    with open(MARK, "w", encoding="utf-8") as fh:
        fh.write("הפרקים נבנו ב-build_local.py, בקול המקומי של Windows.\n")
    rows = B.write_index()
    print(f"סה״כ {len(rows)} פרקים · {B.hebrew_duration(sum(r[3] for r in rows))}")


if __name__ == "__main__":
    main()
