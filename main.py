import asyncio
import os
import json
import random
from pathlib import Path
import shutil
from asyncio import Semaphore
from typing import Dict, Any

import zipfile
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from tqdm import tqdm
from jsonschema import validate, ValidationError

from configs import *

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
semaphore = Semaphore(MAX_CONCURRENT)


def get_proxy(proxy_str: str) -> Dict[str, Any]:
    """Парсинг прокси-строки в формат для Telethon"""
    try:
        host, port, user, password = proxy_str.split(':')
        return {
            'proxy_type': 'socks5',
            'addr': host,
            'port': int(port),
            'username': user,
            'password': password,
            'rdns': True
        }
    except Exception as e:
        logger.error(f"Ошибка парсинга прокси: {str(e)}")
        raise


async def check_spamblock(client: TelegramClient) -> Dict[str, Any]:
    """Проверка статуса блокировки аккаунта"""
    try:
        if not await client.is_user_authorized():
            return {"status": "не_авторизован"}

        spam_bot = await client.get_entity('SpamBot')
        response = await client.send_message(spam_bot, '/start')

        block_keywords = [
            "ограничиваем доступ",
            "аккаунт ограничен",
            "spam ban",
            "restricted",
            "spam detected",
            "account limited",
            "нарушение правил"
        ]

        is_blocked = any(k in response.text.lower() for k in block_keywords)
        return {
            "status": "спам_блок" if is_blocked else "ок",
            "response_text": response.text
        }

    except Exception as e:
        logger.error(f"Ошибка проверки блокировки: {str(e)}")
        return {"status": "ошибка", "details": str(e)}


async def try_reconnect(account_data: dict, json_file: str) -> Dict[str, Any]:
    """Попытка восстановления аккаунта"""
    client = None
    try:
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            try:
                proxy_str = random.choice(PROXIES) if PROXIES else None
                proxy = get_proxy(proxy_str) if proxy_str else None

                client = TelegramClient(
                    StringSession(),
                    account_data['app_id'],
                    account_data['app_hash'],
                    proxy=proxy,
                    device_model=account_data['device'],
                    app_version=account_data['app_version']
                )

                await client.connect()

                if not await client.is_user_authorized():
                    await client.send_code_request(account_data['phone'])
                    if 'phone_code' in account_data:
                        await client.sign_in(
                            phone=account_data['phone'],
                            code=account_data['phone_code'],
                            password=account_data.get('twoFA', '')
                        )

                check_result = await check_spamblock(client)
                if check_result['status'] == 'ок':
                    account_data['session_string'] = client.session.save()
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(account_data, f, ensure_ascii=False, indent=2)
                    return {"status": "восстановлен", "details": check_result}

                await asyncio.sleep(DELAY_BETWEEN_ATTEMPTS)

            except Exception as e:
                logger.error(f"Попытка восстановления {attempt} не удалась: {str(e)}")
                await asyncio.sleep(DELAY_BETWEEN_ATTEMPTS)

        return {"status": "перманентная_блокировка", "details": "Превышено максимальное число попыток"}

    finally:
        if client:
            await client.disconnect()


async def process_account(account_data: dict, json_file: str) -> Dict[str, Any]:
    """Обработка одного аккаунта"""
    client = None
    try:
        proxy = get_proxy(random.choice(PROXIES)) if PROXIES else None
        client = TelegramClient(
            StringSession(account_data.get('session_string', '')),
            account_data['app_id'],
            account_data['app_hash'],
            proxy=proxy,
            device_model=account_data['device'],
            app_version=account_data['app_version']
        )

        await client.connect()

        if not await client.is_user_authorized():
            if 'phone_code' in account_data:
                await client.sign_in(
                    phone=account_data['phone'],
                    code=account_data['phone_code'],
                    password=account_data.get('twoFA', '')
                )
                account_data['session_string'] = client.session.save()
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(account_data, f, ensure_ascii=False, indent=2)
            else:
                await client.send_code_request(account_data['phone'])
                return {"status": "требуется_код"}

        check_result = await check_spamblock(client)
        if check_result['status'] == 'спам_блок':
            return await try_reconnect(account_data, json_file)

        return check_result

    except SessionPasswordNeededError:
        return {"status": "требуется_2fa"}
    except PhoneCodeInvalidError:
        return {"status": "неверный_код"}
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        return {"status": "ошибка", "details": str(e)}
    finally:
        if client:
            await client.disconnect()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "🔒 Бот проверки аккаунтов\n"
        "Отправьте ZIP/RAR архив с JSON файлами аккаунтов"
    )


@dp.message(lambda message: message.document)
async def handle_archive(message: types.Message):
    """Обработчик архивов"""
    Path("temp").mkdir(exist_ok=True)
    Path("accounts").mkdir(exist_ok=True)
    file_path = None

    try:
        if message.document.file_size > MAX_FILE_SIZE:
            await message.answer("❌ Максимальный размер файла 100 МБ")
            return

        # Скачивание файла
        file = await message.bot.get_file(message.document.file_id)
        file_path = f"temp/{message.document.file_name}"
        await message.bot.download_file(file.file_path, file_path)

        # Распаковка архива
        extract_dir = 'accounts'
        if message.document.file_name.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as archive:
                archive.extractall(extract_dir)
        elif message.document.file_name.endswith('.rar'):
            with rarfile.RarFile(file_path) as archive:
                archive.extractall(extract_dir)
        else:
            await message.answer("❌ Поддерживаются только ZIP/RAR архивы")
            return

        # Обработка JSON файлов
        json_files = []
        for root, _, files in os.walk(extract_dir):
            json_files.extend(
                [os.path.join(root, f) for f in files if f.endswith('.json')]
            )

        if not json_files:
            await message.answer("📂 Архив не содержит JSON файлов")
            return

        results = {
            "всего": 0,
            "активны": 0,
            "спам_блок": 0,
            "ошибки": 0,
            "требуется_код": 0,
            "требуется_2fa": 0,
            "восстановлено": 0,
            "перманентные_блокировки": 0
        }

        for json_file in tqdm(json_files, desc="Обработка аккаунтов"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    account = json.load(f)
                    validate(account, ACCOUNT_SCHEMA)

                    async with semaphore:
                        result = await process_account(account, json_file)
                        results["всего"] += 1

                        if result['status'] == 'ок':
                            results["активны"] += 1
                        elif result['status'] == 'спам_блок':
                            results["спам_блок"] += 1
                        elif result['status'] == 'восстановлен':
                            results["восстановлено"] += 1
                        elif result['status'] == 'перманентная_блокировка':
                            results["перманентные_блокировки"] += 1
                        elif result['status'] == 'требуется_код':
                            results["требуется_код"] += 1
                        elif result['status'] == 'требуется_2fa':
                            results["требуется_2fa"] += 1
                        else:
                            results["ошибки"] += 1

            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Неверный JSON: {json_file} - {str(e)}")
                results["ошибки"] += 1
            except Exception as e:
                logger.error(f"Ошибка обработки: {str(e)}")
                results["ошибки"] += 1

        # Формирование отчета
        report = (
            f"📊 Результаты проверки:\n"
            f"• Всего аккаунтов: {results['всего']}\n"
            f"🟢 Активны: {results['активны']}\n"
            f"🔴 Заблокированы: {results['спам_блок']}\n"
            f"♻️ Восстановлено: {results['восстановлено']}\n"
            f"⛔ Перманентные блокировки: {results['перманентные_блокировки']}\n"
            f"📲 Требуется код: {results['требуется_код']}\n"
            f"🔑 Требуется 2FA: {results['требуется_2fa']}\n"
            f"⚠️ Ошибки: {results['ошибки']}"
        )

        await message.answer(report)

    except Exception as e:
        logger.error(f"Ошибка обработки архива: {str(e)}")
        await message.answer("⚠️ Ошибка обработки архива")
    finally:
        # Очистка
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        if not os.path.exists(rarfile.UNRAR_TOOL):
            raise RuntimeError(
                f"UnRAR не найден по пути: {rarfile.UNRAR_TOOL}\n"
                "Требуется установка"
            )

        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        exit(1)
