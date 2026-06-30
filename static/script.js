// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// --- НОВЫЙ БЛОК: СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ БОТА ---
function initFiltersFromBot() {
    try {
        // Получаем хэш из URL (убираем первый символ '#')
        const hash = window.location.hash.substring(1);
        if (!hash) return; // Если хэш пустой, оставляем дефолтные настройки html

        // Декодируем URL и парсим JSON
        const botData = JSON.parse(decodeURIComponent(hash));

        // 1. Синхронизируем Главную Категорию (Продажа / Аренда)
        if (botData.cat) {
            selectedCategory = botData.cat;
            document.querySelectorAll('#mainCategoryTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cat') === botData.cat);
            });
        }

        // 2. Синхронизируем Тип Публикации (Все / Только новые)
        if (botData.type) {
            selectedPostType = botData.type;
            document.querySelectorAll('#postTypeTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-type') === botData.type);
            });
        }

        // 3. Синхронизируем Валюту
        if (botData.curr !== null) {
            selectedCurrency = botData.curr;
            document.querySelectorAll('.currency-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-value') === botData.curr);
            });
        }

        // 4. Синхронизируем Цены
        if (botData.min) document.getElementById('price_min').value = botData.min;
        if (botData.max) document.getElementById('price_max').value = botData.max;

        // 5. Синхронизируем Состояние здания (Վիճակ)
        if (botData.cnd) {
            selectedCondition = botData.cnd;
            document.querySelectorAll('.condition-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cnd') === botData.cnd);
            });
        }

        // 6. Синхронизируем Продавцов (Վաճառողներ)
        if (botData.sel) {
            selectedSeller = botData.sel;
            document.querySelectorAll('.seller-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-user') === botData.sel);
            });
        }

        // 7. Синхронизируем Районы Еревана
        if (botData.regions && Array.isArray(botData.regions)) {
            const childBoxes = document.querySelectorAll('.child-box');
            let checkedCount = 0;

            childBoxes.forEach(box => {
                // Если ID района есть в пришедшем массиве, чекаем его
                if (botData.regions.includes(box.value)) {
                    box.checked = true;
                    checkedCount++;
                } else {
                    box.checked = false;
                }
            });

            // Если зачеканы все районы, ставим галочку и на "Весь Ереван"
            if (checkedCount === childBoxes.length && checkedCount > 0) {
                document.getElementById('all_yerevan').checked = true;
            }
        }

    } catch (error) {
        console.error("Ошибка парсинга данных из бота:", error);
    }
}

// Вызываем функцию синхронизации сразу при загрузке скрипта
initFiltersFromBot();