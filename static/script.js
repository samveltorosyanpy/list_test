// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Состояние приложения
let selectedCategory = "62";
let selectedCurrency = null;
let selectedCondition = null;
let selectedSeller = null;
let selectedPostType = "all";

// Изолированный переключатель публикации (Все / Только новые)
const postTabs = document.querySelectorAll('#postTypeTabs .tab-btn');
postTabs.forEach(btn => {
    btn.addEventListener('click', () => {
        postTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedPostType = btn.getAttribute('data-type');
    });
});

// Изолированный переключатель главных категорий (Продажа / Аренда)
const mainCategoryTabs = document.querySelectorAll('#mainCategoryTabs .tab-btn');
mainCategoryTabs.forEach(btn => {
    btn.addEventListener('click', () => {
        mainCategoryTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedCategory = btn.getAttribute('data-cat');
    });
});

// Выбор валюты
const currencyButtons = document.querySelectorAll('.currency-btn');
currencyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) {
            btn.classList.remove('active');
            selectedCurrency = null;
        } else {
            currencyButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedCurrency = btn.getAttribute('data-value');
        }
    });
});

// Выбор состояния (Վիճակ)
const conditionButtons = document.querySelectorAll('.condition-btn');
conditionButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) {
            btn.classList.remove('active');
            selectedCondition = null;
        } else {
            conditionButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedCondition = btn.getAttribute('data-cnd');
        }
    });
});

// Выбор продавца (Վաճառողներ)
const sellerButtons = document.querySelectorAll('.seller-btn');
sellerButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.classList.contains('active')) {
            btn.classList.remove('active');
            selectedSeller = null;
        } else {
            sellerButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedSeller = btn.getAttribute('data-user');
        }
    });
});

// Логика дерева регионов Еревана
const header = document.getElementById('yerevanHeader');
const list = document.getElementById('yerevanList');
const arrow = document.getElementById('yerevanArrow');
const mainCheckbox = document.getElementById('all_yerevan');
const childBoxes = document.querySelectorAll('.child-box');

header.addEventListener('click', () => {
    list.classList.toggle('show');
    arrow.classList.toggle('open');
    arrow.innerText = list.classList.contains('show') ? "▲" : "▼";
});

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

// Обработка клика по кнопке отправки результатов
document.getElementById('submitBtn').addEventListener('click', () => {
    const priceMin = document.getElementById('price_min').value;
    const priceMax = document.getElementById('price_max').value;

    const selectedIds = [];
    const selectedNames = [];

    if (mainCheckbox.checked) {
        selectedNames.push("Ամբողջ Երևան (Весь Ереван)");
        childBoxes.forEach(box => selectedIds.push(box.value));
    } else {
        childBoxes.forEach(box => {
            if (box.checked) {
                selectedIds.push(box.value);
                selectedNames.push(box.getAttribute('data-name'));
            }
        });
    }

    // Маппинг для красивого отчета в боте
    const categoryMap = { "62": "Վաճառք (Продажа)", "63": "Երկարաժամկետ վարձակալություն (Аренда)" };
    const currencyMap = { "0": "AMD", "1": "USD", "2": "EUR", "3": "RUB" };
    const conditionMap = { "4": "Կառուցված (Построенное)", "5": "Անավարտ (Недостроенное)" };
    const sellerMap = { "1": "Սեփականատեր (Собственник)", "2": "Գործակալություն (Агентство)" };
    const postTypeMap = { "all": "Բոլորը (Все публикации)", "new": "Միայն նոր հայտարարություններ (Только новые)" };

    // Итоговый JSON объект
    const filterData = {
        category_id: selectedCategory,
        category_text: categoryMap[selectedCategory],
        currency_id: selectedCurrency,
        currency_text: selectedCurrency ? currencyMap[selectedCurrency] : "Любая валюта",
        min_price: priceMin ? parseInt(priceMin) : 0,
        max_price: priceMax ? parseInt(priceMax) : "Не указана",
        cnd_id: selectedCondition,
        cnd_text: selectedCondition ? conditionMap[selectedCondition] : "Любое состояние",
        user_id: selectedSeller,
        user_text: selectedSeller ? sellerMap[selectedSeller] : "Все продавцы",
        regions_ids: selectedIds,
        regions_names: selectedNames.length > 0 ? selectedNames : ["Не выбраны"],
        post_type: selectedPostType,
        post_type_text: postTypeMap[selectedPostType]
    };

    // Передаем данные обратно в бота Телеграм
    tg.sendData(JSON.stringify(filterData));
    tg.close();
});