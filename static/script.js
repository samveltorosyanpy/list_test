// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// --- 1. СОСТОЯНИЕ ПРИЛОЖЕНИЯ (ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ) ---
let selectedCategory = "62";
let selectedCurrency = null;
let selectedCondition = null;
let selectedSeller = null;
let selectedPostType = "all";

// --- 2. ПОИСК ЭЛЕМЕНТОВ DOM ДЛЯ ЕРЕВАНА ---
const header = document.getElementById('yerevanHeader');
const list = document.getElementById('yerevanList');
const arrow = document.getElementById('yerevanArrow');
const mainCheckbox = document.getElementById('all_yerevan');
const childBoxes = document.querySelectorAll('.child-box');

// --- 3. ВОССТАНОВЛЕНИЕ: ОБРАБОТЧИКИ КЛИКОВ ДЛЯ КНОПОК И ТАБОВ ---

// Переключатель типа публикации (Все / Только новые)
const postTabs = document.querySelectorAll('#postTypeTabs .tab-btn');
postTabs.forEach(btn => {
    btn.addEventListener('click', () => {
        postTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedPostType = btn.getAttribute('data-type');
    });
});

// Переключатель главных категорий (Продажа / Аренда)
const mainCategoryTabs = document.querySelectorAll('#mainCategoryTabs .tab-btn');
mainCategoryTabs.forEach(btn => {
    btn.addEventListener('click', () => {
        mainCategoryTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedCategory = btn.getAttribute('data-cat');
    });
});

// Универсальная функция для кнопок-пилюль с возможностью отмены (Валюта, Состояние, Продавец)
function setupPillButtons(selector, attrName, callback) {
    const buttons = document.querySelectorAll(selector);
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.classList.contains('active')) {
                btn.classList.remove('active');
                callback(null);
            } else {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                callback(btn.getAttribute(attrName));
            }
        });
    });
}

// Включаем клики для валюты, состояния и продавцов
setupPillButtons('.currency-btn', 'data-value', (val) => selectedCurrency = val);
setupPillButtons('.condition-btn', 'data-cnd', (val) => selectedCondition = val);
setupPillButtons('.seller-btn', 'data-user', (val) => selectedSeller = val);


// --- 4. ВОССТАНОВЛЕНИЕ: ЛОГИКА ДЕРЕВА РЕГИОНОВ ЕРЕВАНА ---

if (header && list && arrow) {
    header.addEventListener('click', () => {
        list.classList.toggle('show');
        arrow.classList.toggle('open');
        arrow.innerText = list.classList.contains('show') ? "▲" : "▼";
    });
}

if (mainCheckbox && childBoxes.length > 0) {
    mainCheckbox.addEventListener('change', (e) => {
        childBoxes.forEach(box => {
            box.checked = e.target.checked;
        });
    });

    childBoxes.forEach(box => {
        box.addEventListener('change', () => {
            if (!box.checked) {
                mainCheckbox.checked = false;
            } else {
                const allChecked = Array.from(childBoxes).every(b => b.checked);
                if (allChecked) mainCheckbox.checked = true;
            }
        });
    });
}


// --- 5. СИНХРОНИЗАЦИЯ ДАННЫХ ИЗ БОТА ---
function initFiltersFromBot() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const encodedData = urlParams.get('start_data');

        if (!encodedData) {
            console.log("Данные start_data не найдены в URL, используем дефолт");
            return;
        }

        const botData = JSON.parse(decodeURIComponent(encodedData));
        console.log("Успешно загрузили данные из бота:", botData);

        // Синхронизируем Главную Категорию
        if (botData.cat) {
            selectedCategory = botData.cat;
            document.querySelectorAll('#mainCategoryTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cat') === botData.cat);
            });
        }

        // Синхронизируем Тип Публикации
        if (botData.type) {
            selectedPostType = botData.type;
            document.querySelectorAll('#postTypeTabs .tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-type') === botData.type);
            });
        }

        // Синхронизируем Валюту
        if (botData.curr !== null && botData.curr !== undefined) {
            selectedCurrency = botData.curr;
            document.querySelectorAll('.currency-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-value') === botData.curr);
            });
        }

        // Синхронизируем Цены (Безопасный вариант)
        if (botData.min !== undefined && botData.min !== null) {
            document.getElementById('price_min').value = botData.min;
        }
        if (botData.max !== undefined && botData.max !== null) {
            document.getElementById('price_max').value = botData.max;
        }

        // Синхронизируем Состояние здания
        if (botData.cnd) {
            selectedCondition = botData.cnd;
            document.querySelectorAll('.condition-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-cnd') === botData.cnd);
            });
        }

        // Синхронизируем Продавцов
        if (botData.sel) {
            selectedSeller = botData.sel;
            document.querySelectorAll('.seller-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-user') === botData.sel);
            });
        }

        // Синхронизируем Районы Еревана
        if (botData.regions && Array.isArray(botData.regions) && childBoxes.length > 0) {
            let checkedCount = 0;

            childBoxes.forEach(box => {
                if (botData.regions.includes(box.value)) {
                    box.checked = true;
                    checkedCount++;
                } else {
                    box.checked = false;
                }
            });

            if (checkedCount === childBoxes.length && checkedCount > 0 && mainCheckbox) {
                mainCheckbox.checked = true;
            }
        }

    } catch (error) {
        console.error("Ошибка парсинга данных из бота:", error);
    }
}


// --- 6. ОБРАБОТКА КЛИКА НА КНОПКУ "ПРИМЕНИТЬ" ---
document.getElementById('submitBtn').addEventListener('click', () => {
    const priceMinRaw = document.getElementById('price_min').value.trim();
    const priceMaxRaw = document.getElementById('price_max').value.trim();

    const priceMin = priceMinRaw ? parseInt(priceMinRaw, 10) : 0;
    const priceMax = priceMaxRaw ? parseInt(priceMaxRaw, 10) : null;

    const selectedIds = [];
    const selectedNames = [];

    if (mainCheckbox && mainCheckbox.checked) {
        selectedNames.push("Ամբողջ Երևան (Весь Ереван)");
        childBoxes.forEach(box => selectedIds.push(box.value));
    } else {
        childBoxes.forEach(box => {
            if (box.checked) {
                selectedIds.push(box.value);
                selectedNames.push(box.getAttribute('data-name') || "Район");
            }
        });
    }

    const categoryMap = { "62": "Վաճառք (Продажа)", "63": "Երկարաժամկետ վարձակալություն (Արենդա)" };
    const currencyMap = { "0": "AMD", "1": "USD", "2": "EUR", "3": "RUB" };
    const conditionMap = { "4": "Կառուցված (Построенное)", "5": "Անավարտ (Недостроенное)" };
    const sellerMap = { "1": "Սեփականատեր (Собственник)", "2": "Գործակալություն (Ագենտություն)" };
    const postTypeMap = { "all": "Բոլորը (Все публикации)", "new": "Միայն նոր հայտարարություններ (Только новые)" };

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

    tg.sendData(JSON.stringify(filterData));
    tg.close();
});

// Вызываем функцию синхронизации сразу при загрузке скрипта
initFiltersFromBot();