import docx
import re
from html.parser import HTMLParser
import difflib
import sys

# Настройка кодировки для вывода в консоль Windows
sys.stdout.reconfigure(encoding='utf-8')

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"Error reading docx: {e}"

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.in_style_or_script = False

    def handle_starttag(self, tag, attrs):
        if tag in ["style", "script"]:
            self.in_style_or_script = True

    def handle_endtag(self, tag):
        if tag in ["style", "script"]:
            self.in_style_or_script = False

    def handle_data(self, data):
        if not self.in_style_or_script:
            text = data.strip()
            if text:
                self.result.append(text)

    def get_text(self):
        return " ".join(self.result)

def extract_text_from_html(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        extractor = HTMLTextExtractor()
        extractor.feed(html_content)
        return extractor.get_text()
    except Exception as e:
        return f"Error reading html: {e}"

def clean_text(text):
    # Убираем лишние пробелы и приводим к нижнему регистру для базового сравнения
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compare_texts(docx_text, html_text):
    docx_clean = clean_text(docx_text)
    html_clean = clean_text(html_text)
    
    # Расчет процента схожести по алгоритму Ратклифа/Обершелпа
    similarity = difflib.SequenceMatcher(None, docx_clean, html_clean).ratio()
    
    return similarity * 100, docx_clean, html_clean

def find_missing_parts(docx_text, html_text):
    # Разбиваем исходный текст из docx на предложения или абзацы для поиска
    docx_parts = re.split(r'(?<=[.!?])\s+', docx_text)
    missing = []
    
    for part in docx_parts:
        clean_part = clean_text(part)
        if len(clean_part) < 10: continue
        
        # Если часть текста не найдена в HTML (даже частично)
        if clean_part not in clean_text(html_text):
            missing.append(part)
            
    return missing

# Пути к файлам
docx_file = "Буклет (3).docx"
html_file = "river-loft-booklet.html"

print(f"Сравниваем файлы:\n1. {docx_file}\n2. {html_file}\n")

docx_raw = extract_text_from_docx(docx_file)
html_raw = extract_text_from_html(html_file)

if "Error" in docx_raw or "Error" in html_raw:
    print(docx_raw)
    print(html_raw)
    sys.exit(1)

percentage, docx_c, html_c = compare_texts(docx_raw, html_raw)
missing = find_missing_parts(docx_raw, html_raw)

print("="*50)
print(f"РЕЗУЛЬТАТ СРАВНЕНИЯ")
print("="*50)
print(f"Точность совпадения: {percentage:.2f}%")
print()

if percentage > 99:
    print("Тексты практически полностью совпадают!")
else:
    print("Обнаружены отличия.")

if missing:
    print("\nЧТО ИМЕННО ОТСУТСТВУЕТ ИЛИ ИЗМЕНЕНО В HTML:")
    for i, part in enumerate(missing, 1):
        print(f"{i}. {part}")
else:
    print("\nЯвных пропусков предложений не обнаружено.")

# Дополнительная проверка на конкретные "отвалы"
print("\n" + "="*50)
print("ДЕТАЛЬНЫЙ АНАЛИЗ")
print("="*50)

# Проверим наличие ключевых разделов
sections = ["Добро пожаловать", "Наши преимущества", "Вопросы и ответы", "Особенности локации", "Свадебное путешествие"]
for s in sections:
    if s.lower() not in html_raw.lower():
        print(f"ВНИМАНИЕ: Раздел '{s}' не найден в HTML!")
    else:
        print(f"Раздел '{s}' на месте.")
