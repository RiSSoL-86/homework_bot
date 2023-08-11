import logging
import os
import time

import requests
import telegram
from telegram.error import TelegramError
from dotenv import load_dotenv

from exceptions import (TokensError, URLError, KeyError, HomeworksError,
                        HomeworkStatusError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

GREETINGS_TEXT = '''Привет, я телеграмм-бот которй будет оповещать тебя
о статусе твоей домашней работы!!!'''

SUCCESSFUL_SENDING_TEXT = 'Сообщение успешно отправлено'

START_HOMEWORK_STATUS = ''

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    encoding='utf-8',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def check_tokens():
    """Проверяет доступность переменных окружения.
    Которые необходимы для работы программы.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params={'from_date': timestamp})
        if response.status_code != 200:
            text_error = f'недоступность эндпоинта {ENDPOINT}'
            raise URLError(text_error)
        return response.json()
    except Exception as error:
        logging.error(error)
        raise Exception(error)


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if isinstance(response, dict):
        homeworks = response.get('homeworks')
        if isinstance(homeworks, list):
            if not homeworks:
                text_error = 'домашние работы для проверки отсутствуют'
                logging.error(text_error)
                raise HomeworksError(text_error)
            return homeworks[0]
    text_error = 'API структура данных не соответствует заданной'
    logging.error(text_error)
    raise TypeError(text_error)


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework['status'])
    if not homework_name:
        text_error = 'домашняя работа с таким именем отсутствует'
        logging.error(text_error)
        raise KeyError(text_error)
    if not verdict:
        text_error = 'неизвестный статус домашней работы'
        logging.error(text_error)
        raise HomeworkStatusError(text_error)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    global START_HOMEWORK_STATUS
    if START_HOMEWORK_STATUS != message:
        try:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logging.debug(SUCCESSFUL_SENDING_TEXT)
            START_HOMEWORK_STATUS = message
        except TelegramError:
            text_error = 'ошибка отправки сообщений'
            logging.error(text_error)
    else:
        logging.info(f'следующий запрос через: {RETRY_PERIOD} сек.')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        text_error = 'Ошибка TOKENs. Программа принудительно остановлена'
        logging.critical(text_error)
        raise TokensError(text_error)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, GREETINGS_TEXT)
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            homework_status = parse_status(homework)
            send_message(bot, homework_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
