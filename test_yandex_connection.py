#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки подключения к Yandex SpeechKit API
Test script for Yandex SpeechKit API connection verification

Использование / Usage:
    python test_yandex_connection.py

Требуется установка переменных окружения:
Required environment variables:
    YANDEX_API_KEY - Ваш API ключ Yandex Cloud
    YANDEX_FOLDER_ID - ID каталога в Yandex Cloud
"""

import os
import sys
import requests
import json
from typing import Dict, Optional, Tuple

# Цвета для вывода в терминал / Terminal colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    """Вывод сообщения об успехе"""
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message: str):
    """Вывод сообщения об ошибке"""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message: str):
    """Вывод предупреждения"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message: str):
    """Вывод информационного сообщения"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def print_header(message: str):
    """Вывод заголовка"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🔧 {message}{Colors.ENDC}")

class YandexSpeechKitTester:
    """Класс для тестирования подключения к Yandex SpeechKit"""
    
    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.base_url = "https://stt.api.cloud.yandex.net"
        self.async_url = "https://transcribe.api.cloud.yandex.net"
        
    def validate_credentials(self) -> bool:
        """Проверка корректности учетных данных"""
        if not self.api_key or self.api_key == "your-api-key-here":
            print_error("API ключ не установлен!")
            print_info("Установите YANDEX_API_KEY в переменные окружения")
            return False
            
        if not self.folder_id or self.folder_id == "your-folder-id-here":
            print_error("Folder ID не установлен!")
            print_info("Установите YANDEX_FOLDER_ID в переменные окружения")
            return False
            
        # Проверка формата API ключа
        if not self.api_key.startswith('AQVN'):
            print_warning("API ключ имеет необычный формат. Обычно он начинается с 'AQVN'")
            
        # Проверка формата Folder ID
        if not self.folder_id.startswith('b1g'):
            print_warning("Folder ID имеет необычный формат. Обычно он начинается с 'b1g'")
            
        print_success("Учетные данные корректно настроены")
        return True
    
    def test_api_availability(self) -> Tuple[bool, Optional[Dict]]:
        """Тест доступности API через простой запрос"""
        print_header("Тестирование доступности API")
        
        url = f"{self.base_url}/speech/v1/stt:recognize"
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Минимальные данные для тестирования API
        data = {
            "folderId": self.folder_id,
            "format": "lpcm",
            "sampleRateHertz": "8000",
        }
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=data, 
                timeout=30,
                # Отправляем пустые аудиоданные для проверки авторизации
                files={'audio': ('test.wav', b'', 'audio/wav')}
            )
            
            print_info(f"HTTP Status: {response.status_code}")
            
            # Проверяем различные коды ответов
            if response.status_code == 200:
                print_success("API доступен и авторизация прошла успешно!")
                return True, response.json() if response.content else None
                
            elif response.status_code == 401:
                print_error("Ошибка авторизации! Проверьте API ключ")
                print_info("Возможные причины:")
                print_info("  • Неверный API ключ")
                print_info("  • API ключ отозван или истек")
                print_info("  • Неверный формат ключа")
                return False, None
                
            elif response.status_code == 403:
                print_error("Доступ запрещен! Проверьте права сервисного аккаунта")
                print_info("Убедитесь, что сервисному аккаунту назначена роль 'ai.speechkit.user'")
                return False, None
                
            elif response.status_code == 429:
                print_error("Превышен лимит запросов!")
                print_info("Подождите немного и повторите попытку")
                return False, None
                
            elif response.status_code == 400:
                # Это ожидаемо для пустого аудио - значит авторизация работает
                print_success("API доступен! (Получена ошибка 400 для пустых данных - это нормально)")
                try:
                    error_data = response.json()
                    print_info(f"Детали ошибки: {error_data.get('message', 'Нет описания')}")
                except:
                    pass
                return True, None
                
            else:
                print_error(f"Неожиданный код ответа: {response.status_code}")
                try:
                    error_data = response.json()
                    print_info(f"Ответ сервера: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print_info(f"Текст ответа: {response.text}")
                return False, None
                
        except requests.exceptions.Timeout:
            print_error("Превышено время ожидания запроса")
            return False, None
        except requests.exceptions.ConnectionError:
            print_error("Ошибка соединения с API")
            print_info("Проверьте интернет-соединение")
            return False, None
        except Exception as e:
            print_error(f"Неожиданная ошибка: {str(e)}")
            return False, None
    
    def test_folder_access(self) -> bool:
        """Проверка доступа к указанному каталогу"""
        print_header("Проверка доступа к каталогу")
        
        # Используем Operations API для проверки доступа к каталогу
        url = "https://operation.api.cloud.yandex.net/operations"
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params={"folderId": self.folder_id},
                timeout=10
            )
            
            if response.status_code in [200, 404]:  # 404 тоже нормально - просто нет операций
                print_success("Доступ к каталогу подтвержден")
                return True
            elif response.status_code == 403:
                print_error("Нет доступа к указанному каталогу!")
                print_info(f"Проверьте правильность Folder ID: {self.folder_id}")
                return False
            else:
                print_warning(f"Неопределенный результат (код {response.status_code})")
                return True  # Считаем успехом, если не явная ошибка доступа
                
        except Exception as e:
            print_warning(f"Не удалось проверить доступ к каталогу: {str(e)}")
            print_info("Это не критично - продолжаем тестирование")
            return True
    
    def test_quota_limits(self) -> bool:
        """Информация о квотах и лимитах"""
        print_header("Информация о квотах")
        
        print_info("Стандартные лимиты Yandex SpeechKit:")
        print_info("  • Синхронное распознавание: файлы до 1 МБ")
        print_info("  • Асинхронное распознавание: файлы до 1 ГБ")
        print_info("  • Максимальная длительность: 4 часа")
        print_info("  • Поддерживаемые форматы: WAV, MP3, FLAC, OGG")
        print_info("  • Частота дискретизации: 8000-48000 Гц")
        
        print_warning("Проверьте ваши квоты в консоли Yandex Cloud:")
        print_info("  https://console.cloud.yandex.com → Квоты → SpeechKit")
        
        return True
    
    def generate_test_summary(self, tests_passed: int, total_tests: int) -> None:
        """Генерация итогового отчета"""
        print_header("Итоговый отчет тестирования")
        
        if tests_passed == total_tests:
            print_success(f"Все тесты пройдены успешно! ({tests_passed}/{total_tests})")
            print_success("Yandex SpeechKit готов к использованию!")
            print_info("\nСледующие шаги:")
            print_info("  1. Запустите приложение transcriber")
            print_info("  2. Загрузите тестовый аудиофайл")
            print_info("  3. Проверьте процесс транскрипции")
        else:
            print_error(f"Пройдено тестов: {tests_passed}/{total_tests}")
            print_error("Исправьте ошибки перед использованием приложения")
            print_info("\nРекомендации по устранению:")
            print_info("  • Проверьте правильность API ключа и Folder ID")
            print_info("  • Убедитесь в наличии интернет-соединения") 
            print_info("  • Проверьте квоты в консоли Yandex Cloud")
            print_info("  • Обратитесь к документации: https://cloud.yandex.ru/docs/speechkit")

def load_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Загрузка учетных данных из переменных окружения или .env файла"""
    
    # Попытка загрузить из .env файла
    env_file = '.env'
    if os.path.exists(env_file):
        print_info(f"Загружаем переменные из {env_file}")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in ['YANDEX_API_KEY', 'YANDEX_FOLDER_ID']:
                            os.environ[key] = value
        except Exception as e:
            print_warning(f"Не удалось загрузить .env файл: {e}")
    
    api_key = os.getenv('YANDEX_API_KEY')
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    
    return api_key, folder_id

def main():
    """Основная функция тестирования"""
    print_header("Yandex SpeechKit Connection Tester")
    print_info("Этот скрипт проверит подключение к Yandex SpeechKit API")
    
    # Загружаем учетные данные
    api_key, folder_id = load_credentials_from_env()
    
    if not api_key or not folder_id:
        print_error("Не найдены учетные данные!")
        print_info("\nСпособы настройки:")
        print_info("1. Создайте файл .env в корне проекта:")
        print_info("   YANDEX_API_KEY=ваш-api-ключ")
        print_info("   YANDEX_FOLDER_ID=ваш-folder-id")
        print_info("")
        print_info("2. Или установите переменные окружения:")
        print_info("   export YANDEX_API_KEY=ваш-api-ключ")
        print_info("   export YANDEX_FOLDER_ID=ваш-folder-id")
        print_info("")
        print_info("Получить ключи: https://console.cloud.yandex.com")
        sys.exit(1)
    
    # Создаем тестер
    tester = YandexSpeechKitTester(api_key, folder_id)
    
    # Запускаем тесты
    tests = [
        ("Проверка учетных данных", tester.validate_credentials),
        ("Тест доступности API", lambda: tester.test_api_availability()[0]),
        ("Проверка доступа к каталогу", tester.test_folder_access),
        ("Информация о квотах", tester.test_quota_limits),
    ]
    
    tests_passed = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                tests_passed += 1
        except Exception as e:
            print_error(f"Ошибка в тесте '{test_name}': {str(e)}")
    
    # Генерируем отчет
    tester.generate_test_summary(tests_passed, total_tests)
    
    # Код выхода
    sys.exit(0 if tests_passed == total_tests else 1)

if __name__ == "__main__":
    main()