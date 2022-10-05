from http import HTTPStatus
import logging
import os
import sys
import time
import requests
import telegram
from dotenv import load_dotenv

import exceptions as my_exc


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        logger.info('Отправка сообщения начата!')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        raise my_exc.RequestExceptionError(
            f'Сообщение в Telegram не отправлено: {telegram_error}')


def get_api_answer(current_timestamp):
    """Получение данных с API YP."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info('Начало получения данных с API YP')
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params,
                                         timeout=10)
    except ConnectionError as error:
        raise my_exc.RequestExceptionError(f'Error in the request {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        homework_statuses.raise_for_status()

    logger.info('успешное получение Эндпоинта')
    return homework_statuses.json()


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            'Некорректная сущность {}'.format(response))

    homeworks = response.get('homeworks')
    if not homeworks or not isinstance(homeworks, list):
        msg = ('homeworks = {} : нет искомого ключа или '
               'список домашних работ пуст'.format(homeworks))
        raise my_exc.EmptyDictionaryOrListError(msg)

    return homeworks


def parse_status(homework):
    """Парсинг информации о домашке."""
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        msg = 'API have returned a homework without a "homework_name" key'
        raise KeyError(msg)
    homework_status = homework.get('status')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        msg = ('API have returned'
               f'an unknown status {homework_status} for "{homework_name}"'
               )
        raise my_exc.APIErrException(msg)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет доступность переменных окружения.
    Которые необходимы для работы программы.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота. Делает запрос к API.
    Проверяет ответ, если есть обновления получает статус,
    работы из обновлений и отправляет сообщение в,
    Telegram и ждет некоторое время и делает новый запрос
    """
    if not check_tokens():
        message = 'Отсутствует один или несколько токенов'
        logger.critical('Я вышел')
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME

    while True:
        try:
            if type(current_timestamp) is not int:
                raise my_exc.LogicExceptionError('В функцию передана не дата')
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if len(homeworks):
                homework_status = parse_status(homeworks[0])
                if homework_status is not None:
                    send_message(bot, homework_status)
            else:
                logger.debug('нет новых статусов')

        except (my_exc.APIErrException,
                requests.exceptions.RequestException) as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='bot.log',
        format='%(asctime)s, %(levelname)s, %(message)s,'
               '%(funcName)s, %(lineno)s',
        filemode='a',
    )
    main()
