import datetime
import logging

import phonenumbers
import telegram
from django.core.management.base import BaseCommand
from django.db.models import Q
from pytz import timezone
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ParseMode,
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
    Client,
    Slot,
    Appointment,
    Review,
    Salon,
    Specialist,
    Service, Payment,
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
            clients = Client.objects.filter(chat_id=update.effective_chat.id)
            no_review_appointments = Appointment.objects.filter(
                client__in=clients,
                reviews__isnull=True,
            )
            logger.info(f'client with effective chat_id {clients}')
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
                        text="Выберите интересующий Вас вопрос:",
                        reply_markup=InlineKeyboardMarkup(keyboard_new),
                    )
                else:
                    update.message.reply_text(
                        text="Выберите интресующий Вас вопрос:",
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
                    mask = f"{appointment.service.name} {appointment.slot.start_date.strftime('%d.%m')}" \
                           f" в {appointment.slot.start_time.strftime('%H.%M')}," \
                           f" мастер: {appointment.slot.specialist.name}"
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
                        InlineKeyboardButton("1 ⭐️", callback_data="mark_1"),
                        InlineKeyboardButton("2 ⭐️", callback_data="mark_2"),
                        InlineKeyboardButton("3 ⭐️", callback_data="mark_3"),
                        InlineKeyboardButton("4 ⭐️", callback_data="mark_4"),
                        InlineKeyboardButton("5 ⭐️", callback_data="mark_5"),
                    ],
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    text="Пожалуйста, оцените Ваше посещение:",
                    reply_markup=reply_markup,
                    parse_mode="HTML",

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
                    InlineKeyboardButton("Выбрать специалиста", callback_data='get_specialist'),
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
            now = datetime.datetime.now()
            today = now.date()
            current_time = now.time()

            available_specialists = Slot.objects.filter(
                Q(appointment__isnull=True, start_date__gt=today, ) |
                Q(appointment__isnull=True, start_date=today, start_time__gte=current_time)
            ).values_list('specialist', flat=True).distinct()
            services = Service.objects.filter(specialist__in=available_specialists)
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

        def get_date(update, context):
            query = update.callback_query
            if query.data.startswith('service_'):
                context.user_data['type'] = 'by_service'
                service_id = query.data.split('_')[-1]
                services = [Service.objects.get(pk=service_id)]
                specialists = Specialist.objects.filter(services__id=service_id)
                context.user_data['specialists'] = specialists
                context.user_data['service_id'] = service_id
                context.user_data['services'] = services
            if query.data.startswith('specialist_'):
                context.user_data['type'] = 'by_specialist'
                specialist_id = query.data.split('_')[-1]
                specialists = [Specialist.objects.get(pk=specialist_id)]
                logger.info(f'специалист {specialist_id}')
                context.user_data['specialist_id'] = specialist_id
                context.user_data['specialists'] = specialists
                services = specialists[0].services.all()
                context.user_data['services'] = services
            if query.data.startswith('specialist_') or query.data.startswith('service_'):
                now = datetime.datetime.now()
                today = now.date()
                current_time = now.time()
                slots = Slot.objects.filter(
                    Q(appointment__isnull=True, start_date__gt=today, specialist__in=specialists, ) |
                    Q(appointment__isnull=True, start_date=today, start_time__gte=current_time,
                      specialist__in=specialists)
                )
                available_dates = slots.values_list('start_date', flat=True).distinct().order_by('start_date')
                logger.info(f'слоты {slots}')
                min_date = available_dates.first()
                max_date = available_dates.last()
                min_date_weekday = min_date.weekday()
                max_date_weekday = max_date.weekday()
                delta_to_monday = datetime.timedelta(days=min_date_weekday)
                delta_to_sunday = datetime.timedelta(days=6 - max_date_weekday)
                start_date = min_date - delta_to_monday
                end_date = max_date + delta_to_sunday
                dates = []
                while start_date <= end_date:
                    dates.append(start_date)
                    start_date += datetime.timedelta(days=1)
                dates_keyboard = []
                for date in dates:
                    if date in available_dates:
                        date_text = f'{date.strftime("%d.%m")}'
                        dates_keyboard.append(
                            InlineKeyboardButton(date_text, callback_data=f'date_{date.strftime("%Y-%m-%d")}'))
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
                keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    text="Пожалуйста, выберите удобную Вам дату:",
                    reply_markup=reply_markup,
                )

            query.answer()

            return 'GET_DATE'

        def get_time(update, context):
            query = update.callback_query
            if query.data.startswith('date_'):
                date = query.data.split('_')[-1]
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                context.user_data['date'] = date
                logger.info(f'get time - date - {date}')
                now = datetime.datetime.now()
                today = now.date()
                current_time = now.time()
                specialists = context.user_data['specialists']
                slots = Slot.objects.filter(
                    Q(appointment__isnull=True, start_date__gt=today, specialist__in=specialists, ) |
                    Q(appointment__isnull=True, start_date=today, start_time__gte=current_time,
                      specialist__in=specialists)
                )
                times = slots.filter(
                    start_date=date,
                ).values_list('start_time', flat=True).distinct().order_by('start_time')
                times_keyboard = []
                for time in times:
                    times_keyboard.append(InlineKeyboardButton(
                        time.strftime('%H:%M'),
                        callback_data=f'time_{time.strftime("%H:%M")}',
                    ))
                times_keyboard = [times_keyboard[i:i + 5] for i in range(0, len(times_keyboard), 5)]
                return_keyboard = [
                    [InlineKeyboardButton("На главный", callback_data="to_start")],
                    # [InlineKeyboardButton("Выбрать дату", callback_data=f'service_{service_id}')],
                ]
                keyboard = times_keyboard + return_keyboard
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    text="Пожалуйста, выберите удобное Вам время:",
                    reply_markup=reply_markup,
                )

            query.answer()

            return 'GET_TIME'

        def get_specialist_after_time(update, context):
            query = update.callback_query
            if query.data.startswith('time_'):
                time = query.data.split('_')[-1]
                context.user_data['time'] = time
                logger.info(f"get specialist after time - {context.user_data['type']}")
                now = datetime.datetime.now()
                today = now.date()
                current_time = now.time()
                date = context.user_data['date']
                if context.user_data['type'] == 'by_service':
                    service_id = context.user_data['service_id']
                    specialists = Specialist.objects.filter(services__pk=service_id)
                    slots = Slot.objects.filter(
                        Q(appointment__isnull=True, start_date__gt=today, specialist__in=specialists, ) |
                        Q(appointment__isnull=True, start_date=today, start_time__gte=current_time,
                          specialist__in=specialists)
                    )
                    available_specialists = slots.filter(
                        start_date=date,
                        start_time=time,
                    ).values_list('specialist', flat=True).distinct()
                    keyboard = []
                    logger.info(f'specialists - {available_specialists}')
                    for specialist in available_specialists:
                        logger.info(f'specialist - {specialist}')
                        logger.info(f'specialists - {specialists}')
                        specialist = specialists.get(pk=specialist)
                        logger.info(specialist.name)
                        keyboard.append([InlineKeyboardButton(f'{specialist.name} {specialist.surname}',
                                                              callback_data=f'specialist_after_{specialist.id}')])
                    # keyboard.append([InlineKeyboardButton("Любой", callback_data="specialist_after_any")])
                    keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    query.edit_message_text(
                        text="Пожалуйста, выберите специалиста:",
                        reply_markup=reply_markup,
                    )
                if context.user_data['type'] == 'by_specialist':
                    services = context.user_data['services']
                    keyboard = []
                    logger.info(f'specialists - services - {services}')
                    for service in services:
                        keyboard.append([InlineKeyboardButton(f'{service.name} ({service.price} руб.)',
                                                              callback_data=f'service_after_{service.id}')])

                    keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])

                    reply_markup = InlineKeyboardMarkup(keyboard)
                    query.edit_message_text(
                        text="Пожалуйста, выберите услугу:",
                        reply_markup=reply_markup,
                    )

            query.answer()

            return 'GET_CLIENT_PHONE'

        def get_client_phone(update, context):
            query = update.callback_query

            logger.info(f'get client phone - query - {update}')
            if query.data.startswith('specialist_after_'):
                specialist_id = query.data.split('_')[-1]
                context.user_data['specialist_id'] = specialist_id
                specialist = Specialist.objects.get(pk=specialist_id)
                context.user_data['specialist'] = specialist
                context.user_data['service'] = context.user_data['services'][0]
            if query.data.startswith('service_after_'):
                logger.info(f'get client phone - in service_after_')
                service_id = query.data.split('_')[-1]
                context.user_data['service_id'] = service_id
                service = context.user_data['services'].get(pk=service_id)
                context.user_data['service'] = service
                context.user_data['specialist'] = context.user_data['specialists'][0]
            if query.data.startswith('specialist_after_') or query.data.startswith('service_after_'):
                date = context.user_data['date']
                time = context.user_data['time']
                service = context.user_data['service']
                specialist = context.user_data['specialist']
                slot = Slot.objects.filter(appointment__isnull=True, start_date=date, start_time=time,
                                           specialist=specialist).first()
                if slot:
                    context.user_data['slot'] = slot
                    context.user_data['slot_id'] = slot.id
                    logger.info(f'get client phone - specialist_id - {specialist}')
                    text = f'Вы хотите записаться на услугу *{service.name}*' \
                           f' на *{date.strftime("%d.%m.%Y")}* в *{time}* к мастеру *{specialist.name} {specialist.surname}.*\n\n' \
                           f'Продолжая, Вы даете свое [согласие на обработку персональных данных]' \
                           f'(https://docs.google.com/document/' \
                           f'd/1U-ZZa9bosHbqEbVwvgubUdR6T9gC33igDmEUMYVREQw/edit?usp=sharing).\n\n' \
                           f'📞 Пожалуйста, введите Ваш номер телефона *в ответном сообщении*.'
                    keyboard = [
                        [
                            InlineKeyboardButton("Позвонить", callback_data="show_phone"),
                            InlineKeyboardButton("На главный", callback_data="to_start")
                        ],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    query.edit_message_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )
                else:
                    query.edit_message_text(
                        text="Извините, время уже занято. Пожалуйста, выберите другое время",
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("Выбрать время", callback_data=f'date_{date}')]])
                    )
                    return 'GET_TIME'

            query.answer()

            return 'GET_CLIENT_NAME'

        def get_client_name(update, context):
            phonenumber = update.message.text
            try:
                phonenumber = phonenumbers.parse(phonenumber, 'RU')
            except phonenumbers.phonenumberutil.NumberParseException:
                is_valid_phonenumber = False
            else:
                is_valid_phonenumber = phonenumbers.is_valid_number(phonenumber)

            if is_valid_phonenumber:
                pure_phonenumber = phonenumbers.format_number(phonenumber, phonenumbers.PhoneNumberFormat.E164)
                context.user_data['phone'] = pure_phonenumber
                keyboard = [
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(
                    text='✅ Введите Ваше имя в ответном сообщении:',
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
                return 'CREATE_APPOINTMENT_RECORD'
            else:
                logger.info({update.message.contact})
                keyboard = [
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text='❌ Пожалуйста, введите корректный номер телефона:',
                                         reply_markup=reply_markup,
                                         )

                return 'GET_CLIENT_NAME'


        def create_appointment_record(update, context):
            logger.info(f'start to create appointment record - {context.user_data}')
            chat_id = update.message.chat_id
            name = update.message.text
            service = context.user_data['service']
            slot = context.user_data['slot']
            specialist = context.user_data['specialist']
            date = context.user_data['date']
            time = context.user_data['time']

            try:
                client, created = Client.objects.get_or_create(
                    chat_id=chat_id,
                    name=name,
                    phonenumber=context.user_data['phone'],
                )
                logger.info(f'trying to create appointment - client - {client} {created}')
                context.user_data['client'] = client
                appointment = Appointment.objects.create(
                    client=client,
                    slot=slot,
                    service=service,
                )
                context.user_data['appointment'] = appointment
            except:
                update.message.reply_text(
                    text='Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.',
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END

            logger.info(f'get client name - {name}')
            text = f'Вы записаны на услугу <b>{service.name}</b> на <b>{date.strftime("%d.%m.%Y")}</b> в <b>{time}</b> ' \
                   f'к мастеру <b>{specialist.name} {specialist.surname}.</b>\n\n' \
                   f'Наш салон находится по адресу: <b>{FAQ_ANSWERS["FAQ_address"]}</b>.\n\n' \
                   f'Стоимость услуги составляет <b>{service.price} руб</b>. ' \
                   f'Вы можете оплатить сейчас или наличными в салоне.\n\n' \
                   f'Номер Вашей записи <b>{appointment.pk}</b>. Спасибо за запись!'

            keyboard = [
                [
                    InlineKeyboardButton("Оплатить", callback_data="to_buy"),
                    InlineKeyboardButton("Промокод", callback_data="get_promocode"),
                    InlineKeyboardButton("На главный", callback_data="to_start"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                text=text, reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )

            return 'CREATE_APPOINTMENT_RECORD'

        def buy(update, context):
            query = update.callback_query
            if query.data == 'to_buy':
                service = context.user_data['service']
                specialist = context.user_data['specialist']
                date = context.user_data['date']
                time = context.user_data['time']
                prices = [LabeledPrice(label=f'{service.name}', amount=service.price * 100)]
                description = f'Оплата за услугу {service.name} (мастер: {specialist.name} {specialist.surname},' \
                              f' время: {date.strftime("%d.%m.%Y")} {time})'
                context.bot.send_invoice(
                    chat_id=update.effective_chat.id,
                    title='Оплата услуг салона красоты',
                    payload=context.user_data['appointment'].pk,
                    description=description,
                    provider_token=settings.yoo_kassa_provider_token,
                    currency='RUB',
                    prices=prices,
                )
            query.answer()

            return ConversationHandler.END

        def process_pre_checkout_query(update, context):
            query = update.pre_checkout_query
            try:
                appointment = Appointment.objects.filter(pk=query.invoice_payload, payment__isnull=True).first()
            except:
                context.bot.answer_pre_checkout_query(
                    pre_checkout_query_id=query.id,
                    ok=False,
                    error_message="Что-то пошло не так...",
                )
                return
            # Отправка подтверждения о готовности к выполнению платежа
            context.bot.answer_pre_checkout_query(query.id, ok=True)


        def success_payment(update, context):
            '''Обработка успешной оплаты'''
            try:
                Payment.objects.create(
                    client = context.user_data['client'],
                    appointment=context.user_data['appointment'],
                    amount=update.message.successful_payment.total_amount / 100,
                )
            except:
                logger.error(f'Ошибка при записи информации о платеже в бд'
                             f' {update.message.successful_payment.invoice_payload}')
            finally:
                text = f'✅ Спасибо за оплату {update.message.successful_payment.total_amount}/100 руб.!\n\n'
                keyboard = [
                    [
                        InlineKeyboardButton("На главный", callback_data="to_start"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )

            return 'SUCCESS_PAYMENT'

        def get_promocode(update, context):
            query = update.callback_query
            if query.data == 'to_apply_promocode':
                pass

            return 'PROMOCODE'

        def get_specialist(update, _):
            '''Выбор специалиста'''
            query = update.callback_query
            if query.data == 'get_specialist':
                now = datetime.datetime.now()
                today = now.date()
                current_time = now.time()

                available_specialists = Slot.objects.filter(
                    Q(appointment__isnull=True, start_date__gt=today, ) |
                    Q(appointment__isnull=True, start_date=today, start_time__gte=current_time)
                ).values_list('specialist', flat=True).distinct()
                specialists = Specialist.objects.filter(pk__in=available_specialists)
                keyboard = []
                for specialist in specialists:
                    full_name = f'{specialist.name} {specialist.surname}'
                    keyboard.append([InlineKeyboardButton(full_name,
                                                          callback_data=f'specialist_{specialist.pk}')])

                keyboard.append([InlineKeyboardButton("На главный", callback_data="to_start")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.answer()

            query.edit_message_text(
                text=f'Пожалуйста, выберите нужного Вам специалиста:',
                reply_markup=reply_markup,
                parse_mode=telegram.ParseMode.MARKDOWN,
            )

            return 'SPECIALISTS'

        def cancel(update, _):
            user = update.message.from_user
            logger.info("Пользователь %s отменил разговор.", user.first_name)
            update.message.reply_text(
                'До новых встреч',
                reply_markup=ReplyKeyboardRemove(),
            )
            return ConversationHandler.END

        pre_checkout_handler = PreCheckoutQueryHandler(process_pre_checkout_query)
        success_payment_handler = MessageHandler(Filters.successful_payment, success_payment)
        dispatcher.add_handler(pre_checkout_handler)
        dispatcher.add_handler(success_payment_handler)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_conversation),
                          CallbackQueryHandler(start_conversation, pattern='to_start'),
                          ],
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
                    CallbackQueryHandler(get_specialist, pattern='get_specialist'),
                ],
                'SERVICES': [
                    CallbackQueryHandler(get_date, pattern='(service_.*)'),
                    CallbackQueryHandler(get_service, pattern='get_service'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_DATE': [
                    CallbackQueryHandler(get_time, pattern='(date_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_TIME': [
                    CallbackQueryHandler(get_date, pattern='(service_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(get_specialist_after_time, pattern='(time_.*)'),
                ],
                'GET_SPECIALIST_OR_SERVICE_AFTER_TIME': [
                    CallbackQueryHandler(get_client_phone, pattern='(specialist_after_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_CLIENT_PHONE': [
                    CallbackQueryHandler(get_client_phone, pattern='(service_after_.*)'),
                    CallbackQueryHandler(get_client_phone, pattern='(specialist_after_.*)'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                ],
                'GET_CLIENT_NAME': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    MessageHandler(Filters.text, get_client_name),
                ],
                'CREATE_APPOINTMENT_RECORD': [
                    CallbackQueryHandler(buy, pattern='to_buy'),
                    CallbackQueryHandler(buy, pattern='to_apply_promocode'),
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    MessageHandler(Filters.text, create_appointment_record),
                    # PreCheckoutQueryHandler(process_pre_checkout_query),
                    # CallbackQueryHandler(success_payment, pattern='success_payment'),
                ],
                'SPECIALISTS': [
                    CallbackQueryHandler(start_conversation, pattern='to_start'),
                    CallbackQueryHandler(get_date, pattern='(specialist_.*)'),
                ],
                'PROCESS_PRE_CHECKOUT': [
                    PreCheckoutQueryHandler(process_pre_checkout_query),
                    CallbackQueryHandler(success_payment, pattern='success_payment'),
                ],
                'SUCCESS_PAYMENT': [
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
