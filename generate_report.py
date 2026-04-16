import docx
import re
from html.parser import HTMLParser
import sys

# Настройка кодировки для вывода в консоль Windows
sys.stdout.reconfigure(encoding='utf-8')

def get_docx_structure(path):
    try:
        doc = docx.Document(path)
        points = []
        current_point = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Логика определения заголовка: капс, или начинается с цифры, или жирный шрифт (если есть)
            is_title = text.isupper() or re.match(r'^(\d+\.|\u25cf)', text)
            
            if is_title:
                if current_point: 
                    points.append(current_point)
                current_point = {"title": text, "text": ""}
            else:
                if current_point:
                    current_point["text"] += " " + text
                else:
                    current_point = {"title": "Вступление/Общее", "text": text}
        
        if current_point: 
            points.append(current_point)
        return points
    except Exception as e:
        print(f"Ошибка при чтении DOCX: {e}")
        return []

class HTMLCleaner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fed = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'): self.skip = True
    def handle_endtag(self, tag):
        if tag in ('style', 'script'): self.skip = False
    def handle_data(self, data):
        if not self.skip: self.fed.append(data)
    def get_data(self):
        return " ".join(self.fed)

def clean(text):
    # Нормализация для сравнения
    if not text: return ""
    text = text.replace('ё', 'е').replace('Ё', 'Е')
    text = re.sub(r'[«»"\'\-\–\—]', ' ', text) # убираем кавычки и тире
    return re.sub(r'\s+', ' ', text).strip().lower()

# Пути
docx_path = "Буклет (3).docx"
html_path = "river-loft-booklet.html"

print(f"Генерация отчета по файлам {docx_path} и {html_path}...")

docx_points = get_docx_structure(docx_path)
try:
    with open(html_path, "r", encoding="utf-8") as f:
        html_raw = f.read()
except Exception as e:
    print(f"Ошибка при чтении HTML: {e}")
    sys.exit(1)

cleaner = HTMLCleaner()
cleaner.feed(html_raw)
html_full_text = cleaner.get_data()
html_clean = clean(html_full_text)

with open("consistency_report.txt", "w", encoding="utf-8") as out:
    out.write("============================================================\n")
    out.write("ОТЧЕТ О СООТВЕТСТВИИ ТЕКСТА (БЛОК ПО БЛОКУ)\n")
    out.write("============================================================\n\n")
    
    total_points = len(docx_points)
    perfect_matches = 0
    
    for p in docx_points:
        title = p['title']
        content = p['text'].strip()
        
        # Проверка
        # Заголовок может быть частью более длинного заголовка в HTML, поэтому ищем вхождение
        title_in_html = clean(title) in html_clean
        content_in_html = clean(content) in html_clean
        
        if title_in_html and content_in_html:
            status = "ВЕРНО (ПОЛНОЕ СОВПАДЕНИЕ)"
            perfect_matches += 1
        elif title_in_html or content_in_html:
            status = "ЧАСТИЧНОЕ СОВПАДЕНИЕ / ЕСТЬ ПРАВКИ"
        else:
            status = "ОТСУТСТВУЕТ"
            
        out.write(f"ЗАГОЛОВОК: {title}\n")
        out.write(f"ОСНОВНОЙ ТЕКСТ: {content}\n")
        out.write(f"СТАТУС: {status}\n")
        
        if status != "ВЕРНО (ПОЛНОЕ СОВПАДЕНИЕ)":
            # Поиск конкретных пропавших предложений
            sentences = re.split(r'(?<=[.!?])\s+', content)
            missing_frags = []
            for s in sentences:
                if len(s.strip()) > 10 and clean(s) not in html_clean:
                    missing_frags.append(s.strip())
            
            if missing_frags:
                out.write("!!! ОТСУТСТВУЮЩИЕ ИЛИ ИЗМЕНЕННЫЕ ФРАГМЕНТЫ:\n")
                for frag in missing_frags:
                    out.write(f"  > {frag}\n")
            elif not title_in_html:
                out.write("!!! Заголовок в HTML перефразирован или отсутствует.\n")
        
        out.write("-" * 60 + "\n\n")

    out.write(f"ИТОГО: Совпало полностью {perfect_matches} из {total_points} блоков.\n")

print(f"Готово! Отчет сохранен в 'consistency_report.txt'.")
