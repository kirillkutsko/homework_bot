import logging
import os
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
    format='%(asctime)s - %(levelname)s - %(message)s',
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
    '%(asctime)s - %(levelname)s - %(message)s'
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
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Получить запрос с API."""
    params = dict(url=ENDPOINT, headers=HEADERS,
                  params={'from_date': current_timestamp})
    try:
        response = requests.get(**params)
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError('Сайт недоступен')
        print(response.json())
        return response.json()
    except Exception as error:
        raise Exception(f'Ошибка при запросе {params}: {error}')


def check_response(response):
    """Проверить корректность ответа API."""
    logging.info('Начало получение ответа от сервера')
    homework_list = response['homeworks']
    current_date = response.get('current_date')
    if not isinstance(response, dict):
        raise TypeError(f'Неверный формат данных {response}')
    if homework_list is None:
        raise KeyError(f'Такой ключ {homework_list} отстуствует на сервере')
    if current_date is None:
        raise KeyError(f'Такой ключ {current_date} отстуствует на сервере')
    if not isinstance(homework_list, list):
        raise TypeError(f'Неверный формат данных {homework_list}')
    return homework_list


def parse_status(homework):
    """Извлечь информацию о статусе домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        logger.error('Работы с таким именем не обнаружено')
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Непредвиденный статус работы')
        raise KeyError('Непредвиденный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверить доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is True:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                current_timestamp = response.get(
                    'current_date',
                    current_timestamp
                )
                homework = check_response(response)
                message = parse_status(homework[0])
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
    else:
        raise KeyError('Отсутсвует один из элементов')
        logger.critical('Отсутсвует один из элементов')


if __name__ == '__main__':
    main()
