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


class UserInfo(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    blood_type = Column(String(50), nullable=False)
    blood_rh = Column(String(50), nullable=False)
    last_donated = Column(String(50), nullable=False)
    joined_date = Column(Date, nullable=False)


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

    def save_user_to_mysql(self, uid, blood_tp, blood_rh, ddate, jdate):
        """Saves the user information into MysqlDB"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        session.add_all([
            UserInfo(user_id=uid,
                     blood_type=blood_tp,
                     blood_rh=blood_rh,
                     last_donated=ddate,
                     joined_date=jdate)])
        session.commit()


def repeat_parsing():
    """Creates an infinite loop, allowing to schedule the execution of functions"""

    while True:
        mysqldb.save_bloodlvl_to_mysql()
        time.sleep(5)


class User:
    def __init__(self):
        self.users_info = dict(user_id=None,
                               blood_type=None,
                               blood_rh=None,
                               last_donated='some_date',
                               joined_date=datetime.date.today())


parser = Parser('http://kmck.kiev.ua/', 'h4')
parser.clear_html_tags()

mysqldb = MysqlDatabase(config.db_credentials)
mysqldb.create_table()

bot = telebot.TeleBot(config.token)
user = User()


# repeat_parsing()

@bot.message_handler(commands=['help'])
def bot_info(message):
    """Shows all available commands when user types '/help' """

    upd = '/update - перевірити запаси крові'
    inf = '/info - довідкова інформація'
    bot.send_message(message.chat.id, f'{strt}\n{upd}\n{inf}')


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

    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        row_width=2)
    blood_type1 = telebot.types.KeyboardButton('I - перша')
    blood_type2 = telebot.types.KeyboardButton('II - друга')
    blood_type3 = telebot.types.KeyboardButton('III - третя')
    blood_type4 = telebot.types.KeyboardButton('IV - четверта')
    blood_types_keyboard.row(blood_type1, blood_type2)
    blood_types_keyboard.row(blood_type3, blood_type4)

    msg = bot.send_message(
        message.chat.id,
        'Привіт! Готовий рятувати життя? \nВкажи свою групу крові: ',
        reply_markup=blood_types_keyboard)
    bot.register_next_step_handler(msg, ask_blood_rh)
    user.users_info.update({'user_id': str(message.chat.id)})

    # Displays the Telegram @username and f-l-names of the user, this info is not stored anywhere
    print(
        f'@{message.chat.username} AKA "{message.chat.first_name} {message.chat.last_name}" logged in on {datetime.date.today()}')
    print(user.users_info)

    # TODO: create a log file recording all the actions
    # TODO: send the info about the user to MySQL


def ask_blood_rh(message):
    """Asks for the blood RH of the user, saves the blood type into a dict"""
    # TODO: add if-else conditions, avoid non-answered questions with recursion

    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    blood_rh_plus = telebot.types.KeyboardButton('(+)')
    blood_rh_minus = telebot.types.KeyboardButton('(–)')
    blood_types_keyboard.row(blood_rh_plus)
    blood_types_keyboard.row(blood_rh_minus)
    msg = bot.send_message(message.chat.id, 'А тепер вкажи свій резус-фактор:',
                           reply_markup=blood_types_keyboard)
    bot.register_next_step_handler(msg, thank_you_for_answers)

    user.users_info['blood_type'] = str(message.text)
    print(f'Blood type: {message.text}')


def thank_you_for_answers(message):
    """Thanks for the information, shows a list of available commands, saves the answers locally to users-info.json"""
    if (message.text == '(+)') or (message.text == '(–)'):
        emoji = u'\U0001F618'
        quest = 'Переглянути повний список функцій - тисни /help'
        keyboard_remove = telebot.types.ReplyKeyboardRemove(selective=True)
        bot.send_message(message.chat.id,
                         f'All done!\nТепер я надсилатиму тобі сповіщення, якщо виникне необхідність у крові твоєї групи! {emoji}\n\n{quest}',
                         reply_markup=keyboard_remove)
        print(f'Blood Rh: {message.text}')
        print('------------------------')
        user.users_info['blood_rh'] = str(message.text)

        import sqlalchemy
        try:
            mysqldb.save_user_to_mysql(user.users_info['user_id'],
                                       user.users_info['blood_type'],
                                       user.users_info['blood_rh'],
                                       user.users_info['last_donated'],
                                       user.users_info['joined_date'])
        except sqlalchemy.exc.IntegrityError:
            print('User already registered')

    else:
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')
        return welcome_message


def get_user_contacts(self):
    # TODO: Optional, users may be unwilling to give up personal information
    # user_name, phone_number
    pass


def get_user_blood_type(self):
    # TODO: send the info about the user to MySQL / JSON database
    pass


def notify_if_blood_is_low(self):
    # TODO: add a weekly recurring task which will notify the user if his blood type is low
    notification_text = f'Запас {bloodtype} {bloodlevel} - ТИ нам потрібен'
    incentive_text = '<bold>Не забувай</bold>: здача крові це 3 врятованих життя, довідка на 2 вихідних, і чай з печивком (емодзі)'
    bot.send_message(chat_id=users_info[message.chat.id], )
    pass


def donation_scheduler(message):
    # TODO: ask the user for the date when they last donated blood, send notifications after 3 months if blood is needed
    # acceptable intervals between blood donations: 2.5 mths for men, 3 mths for women
    pass


bot.polling()
