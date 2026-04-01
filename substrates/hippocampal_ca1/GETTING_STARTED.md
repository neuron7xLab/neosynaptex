# 🚀 Getting Started with Hippocampal-CA1-LAM

**Швидкий старт для початківців** - повна покрокова інструкція.

---

## 📋 Вимоги

Перед початком переконайтеся, що у вас є:

- ✅ **Python 3.10 або новіше** ([завантажити](https://www.python.org/downloads/))
- ✅ **Git** ([завантажити](https://git-scm.com/downloads)) - опційно, для GitHub
- ✅ **Terminal/Command Prompt** - вбудовано в OS
- ✅ **4 GB RAM** (рекомендовано 16 GB)
- ✅ **500 MB вільного місця**

### Перевірка Python

Відкрийте термінал та виконайте:

```bash
python3 --version
# Або на Windows:
python --version
```

Має бути Python 3.10 або новіше.

---

## ⚡ МЕТОД 1: Супер швидкий старт (Рекомендовано)

**Найпростіший спосіб - одна команда!**

### Linux / macOS

```bash
# 1. Перейдіть до папки з проектом
cd Hippocampal-CA1-LAM

# 2. Запустіть швидкий старт
bash quick_start.sh
```

### Windows

```powershell
# 1. Перейдіть до папки з проектом
cd Hippocampal-CA1-LAM

# 2. Запустіть швидкий старт
bash quick_start.sh
# Або якщо bash не встановлено:
python quick_start.py
```

**Що відбудеться**:
1. ✓ Перевірка Python
2. ✓ Створення віртуального середовища
3. ✓ Встановлення всіх залежностей
4. ✓ Запуск тестів для перевірки

**Очікуваний результат**:
```
✅ ГОТОВО! 6/6 PASSED
```

**Що далі?** Перейдіть до [Запуск прикладів](GETTING_STARTED.md#run-examples)

---

## 📦 МЕТОД 2: Ручна установка (Крок за кроком)

Якщо автоматичний скрипт не працює, ось повна інструкція.

### Крок 1: Розпакувати архів

```bash
# Якщо у вас .tar.gz архів
tar -xzf Hippocampal-CA1-LAM-v2.0.tar.gz
cd Hippocampal-CA1-LAM

# Або якщо завантажили з GitHub
git clone https://github.com/neuron7xLab/Hippocampal-CA1-LAM.git
cd Hippocampal-CA1-LAM
```

### Крок 2: Створити віртуальне середовище

**Linux / macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:
```powershell
python -m venv venv
venv\Scripts\activate
```

Ви побачите `(venv)` перед командним рядком.

### Крок 3: Встановити залежності

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Це встановить:
- NumPy (математика)
- SciPy (наукові обчислення)
- scikit-learn (машинне навчання)

### Крок 4: Перевірити установку

```bash
python test_golden_standalone.py
```

**Очікуваний результат**:
```
======================================================================
GOLDEN TEST SUITE - CA1 HIPPOCAMPUS
======================================================================

✓ Network Stability
✓ Ca2+ Plasticity
✓ Input-Specific
✓ Theta-SWR
✓ Reproducibility

RESULTS: 5/5 PASSED
✓ ALL GOLDEN TESTS PASSED
```

**Якщо тести пройшли** ✅ - все працює!

**Якщо є помилки** ❌ - див. [Troubleshooting](GETTING_STARTED.md#troubleshooting)

---

## Run Examples

_(Запуск прикладів)_

Після успішної установки спробуйте приклади:

### Приклад 1: Базове використання

```bash
python examples/demo_basic_usage.py
```

Що показує:
- Створення нейронної мережі
- Симуляція 500 ms
- Пластичність синапсів
- Стабільність мережі

### Приклад 2: Theta-SWR перемикання

```bash
python examples/demo_theta_swr.py
```

Що показує:
- Зміна станів (theta ↔ SWR)
- Детекція replay events
- Модуляція гейтування

### Приклад 3: Ca²⁺ пластичність

```bash
python examples/demo_ca_plasticity.py
```

Що показує:
- LTP (довготривала потенціація)
- LTD (довготривала депресія)
- Залежність від Ca²⁺

---

## 🛠️ Робота з кодом

### Основний workflow

```python
# 1. Імпортувати модулі
from data.biophysical_parameters import get_default_parameters
from plasticity.unified_weights import UnifiedWeightMatrix

# 2. Отримати параметри
params = get_default_parameters()

# 3. Створити мережу
# (див. приклади)

# 4. Запустити симуляцію
# (див. приклади)
```

### Де знайти що

```
Hippocampal-CA1-LAM/
├── data/                       # Параметри (всі з DOI)
├── core/                       # Основні моделі
│   ├── hierarchical_laminar.py # Інференція шарів
│   ├── neuron_model.py         # Динаміка нейронів
│   └── theta_swr_switching.py  # Перемикання станів
├── plasticity/
│   └── unified_weights.py      # Пластичність синапсів
├── ai_integration/
│   └── memory_module.py        # Інтеграція з LLM
├── examples/                   # Приклади використання
└── docs/                       # Документація
```

---

## 📚 Навчальні ресурси

### Документація

1. **[API Reference](docs/API.md)** - Опис всіх функцій
2. **[Usage Guide](docs/USAGE.md)** - Приклади використання
3. **[Architecture](docs/ARCHITECTURE.md)** - Як влаштовано
4. **[Testing](docs/TESTING.md)** - Як тестувати
5. **[Bibliography](docs/BIBLIOGRAPHY.md)** - Наукові джерела

### Поради для початківців

1. **Почніть з прикладів** - `examples/demo_basic_usage.py`
2. **Читайте docstrings** - кожна функція має опис
3. **Запускайте тести** - `python test_golden_standalone.py`
4. **Експериментуйте** - змінюйте параметри в прикладах

---

## Troubleshooting

### Проблема: "ModuleNotFoundError: No module named 'numpy'"

**Рішення**:
```bash
pip install -r requirements.txt
```

### Проблема: "python3: command not found"

**Рішення**:
- **Windows**: Використовуйте `python` замість `python3`
- **Linux/macOS**: Встановіть Python 3

### Проблема: Тести не проходять

**Рішення**:
1. Перевірте версію Python: `python3 --version` (має бути ≥3.10)
2. Перевстановіть залежності: `pip install -r requirements.txt --force-reinstall`
3. Перевірте віртуальне середовище активне: `(venv)` має бути видно

### Проблема: "Permission denied" (Linux/macOS)

**Рішення**:
```bash
chmod +x quick_start.sh
bash quick_start.sh
```

### Проблема: Повільна робота

**Рішення**:
- Використовуйте менше нейронів у прикладах (N=50 замість N=100)
- Закрийте інші програми
- Переконайтеся що NumPy використовує оптимізовану версію

---

## 💡 Корисні команди

### Makefile (якщо є make)

```bash
make help          # Показати всі команди
make install       # Встановити залежності
make test          # Запустити всі тести
make run-example   # Запустити приклад
make clean         # Очистити тимчасові файли
```

### Bash скрипти

```bash
bash quick_start.sh              # Швидкий старт
bash setup_dev_environment.sh    # Dev середовище
bash scripts/run_all_tests.sh    # Всі тести
bash deploy_to_github.sh         # Deploy на GitHub
```

### Python скрипти

```bash
python test_golden_standalone.py          # Golden tests
python examples/demo_basic_usage.py       # Базовий приклад
python utils/create_release.py            # Створити реліз
```

---

## 🎓 Наступні кроки

Тепер коли все працює, ви можете:

1. **Вивчити API** - `docs/API.md`
2. **Модифікувати приклади** - змінити параметри
3. **Створити свій проект** - використати як бібліотеку
4. **Контрибутити** - `CONTRIBUTING.md`

### Для дослідників

- Читайте `docs/BIBLIOGRAPHY.md` - всі DOI джерела
- Перевіряйте `validation/validators.py` - критерії валідації
- Експериментуйте з параметрами - всі з літератури

### Для розробників

- Налаштуйте dev середовище: `bash setup_dev_environment.sh`
- Вивчіть тести: `tests/test_unified_weights.py`
- Використайте pre-commit hooks для якості коду

---

## 📞 Підтримка

**Проблеми?**
- GitHub Issues: https://github.com/neuron7xLab/Hippocampal-CA1-LAM/issues
- Документація: `docs/`

**Питання про використання?**
- GitHub Issues: https://github.com/neuron7xLab/Hippocampal-CA1-LAM/issues

---

## ✅ Чеклист готовності

Перевірте що все працює:

- [ ] Python 3.10+ встановлено
- [ ] Віртуальне середовище створено
- [ ] Залежності встановлені
- [ ] Golden tests проходять (6/6)
- [ ] Приклад запускається без помилок

**Все ✓?** Ви готові використовувати Hippocampal-CA1-LAM! 🎉

---

**Last updated**: December 14, 2025
