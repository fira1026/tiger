import logging

import telegram

from django.utils.timezone import localtime
from django.core.mail import send_mail
from django.conf import settings


logger = logging.getLogger(__name__)
default_bot = telegram.Bot(token=settings.BOT_TOKEN)



def send_telegram_notify(alarm_list: list, chat_id=None, bot_token=None):
    """
    :param alarm_list: string list
    """

    time = localtime().strftime('%Y-%m-%d %X')
    start_line = f'#### Notify from: (TEST SHOPPER), {time} ####\n\r'
    content = '\n\r'.join(alarm_list)
    output = start_line + content

    try:
        _send_message(chat_id, bot_token, output)
    except:
        send_mail(
            'Shopper telegram notify fail',
            output,
            settings.EMAIL_HOST_USER,
            settings.DEFAULT_TO_EMAIL,
            fail_silently=False,
        )


def _send_message(chat_id, bot_token, output):
    chat_id = chat_id or settings.BOT_NOTIFY_GROUP_ID
    bot = default_bot if bot_token is None else telegram.Bot(token=bot_token)
    bot.send_message(chat_id=chat_id, text=output, parse_mode="HTML",
                     timeout=5)
