import sys
from vkbottle import Keyboard, Text, KeyboardButtonColor, EMPTY_KEYBOARD
from vkbottle.bot import Bot, Message

from loguru import logger

from config import group_token, access_token
from hunter import Hunter
from logic import check_search_age, check_city_id, check_city_title,\
                    get_user_from_stream, get_user_from_fav, get_user_photo, get_help_text
import db

# logger.disable('vkbottle')
logger.remove()
logger.add(sys.stderr, level='ERROR')

bot = Bot(token=group_token)
bot_user = Bot(token=access_token)
bot.labeler.vbml_ignore_case = True


# начало работы пользователя
@bot.on.private_message(text='/start')
async def start_bot(message: Message):
    # создадим словарь всех hunters
    await db.get_all_hunter_from_db()

    keyboard = Keyboard()
    user = await bot.api.users.get([message.from_id], Hunter.fields)
    user = user[0]
    print(f'В бот зашел новый hunter: {user.id} {user.first_name} {user.last_name}')
    mes1 = ''

    # проверяем есть ли user, запустивший бота в БД
    if user.id not in Hunter.all_hunters.keys():
        hunter = Hunter(user.id, first_name=user.first_name, last_name=user.last_name)
        Hunter.all_hunters[user.id] = hunter
        await db.add_db_hunter(hunter)
        mes1 = '\nЭто бот для поиска людей в ВК.\nТак как вы первый раз используете бота, загляните в раздел ' \
               '"Помощь".\nУстановите свои параметры поиска.'
    else:
        hunter = Hunter.all_hunters[user.id]
    hunter.fav_list = await db.get_fav_list(hunter.id)
    hunter.black_list = await db.get_black_list(hunter.id)

    mes = f'Добро пожаловать, {hunter.first_name} {hunter.last_name}!' + mes1
    txt_btn = f'Вперед, {hunter.first_name} !'
    keyboard.add(Text(txt_btn, {'cmd': 'main_menu'}), color=KeyboardButtonColor.POSITIVE)
    await message.answer(mes, keyboard=keyboard)


# главное меню
@bot.on.private_message(payload={'cmd': 'main_menu'})
async def main_menu(message: Message):
    hunter = Hunter.all_hunters[message.from_id]
    color_fav = KeyboardButtonColor.PRIMARY if hunter.fav_list else KeyboardButtonColor.SECONDARY
    color_show_next = KeyboardButtonColor.PRIMARY if hunter.users_dic else KeyboardButtonColor.SECONDARY
    button_tittle_show_users = f'Анкеты: {len(hunter.users_dic)}'
    button_tittle_show_fav = f'Избранное: {len(hunter.fav_list)}'
    keyboard = Keyboard()
    keyboard.add(Text(button_tittle_show_fav, {'cmd': 'show_fav'}), color=color_fav)
    keyboard.add(Text(button_tittle_show_users, {'cmd': 'show_users'}), color=color_show_next)
    keyboard.row()
    keyboard.add(Text('Новый поиск', {'cmd': 'new_search'}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text('Помощь', {'cmd': 'help'}))
    keyboard.add(Text('Настройки', {'cmd': 'settings'}))
    await message.answer('Используйте меню', keyboard=keyboard)


# новый поиск
@bot.on.private_message(payload={'cmd': 'new_search'})
async def new_search(message: Message):
    hunter = Hunter.all_hunters[message.from_id]
    keyboard = Keyboard()

    mes = f"""Начинаем поиск по параметрам:
    Город поиска - {hunter.search_city_title} (id - {hunter.search_city_id})
    Пол - {hunter.search_sex} (0-любой; 1-женщина; 2-мужчина)
    Возраст от {hunter.search_age_from} до {hunter.search_age_to}
    Интересы: {hunter.search_interests}
    Статус: {hunter.search_status}
    ------------------------------------"""
    await message.answer(mes)
    try:
        res = await bot_user.api.users.search(count=hunter.count_find_users, offset=hunter.offset,
                                              city=hunter.search_city_id, sex=hunter.search_sex,
                                              age_from=hunter.search_age_from, has_photo=True,
                                              age_to=hunter.search_age_to, status=hunter.search_status,
                                              fields=Hunter.fields)
        hunter.get_users_dic(res)
        if len(hunter.users_dic) > 0:
            mes = f'Поиск удачно завершён.\nТеперь доступно анкет: {len(hunter.users_dic)}'
            color_main_menu = KeyboardButtonColor.POSITIVE
            hunter.offset += hunter.count_find_users
        else:
            mes = 'Поиск завершён. По вашим параметрам анкет не найдено'
            color_main_menu = KeyboardButtonColor.SECONDARY
    except Exception as er:
        print(er)
        mes = 'Что-то пошло не так. Поиск не удался'
        color_main_menu = KeyboardButtonColor.NEGATIVE
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}), color=color_main_menu)
    await message.answer(mes, keyboard=keyboard)


# меню показа анкет текущее
@bot.on.private_message(payload={'cmd': 'show_users'})
async def menu_show_users(message: Message):
    hunter = Hunter.all_hunters[message.from_id]
    color_show_next = KeyboardButtonColor.PRIMARY if hunter.users_dic else KeyboardButtonColor.SECONDARY
    keyboard = Keyboard()
    keyboard.add(Text('Добавить в избранное', {'cmd': 'add_to_fav'}))
    keyboard.add(Text('Следующая', {'cmd': 'next_user', 'show_fav': 0}), color=color_show_next)
    keyboard.row()
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}))
    await message.answer('Используйте меню', keyboard=keyboard)


# меню показа избранное
@bot.on.private_message(payload={'cmd': 'show_fav'})
async def menu_show_fav(message: Message):
    hunter = Hunter.all_hunters[message.from_id]
    color_show_next = KeyboardButtonColor.PRIMARY if hunter.fav_list else KeyboardButtonColor.SECONDARY
    keyboard = Keyboard()
    keyboard.add(Text('Удалить из избранного', {'cmd': 'del_to_fav'}))
    keyboard.add(Text('Далее в избранном', {'cmd': 'next_user', 'show_fav': 1}), color=color_show_next)
    keyboard.row()
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}))
    await message.answer('Используйте меню', keyboard=keyboard)


# меню настройки
@bot.on.private_message(payload={'cmd': 'settings'})
async def show_settings(message: Message):
    hunter = Hunter.all_hunters[message.from_id]
    keyboard = Keyboard()
    keyboard.add(Text('Очистить папки', {'cmd': 'clear'}))
    keyboard.add(Text('Изменить настройки', {'cmd': 'change_search'}))
    keyboard.row()
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}))
    mes = f"""Настройки поиска для {hunter.first_name} {hunter.last_name}:
    Город поиска - {hunter.search_city_title} (id - {hunter.search_city_id})
    Пол - {hunter.search_sex} - {['любой', 'женщина', 'мужчина'][hunter.search_sex]}
    Возраст от {hunter.search_age_from} до {hunter.search_age_to}
    Интересы: {hunter.search_interests}
    Статус анкеты: {hunter.search_status} 
    offset: {hunter.offset}
    count: {hunter.count_find_users}"""
    await message.answer(mes, keyboard=keyboard)


# меню очистки
@bot.on.private_message(payload={'cmd': 'clear'})
async def menu_clear(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    color_clear_fav = KeyboardButtonColor.NEGATIVE if hunter.fav_list else KeyboardButtonColor.SECONDARY
    color_black_list = KeyboardButtonColor.NEGATIVE if hunter.black_list else KeyboardButtonColor.SECONDARY
    color_users_list = KeyboardButtonColor.NEGATIVE if hunter.users_dic else KeyboardButtonColor.SECONDARY

    keyboard = Keyboard()
    keyboard.add(Text(f'Избранное: {len(hunter.fav_list)}', {'cmd': 'clear_fav'}), color=color_clear_fav)
    keyboard.add(Text(f'Просмотренное: {len(hunter.black_list)}', {'cmd': 'clear_black_list'}), color=color_black_list)
    keyboard.row()
    keyboard.add(Text(f'Текущее: {len(hunter.users_dic)}', {'cmd': 'clear_users_list'}), color=color_users_list)
    keyboard.add(Text('Назад в настройки', {'cmd': 'settings'}))
    await message.answer('Чтобы очистить папку, нажмите кнопку в меню', keyboard=keyboard)


# меню изменение настроек
@bot.on.private_message(payload={'cmd': 'change_search'})
async def menu_change_settings(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Пол', {'cmd': 'change_search_sex'}))
    keyboard.add(Text('Город', {'cmd': 'change_search_city'}))
    keyboard.add(Text('Возраст', {'cmd': 'change_search_age'}))
    keyboard.row()
    keyboard.add(Text('Статус', {'cmd': 'change_search_status'}))
    keyboard.add(Text('Интересы', {'cmd': 'change_search_interests'}))
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}))
    await message.answer('Используйте меню', keyboard=keyboard)


# кнопка меню изменения поля "Пол"
@bot.on.private_message(payload={'cmd': 'change_search_sex'})
async def menu_change_setting_sex(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад', {'cmd': 'change_search'}))
    mes = 'Изменяем параметр <Пол> (0-любой / 1-женщина / 2-мужчина)\n' \
          'Введите команду, например /sex 2\nДождитесь ответа'
    await message.answer(mes, keyboard=keyboard)


# кнопка меню изменения поля "Возраст"
@bot.on.private_message(payload={'cmd': 'change_search_age'})
async def menu_change_settings_age(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад', {'cmd': 'change_search'}))
    mes = 'Изменяем параметр <Возраст>\nВведите команду, например: /age 25-26\nЗначения через дефис\nДождитесь ответа'
    await message.answer(mes, keyboard=keyboard)


# кнопка меню изменения поля "Город"
@bot.on.private_message(payload={'cmd': 'change_search_city'})
async def menu_change_settings_city(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад', {'cmd': 'change_search'}))
    mes = 'Изменяем параметр <Город>\nЗдесь потребуется 2 шага.\nСначала введите команду /city <название>\n' \
          'например: /city Москва\nЗатем из ответного сообщения введите id вашего города\nКоманда: /id <знач>\n' \
          'Дождитесь ответа'
    await message.answer(mes, keyboard=keyboard)


# кнопка меню изменения поля "Интересы"
@bot.on.private_message(payload={'cmd': 'change_search_interests'})
async def menu_change_settings_interests(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад', {'cmd': 'change_search'}))
    mes = 'Изменяем параметр <Интересы>\nЗдесь нет никаких ограничений\nВведите команду /inter <знач1>, <знач2>\n' \
          'Например: /inter музыка, книги, спорт\nПоле можно оставить пустым\nДождитесь ответа'
    await message.answer(mes, keyboard=keyboard)


# кнопка меню изменения поля "Статус анкеты"
@bot.on.private_message(payload={'cmd': 'change_search_status'})
async def menu_change_settings_interests(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад', {'cmd': 'change_search'}))
    mes = '''Изменяем параметр <Статус искомого профиля>\nВозможные значения:
    1 — не женат/не замужем;
    2 — есть друг/есть подруга;
    3 — помолвлен/помолвлена;
    4 — женат/замужем;
    5 — всё сложно;
    6 — в активном поиске;
    7 — влюблён/влюблена;
    8 — в гражданском браке;
    0 — не указано.
    Введите команду /status <знач>\nНапример: /status 6\nДождитесь ответа.'''
    await message.answer(mes, keyboard=keyboard)


# меню Помощь
@bot.on.private_message(payload={'cmd': 'help'})
async def menu_help(message: Message):
    keyboard = Keyboard()
    keyboard.add(Text('Назад в меню', {'cmd': 'main_menu'}))
    await message.answer(get_help_text(), keyboard=keyboard)


# команда показа анкеты Избранное или Текущее
@bot.on.private_message(payload={'cmd': 'next_user', 'show_fav': 1})
@bot.on.private_message(payload={'cmd': 'next_user', 'show_fav': 0})
async def next_user(message: Message):
    hunter = Hunter.all_hunters[message.from_id]

    # показываем анкету из Текущего
    if message.payload[-2:-1] == '0' and hunter.users_dic:
        user, mes, mes_att = get_user_from_stream(message.from_id)
        user_id, main_photo_id = user[0], user[5]
        await db.add_to_black_list(hunter.id, user)
        if mes:
            await message.answer(mes, attachment=mes_att)
            photos = await bot_user.api.photos.get(owner_id=user_id, album_id='profile',
                                                   extended=True, photo_sizes=True)
            if photos:
                mes = get_user_photo(user_id, main_photo_id, photos)
                if mes:
                    await message.answer(attachment=mes)
            else:
                await message.answer(f'Фото в профиле не найдены')

    # показываем анкету из Избранного
    elif message.payload[-2:-1] == '1' and hunter.fav_list:
        user_id, main_photo_id, mes, mes_att = get_user_from_fav(message.from_id)
        if mes:
            await message.answer(mes, attachment=mes_att)
            photos = await bot_user.api.photos.get(owner_id=user_id, album_id='profile',
                                                   extended=True, photo_sizes=True)
            if photos:
                mes = get_user_photo(user_id, main_photo_id, photos)
                if mes:
                    await message.answer(attachment=mes)
            else:
                await message.answer(f'Фото в профиле не найдены')
        await menu_show_fav(message)
    else:
        await message.answer('Анкет к показу нет.')
        if message.payload[-2:-1] == '1':
            await menu_show_fav(message)
        elif message.payload[-2:-1] == '0':
            await menu_show_users(message)


# команда добавления в избранное
@bot.on.private_message(payload={'cmd': 'add_to_fav'})
async def add_to_fav(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    mes = 'Нет анкеты для сохранения в Избранном!'
    if hunter.black_list:
        last_user = hunter.black_list.pop()
        hunter.fav_list.append(last_user)
        await db.add_to_fav_list(hunter.id, last_user)
        await db.del_from_black_list(hunter.id, last_user[0])
        hunter.fav_list_index = len(hunter.fav_list)-1
        mes = f'{hunter.fav_list[-1][1]} {hunter.fav_list[-1][2]} - анкета добавлена в избранное!'
    await message.answer(mes)


# команда удаления из Избранного
@bot.on.private_message(payload={'cmd': 'del_to_fav'})
async def add_to_fav(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    mes = 'Нет анкеты для удаления!'
    if hunter.fav_list:
        del_user = hunter.fav_list.pop(hunter.fav_list_index)
        await db.del_from_fav_list(hunter.id, del_user[0])
        hunter.fav_list_index -= 1
        if hunter.fav_list_index < 0:
            hunter.fav_list_index = 0
        hunter.black_list.append(del_user)
        await db.add_to_black_list(hunter.id, del_user)
        mes = f'{hunter.black_list[-1][1]} {hunter.black_list[-1][2]} - анкета удалена из избранного!'
    await message.answer(mes)


# команда очистки Избранное
@bot.on.private_message(payload={'cmd': 'clear_fav'})
async def clear_fav(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    hunter.fav_list = []
    await db.clear_all_fav(hunter.id)
    await message.answer('Раздел "Избранное" очищен!')
    await menu_clear(message)


# команда очистки Просмотренные
@bot.on.private_message(payload={'cmd': 'clear_black_list'})
async def clear_black_list(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    hunter.black_list = []
    await db.clear_all_blacklist(hunter.id)
    await message.answer('Раздел "Просмотренное" очищен!')
    await menu_clear(message)


# команда очистки текущего списка анкет
@bot.on.private_message(payload={'cmd': 'clear_users_list'})
async def clear_users_list(message: Message):
    hunter = Hunter.all_hunters.get(message.from_id)
    hunter.users_dic = {}
    await message.answer('Результаты поиска удалены!\nНачните новый поиск.')
    await menu_clear(message)


# команда на изменение параметра 'пол'
@bot.on.private_message(text=['/sex <sex>', '/sex'])
async def set_sex_param(message: Message, sex=None):
    if Hunter.all_hunters.get(message.from_id):
        hunter = Hunter.all_hunters[message.from_id]
        if sex:
            sex = int(sex) if sex.isdigit() else sex
            if sex in [0, 1, 2]:
                sex_title = ['любой', 'женщина', 'мужчина']
                hunter.search_sex = sex
                await db.change_search_sex(hunter.id, sex)
                hunter.reset_offset()
                await message.answer(f'Установлен параметр поиска <пол>: {sex_title[sex]} - {sex}')
            else:
                await message.answer(f'Неверный ввод! Например, надо написать: /sex 0')
        else:
            await message.answer(f'Пустая команда! Например, надо написать: /sex 1')
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# команда на изменение параметра 'возраст'
@bot.on.private_message(text=['/age <age1>-<age2>', '/age'])
async def set_age_param(message: Message, age1=None, age2=None):
    if Hunter.all_hunters.get(message.from_id):
        hunter = Hunter.all_hunters[message.from_id]
        if age1 and age2:
            res_age = check_search_age(age1, age2)
            if res_age:
                hunter.search_age_from = res_age[0]
                hunter.search_age_to = res_age[1]
                hunter.reset_offset()
                await db.change_age(hunter.id, hunter.search_age_from, hunter.search_age_to)
                await message.answer(f'Установлен параметр поиска <Возраст> от {res_age[0]} до {res_age[1]}')
            else:
                await message.answer(f'Неверный ввод! Возраст в диапазоне (18-100)!\nНапример: /age 25-30')
        else:
            await message.answer(f'Пустая команда.\nНапример, надо написать: /age 22-22')
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# команда на изменение параметра 'город'
@bot.on.private_message(text=['/city <city>', '/city'])
async def set_city_title(message: Message, city=None):
    if Hunter.all_hunters.get(message.from_id):
        if city is not None:
            mes = check_city_title(city)
            await message.answer(f'Теперь введите id вашего города:\nКоманда: /id <знач>\n{mes}')
        else:
            await message.answer(f'Например, надо написать: /city Москва')
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# команда на изменение параметра 'id город'
@bot.on.private_message(text=['/id <city_id>', '/id'])
async def set_city_id(message: Message, city_id=None):
    if Hunter.all_hunters.get(message.from_id):
        hunter = Hunter.all_hunters[message.from_id]
        if city_id is not None:
            mes = check_city_id(city_id)
            hunter.search_city_id = mes[0]
            hunter.search_city_title = mes[1]
            hunter.reset_offset()
            await db.change_city(hunter.id, hunter.search_city_id, hunter.search_city_title)
            await message.answer(f'Установлен параметр поиска "Город": {mes[1]} - {mes[0]}')
        else:
            await message.answer(f'Например, надо написать: /id 2')
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# команда на изменение параметра 'интересы'
@bot.on.private_message(text=['/inter <interests>', '/inter'])
async def set_interests(message: Message, interests=None):
    if Hunter.all_hunters.get(message.from_id):
        hunter = Hunter.all_hunters[message.from_id]
        if interests is not None:
            hunter.search_interests = interests
            await message.answer(f'Установлен параметр поиска "Интересы": {hunter.search_interests}')
        else:
            hunter.search_interests = ''
            await message.answer(f'Теперь параметр "Интересы" не влияет на поиск')
        hunter.reset_offset()
        await db.change_interests(hunter.id, hunter.search_interests)
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# команда на изменение параметра 'Статус'
@bot.on.private_message(text=['/status <status>', '/status'])
async def set_interests(message: Message, status=None):
    if Hunter.all_hunters.get(message.from_id):
        hunter = Hunter.all_hunters[message.from_id]
        if status:
            status = int(status) if status.isdigit() else status
            if status in range(0, 9):
                status_title = ['не указано', 'не женат/не замужем', 'есть друг/есть подруга',
                                'помолвлен/помолвлена', 'женат/замужем', 'всё сложно',
                                'в активном поиске', 'влюблён/влюблена', 'в гражданском браке']
                hunter.search_status = status
                await db.change_search_status(hunter.id, status)
                hunter.reset_offset()
                await message.answer(f'Установлен параметр поиска <Статус>: {status_title[status]} - {status}')
            else:
                await message.answer(f'Неверный ввод! Например, надо написать: /status 6')
        else:
            await message.answer(f'Пустая команда! Например, надо написать: /status 5')
    else:
        await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


# пересоздание БД
@bot.on.private_message(text='/new db')
async def any_message(message: Message):
    await db.recreate_db()
    print('Таблицы БД перезаписаны')
    await message.answer(f'Все данные в БД удалены!', keyboard=EMPTY_KEYBOARD)


@bot.on.private_message()
async def any_message(message: Message):
    await message.answer(f'Для запуска бота введите: /start', keyboard=EMPTY_KEYBOARD)


bot.run_forever()
