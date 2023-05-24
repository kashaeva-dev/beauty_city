import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q
from pytz import timezone
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Updater,
    Filters,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
)

from conf import settings

from bot.models import (
    Client,
    Slot
)
from bot.text_templates import (
    FAQ_ANSWERS,
)

# Ведение журнала логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Команда для запуска телеграм-бота
    """

    def handle(self, *args, **kwargs):
        updater = Updater(token=settings.tg_token, use_context=True)
        dispatcher = updater.dispatcher

        def start_conversation(update, _):
            query = update.callback_query
            client = Client.objects.filter(chat_id=update.effective_chat.id).first()
            print('chat_id', client)
            if query:
                query.answer()

            keyboard_new = [
                [
                    InlineKeyboardButton("О нас", callback_data='about'),
                    InlineKeyboardButton("Записаться", callback_data="to_order"),
                ],
            ]
            keyboard_old = [
                    [
                        InlineKeyboardButton("О нас", callback_data='about'),
                        InlineKeyboardButton("Отставить отзыв", callback_data="to_review")
                    ],
                    [
                        InlineKeyboardButton("Записаться", callback_data="to_order")
                    ],
            ]

            if client:
                if query:
                    query.edit_message_text(
                        text="Выберите интересующий вопрос:",
                        reply_markup=InlineKeyboardMarkup(keyboard_old),
                    )
                else:
                    update.message.reply_text(
                        text="Выберите интресующий вас вопрос:",
                        reply_markup=InlineKeyboardMarkup(keyboard_old),
                    )
            else:
                if query:
                    query.edit_message_text(
                        text="Выберите интересующий вопрос:",
                        reply_markup=InlineKeyboardMarkup(keyboard_new),
                    )
                else:
                    update.message.reply_text(
                        text="Выберите интресующий вас вопрос:",
                        reply_markup=InlineKeyboardMarkup(keyboard_new),
                    )

            return 'MAIN_MENU'

        # def get_delivery(update, _):
        #     query = update.callback_query
        #     deliveries = Delivery.objects.filter(
        #         Q(type__pk=1, took_at__isnull=True) |
        #         Q(type__pk=2, delivered_at__isnull=True),
        #     )
        #     client_contacts = []
        #     if query.data == 'to_delivery':
        #         for delivery in deliveries:
        #             client_contact = get_client_contact_for_delivery(delivery)
        #             client_contacts.append(client_contact)
        #         client_contacts = "\n".join(client_contacts)
        #         if not client_contacts:
        #             client_contacts = "Сейчас не требуются доставки!"
        #         keyboard = [
        #             [
        #                 InlineKeyboardButton("На главный", callback_data="to_start"),
        #             ],
        #         ]
        #         reply_markup = InlineKeyboardMarkup(keyboard)
        #         query.edit_message_text(
        #             text=client_contacts,
        #             reply_markup=reply_markup,
        #         )
        #
        #     query.answer()
        #     return 'DELIVERY'
        #
        # def get_expired(update, _):
        #     query = update.callback_query
        #     today = datetime.datetime.now(timezone('UTC')).date()
        #     orders = Order.objects.filter(end_storage_date__isnull=True, paid_up_to__lt=today)
        #     client_contacts = []
        #     for order in orders:
        #         client_contact = get_client_contact_for_expired(today, order)
        #         client_contacts.append(client_contact)
        #     client_contacts = "\n".join(client_contacts)
        #     if not client_contacts:
        #         client_contacts = "Сейчас нет просроченных заказов!"
        #     if query.data == 'to_expired':
        #         keyboard = [
        #             [
        #                 InlineKeyboardButton("На главный", callback_data="to_start"),
        #             ],
        #         ]
        #         reply_markup = InlineKeyboardMarkup(keyboard)
        #         query.edit_message_text(
        #             text=client_contacts,
        #             reply_markup=reply_markup,
        #         )
        #
        #     query.answer()
        #     return 'EXPIRED'
        #
        # def show_ad(update, _):
        #     query = update.callback_query
        #
        #     keyboard = [
        #         [
        #             InlineKeyboardButton("Добавить", callback_data="add_new_campaign"),
        #             InlineKeyboardButton("Статистика", callback_data="to_stat"),
        #         ],
        #         [
        #             InlineKeyboardButton("На главный", callback_data="to_start"),
        #         ],
        #     ]
        #     reply_markup = InlineKeyboardMarkup(keyboard)
        #     query.edit_message_text(
        #         text="Выберите, что Вы хотите сделать",
        #         reply_markup=reply_markup,
        #     )
        #     query.answer()
        #     return 'SHOW_AD'
        #
        # def show_stat(update, _):
        #     query = update.callback_query
        #     print(query.data)
        #     campaigns = Advertisement.objects.all()
        #     campaigns_keyboard = []
        #     for campaign in campaigns:
        #         callback_data = f"stat_{campaign.pk}"
        #         campaigns_keyboard.append([InlineKeyboardButton(campaign.name, callback_data=callback_data)])
        #
        #     to_start_keyboard = [
        #         [
        #             InlineKeyboardButton("На главный", callback_data="to_start"),
        #         ],
        #     ]
        #     to_stat_keyboard = [
        #         [
        #             InlineKeyboardButton("Кампании", callback_data="to_stat"),
        #             InlineKeyboardButton("На главный", callback_data="to_start"),
        #         ],
        #     ]
        #     campaigns_markup = InlineKeyboardMarkup(campaigns_keyboard + to_start_keyboard)
        #     stat_markup = InlineKeyboardMarkup(to_stat_keyboard)
        #     query.answer()
        #
        #     if query.data == 'to_stat':
        #         query.edit_message_text(
        #             text="Выберите компанию, по которой хотите узнать статистику:",
        #             reply_markup=campaigns_markup,
        #         )
        #
        #     if query.data.startswith('stat_'):
        #         ad_pk = int(query.data.split('_')[1])
        #         url = Advertisement.objects.get(pk=ad_pk).url
        #         text = get_clicks(url, bitly_token)
        #         query.edit_message_text(
        #             text=text,
        #             reply_markup=stat_markup,
        #         )
        #
        #     return 'SHOW_STAT'
        #
        # def add_new_campaign(update, _):
        #     query = update.callback_query
        #     query.answer()
        #     keyboard = [
        #         [
        #             InlineKeyboardButton("На главный", callback_data="to_start"),
        #         ],
        #     ]
        #     reply_markup = InlineKeyboardMarkup(keyboard)
        #     query.edit_message_text(
        #         text="В ответном сообщении введите ссылку, по которой будете просматривать статистику кампании",
        #         reply_markup=reply_markup,
        #     )
        #     return 'GET_URL'
        #
        # def get_url(update, context):
        #     url = update.message.text
        #     ad, created = Advertisement.objects.get_or_create(
        #         url=url,
        #     )
        #     if not created:
        #         callback_data = f'stat_{ad.pk}'
        #         keyword = [
        #             [
        #                 InlineKeyboardButton("Посмотреть", callback_data=callback_data),
        #                 InlineKeyboardButton("Изменить ссылку", callback_data="add_new_campaign"),
        #                 InlineKeyboardButton("На главный", callback_data="to_start"),
        #             ],
        #         ]
        #         reply_markup = InlineKeyboardMarkup(keyword)
        #         context.bot.send_message(chat_id=update.effective_chat.id,
        #                                  text="Такая ссылка уже есть в списке кампаний", reply_markup=reply_markup)
        #
        #         return 'CHECK_URL'
        #     else:
        #         context.user_data['ad_pk'] = ad.pk
        #         keyboard = [
        #             [
        #                 InlineKeyboardButton("Назад", callback_data="to_start"),
        #             ],
        #         ]
        #         reply_markup = InlineKeyboardMarkup(keyboard)
        #         text = 'Вы ввели ссылку: ' + update.message.text + '\nВведите название кампании:'
        #         context.bot.send_message(chat_id=update.effective_chat.id,
        #                                  text=text, reply_markup=reply_markup)
        #
        #         return 'GET_NAME'
        #
        # def get_name(update, context):
        #     name = update.message.text
        #     ad_pk = context.user_data.get('ad_pk')
        #     print(ad_pk)
        #     ad = Advertisement.objects.get(pk=ad_pk)
        #     ad.name = name
        #     ad.save()
        #     keyboard = [
        #         [
        #             InlineKeyboardButton("На главный", callback_data="to_start"),
        #         ],
        #     ]
        #     reply_markup = InlineKeyboardMarkup(keyboard)
        #     text = 'Вы ввели: ' + update.message.text + '\nНовая кампания успешно добавлена в базу данных'
        #     context.bot.send_message(chat_id=update.effective_chat.id,
        #                              text=text, reply_markup=reply_markup)
        #     return 'MAIN_MENU'

        def cancel(update, _):
            user = update.message.from_user
            logger.info("Пользователь %s отменил разговор.", user.first_name)
            update.message.reply_text(
                'До новых встреч',
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_conversation)],
            states={
                'MAIN_MENU': [
                    # CallbackQueryHandler(show_ad, pattern='to_ad'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    # CallbackQueryHandler(get_delivery, pattern='to_delivery'),
                    # CallbackQueryHandler(get_expired, pattern='to_expired'),
                ],
                # 'SHOW_AD': [
                #     CallbackQueryHandler(show_stat, pattern='to_stat'),
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                #     CallbackQueryHandler(add_new_campaign, pattern='add_new_campaign'),
                # ],
                # 'CHECK_URL': [
                #     CallbackQueryHandler(show_stat, pattern='(stat_.*)'),
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                #     CallbackQueryHandler(add_new_campaign, pattern='add_new_campaign'),
                # ],
                # 'DELIVERY': [
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                # ],
                # 'EXPIRED': [
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                # ],
                # 'SHOW_STAT': [
                #     CallbackQueryHandler(show_stat, pattern='(stat_.*|to_stat)'),
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                # ],
                # 'GET_NAME': [
                #     MessageHandler(Filters.text, get_name),
                # ],
                # 'GET_URL': [
                #     MessageHandler(Filters.text, get_url),
                #     CallbackQueryHandler(start_conversation, pattern='to_start'),
                # ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        dispatcher.add_handler(conv_handler)
        start_handler = CommandHandler('start', start_conversation)
        dispatcher.add_handler(start_handler)

        updater.start_polling()
        updater.idle()
