from bs4 import BeautifulSoup
from functools import lru_cache
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import config
import datetime
import requests
import telebot


Base = declarative_base()

class Parser:
    """Parses the page and saves the data that has been collected into the mysqldb"""

    def __init__(self, url: str, tag: str):
        self.page_url = url
        self.tag = tag

    @lru_cache(maxsize=128)
    def parse_a_page(self):
        page_headers = {
            'User-Agent':
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/81.0.4044.138 Chrome/81.0.4044.138 Safari/537.36"
        }  # headers are necessary to emulate a 'live user' connection
        open_url = requests.get(self.page_url, headers=page_headers).text
        soup = BeautifulSoup(open_url, 'lxml')
        return soup

    def clear_html_tags(self) -> list:
        # Search inside <div class="vc_row wpb_row vc_inner vc_row-fluid">
        # Two separate columns have similar structure - data can be collected through indexing of elements
        parsed_tag = [item.string for item in self.parse_a_page().find_all(self.tag)]
        print(parsed_tag)
        return parsed_tag


class DataFrame:
    def convert_into_dataframe(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


class BloodLevels(Base):
    __tablename__ = 'blood_by_group'

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

    def __init__(self, db_credentials: str):
        self.mysql_credentials = db_credentials
        self.engine = create_engine(self.mysql_credentials)
        # for convenience pymysql is used instead of the official mysql.connector
        # (the latter is maintained by MySQL team)

    def create_table(self):
        Base.metadata.create_all(self.engine)

    def create_session(self):
        Session = sessionmaker(bind=self.engine)
        session = Session()
        return session

    def save_to_mysql(self):
        self.create_session().add_all([
            BloodLevels(date=datetime.date.today(),
                        one_plus=parser.clear_html_tags()[0],
                        two_plus=parser.clear_html_tags()[1],
                        tree_plus=parser.clear_html_tags()[2],
                        four_plus=parser.clear_html_tags()[3],
                        one_minus=parser.clear_html_tags()[4],
                        two_minus=parser.clear_html_tags()[5],
                        tree_minus=parser.clear_html_tags()[6],
                        four_minus=parser.clear_html_tags()[7])])
        self.create_session().commit()
        pass


parser = Parser('http://kmck.kiev.ua/', 'h4')

mysqldb = MysqlDatabase(config.db_credentials)
mysqldb.create_table()
mysqldb.save_to_mysql()

bot = telebot.TeleBot(config.token)


@bot.message_handler(commands=['help'])
def bot_info(message):
    upd = '/update - перевірити запаси крові'
    strt = '/start - вказати / оновити групу крові'
    inf = '/info - довідкова інформація'
    bot.send_message(message.chat.id, f'{strt}\n{upd}\n{inf}')


@bot.message_handler(commands=['start'])
def welcome_message(message):
    print(
        f'@{message.chat.username} AKA "{message.chat.first_name} {message.chat.last_name}" logged in on {datetime.date.today()}')  # returns the Telegram @username of the user
    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    blood_type1 = telebot.types.KeyboardButton('I - перша')
    blood_type2 = telebot.types.KeyboardButton('II - друга')
    blood_type3 = telebot.types.KeyboardButton('III - третя')
    blood_type4 = telebot.types.KeyboardButton('IV - четверта')
    blood_types_keyboard.row(blood_type1, blood_type2)
    blood_types_keyboard.row(blood_type3, blood_type4)

    msg = bot.send_message(message.chat.id, 'Привіт! Готовий рятувати життя? \nВкажи свою групу крові: ',
                           reply_markup=blood_types_keyboard)
    bot.register_next_step_handler(msg, ask_blood_rh)
    # TODO: create a log file recording all the actions
    # TODO: send the info about the user to MySQL


def ask_blood_rh(message):
    # TODO: add if-else conditions, avoid non-answered questions with recursion
    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    blood_rh_plus = telebot.types.KeyboardButton('(+)')
    blood_rh_minus = telebot.types.KeyboardButton('(–)')
    blood_types_keyboard.row(blood_rh_plus)
    blood_types_keyboard.row(blood_rh_minus)
    msg = bot.send_message(message.chat.id, 'А тепер вкажи свій резус-фактор:',
                           reply_markup=blood_types_keyboard)
    print(f'Blood type: {message.text}')
    bot.register_next_step_handler(msg, thank_you_for_answers)


def thank_you_for_answers(message):
    if (message.text == '(+)') or (message.text == '(–)'):
        emoji = u'\U0001F618'
        quest = 'Переглянути повний список функцій - тисни /help'
        keyboard_remove = telebot.types.ReplyKeyboardRemove(selective=True)
        bot.send_message(message.chat.id,
                         f'All done!\nТепер я надсилатиму тобі сповіщення, якщо виникне необхідність у крові твоєї групи! {emoji}\n\n{quest}',
                         reply_markup=keyboard_remove)
        print(f'Blood Rh: {message.text}')
        print('------------------------')
    else:
        bot.send_message(message.chat.id, 'Дурник-бот не зрозумів :( Натисни /help і вибери команду зі списку')


@bot.message_handler(commands=['update'])
def awaiting_functions(message):
    bot.send_message(message.chat.id, f'Запаси станом на {datetime.date.today()}')
    bot.send_message(message.chat.id,
                     f'I (+) : {blood_level[0]}\nII (+) : {blood_level[1]}\nIII (+) : {blood_level[2]}\nIV (+) : {blood_level[3]}')
    bot.send_message(message.chat.id,
                     f'I (–) : {blood_level[4]}\nII (–) : {blood_level[5]}\nIII (–) : {blood_level[6]}\nIV (–) : {blood_level[7]}')
    # TODO: apply markup formatting to the text


@bot.message_handler(commands=['info'])
def donor_info(message):
    bot.send_message(message.chat.id, 'Більше інформації про процедуру та пункти здачі крові на kmck.kiev.ua')


def get_user_blood_type(self):
    # TODO: send the info about the user to MySQL
    pass


def get_user_contacts(self):
    # TODO: Optional, users may be unwilling to give up personal information
    # user_name, phone_number
    pass


def check_blood_availability(self):
    # TODO: see if today's level is ok - check latest parsed info
    pass


def notify_if_blood_is_low(self):
    notification_text = f'{bloodtype} is low - we need YOU to save lives'
    incentive_text = 'Short reminder: Blood donation will give you 2 days off and a financial remuneration'
    pass


def donation_scheaduler(message):
    # TODO: ask the user for the date when they last donated blood, send notifications after 3 months if blood is needed
    # acceptable intervals between blood donations: 2.5 mths for men, 3 mths for women
    pass


# bot.polling()
