import datetime
import json
import schedule
import threading
import time
from functools import lru_cache

import requests
import telebot
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config


# Parser and Database code ##########################


class Parser:
    """Parses the page and saves the data that has been collected into the mysqldb"""

    def __init__(self, url: str, tag: str):
        self.page_url = url
        self.tag = tag

    @lru_cache(maxsize=128)  # caches the data retrieved during parsing
    def parse_a_page(self):
        """Parses the page, pretending to be a user due to page_headers parameter"""

        # headers are necessary to emulate a 'live user' connection, otherwise produces an error
        page_headers = {
            'User-Agent':
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/81.0.4044.138 Chrome/81.0.4044.138 Safari/537.36"
        }
        open_url = requests.get(self.page_url, headers=page_headers).text
        soup = BeautifulSoup(open_url, 'lxml')
        return soup

    def clear_html_tags(self) -> list:
        """strips all the tags surrounding relevant text strings"""

        parsed_tag = [item.string for item in self.parse_a_page().find_all(self.tag)]
        return parsed_tag


class DataFrame:
    def convert_into_data_frame(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


class MysqlDatabase:
    """Class containing all the functions related to db's CRUD"""

    Base = declarative_base()

    def __init__(self, db_credentials: str):
        self.mysql_credentials = db_credentials
        self.engine = create_engine(self.mysql_credentials, echo=True)
        # for convenience pymysql is used instead of the official mysql.connector
        # (the latter is maintained by MySQL team)

    class BloodLevelsTable(Base):
        """Creates the blood_by_group table and defines its structure"""

        # tablename is a compulsory attribute for the Base constructor to work
        __tablename__ = 'blood_availability'
        # Data types should be imported from the sqlalchemy library before using them
        id = Column(Integer, primary_key=True)
        date = Column(Date)
        one_plus = Column('I (+)', String(50), nullable=False)
        two_plus = Column('II (+)', String(50), nullable=False)
        tree_plus = Column('III (+)', String(50), nullable=False)
        four_plus = Column('IV (+)', String(50), nullable=False)
        one_minus = Column('I (–)', String(50), nullable=False)
        two_minus = Column('II (–)', String(50), nullable=False)
        tree_minus = Column('III (–)', String(50), nullable=False)
        four_minus = Column('IV (–)', String(50), nullable=False)

    def create_table(self):
        # 'create_all' method creates the structure outlined in BloodLevelsTable
        return self.Base.metadata.create_all(self.engine)

    def save_bloodlvl_to_mysql(self):
        """Saves the clean information into the MysqlDB"""
        session = sessionmaker(bind=self.engine)
        session = session()
        session.add_all([
            self.BloodLevelsTable(date=datetime.date.today(),
                                  one_plus=parser.clear_html_tags()[0],
                                  two_plus=parser.clear_html_tags()[1],
                                  tree_plus=parser.clear_html_tags()[2],
                                  four_plus=parser.clear_html_tags()[3],
                                  one_minus=parser.clear_html_tags()[4],
                                  two_minus=parser.clear_html_tags()[5],
                                  tree_minus=parser.clear_html_tags()[6],
                                  four_minus=parser.clear_html_tags()[7])])
        session.commit()


parser = Parser('http://kmck.kiev.ua/', 'h4')
parser.clear_html_tags()

# mysqldb = MysqlDatabase(config.db_credentials)
# mysqldb.create_table()
# mysqldb.save_bloodlvl_to_mysql()

# Telegram Bot code #########################

bot = telebot.TeleBot(config.token, True, 2)
try:
    with open('user-table.json', 'r') as f:
        user = json.load(f)
except FileNotFoundError:
    user = dict()


def calculate_last_donation_date(message):
    """Defines the date of last donation in datetime format"""

    if message == '2+ місяців тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=60))
        return str(last_donated_date)
    elif message == 'Місяць тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=30))
        return str(last_donated_date)
    elif message == "Два тижні тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=14))
        return str(last_donated_date)
    elif message == "Тиждень тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=7))
        return str(last_donated_date)
    else:
        print('Сталася помилка - бот взяв і вмер :(')
        raise ValueError


def schedule_notification(last_donation_date: str) -> str:
    """Defines the notification date based on the date of last donation"""

    date_object = datetime.datetime.strptime(last_donation_date, '%Y-%m-%d')
    return str(date_object.date() + datetime.timedelta(days=60))


class Notifier:

    def __init__(self, notify_date, notify_time):
        self.date = notify_date
        self.time = notify_time
        self.user_table = self.dict_from_json('user-table.json')

    def dict_from_json(self, filename: str):
        with open(filename, 'r') as file:
            user_info = json.load(file)
        return user_info

    def check_if_blood_is_low(self, user_id: str, json_dict: dict):
        """Checks if parsed blood level corresponding to users blood is low"""

        parser_info = parser.clear_html_tags()
        blood_types = ['I(+)', 'II(+)', 'III(+)', 'IV(+)', 'I(-)', 'II(-)', 'III(-)', 'IV(-)']
        blood_levels = {key: value for key, value in
                        zip(blood_types, parser_info)}  # transforming two lists into a dict
        user_blood = f"{json_dict[user_id]['blood_type']}{json_dict[user_id]['blood_rh']}"
        if blood_levels[user_blood] != "Достатньо":
            print('Схоже, існує необхідність у крові твоєї групи')
            return True
        elif blood_levels[user_blood] == 'Достатньо':
            print('Схоже, наразі крові твоєї групи достатньо')
            return False
        else:
            print('An error occurred, sorry pal :(  --- check_if_blood_is_low')

    def check_if_scheduled_date_is_today(self, user_id, json_dict):
        """Checks if the scheduled notification date is today"""

        if json_dict[user_id]['notify_date'] == str(datetime.date.today()):
            print('Notification date is due today')
            return True
        else:
            print('check_if_scheduled - error occurred')
            return False

    def reschedule_notification(self, user_id: str, json_dict: dict, delay: int):
        """Reschedules the notification to the next week"""

        json_dict[user_id]['notify_date'] = str(datetime.date.today() + datetime.timedelta(days=delay))
        with open('user-table.json', 'w') as json_file:
            json.dump(json_dict, json_file, indent=4)  # added indents make the json file more readable

    def notify_the_user(self, user_id):
        """Sends a notification each monday including the blood centre location"""
        # TODO: include send_location of the blood bank

        keyboard = telebot.types.InlineKeyboardMarkup()
        dont_disturb_week = telebot.types.InlineKeyboardButton(text='Не турбувати тиждень',
                                                               callback_data='add_one_week')
        dont_disturb_two_months = telebot.types.InlineKeyboardButton(text='Щойно здав :) Не турбувати два місяці',
                                                                     callback_data='add_two_months')
        keyboard.row(dont_disturb_week)
        keyboard.row(dont_disturb_two_months)

        incentive_text = 'Не забувай: здача крові це 3 врятованих життя' \
                         ', довідка на 2 вихідних, і чай з печивком (емодзі)'
        bot.send_message(user_id,
                         'Привіт! З моменту твоєї останньої донації пройшло більше двох місяців, а '
                         f'у Київського Центру Крові закінчується '
                         '{user[user_id]["blood_type"]} {user[user_id]["blood_rh"]}\n\n'
                         f'{incentive_text}',
                         reply_markup=keyboard)

    def decide_when_to_notify(self):
        """Compares the scheduled date with current one, notifies if blood is low, and reschedules if not"""

        start = time.time()
        for cid in self.user_table.keys():
            if self.check_if_blood_is_low(cid, self.user_table):
                if self.check_if_scheduled_date_is_today(cid, self.user_table):
                    if time.strftime('%a') == self.date:
                        print('Indeed, today is Monday')
                        if time.strftime('%H') == self.time:
                            self.notify_the_user(cid)
                            self.reschedule_notification(cid, self.user_table, 7)
                        else:
                            pass
                    else:
                        self.reschedule_notification(cid, self.user_table, 1)
                    # schedule.every().monday.at('09:30').do(notify)
            #         elif blood_low is False:
            #             return reschedule_notification(cid)
            #         else:
            #             print('ERROR - could not define if the blood level is low')
            #             raise TypeError
            else:
                print('Sorry pal, the notification is not due today')
        finish = time.time()
        print(start - finish)

    def infinite_update_loop(self, delay):
        schedule.every(delay).minutes.do(self.decide_when_to_notify)
        while True:
            schedule.run_pending()
            time.sleep(15)

    def get_user_contacts(self):
        # TODO: Optional, users may be unwilling to give up personal information
        # user_name, phone_number
        pass


@bot.message_handler(commands=['help'])
def bot_info(message):
    """Shows all available commands when user types '/help' """
    rstrt = '/reset - повторно вказати свою групу крові'
    upd = '/update - перевірити запаси крові'
    interv = '/intervals - інтервали між кроводачами'
    inf = '/info - довідкова інформація'
    bot.send_message(message.chat.id, f'{rstrt}\n{upd}\n{interv}\n{inf}')


@bot.message_handler(commands=['info'])
def donor_info(message):
    """Sends a link to the Municipal Blood Centre for more information"""
    bot.send_message(message.chat.id, 'Більше інформації про процедуру та пункти здачі крові на kmck.kiev.ua')


@bot.message_handler(commands=['update'])
def check_blood_availability(message):
    """Displays the freshly parsed info about blood availability"""

    blood_level = parser.clear_html_tags()
    bot.send_message(message.chat.id, f'Запаси станом на {datetime.date.today()}')
    bot.send_message(
        message.chat.id,
        f'I (+) : {blood_level[0]}\nII (+) : {blood_level[1]}\nIII (+) : {blood_level[2]}\nIV (+) : {blood_level[3]}'
    )
    bot.send_message(
        message.chat.id,
        f'I (–) : {blood_level[4]}\nII (–) : {blood_level[5]}\nIII (–) : {blood_level[6]}\nIV (–) : {blood_level[7]}'
    )
    # TODO: apply markup formatting to the text


@bot.message_handler(commands=['reset'])
def delete_user_id(message):
    """Deletes the info about the user from the user-info dict and json db"""

    cid = message.chat.id
    del user[str(cid)]
    message.text = 'start'
    bot.register_next_step_handler(message, welcome_message(message))


@bot.message_handler(commands=['start'])
def welcome_message(message):
    """Displays available blood types and asks to choose one from the list"""

    cid = message.chat.id
    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    blood_types_keyboard.row('I - перша', 'II - друга')
    blood_types_keyboard.row('III - третя', 'IV - четверта')

    # TODO: check the bot_stage of the user
    if str(cid) in user:
        bot.send_message(cid, 'Схоже, ти вже в базі користувачів.\n'
                              'Дякую що допомагаєш рятувати життя!\n\n'
                              'Якщо хочеш оновити дані про себе - тисни /reset')

    else:
        msg = bot.send_message(
            cid, 'Привіт! Готовий рятувати життя? \nВкажи свою групу крові: ', reply_markup=blood_types_keyboard)
        bot.register_next_step_handler(msg, ask_blood_rh)
        user[str(cid)] = dict(blood_type=None,
                              blood_rh=None,
                              last_donated=None,
                              bot_stage=0)

        # Displays the Telegram @username and f-l-names of the user, this info is not stored anywhere
        print(
            '*' * 10,
            f'@{message.chat.username} AKA "{message.chat.first_name} {message.chat.last_name}"',
            f'logged in on {datetime.date.today()}',
            '*' * 10)

    # TODO: create a log file recording all the actions (use standard library)


def ask_blood_rh(message):
    """Asks for the blood RH of the user, saves the blood type into a dict"""
    message.text = f'{message.text}'.split()[0]
    cid = message.chat.id
    # replacing '==' with 'in set()' expression is more concise and provides better performance
    if message.text in {'I', 'II', 'III', 'IV'}:

        blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        blood_types_keyboard.row('(+)')
        blood_types_keyboard.row('(-)')
        msg = bot.send_message(cid, 'А тепер вкажи свій резус-фактор:', reply_markup=blood_types_keyboard)
        bot.register_next_step_handler(msg, last_donated)

        user[str(cid)]['blood_type'] = str(message.text)
        user[str(cid)]['bot_stage'] = 1
        print(f'Blood type: {message.text}')
    else:
        del user[str(cid)]
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')


def last_donated(message):
    """Asks when approximately the user last donated blood. Info is used for reminders"""
    if message.text in {'(+)', '(-)'}:
        cid = message.chat.id
        donation_dates_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        donation_dates_keyboard.row("2+ місяців тому", "Місяць тому")
        donation_dates_keyboard.row("Два тижні тому", "Тиждень тому")
        msg = bot.send_message(cid,
                               'Коли приблизно ти востаннє здавав кров?\n'
                               'Від цього залежатиме коли ти отримаєш сповіщення',
                               reply_markup=donation_dates_keyboard)
        bot.register_next_step_handler(msg, thank_you_for_answers)

        user[str(cid)]['blood_rh'] = str(message.text)
        user[str(cid)]['bot_stage'] = 2
        print(f'Blood Rh: {message.text}')

    else:
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')
        del user[str(message.chat.id)]['blood_rh']


def thank_you_for_answers(message):
    """Thanks for the information, shows a list of available commands, saves the answers locally to users-info.json"""
    cid = message.chat.id
    emoji = u'\U0001F618'
    quest = 'Переглянути повний список функцій - тисни /help'
    keyboard_remove = telebot.types.ReplyKeyboardRemove(selective=True)
    bot.send_message(cid, 'All done!\nТепер я надсилатиму тобі сповіщення, '
                          f'якщо виникне необхідність у крові твоєї групи! {emoji}\n\n{quest}',
                     reply_markup=keyboard_remove)

    print(f'Last donated: {message.text}\n', '*' * 50)

    user[str(cid)]['last_donated'] = calculate_last_donation_date(message.text)
    user[str(cid)]['notify_date'] = schedule_notification(user[str(cid)]['last_donated'])
    user[str(cid)]['bot_stage'] = 3
    save_to_json_db(user)


def save_to_json_db(dictionary: dict):
    with open('user-table.json', 'w') as json_file:
        json.dump(dictionary, json_file, indent=4)


# Turn on the notifications with specific parameters

notifier = Notifier('Tue', '13')

task1 = threading.Thread(target=notifier.infinite_update_loop, args=(15,), daemon=True)
task1.start()

bot.polling(interval=1)

# bot.set_update_listener(check_if_scheduled_date_is_today)
