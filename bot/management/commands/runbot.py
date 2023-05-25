import datetime
import logging

import telegram
from django.core.management.base import BaseCommand
from django.db.models import Q
from pytz import timezone
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove, ParseMode,
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
    Slot,
    Appointment,
    Review,
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

        def start_conversation(update, context):
            query = update.callback_query
            client = Client.objects.filter(chat_id=update.effective_chat.id).first()
            no_review_appointments = Appointment.objects.filter(
                client=client,
                reviews__isnull=True,
                payment__isnull=False,
            )
            logger.info(f'client with effective chat_id {client}')
            logger.info(f'no_review_appointments {no_review_appointments}')
            if query:
                query.answer()

            keyboard_new = [
                [
                    InlineKeyboardButton("О нас", callback_data='to_FAQ'),
                    InlineKeyboardButton("Записаться", callback_data="to_order"),
                ],
            ]
            keyboard_old = [
                    [
                        InlineKeyboardButton("О нас", callback_data='to_FAQ'),
                        InlineKeyboardButton("Отставить отзыв", callback_data="to_review")
                    ],
                    [
                        InlineKeyboardButton("Записаться", callback_data="to_order")
                    ],
            ]

            if no_review_appointments.exists():
                logger.info(f'There are appointments without reviews: {no_review_appointments}')
                context.user_data['no_review_appointments'] = no_review_appointments
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
                logger.info('client is None')
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


        def faq(update, _):
            query = update.callback_query

            keyboard = [
                [
                    InlineKeyboardButton("Услуги", callback_data='FAQ_services'),
                    InlineKeyboardButton("Режим работы", callback_data='FAQ_working_hours'),
                ],
                [
                    InlineKeyboardButton("Адрес", callback_data='FAQ_address'),
                    InlineKeyboardButton("Телефон", callback_data="FAQ_phone"),
                ],
                [
                    InlineKeyboardButton("Портфолио", callback_data='FAQ_portfolio'),
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            if query.data == 'to_FAQ':
                query.edit_message_text(
                    text="Выберите интересующий вопрос:",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            else:
                query.edit_message_text(
                    text=FAQ_ANSWERS[query.data],
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            return 'SHOW_INFO'


        def review(update, context):
            query = update.callback_query
            no_review_appointments = context.user_data['no_review_appointments']
            if query.data == 'to_review':
                keyboard = []
                for appointment in no_review_appointments:
                    logger.info(f'appointment {appointment}')
                    mask = f"{appointment.service.name} {appointment.slot.start_date.strftime('%d.%m')} {appointment.slot.start_time.strftime('%H.%M')}, мастер: {appointment.slot.specialist.name}"
                    keyboard.append([InlineKeyboardButton(mask, callback_data=f'review_{appointment.id}')])
                keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                text = f'Пожалуйста, выберите посещение, для которого хотите оставить отзыв:'
                query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                )
            query.answer()
            return 'REVIEW'

        def get_mark(update, context):
            query = update.callback_query
            if query.data.startswith('review_'):
                appointment_id = query.data.split('_')[-1]
                logger.info(f'pk записи {appointment_id}')
                context.user_data['appointment_id'] = appointment_id
                keyboard = [
                    [
                        InlineKeyboardButton("'1'", callback_data="mark_1"),
                        InlineKeyboardButton("'2'", callback_data="mark_2"),
                        InlineKeyboardButton("'3'", callback_data="mark_3"),
                        InlineKeyboardButton("'4'", callback_data="mark_4"),
                        InlineKeyboardButton("'5'", callback_data="mark_5"),
                    ],
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                    ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    text="Пожалуйста, оцените Ваше посещение:",
                    reply_markup=reply_markup,
                )
            if query.data.startswith('mark_'):
                mark = query.data.split('_')[-1]
                context.user_data['mark'] = mark
                context.user_data['appointment_id'] = context.user_data['appointment_id']
                keyboard = [
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    text="В ответном сообщении пришлите, пожалуйста, текст Вашего отзыва:",
                    reply_markup=reply_markup,
                )

                return 'GET_REVIEW_TEXT'

            query.answer()

            return 'REVIEW_MARK'

        def get_review_text(update, context):
            review_text = update.message.text
            appointment_id = context.user_data['appointment_id']
            mark = context.user_data['mark']
            logger.info(f'записть - {appointment_id}, оценка - {mark}')
            appointment = Appointment.objects.get(pk=appointment_id)
            Review.objects.get_or_create(appointment=appointment, defaults={
                'mark': int(mark),
                'text': review_text,
            },
                                         )
            keyboard = [
                [
                    InlineKeyboardButton("Записаться", callback_data="to_order"),
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                text='✅ Спасибо! Ваш отзыв записан! Нам очень важно Ваше мнение!',
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )

            return 'MAIN_MENU'


        def order(update, _):
            '''Функция создает ордер на услугу'''
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("Выбрать услугу", callback_data='FAQ_services'),
                    InlineKeyboardButton("Выбрать специалиста", callback_data='FAQ_working_hours'),
                ],
                [
                    InlineKeyboardButton("Адрес", callback_data='FAQ_address'),
                    InlineKeyboardButton("Телефон", callback_data="FAQ_phone"),
                ],
                [
                    InlineKeyboardButton("Портфолио", callback_data='FAQ_portfolio'),
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            if query.data == 'to_order':
                query.edit_message_text(
                    #TODO сделать запрос, чтобы адресс тянулся из бд
                    text="BeautyCity м. Давыдково, ул. Инициативная, д. 9",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            else:
                query.edit_message_text(
                    text=FAQ_ANSWERS[query.data],
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            return 'SHOW_INFO'


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
                    CallbackQueryHandler(faq, pattern='to_FAQ'),
                    CallbackQueryHandler(order, pattern='to_order'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(review, pattern='to_review'),
                    # CallbackQueryHandler(get_expired, pattern='to_expired'),
                ],
                'SHOW_INFO': [
                    CallbackQueryHandler(faq, pattern='(FAQ_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'REVIEW': [
                    CallbackQueryHandler(get_mark, pattern='(review_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(get_mark, pattern='(mark_.*)'),
                ],
                'REVIEW_MARK': [
                    CallbackQueryHandler(get_mark, pattern='(mark_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_REVIEW_TEXT': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    MessageHandler(Filters.text, get_review_text),
                ]
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
