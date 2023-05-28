from bot.models import Service
from prettytable import PrettyTable


def get_services():
    services = Service.objects.all()
    table = PrettyTable()
    table.field_names = ['Услуга', 'Цена, руб.']
    for service in services:
        table.add_row([service.name, service.price])
    table.align = 'l'
    return table


table = get_services()


FAQ_ANSWERS = {
    'FAQ_working_hours': '''Мы работаем каждый день с 9:00 до 21:00''',
    'FAQ_address': '''м. Дмитровская, ул. Сущевский Вал, д. 5 стр. 18''',
    'FAQ_phone': '''Наш телефон: +7 (495) 150-10-10. Рады звонку в любое время!''',
    'FAQ_portfolio': '''Вы можете посмотреть наши работы по ссылке: https://bit.ly/3j1QZ6V''',
    'FAQ_services': f'```{table}```',
}
