import docx
import sys
import os

# На всякий случай настраиваем кодировку вывода
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

input_file = "Буклет (3).docx"
output_file = "booklet_v3.txt"

if not os.path.exists(input_file):
    print(f"Ошибка: Файл {input_file} не найден!")
    sys.exit(1)

print(f"Конвертирую {input_file}...")

doc = docx.Document(input_file)
lines = []

for para in doc.paragraphs:
    text = para.text.strip()
    if text:
        lines.append(text)

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Готово! Текст сохранен в {output_file}")
