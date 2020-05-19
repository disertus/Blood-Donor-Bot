from bs4 import BeautifulSoup
from functools import lru_cache
import config
import datetime
import requests
import telebot


class Parser:
    """Parses the page and saves the data that has been collected into the mysqldb"""

    def __init__(self, url: str):
        self.page_url = url

    @lru_cache(maxsize=128)
    def parse_a_page(self):
        page_headers = {
            'User-Agent':
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/81.0.4044.138 Chrome/81.0.4044.138 Safari/537.36"
        }  # headers are necessary to emulate a 'live user' connection
        open_url = requests.get(self.page_url, headers=page_headers).text
        soup = BeautifulSoup(open_url, 'lxml')
        return soup

    def clear_html_tags(self, tag: str) -> list:
        # Search inside <div class="vc_row wpb_row vc_inner vc_row-fluid">
        # Two separate columns have similar structure - data can be collected through indexing of elements
        parsed_tag = [item.string for item in self.parse_a_page().find_all(tag)]
        return parsed_tag


class MySQLdb:

    def __init__(self, db_credentials: tuple):
        self.mysql_credentials = db_credentials
        self.connection = None

    def create_database(self):
        pass

    def create_table(self):
        pass

    def save_to_mysqldb(self):
        # TODO: use the same approach as in covid, but with string concatenation, hide db credentials inside cfg module
        pass


class DataFrame:
    def convert_into_dataframe(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


parser = Parser('http://kmck.kiev.ua/')
blood_level = parser.clear_html_tags('h4')

mysql_db = MySQLdb(config.db_credentials)

bot = telebot.TeleBot(config.token)
user = bot.get_me()


@bot.message_handler(commands=['help'])
def bot_info(message):
    upd = '/update - перевірити запаси крові'
    strt = '/start - вказати / оновити групу крові'
    inf = '/info - довідкова інформація'
    bot.send_message(message.chat.id, f'{strt}\n{upd}\n{inf}')



@bot.message_handler(commands=['start'])
def welcome_message(message):
    print(f'@{message.chat.username} AKA "{message.chat.first_name} {message.chat.last_name}" logged in on {datetime.date.today()}')  # returns the Telegram @username of the user
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

bot.polling()
