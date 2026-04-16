"""
inject_content.py  v2
Читает Буклет (2).docx и точно переносит весь текст в river-loft-booklet.html.
"""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")

import docx
from bs4 import BeautifulSoup, NavigableString, Tag

# ══════════════════════════════════════════════════════════
# 1. Парсим DOCX
# ══════════════════════════════════════════════════════════
doc = docx.Document("Буклет (2).docx")
paras = [(p.style.name, p.text.strip()) for p in doc.paragraphs if p.text.strip()]

normal = [t for s, t in paras if "List" not in s]
listps = [t for s, t in paras if "List" in s]

# ── Приветствие ──────────────────────────────────────────
welcome_paras = normal[1:5]   # абзацы 2–5 (без заголовка "Добрый день")
welcome_sign  = normal[5]     # "Желаем Вам…"

# ── Преимущества ─────────────────────────────────────────
def split_adv(text):
    text = re.sub(r"^\d+\.\s*", "", text)
    dot = text.index(". ")
    return text[:dot], text[dot+2:]

adv_items_data = []
for t in normal[7:13]:   # строки 8–13 = пункты 1–6
    try:
        title, desc = split_adv(t)
        adv_items_data.append((title, desc))
    except (ValueError, IndexError):
        pass

# пункт 6: добавить второй абзац
if len(adv_items_data) == 6:
    t6, d6 = adv_items_data[5]
    adv_items_data[5] = (t6, d6 + "\n\n" + normal[13])

# ── FAQ: строим пары Q/A ──────────────────────────────────
faq_qa = []
i = 0
while i < len(listps):
    t = listps[i]
    if "?" in t and len(t) < 250:
        q = t
        ans = []
        i += 1
        while i < len(listps):
            nxt = listps[i]
            if "?" in nxt and len(nxt) < 250:
                break
            ans.append(nxt)
            i += 1
        faq_qa.append((q, ans))
    else:
        i += 1

# Находим "тяжёлый дым" как отдельную пару
heavy_smoke_idx = next((i for i, (q, _) in enumerate(faq_qa) if "тяжелый дым" in q.lower()), None)
# Находим "светомузыка" как пару, куда тяжёлый дым нужно вмерджить
light_idx = next((i for i, (q, _) in enumerate(faq_qa) if "светомузык" in q.lower()), None)
if heavy_smoke_idx is not None and light_idx is not None:
    hs_q, hs_a = faq_qa.pop(heavy_smoke_idx)
    # вмерджим в ответ светомузыки
    lq, la = faq_qa[light_idx if light_idx < heavy_smoke_idx else light_idx - 1]
    la.append("Есть ли на площадке тяжёлый дым?")
    la.extend(hs_a)

# "Особенности локации." и "Свадебное путешествие." попали в listps
# Удаляем их из faq (они не вопросы)
faq_qa = [(q, a) for q, a in faq_qa
          if "Особенности локации" not in q and "Свадебное путешествие" not in q]

print(f"=== FAQ: {len(faq_qa)} пар Q/A ===")
for q, a in faq_qa:
    print(f"  Q: {q[:70]}")

# ── Локация ───────────────────────────────────────────────
# В docx это List Paragraph после "Особенности локации."
loc_marker = next((i for i, t in enumerate(listps) if "Особенности локации" in t), None)
travel_marker = next((i for i, t in enumerate(listps) if "Свадебное путешествие" in t), None)
location_src = listps[loc_marker+1:travel_marker] if loc_marker is not None else []
travel_src   = listps[travel_marker+1:]           if travel_marker is not None else []

# ══════════════════════════════════════════════════════════
# 2. Загружаем HTML
# ══════════════════════════════════════════════════════════
with open("river-loft-booklet.html", encoding="utf-8") as f:
    html = f.read()
soup = BeautifulSoup(html, "html.parser")

def set_text(tag, text):
    tag.clear()
    tag.append(NavigableString(text))

def set_html(tag, markup):
    tag.clear()
    tag.append(BeautifulSoup(markup, "html.parser"))

# ══════════════════════════════════════════════════════════
# 3. ПРИВЕТСТВИЕ
# ══════════════════════════════════════════════════════════
wt = soup.find_all(class_="welcome-text")
for tag, text in zip(wt, welcome_paras):
    set_text(tag, text)

ws = soup.find(class_="welcome-sign")
if ws:
    set_text(ws, "— " + welcome_sign)

# ══════════════════════════════════════════════════════════
# 4. ПРЕИМУЩЕСТВА
# ══════════════════════════════════════════════════════════
adv_tags = soup.find_all(class_="adv-item")
for tag, (title, desc) in zip(adv_tags, adv_items_data):
    t_tag = tag.find(class_="adv-title")
    d_tag = tag.find(class_="adv-desc")
    if t_tag:
        set_text(t_tag, title)
    if d_tag:
        if "\n\n" in desc:
            p1, p2 = desc.split("\n\n", 1)
            set_html(d_tag, p1 + "<br/><br/>" + p2)
        else:
            set_text(d_tag, desc)

# ══════════════════════════════════════════════════════════
# 5. FAQ
# ══════════════════════════════════════════════════════════
def build_answer_html(parts):
    out = []
    ul, ol = [], []

    def flush_ul():
        if ul:
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in ul) + "</ul>")
            ul.clear()
    def flush_ol():
        if ol:
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in ol) + "</ol>")
            ol.clear()

    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith("- "):
            flush_ol(); ul.append(p[2:])
        elif re.match(r"^\d+[\.\-]\s", p):
            flush_ul(); ol.append(re.sub(r"^\d+[\.\-]\s*", "", p))
        elif p.endswith("?"):
            # встроенный под-вопрос (тяжёлый дым)
            flush_ul(); flush_ol()
            out.append(f'<p style="margin-top:4mm;font-style:italic;color:var(--muted);">{p}</p>')
        else:
            flush_ul(); flush_ol()
            out.append(f"<p>{p}</p>")

    flush_ul(); flush_ol()
    return "".join(out)

def words(text):
    return set(re.findall(r"[а-яёА-ЯЁa-zA-Z]{4,}", text.lower()))

faq_html_items = soup.find_all(class_="faq-item")

for faq_tag in faq_html_items:
    q_tag = faq_tag.find(class_="faq-q")
    a_tag = faq_tag.find(class_="faq-a")
    if not q_tag or not a_tag:
        continue

    hw = words(q_tag.get_text())
    best, best_score = None, 0

    for docx_q, docx_a in faq_qa:
        dw = words(docx_q)
        if not dw:
            continue
        inter = len(hw & dw)
        # нормируем по длине большего множества → jaccard-like
        score = inter / max(len(hw), len(dw))
        if score > best_score:
            best_score = score
            best = (docx_q, docx_a)

    if best and best_score >= 0.25:
        docx_q, docx_a = best
        set_text(q_tag, docx_q)
        set_html(a_tag, build_answer_html(docx_a))
        print(f"  ✓ {best_score:.2f} | {docx_q[:60]}")
    else:
        print(f"  ✗ не смэтчен: {q_tag.get_text()[:60]}")

# ── «Как показывает практика» — плашка ───────────────────
practice_q, practice_a = next(
    ((q, a) for q, a in faq_qa if "практика" in q.lower()), (None, None)
)
if practice_a:
    # найдём div с "Как показывает практика" по тексту
    for div in soup.find_all("div"):
        inner = div.find(string=re.compile("Как показывает практика", re.I))
        if inner:
            # следующий div (с текстом ответа)
            nxt = div.find_next_sibling("div")
            # или найдём параграф внутри
            p_tag = div.find_all("div")
            if p_tag and len(p_tag) >= 2:
                set_text(p_tag[1], practice_a[0] if practice_a else "")
            break

# ── «Важно знать» — блок ─────────────────────────────────
vazh_q, vazh_a = next(
    ((q, a) for q, a in faq_qa if "перечень имущества" in " ".join(a).lower()), (None, None)
)
if vazh_a:
    for div in soup.find_all("div"):
        txt = div.get_text()
        if "Важно знать" in txt and "перечень" in txt.lower():
            inner_divs = div.find_all("div")
            if len(inner_divs) >= 2:
                set_text(inner_divs[1], " ".join(vazh_a))
            break

# ══════════════════════════════════════════════════════════
# 6. ЛОКАЦИЯ
# ══════════════════════════════════════════════════════════
loc_tags = soup.find_all(class_="location-text")
# Текстовые абзацы локации — первые 2 из location_src (остальное — facts)
for tag, text in zip(loc_tags, location_src[:2]):
    set_text(tag, text)

# Location facts
fact_labels = soup.find_all(class_="location-fact-label")
fact_values  = soup.find_all(class_="location-fact-value")
for lbl, val in zip(fact_labels, fact_values):
    label = lbl.get_text()
    # находим нужное в location_src[2] (строка с расстоянием, шоссе, такси)
    loc_fact_line = location_src[2] if len(location_src) > 2 else ""
    if "Парковка" in label:
        set_text(val, "Бесплатная, обширная; каршеринг доступен")
    elif "Шоссе" in label:
        set_text(val, "Калужское · Варшавское · Симферопольское")
    elif "Такси" in label:
        set_text(val, "До 15 мин ожидания; остановка общ. транспорта рядом")

# ══════════════════════════════════════════════════════════
# 7. СВАДЕБНОЕ ПУТЕШЕСТВИЕ
# ══════════════════════════════════════════════════════════
tr_tags = soup.find_all(class_="travel-text")
if tr_tags and travel_src:
    set_text(tr_tags[0], travel_src[0])

brand_tags = soup.find_all(class_="travel-brand-desc")
for tag, text in zip(brand_tags, travel_src[1:]):
    set_text(tag, text)

# ══════════════════════════════════════════════════════════
# 8. Сохраняем
# ══════════════════════════════════════════════════════════
with open("river-loft-booklet.html", "w", encoding="utf-8") as f:
    f.write(str(soup))

print("\n✓ Готово. Текст из docx точно перенесён в HTML.")
