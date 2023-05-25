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
    Salon,
    Specialist,
    Service,
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
            return 'ABOUT'


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


        def make_appointment(update, _):
            '''Функция создает ордер на услугу'''
            query = update.callback_query
            keyboard = [
                [
                    InlineKeyboardButton("Выбрать услугу", callback_data='get_service'),
                    InlineKeyboardButton("Выбрать специалиста", callback_data='сhoose_specialist'),
                ],
                [
                    InlineKeyboardButton("Позвонить", callback_data="show_phone"),
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if query.data == 'to_order':
                query.edit_message_text(
                    text="Пожалуйста, выберите, что Вас интересует:",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )

            if query.data == 'show_phone':
                query.edit_message_text(
                    text=f"{FAQ_ANSWERS['FAQ_phone']}",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )

            query.answer()

            return 'MAKE_APPOINTMENT'

        def get_service(update, _):

            '''Функция отвечает за вывод списка услуг для выбора пользователя>'''

            query = update.callback_query
            logger.info(f'get service query data {query.data}')
            services = Service.objects.all()
            keyboard = []
            for service in services:
                mask = f"{service.name} ({service.price} руб.)"
                keyboard.append([InlineKeyboardButton(mask, callback_data=f'service_{service.id}')])

            reply_markup = InlineKeyboardMarkup(keyboard)
            keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])
            if query.data == 'get_service':
                query.edit_message_text(
                    text="Пожалуйста, выберите, что Вас интересует:",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )

            query.answer()

            return 'SERVICES'

        def сhoose_specialist(update, _):
            '''Выбор специалиста'''
            query = update.callback_query
            specialists = Specialist.objects.all()
            keyboard = []
            for  specialist in specialists:
                full_name = f'{specialist.name} {specialist.surname}'
                keyboard.append([InlineKeyboardButton(full_name,
                                callback_data=specialist.id)])
            
            buttons =[
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
                ]
            ]
            for button in buttons:
                keyboard.append(button)

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()
            
            if query.data == 'сhoose_service':
                query.edit_message_text(
                    text = 'Специалист',# {specialist.name} {specialist.surname}",
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            else:
                query.edit_message_text(
                    text= 'Специалист',#FAQ_ANSWERS[query.data],
                    reply_markup=reply_markup,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                )
            return 'SHOW_INFO'


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
                    CallbackQueryHandler(make_appointment, pattern='to_order'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(review, pattern='to_review'),
                ],
                'ABOUT': [
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
                ],
                'MAKE_APPOINTMENT': [
                    CallbackQueryHandler(make_appointment, pattern='to_order'),
                    CallbackQueryHandler(get_service, pattern='get_service'),
                    CallbackQueryHandler(make_appointment, pattern='show_phone'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'SERVICES': [
                    CallbackQueryHandler(get_service, pattern='get_service'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        dispatcher.add_handler(conv_handler)
        start_handler = CommandHandler('start', start_conversation)
        dispatcher.add_handler(start_handler)

        updater.start_polling()
        updater.idle()
