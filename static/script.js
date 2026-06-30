// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// --- НОВЫЙ БЛОК: СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ БОТА ---
function initFiltersFromBot() {
    try {
        // 1. Ищем параметр start_data в URL (после знака ?)
        const urlParams = new URLSearchParams(window.location.search);
        const encodedData = urlParams.get('start_data');

        if (!encodedData) {
            console.log("Данные start_data не найдены в URL, используем дефолт");
            return;
        }

        // 2. Декодируем и парсим JSON
        const botData = JSON.parse(decodeURIComponent(encodedData));
        console.log("Успешно загрузили данные из бота:", botData);

        // 3. Синхронизируем Главную Категорию
        if (botData.cat) {
            selectedCategory = botData.cat;
            document.querySelectorAll('#mainCategoryTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cat') === botData.cat);
            });
        }

        // 4. Синхронизируем Тип Публикации
        if (botData.type) {
            selectedPostType = botData.type;
            document.querySelectorAll('#postTypeTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-type') === botData.type);
            });
        }

        // 5. Синхронизируем Валюту
        if (botData.curr !== null && botData.curr !== undefined) {
            selectedCurrency = botData.curr;
            document.querySelectorAll('.currency-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-value') === botData.curr);
            });
        }

        // 6. Синхронизируем Цены (Строгая проверка, чтобы не терять 0 или 2)
        if (botData.min !== undefined && botData.min !== null) {
            document.getElementById('price_min').value = botData.min;
        }
        if (botData.max !== undefined && botData.max !== null) {
            document.getElementById('price_max').value = botData.max;
        }

        // 7. Синхронизируем Состояние здания
        if (botData.cnd) {
            selectedCondition = botData.cnd;
            document.querySelectorAll('.condition-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cnd') === botData.cnd);
            });
        }

        // 8. Синхронизируем Продавцов
        if (botData.sel) {
            selectedSeller = botData.sel;
            document.querySelectorAll('.seller-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-user') === botData.sel);
            });
        }

        // 9. Синхронизируем Районы Еревана
        if (botData.regions && Array.isArray(botData.regions)) {
            const childBoxes = document.querySelectorAll('.child-box');
            let checkedCount = 0;

            childBoxes.forEach(box => {
                if (botData.regions.includes(box.value)) {
                    box.checked = true;
                    checkedCount++;
                } else {
                    box.checked = false;
                }
            });

            if (checkedCount === childBoxes.length && checkedCount > 0) {
                document.getElementById('all_yerevan').checked = true;
            }
        }

    } catch (error) {
        console.error("Ошибка парсинга данных из бота:", error);
    }
}
document.getElementById('submitBtn').addEventListener('click', () => {
    // 1. Получаем значения из инпутов цен
    const priceMinRaw = document.getElementById('price_min').value.trim();
    const priceMaxRaw = document.getElementById('price_max').value.trim();

    // Преобразуем в числа, если заполнено, иначе ставим дефолт
    const priceMin = priceMinRaw ? parseInt(priceMinRaw, 10) : 0;
    const priceMax = priceMaxRaw ? parseInt(priceMaxRaw, 10) : null;

    // 2. Собираем выбранные ID и имена районов Еревана
    const selectedIds = [];
    const selectedNames = [];

    if (mainCheckbox.checked) {
        // Если выбран "Весь Ереван", отправляем ID всех дочерних чекбоксов
        selectedNames.push("Ամբողջ Երևան (Весь Ереван)");
        childBoxes.forEach(box => selectedIds.push(box.value));
    } else {
        // Иначе собираем только те районы, где стоят галочки
        childBoxes.forEach(box => {
            if (box.checked) {
                selectedIds.push(box.value);
                selectedNames.push(box.getAttribute('data-name') || "Район");
            }
        });
    }

    // 3. Маппинг текстовых названий для красивого отображения в дашборде бота
    const categoryMap = { "62": "Վաճառք (Продажа)", "63": "Երկարաժամկետ վարձակալություն (Արենդա)" };
    const currencyMap = { "0": "AMD", "1": "USD", "2": "EUR", "3": "RUB" };
    const conditionMap = { "4": "Կառուցված (Построенное)", "5": "Անավարտ (Недостроенное)" };
    const sellerMap = { "1": "Սեփականատեր (Собственник)", "2": "Գործակալություն (Ագենտություն)" };
    const postTypeMap = { "all": "Բոլորը (Все публикации)", "new": "Միայն նոր հայտարարություններ (Только новые)" };

    // 4. Формируем единый объект конфигурации фильтров
    const filterData = {
        category_id: selectedCategory,
        category_text: categoryMap[selectedCategory] || "Не указан",
        currency_id: selectedCurrency,
        currency_text: selectedCurrency ? currencyMap[selectedCurrency] : "Любая валюта",
        min_price: priceMin,
        max_price: priceMax !== null ? priceMax : "Не указана",
        cnd_id: selectedCondition,
        cnd_text: selectedCondition ? conditionMap[selectedCondition] : "Любое состояние",
        user_id: selectedSeller,
        user_text: selectedSeller ? sellerMap[selectedSeller] : "Все продавцы",
        regions_ids: selectedIds,
        regions_names: selectedNames.length > 0 ? selectedNames : ["Не выбраны"],
        post_type: selectedPostType,
        post_type_text: postTypeMap[selectedPostType] || "Все"
    };

    console.log("Отправка фильтров в Телеграм:", filterData);

    // 5. КРИТИЧЕСКИЙ ШАГ: Передаем строку JSON обратно в бота
    tg.sendData(JSON.stringify(filterData));

    // 6. Закрываем WebApp окно
    tg.close();
});

// Вызываем функцию синхронизации сразу при загрузке скрипта
initFiltersFromBot();