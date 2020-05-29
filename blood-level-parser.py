import datetime
import json
import time
from functools import lru_cache

import requests
import telebot
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config

Base = declarative_base()


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
    def convert_into_dataframe(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


class BloodLevelsTable(Base):
    """Creates the blood_by_group table and defines its structure"""
    # __tablename__ is a compulsory attribute for the Base constructor to work
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


class MysqlDatabase:
    """Class containing all the functions related to db's CRUD"""

    def __init__(self, db_credentials: str):
        self.mysql_credentials = db_credentials
        self.engine = create_engine(self.mysql_credentials, echo=True)
        # for convenience pymysql is used instead of the official mysql.connector
        # (the latter is maintained by MySQL team)

    def create_table(self):
        # 'create_all' method creates the structure outlined in BloodLevelsTable
        return Base.metadata.create_all(self.engine)

    def save_bloodlvl_to_mysql(self):
        """Saves the clean information into the MysqlDB"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        session.add_all([
            BloodLevelsTable(date=datetime.date.today(),
                             one_plus=parser.clear_html_tags()[0],
                             two_plus=parser.clear_html_tags()[1],
                             tree_plus=parser.clear_html_tags()[2],
                             four_plus=parser.clear_html_tags()[3],
                             one_minus=parser.clear_html_tags()[4],
                             two_minus=parser.clear_html_tags()[5],
                             tree_minus=parser.clear_html_tags()[6],
                             four_minus=parser.clear_html_tags()[7])])
        session.commit()


def repeat_parsing():
    """Creates an infinite loop, allowing to schedule the execution of functions """

    while True:
        mysqldb.save_bloodlvl_to_mysql()
        time.sleep(5)


parser = Parser('http://kmck.kiev.ua/', 'h4')
parser.clear_html_tags()

mysqldb = MysqlDatabase(config.db_credentials)
mysqldb.create_table()

bot = telebot.TeleBot(config.token, True, 2)
try:
    with open('user-table.json', 'r') as f:
        user = json.load(f)
except FileNotFoundError:
    user = dict()


# repeat_parsing()

@bot.message_handler(commands=['help'])
def bot_info(message):
    """Shows all available commands when user types '/help' """
    rstrt = '/restart - повторно вказати свою групу крові'
    upd = '/update - перевірити запаси крові'
    inf = '/info - довідкова інформація'
    bot.send_message(message.chat.id, f'{rstrt}\n{upd}\n{inf}')


@bot.message_handler(commands=['info'])
def donor_info(message):
    """Sends a link to the Municipal Blood Centre for more information"""
    bot.send_message(message.chat.id, 'Більше інформації про процедуру та пункти здачі крові на kmck.kiev.ua')


@bot.message_handler(commands=['update'])
def check_blood_availability(message):
    """Displays the freshly parsed info about blood availability"""

    blood_level = parser.clear_html_tags()
    bot.send_message(message.chat.id, f'Запаси станом на {datetime.date.today()}')
    bot.send_message(message.chat.id,
                     f'I (+) : {blood_level[0]}\nII (+) : {blood_level[1]}\nIII (+) : {blood_level[2]}\nIV (+) : {blood_level[3]}')
    bot.send_message(message.chat.id,
                     f'I (–) : {blood_level[4]}\nII (–) : {blood_level[5]}\nIII (–) : {blood_level[6]}\nIV (–) : {blood_level[7]}')
    # TODO: apply markup formatting to the text


@bot.message_handler(commands=['start'])
def welcome_message(message):
    """Displays available blood types and asks to choose one from the list"""

    cid = message.chat.id
    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                                             row_width=2)
    blood_type1 = telebot.types.KeyboardButton('I - перша')
    blood_type2 = telebot.types.KeyboardButton('II - друга')
    blood_type3 = telebot.types.KeyboardButton('III - третя')
    blood_type4 = telebot.types.KeyboardButton('IV - четверта')
    blood_types_keyboard.row(blood_type1, blood_type2)
    blood_types_keyboard.row(blood_type3, blood_type4)

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
            '*'*10,
            f'@{message.chat.username} AKA "{message.chat.first_name} {message.chat.last_name}" logged in on {datetime.date.today()}',
            '*'*10)

    # TODO: create a log file recording all the actions


def ask_blood_rh(message):
    """Asks for the blood RH of the user, saves the blood type into a dict"""
    if message.text == 'I - перша' or message.text == 'II - друга' or message.text == 'III - третя' or message.text == 'IV - четверта':
        cid = message.chat.id
        blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
        blood_rh_plus = telebot.types.KeyboardButton('(+)')
        blood_rh_minus = telebot.types.KeyboardButton('(–)')
        blood_types_keyboard.row(blood_rh_plus)
        blood_types_keyboard.row(blood_rh_minus)
        msg = bot.send_message(cid, 'А тепер вкажи свій резус-фактор:',
                               reply_markup=blood_types_keyboard)
        bot.register_next_step_handler(msg, last_donated)

        user[str(cid)]['blood_type'] = str(message.text)
        user[str(cid)]['bot_stage'] = 1
        print(f'Blood type: {message.text}')
    else:
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')
        return welcome_message


def last_donated(message):
    """Asks when approximately the user last donated blood. Info is used for reminders"""
    if message.text == '(+)' or message.text == '(–)':
        cid = message.chat.id

        donation_dates_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
        more_than_two_months = telebot.types.KeyboardButton("2+ місяців тому")
        one_month_ago = telebot.types.KeyboardButton("Місяць тому")
        two_weeks_ago = telebot.types.KeyboardButton("Два тижні тому")
        one_week_ago = telebot.types.KeyboardButton("Тиждень тому")
        donation_dates_keyboard.row(more_than_two_months, one_month_ago)
        donation_dates_keyboard.row(two_weeks_ago, one_week_ago)
        msg = bot.send_message(cid, 'Коли приблизно ти востаннє здавав кров?\n'
                                    'Від цього залежить коли ти отримаєш сповіщення',
                               reply_markup=donation_dates_keyboard)
        bot.register_next_step_handler(msg, thank_you_for_answers)

        user[str(cid)]['blood_rh'] = str(message.text)
        user[str(cid)]['bot_stage'] = 2
        print(f'Blood Rh: {message.text}')

    else:
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')
        del user[str(message.chat.id)]


def thank_you_for_answers(message):
    """Thanks for the information, shows a list of available commands, saves the answers locally to users-info.json"""
    cid = message.chat.id
    emoji = u'\U0001F618'
    quest = 'Переглянути повний список функцій - тисни /help'
    keyboard_remove = telebot.types.ReplyKeyboardRemove(selective=True)
    bot.send_message(cid, 'All done!\nТепер я надсилатиму тобі сповіщення,'
                          f'якщо виникне необхідність у крові твоєї групи! {emoji}\n\n{quest}',
                          reply_markup=keyboard_remove)

    print(f'Last donated: {message.text}\n', '*' * 50)

    user[str(cid)]['last_donated'] = calculate_last_donation_date(message.text)
    user[str(cid)]['notify_date'] = donation_scheduler(user[str(cid)]['last_donated'])
    user[str(cid)]['bot_stage'] = 3
    with open('user-table.json', 'w') as json_file:
        json.dump(user, json_file)


def calculate_last_donation_date(message):
    if message == '2+ місяців тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=60))
        return f'{last_donated_date}'
    elif message == 'Місяць тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=30))
        return f'{last_donated_date}'
    elif message == "Два тижні тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=14))
        return f'{last_donated_date}'
    elif message == "Тиждень тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=7))
        return f'{last_donated_date}'
    else:
        print('Сталася помилка і все покотилося ')
        raise ValueError


# @bot.set_update_listener()
def donation_scheduler(last_donation_date: str) -> str:
    # TODO: defines the notification date based on last_donated date
    date_object = datetime.datetime.strptime(last_donation_date, '%Y-%m-%d')
    return f'{date_object.date() + datetime.timedelta(days=60)}'


def check_if_scheduled_date_is_today(*messages):
    # TODO: add a weekly recurring task which will notify the user if the scheduled date has come and blood is low
    # TODO: if blood is not low on scheduled date - reschedules the notification to the next week
    # should run as a background task of comparing scheduled date with today's date, and sends a notif
    print(f'New message recieved at {datetime.time.hour}')
    # notification_text = f'Запас {bloodtype} {bloodlevel} - ТИ нам потрібен'
    # incentive_text = '<bold>Не забувай</bold>: здача крові це 3 врятованих життя, довідка на 2 вихідних, і чай з печивком (емодзі)'
    # bot.send_message(chat_id=users_info[message.chat.id], )
    pass


def notify_if_blood_is_low(message):
    pass


def get_user_contacts(self):
    # TODO: Optional, users may be unwilling to give up personal information
    # user_name, phone_number
    pass


bot.set_update_listener(check_if_scheduled_date_is_today)
bot.polling(interval=2)
