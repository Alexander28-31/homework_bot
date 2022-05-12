import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (DictKeyError, JsonError, KeyErrorStatus, NetError,
                        TypeErrorHTTPStatus)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w')

logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = 1101252719

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(
            f'Сообщение в TG {message}  отправленно'
        )
    except telegram.error.TelegramError:
        logger.error(
            f'Сообщение {message} не отправленно'
        )


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logging.info('Попытка соединения до эндпоинта')
    misstake_inet = 'Проблемы с интернетом'
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except telegram.error.NetworkError:
        logger.error(misstake_inet)
        raise NetError(misstake_inet)
    misstake_serv = (f'Проблема с соединением с сервером'
                     f'Ошибка {homework_statuses.status_code}')
    misstake_json = 'Json не получен'
    try:
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        logging.error(misstake_serv)
        raise TypeErrorHTTPStatus(misstake_serv)
    except ValueError:
        logger.error(misstake_json)
        raise JsonError(misstake_json)


def check_response(response):
    """Проверка ответ API на корректность."""
    misstake_api = 'Ответ API отличен от словаря'
    misstake_key = 'Ошибка словаря по ключу homeworks'
    misstake_list = 'Список работ пуст'
    if type(response) is not dict:
        raise TypeError(misstake_api)
    try:
        list_works = response['homeworks']
    except KeyError:
        logger.error(misstake_key)
        raise DictKeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = list_works[0]
    except Exception:
        logger.info(misstake_list)
    return homework


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    misstake_homework = 'homework_name отсутствует в homework'
    misstake_key_status = 'Отсутствует ключ "status" в ответе API'
    if 'homework_name' not in homework:
        raise KeyError(misstake_homework)
    if 'status' not in homework:
        raise KeyErrorStatus(misstake_key_status)
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    tok_bool = True
    if PRACTICUM_TOKEN is None:
        tok_bool = False
        logger.critical(f'Токен {PRACTICUM_TOKEN} не найден')
    if TELEGRAM_TOKEN is None:
        tok_bool = False
        logger.critical(f'Токен {TELEGRAM_TOKEN} не найден')
    if TELEGRAM_CHAT_ID is None:
        tok_bool = False
        logger.critical(f'Чат {TELEGRAM_CHAT_ID} не найден')
    return tok_bool


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    misstake_critical = 'Отсутствуют одна или несколько переменных окружения'
    if not check_tokens():
        logger.critical(misstake_critical)
        sys.exit()

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            current_timestamp = int(time.time())
        else:
            logger.debug('Нет новых статусов')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
