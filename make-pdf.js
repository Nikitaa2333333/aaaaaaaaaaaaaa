/**
 * make-pdf.js — конвертер river-loft-booklet.html → PDF
 *
 * Запуск: node make-pdf.js
 *
 * Что делает:
 *  1. Загружает HTML в Puppeteer
 *  2. Колет CSS-фиксы (уменьшает изображения, сжимает отступы)
 *  3. Автоматически разбивает переполненные страницы
 *  4. Перенумеровывает все страницы сквозной нумерацией
 *  5. Генерирует PDF формата A4
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const HTML_FILE = path.resolve(__dirname, 'river-loft-booklet.html');
const PDF_FILE  = path.resolve(__dirname, 'river-loft-booklet.pdf');

// ── CSS-патч, который вкалывается поверх оригинальных стилей ────────────────
const CSS_PATCH = `
    /* Уменьшаем полосы-изображения — главная причина переполнения */
    .adv-stripe { height: 88mm !important; margin: -10mm -16mm 10mm !important; }
    .hero-img   { height: 88mm !important; margin: -10mm -16mm 10mm !important; }

    /* Сжимаем внутренние отступы страниц */
    .inner { padding: 10mm 16mm 12mm !important; min-height: 297mm; }

    /* Уменьшаем зазоры в FAQ */
    .faq-item     { margin-bottom: 4mm !important; padding-bottom: 4mm !important; }
    .faq-category { margin-top: 5mm !important; margin-bottom: 5mm !important; }
    .faq-q        { margin-bottom: 1.5mm !important; }
    .faq-a p      { margin-bottom: 1.5mm !important; }
    .faq-a li     { margin-bottom: 1mm !important; }

    /* Преимущества */
    .adv-item     { margin-bottom: 5mm !important; padding-bottom: 5mm !important; }
    .welcome-text { margin-bottom: 4mm !important; }

    /* Убираем лишний разрыв после последней страницы */
    .page:last-child { page-break-after: avoid !important; break-after: avoid !important; }
`;

// ── Логика авторазбивки и нумерации (запускается внутри браузера) ───────────
const PAGE_LAYOUT_SCRIPT = /* javascript */ `
(function() {
    const A4_PX    = 297 * 3.7795;   // ~1122px
    const TOLERANCE = 8;              // px допуск
    const log = [];

    // Создаёт пустую страницу-продолжение
    function makeContPage() {
        const pg  = document.createElement('div');
        pg.className = 'page';
        pg.dataset.continuation = 'true';

        const inn = document.createElement('div');
        inn.className = 'inner';
        pg.appendChild(inn);

        const num = document.createElement('div');
        num.className = 'page-number';
        pg.appendChild(num);

        return { pg, inn };
    }

    // Разбивает одну страницу если она переполнена.
    // Moveable-элементы: .faq-item и .adv-item
    function splitPage(pageEl, depth) {
        if (depth > 8) return;

        const inner = pageEl.querySelector('.inner');
        if (!inner) return;

        let iter = 0;
        while (pageEl.getBoundingClientRect().height > A4_PX + TOLERANCE) {
            if (++iter > 30) break;

            const items = inner.querySelectorAll(':scope > .faq-item, :scope > .adv-item');
            if (items.length < 2) break;

            // Берём или создаём страницу-продолжение сразу после текущей
            let nextPage = pageEl.nextElementSibling;
            let nextInner;

            if (nextPage && nextPage.dataset.continuation === 'true') {
                nextInner = nextPage.querySelector('.inner');
            } else {
                const { pg, inn } = makeContPage();
                pageEl.parentNode.insertBefore(pg, pageEl.nextSibling);
                nextPage  = pg;
                nextInner = inn;
            }

            // Переносим последний item в начало следующей страницы
            nextInner.insertBefore(items[items.length - 1], nextInner.firstChild);
            log.push('moved item → continuation page');
        }

        // Рекурсивно проверяем созданную страницу-продолжение
        const next = pageEl.nextElementSibling;
        if (next && next.dataset.continuation === 'true') {
            splitPage(next, depth + 1);
        }
    }

    // Обходим только оригинальные страницы (снепшот до изменений)
    const originalPages = Array.from(document.querySelectorAll('.page'));
    originalPages.forEach(p => {
        const h = p.getBoundingClientRect().height;
        if (h > A4_PX + TOLERANCE) {
            log.push('overflow ' + Math.round(h / 3.7795) + 'mm — splitting');
            splitPage(p, 0);
        }
    });

    // Сквозная нумерация: 01, 02, 03 ...
    // Обложка (первая .page без .page-number) и задняя обложка (back-cover) — без номера
    document.querySelectorAll('.page').forEach((p, idx) => {
        const numEl = p.querySelector('.page-number');
        if (numEl) {
            numEl.textContent = String(idx + 1).padStart(2, '0');
        }
    });

    return {
        totalPages: document.querySelectorAll('.page').length,
        log: log
    };
})();
`;

// ── Главная функция ──────────────────────────────────────────────────────────
(async () => {
    console.log('▶ Запуск браузера...');
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();

        console.log('▶ Загрузка HTML...');
        const fileUrl = 'file:///' + HTML_FILE.replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/');
        await page.goto(fileUrl, {
            waitUntil: 'networkidle0',
            timeout: 60000
        });

        // Ждём загрузку Google Fonts
        await new Promise(r => setTimeout(r, 2500));

        // Шаг 1: CSS-патч
        console.log('▶ Применение CSS-патча...');
        await page.addStyleTag({ content: CSS_PATCH });

        // Шаг 2: Разбивка страниц + нумерация
        console.log('▶ Авторазбивка и нумерация...');
        const result = await page.evaluate(PAGE_LAYOUT_SCRIPT);

        console.log(`  Страниц итого: ${result.totalPages}`);
        result.log.forEach(l => console.log('  • ' + l));

        // Шаг 3: Генерация PDF
        console.log('▶ Генерация PDF...');
        await page.pdf({
            path: PDF_FILE,
            format: 'A4',
            printBackground: true,
            margin: { top: 0, right: 0, bottom: 0, left: 0 },
            preferCSSPageSize: false,
        });

        const size = (fs.statSync(PDF_FILE).size / 1024 / 1024).toFixed(2);
        console.log(`\n✓ Готово!`);
        console.log(`  Файл:   ${PDF_FILE}`);
        console.log(`  Размер: ${size} MB`);
        console.log(`  Страниц: ${result.totalPages}`);

    } finally {
        await browser.close();
    }
})();
