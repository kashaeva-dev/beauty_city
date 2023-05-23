import logging

import telegram
from django.core.management.base import BaseCommand
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    LabeledPrice,
)
from telegram.ext import (
    Updater,
    Filters,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    PreCheckoutQueryHandler,
)
from conf import settings

logging.basicConfig(
    format='{asctime}-{name}-{levelname}-{message}', style='{',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        updater = Updater(token=settings.tg_token)
        dispatcher = updater.dispatcher

        def start(update, context):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Введите /buy, чтобы оплатить 500 рублей!",
                                     )

        prices = [LabeledPrice(label='Стрижка', amount=50000)]

        def buy(update, context):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Вы хотите оплатить 500 рублей?")
            context.bot.send_invoice(
                chat_id=update.effective_chat.id,
                title='Оплата услуг салона красоты',
                payload='some-invoice-payload-for-our-internal-use',
                description='Оплата за стрижку у Татьяны 27.05.2023',
                provider_token=settings.yoo_kassa_provider_token,
                currency='RUB',
                prices=prices,
            )

        def process_pre_checkout_query(update, context):
            query = update.pre_checkout_query
            # Отправка подтверждения о готовности к выполнению платежа
            context.bot.answer_pre_checkout_query(query.id, ok=True)

        start_handler = CommandHandler('start', start)
        buy_handler = CommandHandler('buy', buy)
        pre_checkout_handler = PreCheckoutQueryHandler(process_pre_checkout_query)

        dispatcher.add_handler(start_handler)
        dispatcher.add_handler(buy_handler)
        dispatcher.add_handler(pre_checkout_handler)

        updater.start_polling()
        updater.idle()
