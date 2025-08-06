# 🎯 Yandex SpeechKit Setup Guide

Complete guide for setting up Yandex Cloud SpeechKit API for transcription service.

## Шаг 1: Создание аккаунта Yandex Cloud

1. **Регистрация:**
   - Перейдите на [console.cloud.yandex.com](https://console.cloud.yandex.com)
   - Нажмите **"Создать аккаунт"** или войдите через Yandex ID
   - Подтвердите email адрес

2. **Активация пробного периода:**
   - При первом входе активируйте **пробный период** 
   - Вы получите 4000₽ на 60 дней для тестирования
   - Привяжите банковскую карту (средства не списываются в пробном периоде)

## Шаг 2: Создание облака и каталога

### 2.1 Создание облака (Cloud)

1. **Откройте консоль управления:**
   - Перейдите на [console.cloud.yandex.com](https://console.cloud.yandex.com)
   - Убедитесь, что вы вошли в аккаунт

2. **Создайте облако:**
   - На главной странице найдите кнопку **"Создать облако"** (синяя кнопка)
   - Или в левом меню выберите **"Облака"** → **"Создать облако"**
   - Укажите название: `transcriber-cloud` (или любое другое)
   - Выберите организацию или создайте новую
   - Нажмите **"Создать"**

### 2.2 Создание каталога (Folder) - ВАЖНЫЙ ШАГ

**❗ Каталог (Folder) - это контейнер для ресурсов, БЕЗ него SpeechKit не будет работать!**

1. **Войдите в созданное облако:**
   - Кликните на название вашего облака в списке
   - Вы попадете на страницу управления облаком

2. **Создайте каталог:**
   - В левом меню найдите **"Каталоги"** или **"Folders"**
   - Нажмите **"Создать каталог"** (синяя кнопка справа)
   - **Название**: `transcriber-folder` (можно любое)
   - **Описание**: `Folder for transcriber application` (опционально)
   - Нажмите **"Создать"**

3. **Получите Folder ID:**
   - После создания каталога откроется его страница
   - **СПОСОБ 1**: ID отображается в адресной строке после `/folders/`
     - Пример URL: `https://console.cloud.yandex.com/folders/b1g0123456789abcdef`
     - Ваш ID: `b1g0123456789abcdef`
   
   - **СПОСОБ 2**: ID показан на странице каталога
     - В правом верхнем углу найдите **"Общая информация"** или иконку информации
     - Скопируйте **"Идентификатор"** или **"ID"**
   
   - **СПОСОБ 3**: В списке каталогов
     - Перейдите в **"Каталоги"** в левом меню
     - ID отображается в столбце рядом с названием каталога

4. **Сохраните Folder ID:**
   - **⚠️ КРИТИЧЕСКИ ВАЖНО**: Это ваш `YANDEX_FOLDER_ID`
   - Пример: `b1g0123456789abcdef` (длина ~20 символов)
   - Сохраните его - он понадобится в `.env` файле

**🔍 Как проверить правильность Folder ID:**
```bash
# ID должен начинаться с b1g и содержать буквы/цифры
echo "b1g0123456789abcdef" | grep -E "^b1g[a-z0-9]{16,20}$"
# Если команда вернула ваш ID - формат правильный
```

## Шаг 3: Включение SpeechKit API

1. **Активация сервиса:**
   - В каталоге перейдите в **"Сервисы"**
   - Найдите **"SpeechKit"** 
   - Нажмите **"Подключить"** или **"Активировать"**
   - Подтвердите включение сервиса

2. **Проверка доступности:**
   - Убедитесь, что статус SpeechKit: **"Активен"**
   - Проверьте квоты: STT (Speech-to-Text) должен быть доступен

## Шаг 4: Создание сервисного аккаунта

1. **Создание аккаунта:**
   - Перейдите в **"Сервисные аккаунты"** → **"Создать сервисный аккаунт"**
   - Имя: `transcriber-service-account`
   - Описание: `Service account for audio transcription`

2. **Назначение ролей:**
   - Добавьте роль: **`ai.speechkit.user`** (для использования SpeechKit)
   - Дополнительно: **`storage.viewer`** (если планируете загрузку из Object Storage)
   - Нажмите **"Создать"**

## Шаг 5: Получение API ключа

1. **Создание API ключа:**
   - Откройте созданный сервисный аккаунт
   - Перейдите на вкладку **"API-ключи"**
   - Нажмите **"Создать API-ключ"**
   - Описание: `Transcriber API Key`

2. **Сохранение ключа:**
   - **⚠️ ВАЖНО**: API ключ показывается только один раз!
   - Скопируйте ключ: `AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Это ваш `YANDEX_API_KEY`
   - Сохраните в надежном месте

## Шаг 6: Альтернативные методы аутентификации

### Вариант A: IAM токен (временный, рекомендуется для продакшена)

```bash
# Установка Yandex CLI
curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash

# Аутентификация
yc init

# Получение IAM токена
yc iam create-token
# Токен действует 12 часов
```

### Вариант B: Авторизованные ключи (для продакшена)

```bash
# Создание авторизованного ключа
yc iam key create --service-account-name transcriber-service-account --output key.json

# Использование в коде:
export GOOGLE_APPLICATION_CREDENTIALS=key.json
```

## Шаг 7: Настройка квот и лимитов

1. **Проверка квот:**
   - Перейдите в **"Квоты"** → **"SpeechKit"**
   - Убедитесь в наличии квот на:
     - **STT requests per second**: минимум 10
     - **STT requests per hour**: минимум 1000
     - **STT units per month**: в зависимости от потребности

2. **Увеличение квот (при необходимости):**
   - Нажмите **"Изменить квоты"**
   - Заполните форму с обоснованием
   - Ожидайте одобрения (обычно 1-2 дня)

## Шаг 8: Настройка биллинга

1. **Платежный аккаунт:**
   - Перейдите в **"Биллинг"**
   - Создайте платежный аккаунт
   - Привяжите карту для автоплатежей

2. **Мониторинг расходов:**
   - Настройте уведомления о расходах
   - Рекомендуемый лимит: 1000₽/месяц для начала
   - 1 час аудио ≈ 100-200₽ (зависит от качества)

## Шаг 9: Тестирование подключения

**Создайте тестовый скрипт:**

```bash
# test_yandex_connection.py
import os
import requests

API_KEY = "your-api-key-here"
FOLDER_ID = "your-folder-id-here"

# Тест синхронного распознавания (для файлов <1MB)
def test_sync_recognition():
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "text": "привет мир",  # Тест с синтезом речи
        "folderId": FOLDER_ID,
        "format": "lpcm",
        "sampleRateHertz": "8000"
    }
    
    response = requests.post(url, headers=headers, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

# Тест асинхронного распознавания
def test_async_recognition():
    url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "config": {
            "specification": {
                "languageCode": "ru-RU",
                "model": "general",
                "profanityFilter": False,
                "literature_text": False,
                "format": "lpcm",
                "sampleRateHertz": 8000
            }
        },
        "audio": {
            "uri": f"https://storage.yandexcloud.net/{FOLDER_ID}/test.wav"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Async Status: {response.status_code}")
    return response.status_code in [200, 202]

if __name__ == "__main__":
    print("🧪 Testing Yandex SpeechKit connection...")
    
    if not API_KEY or API_KEY == "your-api-key-here":
        print("❌ Please set your API_KEY")
        exit(1)
    
    if not FOLDER_ID or FOLDER_ID == "your-folder-id-here":
        print("❌ Please set your FOLDER_ID") 
        exit(1)
    
    print("✅ Credentials configured")
    print("🔄 Testing API connection...")
    
    if test_sync_recognition():
        print("✅ Yandex SpeechKit connection successful!")
    else:
        print("❌ Connection failed. Check credentials and quotas.")
```

**Запуск теста:**
```bash
# Установите credentials в .env или экспортируйте
export YANDEX_API_KEY=AQVNxxxxxxxxx
export YANDEX_FOLDER_ID=b1gxxxxxxxxx

# Запустите тест
python test_yandex_connection.py
```

## Шаг 10: Финальная конфигурация

**Добавьте в `.env` файл:**
```bash
# ===== YANDEX SPEECHKIT CONFIGURATION =====
# API Key (обязательно)
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Folder ID (обязательно)  
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx

# Дополнительные настройки (опционально)
YANDEX_API_ENDPOINT=https://stt.api.cloud.yandex.net
YANDEX_ASYNC_ENDPOINT=https://transcribe.api.cloud.yandex.net
YANDEX_DEFAULT_LANGUAGE=ru-RU
YANDEX_MODEL=general
YANDEX_SAMPLE_RATE=16000

# Лимиты и таймауты
YANDEX_REQUEST_TIMEOUT=300
YANDEX_MAX_FILE_SIZE=1073741824  # 1GB
YANDEX_MAX_DURATION=14400        # 4 часа
```

## 🚨 Важные моменты безопасности:

1. **Никогда не публикуйте API ключи в коде**
2. **Используйте переменные окружения**
3. **Регулярно ротируйте API ключи**
4. **Мониторьте использование и расходы**
5. **Настройте уведомления о превышении лимитов**

## 💰 Тарификация (примерные цены):

- **STT (распознавание речи)**: ~2.40₽ за минуту
- **Бесплатный лимит**: 1000 запросов в месяц для разработчиков
- **Дискирование спикеров**: +20% к стоимости
- **Пунктуация**: включена бесплатно

## 📞 Поддержка:

- **Техническая поддержка**: support@cloud.yandex.com  
- **Документация**: [cloud.yandex.ru/docs/speechkit](https://cloud.yandex.ru/docs/speechkit)
- **Сообщество**: [Yandex Cloud Community](https://t.me/yandexcloud)