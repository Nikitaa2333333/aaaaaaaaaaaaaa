import docx
from html.parser import HTMLParser
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ── Извлечь текст из DOCX ─────────────────────────────────────────────────────
doc = docx.Document("Буклет (2).docx")
docx_lines = []
for para in doc.paragraphs:
    t = para.text.strip()
    if t:
        docx_lines.append(t)

# ── Извлечь текст из HTML ─────────────────────────────────────────────────────
class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.texts.append(t)

with open("river-loft-booklet.html", encoding="utf-8") as f:
    html_raw = f.read()

extractor = TextExtractor()
extractor.feed(html_raw)
html_text = " ".join(extractor.texts)
# нормализуем пробелы
html_text = re.sub(r'\s+', ' ', html_text)

# ── Сравнение: ищем строки из docx, которых нет в HTML ───────────────────────
print("=" * 70)
print("СТРОКИ ИЗ DOCX, КОТОРЫХ НЕТ (или мало) В HTML")
print("=" * 70)

missing = []
for line in docx_lines:
    # упрощённый поиск: берём первые 30 символов подстроки
    fragment = line[:40].strip()
    if fragment and fragment not in html_text:
        missing.append(line)

for i, line in enumerate(missing, 1):
    print(f"{i:3}. {line}")

print()
print(f"Итого строк в docx:   {len(docx_lines)}")
print(f"Строк не найдено в html: {len(missing)}")

# ── Для наглядности — весь текст docx ────────────────────────────────────────
print()
print("=" * 70)
print("ПОЛНЫЙ ТЕКСТ ИЗ DOCX (построчно)")
print("=" * 70)
for i, line in enumerate(docx_lines, 1):
    print(f"{i:3}. {line}")
