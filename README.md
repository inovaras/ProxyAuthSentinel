Telegram-бот, предназначенный для массовой проверки Telegram-аккаунтов на наличие спам-блокировки через официального Telegram-бота.
Бот принимает архивы с JSON-файлами аккаунтов, пересоздаёт сессии на основе данных из этих файлов и проверяет каждую новую сессию на блокировку.

Возможности: 
- Загрузка .zip или .rar архивов
- Автоматическая распаковка и обработка JSON-файлов
- Пересоздание сессий на основе данных из JSON
- Проверка спам-блокировки
- Вывод статистики: активных, заблокированных, ошибочных аккаунтов
- Восстановление временно заблокированных аккаунтов
- Параллельная обработка с ограничением потоков
- Поддержка прокси (SOCKS5)
- Логирование действий

📁 Структура проекта
```
├── main.py              # Код бота
├── configs.py           # Конфигурация, логирование, настройки
├── requirements.txt     
├── .env                 # Переменные окружения
├── .gitignore          
├── README.md            
```

⚙️ Установка и настройка
1. Клонируйте репозиторий:
```bash
  git clone https://github.com/inovaras/ProxyAuthSentinel
  cd ProxyAuthSentinel
```
2. Создайте и активируйте виртуальное окружение, установите зависимости:
```bash
  # Создание виртуального окружения
  # Windows:
  python -m venv venv
  
  # Linux:
  python3 -m venv venv
  
  # Активация
  # Windows:
  .\venv\Scripts\activate
  
  # Linux:
  source venv/bin/activate
  
  pip install -r requirements.txt
```
Для работы с .rar также установите UnRAR :

Windows : Скачайте UnRAR.exe и положите в корень проекта или системный PATH
Linux :
```bash
  sudo apt-get install unrar
```
3. Настройте .env файл:
Создайте файл .env в корне проекта со следующими переменными:

```env
BOT_TOKEN=telegram_bot_token
API_ID=telegram_api_id
API_HASH=telegram_api_hash
PROXIES=ip:port:user:pass,ip:port:user:pass

MAX_RECONNECT_ATTEMPTS=3
DELAY_BETWEEN_ATTEMPTS=10
```
🤖 Как использовать бота
Запустите бота:
```bash
  python main.py
```

Напишите команду /start боту в Telegram.
Отправьте ZIP/RAR архив с JSON-файлами аккаунтов.
Бот выдаст подробный отчёт по состоянию каждого аккаунта.

📊 Пример отчёта
```
📊 Результаты проверки:
• Всего аккаунтов: 50
🟢 Активны: 30
🔴 Заблокированы: 5
♻️ Восстановлено: 3
⛔ Перманентные блокировки: 2
🔑 Требуется 2FA: 2
⚠️ Ошибки: 1
📌 Формат JSON-файла аккаунта
```
Каждый аккаунт должен быть сохранён в отдельном JSON-файле со следующими полями:

```json
{
  "phone": "+79991234567",
  "twoFA": "password",
  "app_id": 123456,
  "app_hash": "abcdef1234567890abcdef1234567890",
  "device": "iPhone 13",
  "app_version": "Telegram iOS 10.1",
  "phone_code": "12345",
  "session_string": "1AgAAA..."
}
```
Обязательные поля: phone, app_id, app_hash, device, app_version 

📦 Константы в configs.py
```Python
MAX_CONCURRENT # Максимальное количество одновременно обрабатываемых аккаунтов
MAX_FILE_SIZE # Максимальный размер загружаемого архива (в байтах)
MAX_RECONNECT_ATTEMPTS # Максимальное число попыток восстановления аккаунта
DELAY_BETWEEN_ATTEMPTS # Задержка между попытками (в секундах)
PROXY_ROTATION # Использовать разные прокси при повторных попытках
```