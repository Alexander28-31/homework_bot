import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (DictKeyError, KeyErrorStatus, ListHomeworkNull,
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

HOMEWORK_STATUSES = {
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
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except telegram.error.NetworkError:
        logger.error('Проблемы с интернетом')
    try:
        misstake = (f'Проблема с соединением с сервером'
                    f'Ошибка {homework_statuses.status_code}')
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        elif homework_statuses.status_code != HTTPStatus.OK:
            logging.error(misstake)
            raise TypeErrorHTTPStatus(misstake)
    except ValueError:
        logger.error('Json не получен')


def check_response(response):
    """Проверка ответ API на корректность."""
    if type(response) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        list_works = response['homeworks']
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise DictKeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = list_works[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise ListHomeworkNull('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('homework_name отсутствует в homework')
    if 'status' not in homework:
        raise KeyErrorStatus('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
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
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
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
            time.sleep(RETRY_TIME)
        else:
            logger.debug('Нет новых статусов')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
