class Hunter:
    all_hunters = {}

    # поля, по которым происходит поиск анкет
    fields = ["id", "domain", "bdate", "photo_max_orig", "interests", "about", "relation", "status", "sex",
              "first_name", "last_name", "can_access_closed", "is_closed", "city", "last_seen", "activities",
              "books", "movies", "personal", "photo_id"]

    def __init__(self, hunter_id, count_find_users=300, first_name='', last_name='',
                 search_sex=1, search_city_id=1, search_city_title='Москва',
                 search_age_from=20, search_age_to=30, search_interests='', search_status=0):

        self.id = hunter_id
        self.first_name = first_name
        self.last_name = last_name
        self.search_sex = search_sex
        self.search_city_id = search_city_id
        self.search_city_title = search_city_title
        self.search_age_from = search_age_from
        self.search_age_to = search_age_to
        self.search_interests = search_interests
        self.search_status = search_status
        self.count_find_users = count_find_users
        self.offset = 0
        self.show_fav = False
        self.fav_list_index = 0
        self.users_dic = {}
        self.fav_list = []
        self.black_list = []

    def reset_offset(self):
        self.offset = 0

    def get_users_dic(self, res):
        for user in res.items:
            if user.id not in self.black_list and \
                    user.id not in self.fav_list and \
                    not user.is_closed:
                self.users_dic[user.id] = {'user_id': user.id,
                                           'domain': user.domain,
                                           'first_name': user.first_name,
                                           'last_name': user.last_name,
                                           'sex': user.sex,
                                           'photo_id': user.photo_id,
                                           'bdate': user.bdate}
