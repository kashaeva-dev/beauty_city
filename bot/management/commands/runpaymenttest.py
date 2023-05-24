import datetime
import logging
from prettytable import PrettyTable

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

from bot.models import (
    Slot,
    Appointment,
    Client,
    Service,
)

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
            context.user_data['ap_id'] = 45
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

        def calendar(update, context):
            slots = Slot.objects.filter(appointment__isnull=True).values_list('start_date', flat=True).distinct().order_by('start_date')
            print(slots)
            min_date = slots.first()
            print(min_date)
            max_date = slots.last()
            print(max_date)
            min_date_weekday = min_date.weekday()
            print(min_date_weekday)
            max_date_weekday = max_date.weekday()
            print(max_date_weekday)
            delta_to_monday = datetime.timedelta(days=min_date_weekday)
            print(delta_to_monday)
            delta_to_sunday = datetime.timedelta(days=6 - max_date_weekday)
            print(delta_to_sunday)
            start_date = min_date - delta_to_monday
            print('start_date', start_date)
            end_date = max_date + delta_to_sunday
            print('end_date', end_date)
            dates = []
            while start_date <= end_date:
                dates.append(start_date)
                start_date += datetime.timedelta(days=1)
            print(*dates)
            dates_keyboard = []
            for date in dates:
                if date in slots:
                    date_text = f'{date.strftime("%d.%m")}'
                    dates_keyboard.append(InlineKeyboardButton(date_text, callback_data=f'date_{date.strftime("%Y-%m-%d")}'))
                else:
                    dates_keyboard.append(InlineKeyboardButton(' ', callback_data='null'))
            dates_keyboard = [dates_keyboard[i:i + 7] for i in range(0, len(dates_keyboard), 7)]
            keyboard = [
                [InlineKeyboardButton(" Пн. ", callback_data='null'),
                 InlineKeyboardButton(" Вт. ", callback_data='null'),
                 InlineKeyboardButton(" Ср. ", callback_data='null'),
                 InlineKeyboardButton(" Чт. ", callback_data='null'),
                 InlineKeyboardButton(" Пт. ", callback_data='null'),
                 InlineKeyboardButton(" Сб. ", callback_data='null'),
                 InlineKeyboardButton(" Вс. ", callback_data='null'),
                 ]
            ] + dates_keyboard
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text('Пожалуйста, выберите удобную Вам дату:', reply_markup=reply_markup)

        def process_pre_checkout_query(update, context):
            query = update.pre_checkout_query
            # Отправка подтверждения о готовности к выполнению платежа
            context.bot.answer_pre_checkout_query(query.id, ok=True)

        def success_payment(update, context):
            update.message.reply_text(f'Спасибо за оплату!{update.message.successful_payment.invoice_payload} {context.user_data["ap_id"]}')

        def echo(update, context):
            print(update.message.text)
            context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


        def show_services(update, context):
            print('show_services')
            services = Service.objects.all()
            table = PrettyTable()
            table.field_names = ['*', 'Услуга', 'Цена, руб.']
            for service in services:
                table.add_row([service.id, service.name, service.price])
            table.align = 'l'
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'```{table}```', parse_mode=telegram.ParseMode.MARKDOWN)


        start_handler = CommandHandler('start', start)
        buy_handler = CommandHandler('buy', buy)
        calendar_handler = CommandHandler('calendar', calendar)
        pre_checkout_handler = PreCheckoutQueryHandler(process_pre_checkout_query)
        success_payment_handler = MessageHandler(Filters.successful_payment, success_payment)
        echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
        show_services_handler = CommandHandler('services', show_services)

        dispatcher.add_handler(start_handler)
        dispatcher.add_handler(buy_handler)
        dispatcher.add_handler(calendar_handler)
        dispatcher.add_handler(pre_checkout_handler)
        dispatcher.add_handler(success_payment_handler)
        dispatcher.add_handler(echo_handler)
        dispatcher.add_handler(show_services_handler)

        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
    pass
