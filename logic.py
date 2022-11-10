import requests
import random
from config import access_token
from hunter import Hunter


# проверка правильности установки параметра "возраст"
def check_search_age(age1, age2):
    try:
        if (age1.isdigit() and int(age1) in range(18, 100)) and (
                age2.isdigit() and int(age2) in range(18, 100)):
            return (min(int(age1), int(age2)), max(int(age1), int(age2)))
    except TypeError as er:
        print(er)
        return


# поиск по города по названию
def find_a_city_title(city):
    url = 'https://api.vk.com/method/database.getCities'
    params = {
        'country_id': 1,
        'need_all': 0,
        'count': 1000,
        'access_token': access_token,
        'v': '5.130',
        'q': city
    }
    try:
        res = requests.get(url, params=params).json()['response']['items']
        return res
    except:
        return "Ошибка"


# поиск id города по названию
def find_a_city_id(city_id):
    url = 'https://api.vk.com/method/database.getCitiesById'
    params = {
        'city_ids': city_id,
        'access_token': access_token,
        'v': '5.130',
    }
    try:
        res = requests.get(url, params=params).json()['response'][0]
        return res
    except:
        return "Ошибка"


# результаты поиска города по названию
def check_city_title(city):
        try:
            res = find_a_city_title(city)
            mes = 'id | город | район | регион |\n=============================\n'
            for i in res:
                mes += f"{i.get('id')} | {i.get('title')} | {i.get('area')} | {i.get('region')}\n"
            return mes
        except:
            return 'Произошла ошибка'


# установка значения параметра "город"
def check_city_id(city_id):
        try:
            city = find_a_city_id(city_id)
            city_title = city['title']
            city_id = city['id']
            return (city_id, city_title)
        except:
            return ('1', 'Москва')


# получаем данные профиля анкеты из Текущего
def get_user_from_stream(hunter_id):
    hunter = Hunter.all_hunters[hunter_id]
    mes = 0
    if hunter.users_dic:
        user_id = random.choice(list(hunter.users_dic.keys()))
        first_name = hunter.users_dic[user_id]['first_name']
        last_name = hunter.users_dic[user_id]['last_name']
        domain = hunter.users_dic[user_id]['domain']
        bdate = hunter.users_dic[user_id]['bdate']
        main_photo_id = hunter.users_dic[user_id]['photo_id']
        del hunter.users_dic[user_id]
        # показанная анкета сразу идет в Просмотренное и БД
        user = [user_id, first_name, last_name, domain, bdate, main_photo_id]
        hunter.black_list.append(user)
        #db.add_to_black_list(hunter.id, [user_id, first_name, last_name, domain, bdate, main_photo_id])  # <-----------------------------!!!!!1
        mes = f'{first_name} {last_name}, {bdate}\nhttps://vk.com/{domain}\n'
        mes_att = f'photo{main_photo_id}'

        return (user, mes, mes_att)
        #return (user_id, main_photo_id, mes, mes_att)
    return mes


# получаем данные профиля анкеты из Избранного
def get_user_from_fav(hunter_id):
    hunter = Hunter.all_hunters[hunter_id]
    hunter.fav_list_index += 1
    if hunter.fav_list_index > len(hunter.fav_list) - 1:
        hunter.fav_list_index = 0

    user = hunter.fav_list[hunter.fav_list_index]
    user_id = user[0]
    first_name = user[1]
    last_name = user[2]
    domain = user[3]
    bdate = user[4]
    main_photo_id = user[5]
    mes = f'{first_name} {last_name}, {bdate}\nhttps://vk.com/{domain}\n'
    mes_att = f'photo{main_photo_id}'

    return (user_id, main_photo_id, mes, mes_att)


# собираем фото из профиля юзера
def get_user_photo(user_id, main_photo_id, photos):
    mes = ''

    #сортируем по признаку (лайки+комменты), берем 3 самых популярных и выводим их в чат
    best_photos = sorted(photos.items, key=lambda x: (x.likes.count + x.comments.count), reverse=True)[:3]
    for photo in best_photos:
        if main_photo_id != f'{user_id}_{photo.id}':
            mes += f'photo{user_id}_{photo.id},'

    return mes


# текст для меню Помощь
def get_help_text():
    mes = """
        Это бот для поиска анкет по заданным параметрам.
        Навигация по меню бота:
        -----------------------------
        <Новый поиск> - подбор анкет по вашим параметрам
        <Избранное> - показ анкет из папки "Избранное"
        <Анкеты> - показ найденных анкет
        <Добавить в избранное> добавить анкету в Избранное. 
        Анкеты добавляются с последней показанной в обратном порядке.
        -----------------------------
        <Настройки> - установка параметров поиска
        установка параметров: /<команда> <значение>  
        <Пол> - пол в искомых анкета [0-любой, 1-женщина, 2-мужчина] | /sex 1
        <Возраст> - возрастной интервал (мин. значение от: 18) | /age 25-30
        <Статус> - семейный статус пользователя (0-8) | /status 5
        <Интересы> - поля в анкете [книги, фильмы, музыка, о себе, интересы]
        | /inter  <знач1, знач2, ..> | перечислите через запятую ключевые слова(необязательное поле)
        
        <Город> - город в анкете | /city Москва --> /id 1 | 
        команду /city используйте, если не знаете id города 
        -----------------------------
        <Очистка> -> <Избранное> - полностью очищает ваш список избранного
        <Очистка> - <Текущее> - очистка списка текущего поиска
        <Очистка> -> <Просмотренное> - очищает ваш список показанного. Эти анкеты 
        снова будут появляться в поиске
                
        Просмотренные анкеты, автоматически добавляются в "Просмотренное" и больше не выводятся в показах."""

    return mes
