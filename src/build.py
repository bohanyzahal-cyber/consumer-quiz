"""בונה את index.html מהתבנית + בנקי השאלות.

הרצה:  python build.py      (מתוך התיקייה הזו)
כותב גם ל-consumer-quiz/index.html וגם לעותק הנוח בתיקיית הקורס, ואת דף העזר sheet.html
(מהמקור src/sheet.html). אחרי בניית פודקאסט (podcast/build.py) מריצים שוב, כדי שהקישורים אליו יופיעו.

סכמת שאלה (בקובצי bank*.js):
  {l:3, t:"נושא", s:"מקור", q:"השאלה", o:["1","2","3","4","5"], c:1, e:"הסבר"}
  l = מספר היחידה (1-5), c = אינדקס התשובה הנכונה לפני הערבוב.
לכל שאלה חמש תשובות, כמו בדף התרגול של המרצה. האתר מערבב את סדר התשובות בכל סבב,
ולכן אין לכתוב תשובות תלויות מיקום («כל התשובות נכונות»).
הצינור הועתק מהאתר management-quiz (שיטות וכלי ניהול מתקדמים).
"""
import os, sys, re, glob, json, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE   = os.path.dirname(os.path.abspath(__file__))
REPO   = os.path.dirname(HERE)                     # .../consumer-quiz
COURSE = os.path.dirname(REPO)                     # תיקיית הקורס
NOPT   = 5

LNAME = {1: "הצרכן החדש (רקע)", 2: "הכרה בצורך וערכים", 3: "תפיסה", 4: "זיכרון", 5: "מעורבות"}

# (קובץ יעד, דף העזר שלצידו, דף הנגן של הפודקאסט) — כל קישור יחסי לתיקייה של הקובץ עצמו
TARGETS = [
    (os.path.join(REPO, "index.html"), "sheet.html", "podcast/index.html"),
    (os.path.join(COURSE, "בוחן תרגול - התנהגות צרכנים.html"),
     "consumer-quiz/sheet.html", "consumer-quiz/podcast/index.html"),
]

def bank_files():
    fs = glob.glob(os.path.join(HERE, "bank*.js"))
    return sorted(fs, key=lambda f: int(re.search(r"bank(\d+)", os.path.basename(f)).group(1)))

tpl  = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
bank = "\n".join(open(f, encoding="utf-8").read() for f in bank_files())
html = tpl.replace("/*__BANK__*/", bank).replace("/*__READY__*/", "var READY=[];")

# קישורים לעזרים נוספים (דף עזר להדפסה, פודקאסט) — כל אחד מוצג רק אם הקובץ קיים
SHEET_SRC   = os.path.join(HERE, "sheet.html")
HAS_PODCAST = os.path.exists(os.path.join(REPO, "podcast", "index.html"))
def aids_for(sheet_href, podcast_href):
    items = []
    if os.path.exists(SHEET_SRC):
        items.append('<a class="aid" href="' + sheet_href + '" target="_blank" rel="noopener">'
                     '<i>📄</i><span><b>דף עזר להדפסה</b> · כל החומר לבחינה בכמה עמודים — מותר להכניס חומר מודפס</span></a>')
    if HAS_PODCAST:
        items.append('<a class="aid" href="' + podcast_href + '" target="_blank" rel="noopener">'
                     '<i>🎧</i><span><b>פודקאסט</b> · פרק לכל נושא, עם שאלות לדרך — להאזנה בדרכים</span></a>')
    return ('<div class="aids">' + "".join(items) + "</div>") if items else ""

for t, sheet_href, podcast_href in TARGETS:
    open(t, "w", encoding="utf-8", newline="\n").write(html.replace("<!--AIDS-->", aids_for(sheet_href, podcast_href)))
    print("נכתב:", t)
print("גודל: %.0f KB" % (len(html) / 1024))

# דף העזר: המקור ב-src/sheet.html. הקישור לפודקאסט נכנס רק אם דף הנגן כבר נבנה.
if os.path.exists(SHEET_SRC):
    sheet = open(SHEET_SRC, encoding="utf-8").read()
    link = '<a href="podcast/index.html">🎧 פודקאסט</a>' if HAS_PODCAST else ""
    out = os.path.join(REPO, "sheet.html")
    open(out, "w", encoding="utf-8", newline="\n").write(sheet.replace("<!--PODCAST-->", link))
    print("נכתב:", out)

# ---------- סטטיסטיקה ----------
objs = re.findall(r'\{l:(\d+),t:"(.*?)",s:"(.*?)",q:', bank)
objs = [(int(l), t, s) for l, t, s in objs]
print("\nשאלות:", len(objs))
lects, topics, srcs = {}, {}, {}
for l, t, s in objs:
    lects[l]  = lects.get(l, 0) + 1
    topics[t] = topics.get(t, 0) + 1
    srcs[s]   = srcs.get(s, 0) + 1
print("\nלפי יחידה:")
for k in sorted(lects):
    print("  יחידה %-3d %3d  %s" % (k, lects[k], LNAME.get(k, "")))
print("לפי נושא:")
for k, v in topics.items():
    print("  %-34s %3d" % (k, v))
print("לפי מקור:")
for k, v in sorted(srcs.items(), key=lambda x: -x[1]):
    print("  %-16s %3d" % (k, v))
cs = re.findall(r',c:(\d),e:"', bank)
dist = {}
for c in cs:
    dist[c] = dist.get(c, 0) + 1
print("\nפיזור מיקום התשובה הנכונה במקור:", dict(sorted(dist.items())))
if len(cs) != len(objs):
    print("!! אזהרה: לא כל השאלות נותחו (%d מתוך %d)" % (len(cs), len(objs)))

# ---------- עדכון אוטומטי של ה-README ----------
def update_readme():
    path = os.path.join(REPO, "README.md")
    if not os.path.exists(path):
        return
    txt = open(path, encoding="utf-8").read()
    start, end = "<!-- STATS:START", "<!-- STATS:END -->"
    i, j = txt.find(start), txt.find(end)
    if i < 0 or j < 0:
        return
    lines = ["| יחידה | נושא | שאלות |", "|---|---|---|"]
    for k in sorted(lects):
        lines.append("| %d | %s | %d |" % (k, LNAME.get(k, ""), lects[k]))
    src_line = " · ".join("%s (%d)" % (k, v) for k, v in sorted(srcs.items(), key=lambda x: -x[1]))
    top_line = " · ".join("%s (%d)" % (k, v) for k, v in topics.items())
    block = (
        "<!-- STATS:START — נוצר אוטומטית על ידי src/build.py, אין לערוך ידנית -->\n"
        "**%d שאלות** רב-ברירתיות (אמריקאיות), חמש תשובות לכל שאלה.\n\n"
        "%s\n\n"
        "**לפי מקור:** %s\n\n"
        "**נושאים:** %s\n"
        % (len(objs), "\n".join(lines), src_line, top_line)
    )
    open(path, "w", encoding="utf-8", newline="\n").write(txt[:i] + block + txt[j:])
    print("עודכן:", path)

update_readme()

# ---------- בדיקות מבנה ----------
STRUCT = r"""
const fs=require('fs');
eval(fs.readFileSync(process.argv[2],'utf8'));
const N=+process.argv[3];
/* דפוסים תלויי-מיקום: האפליקציה מערבבת את סדר האפשרויות בכל סבב,
   ולכן מסיח כמו "כל התשובות נכונות" או "תשובות 1 ו-2" נשבר. */
const POS=/כל התשובות נכונות|כל ההיגדים נכונים|כל הנ["״']ל|תשובות? א['׳']\s*(\+|ו)|תשובות? \d\s*(\+|ו)|אף תשובה אינה|כל האמור לעיל|אף אחת מהתשובות|אף אחת מן התשובות|כל האפשרויות/;
const err=[], seen={};
BANK.forEach((q,i)=>{
  const at=`#${i} ${(q.q||'').slice(0,40)}`;
  if(typeof q.l!=='number'||q.l<1||q.l>5)  err.push(at+' — מספר יחידה חסר/שגוי');
  if(!q.t||!q.s||!q.q||!q.e)             err.push(at+' — שדה חסר');
  if(!Array.isArray(q.o)||q.o.length!==N) err.push(at+' — אין בדיוק '+N+' אפשרויות');
  else if(new Set(q.o).size!==N)          err.push(at+' — אפשרות כפולה');
  if(typeof q.c!=='number'||q.c<0||q.c>=N) err.push(at+' — c מחוץ לתחום');
  if((q.o||[]).some(o=>POS.test(o)))      err.push(at+' — מסיח תלוי-מיקום');
  (q.o||[]).forEach((o)=>{
    const w=String(o).split(/\s+/);
    for(let k=0;k+1<w.length;k++){
      if(w[k].length>=4 && w[k]===w[k+1]) { err.push(at+' — מילה כפולה ברצף: "'+w[k]+'"'); break; }
    }
  });
  if((q.e||'').length<40)                 err.push(at+' — הסבר קצר מדי');
  if(seen[q.q]!==undefined)               err.push(at+' — שאלה כפולה (גם ב-#'+seen[q.q]+')');
  else seen[q.q]=i;
});

/* מפתח תשובה שגוי: c מצביע על מסיח בעוד ההסבר מתאר אפשרות אחרת.
   מדד רועש — לכן זו התראה לבדיקה ידנית ולא שגיאה. */
const STOP=new Set(('של את על אל כי גם רק אם לא זה זו אלה הוא היא הם הן אני אתה אנחנו יש אין כל כמו אבל או אז מה מי איך למה כאשר לאחר לפני בתוך בין עם ללא אשר היה היו יהיה להיות אינו אינה אינם מפני מכיוון בגלל כדי לכן ולכן אלא אף כך יותר פחות מאוד ממש בדרך כלל למשל דוגמה המרצה שהוא שהיא ניתן צריך יכול אפשר בפועל בלבד כמובן עדיין זאת אותו אותה אותם לפי הסיכום בסיכום שבסיכום הצרכן הצרכנים המוצר').split(' '));
const stem=w=>w.replace(/^(כש|לכ|מה|שה|וה|וב|ול|ומ|ו|ה|ב|ל|מ|ש|כ)/,'');
const toks=s=>{const o=new Set();String(s).split(/[^\wא-ת]+/).forEach(w=>{
  if(w.length>=4 && !STOP.has(w)) o.add(stem(w));});return o;};
const key=[];
BANK.forEach((q,i)=>{
  if(!q.e||!Array.isArray(q.o)) return;
  const E=toks(q.e);
  const sc=q.o.map(o=>{const O=toks(o);let n=0;O.forEach(x=>{if(E.has(x))n++;});
                       return O.size? n/Math.sqrt(O.size):0;});
  const best=sc.indexOf(Math.max(...sc));
  if(best!==q.c && sc[best]-sc[q.c] > 1.0)
    key.push('#'+i+' מסומן '+(q.c+1)+' אך ההסבר מתאים ל-'+(best+1)+' — '+(q.q||'').slice(0,44));
});

/* תל האורך: דירוג האורך של התשובה הנכונה בין חמש התשובות (0 = הארוכה ביותר) */
const rank=new Array(N).fill(0), pos=new Array(N).fill(0), per={};
BANK.forEach(q=>{
  const L=q.o.map(o=>o.length);
  const r=L.map((l,i)=>[l,i]).sort((a,b)=>b[0]-a[0]).map(x=>x[1]).indexOf(q.c);
  rank[r]++; pos[q.c]++;
  (per[q.l]=per[q.l]||new Array(N).fill(0))[r]++;
});
console.log(JSON.stringify({n:BANK.length,err,key,rank,pos,per}));
"""

try:
    with tempfile.TemporaryDirectory() as td:
        jsf = os.path.join(td, "all.js")
        open(jsf, "w", encoding="utf-8").write(bank)
        chk = os.path.join(td, "struct.js")
        open(chk, "w", encoding="utf-8").write(STRUCT)
        r = subprocess.run(["node", chk, jsf, str(NOPT)], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "")[:400])
        s = json.loads(r.stdout.strip())
        n = s["n"]
        print("\nבדיקות מבנה (%d שאלות):" % n)
        if s["err"]:
            for e in s["err"][:40]:
                print("  !!", e)
        else:
            print("  תקין — ללא כפילויות, שדות חסרים או מסיחים תלויי-מיקום.")
        for k in s.get("key", []):
            print("  ?? מפתח תשובה (לבדיקה ידנית):", k)

        # כשכותבים שאלות בכמות, התשובה הנכונה יוצאת כמעט תמיד הארוכה ביותר, ואז אפשר לענות
        # נכון בלי לקרוא. מקרי = 20% לכל דירוג; דירוג שעובר 35% הוא רמז שאפשר לנצל.
        pct = lambda x, m: int(round(x / m * 100)) if m else 0
        print("\nבדיקת אורך התשובות — דירוג האורך של התשובה הנכונה (ארוכה ביותר ... קצרה ביותר), מקרי = 20%:")
        bad = False
        for l in sorted(s["per"], key=int):
            row = s["per"][l]; m = sum(row)
            flag = "  <-- !!" if max(row) / m > 0.40 and m >= 15 else ""
            bad = bad or bool(flag)
            print("  יחידה %s  n=%-3d  %s%s" % (l, m, " / ".join("%2d%%" % pct(x, m) for x in row), flag))
        flag = "  <-- !!" if max(s["rank"]) / n > 0.35 else ""
        bad = bad or bool(flag)
        print("  סה\"כ     n=%-3d  %s%s" % (n, " / ".join("%2d%%" % pct(x, n) for x in s["rank"]), flag))
        print("  מיקום התשובה הנכונה במקור (1..5):", " / ".join("%d%%" % pct(x, n) for x in s["pos"]))
        print("  " + ("!! יש דירוג אורך שאפשר לנצל בלי לקרוא — לאזן את אורכי התשובות." if bad
                      else "תקין — אף אסטרטגיה עיוורת אינה בולטת."))
except Exception as e:
    print("\n(הבדיקות דילגו — נדרש node:", e, ")")
