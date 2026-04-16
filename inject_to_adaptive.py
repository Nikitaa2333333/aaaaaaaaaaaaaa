
import re
from bs4 import BeautifulSoup, NavigableString

# 1. Читаем текст из booklet_final.txt
with open("booklet_final.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

# Разделяем на секции по длинным линиям
sections_raw = re.split(r"-{40,}", raw_text)
sections = [s.strip() for s in sections_raw]

# --- Разбор ПРИВЕТСТВИЯ (Секция 0) ---
welcome_clean = re.sub(r"={10,}.*?={10,}", "", sections[0], flags=re.DOTALL | re.I).strip()
welcome_paras = [p.strip() for p in welcome_clean.split('\n\n') if p.strip()]

# --- Разбор ПРЕИМУЩЕСТВ (Секция 1) ---
adv_text = sections[1]
adv_raw = re.split(r"(\d+\.\s+)", adv_text)[1:] # [ "1. ", "Локация. Текст...", "2. ", "Текст..." ]
adv_items = []
for i in range(0, len(adv_raw), 2):
    num_str = adv_raw[i]
    content = adv_raw[i+1].strip()
    if ". " in content:
        title, desc = content.split(". ", 1)
        adv_items.append((title.strip(), desc.strip()))
    else:
        adv_items.append(("", content.strip()))

# --- Разбор FAQ (Секция 2) ---
faq_text = sections[2]
faq_blocks = re.split(r"●\s*", faq_text)[1:]
faq_items = []
for block in faq_blocks:
    if "?" in block:
        q_part, a_part = block.strip().split('?', 1)
        faq_items.append((q_part.strip() + "?", a_part.strip()))

# --- Разбор ЛОКАЦИИ (Секция 3) ---
loc_text = sections[3]
loc_paras = [p.strip() for p in loc_text.split('\n\n') if p.strip() and "ОСОБЕННОСТИ" not in p]

# --- Разбор ПУТЕШЕСТВИЯ (Секция 4) ---
travel_text = sections[4]
travel_paras = [p.strip() for p in travel_text.split('\n\n') if p.strip() and "СВАДЕБНОЕ" not in p]

# 2. Загружаем HTML
with open("river_loft_adaptive.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

def set_html(tag, text):
    tag.clear()
    html_content = text.strip().replace('\n', '<br>')
    tag.append(BeautifulSoup(html_content, "html.parser"))

# --- ИНЪЕКЦИЯ ---

# Приветствие
welcome_container = soup.select_one("#welcome .welcome-text")
if welcome_container:
    h2 = welcome_container.find("h2")
    welcome_container.clear()
    if h2: welcome_container.append(h2)
    for p in welcome_paras:
        p_tag = soup.new_tag("p")
        set_html(p_tag, p)
        welcome_container.append(p_tag)

# Преимущества
adv_container = soup.select_one("#advantages .adv-grid")
if adv_container:
    adv_container.clear()
    for i, (title, desc) in enumerate(adv_items):
        num_label = "{:02d}".format(i+1)
        clean_desc = desc.replace('\n', '<br>')
        card_tpl = """
        <div class="adv-card reveal">
            <div class="adv-num">{}</div>
            <h3 class="adv-title">{}</h3>
            <p class="adv-desc">{}</p>
        </div>
        """
        adv_container.append(BeautifulSoup(card_tpl.format(num_label, title, clean_desc), "html.parser"))

# FAQ
faq_container = soup.select_one("#faq .faq-container")
if faq_container:
    faq_container.clear()
    for q, a in faq_items:
        clean_q = q.replace('\n', ' ')
        clean_a = a.replace('\n', '<br>')
        faq_tpl = """
        <div class="faq-item reveal">
            <div class="faq-q">{} <span class="icon">+</span></div>
            <div class="faq-a">{}</div>
        </div>
        """
        faq_container.append(BeautifulSoup(faq_tpl.format(clean_q, clean_a), "html.parser"))

# Локация
loc_container = soup.select_one("#location .welcome-text")
if loc_container:
    h2 = loc_container.find("h2")
    loc_container.clear()
    if h2: loc_container.append(h2)
    for p in loc_paras:
        p_tag = soup.new_tag("p")
        set_html(p_tag, p)
        loc_container.append(p_tag)

# Путешествие
travel_p = soup.select_one("#travel .travel-box p")
if travel_p:
    full_travel_text = "\n\n".join(travel_paras)
    set_html(travel_p, full_travel_text)

# 3. Сохраняем
with open("river_loft_adaptive.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

print("✓ Успешно! Перенесено: приветствие, {} преимуществ, {} вопросов FAQ.".format(len(adv_items), len(faq_items)))
