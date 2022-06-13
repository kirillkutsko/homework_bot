import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(lineno)d',
    encoding='utf-8',
    filename='homework_bot/logging/main.log',
    filemode="w"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    encoding='UTF-8',
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(lineno)d'
)
handler.setFormatter(formatter)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправить сообщение о результатах ревью."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Начало отправки сообщения')
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception as error:
        logging.error(f'Сообщение не отправлено {error}')
        raise Exception(f'Сообщение не отправлено {error}')


def get_api_answer(current_timestamp):
    """Получить запрос с API."""
    params = dict(url=ENDPOINT, headers=HEADERS,
                  params={'from_date': current_timestamp})
    try:
        response = requests.get(**params)
        logger.info('Отправлен API запрос.')
    except Exception as error:
        logging.error(f'Ошибка при запросе {params}: {error}')
        raise Exception(f'Ошибка при запросе {params}: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    return response.json()


def check_response(response):
    """Проверить корректность ответа API."""
    logging.info('Начало получения ответа от сервера')
    if not isinstance(response, dict):
        raise TypeError(f'Неверный формат данных {response}')
    homework_list = response.get('homeworks')
    current_date = response.get('current_date')
    if homework_list is None or current_date is None:
        raise KeyError(
            f'Такой ключ {homework_list} {current_date} отстуствует на сервере'
        )
    if not isinstance(homework_list, list):
        raise TypeError(f'Неверный формат данных {homework_list}')
    return homework_list


def parse_status(homework):
    """Извлечь информацию о статусе домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверить доступность переменных окружения."""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cache_message = ''
    cache_error_message = ''
    if not check_tokens():
        logger.critical('Отсутсвует один из токенов')
        sys.exit('Отсутсвует один из токенов')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            # message = parse_status(check_response(response))
            homework = check_response(response)
            message = parse_status(homework[0])
            if message != cache_message:
                send_message(bot, message)
                cache_message = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            message_error = f'Сбой в работе программы: {error}'
            if message_error != cache_error_message:
                send_message(bot, message_error)
                cache_error_message = message_error
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
