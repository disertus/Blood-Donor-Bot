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
print(user)


@bot.message_handler(commands=['start', 'help'])
def welcome_message(message):
    bot.send_message(message.chat.id, 'Привіт! Дякую що приєдналися до спільноти, що рятує життя!')
    bot.send_message(message.chat.id, 'Відправ повідомлення з будь-яким текстом аби отримати інформацію про стан запасів крові в Київському Міському Центрі Крові')

    user_nickname = message.chat.username # returns the Telegram @username of the user
    print(f'@{user_nickname} logged in on {datetime.date.today()}')
    # TODO: send the info about the user to MySQL


@bot.message_handler(func=lambda message: True)
def awaiting_functions(message):
    bot.send_message(message.chat.id, f'Запаси станом на {datetime.date.today()}')
    bot.send_message(message.chat.id, f'I (+) : {blood_level[0]}\nII (+) : {blood_level[1]}\nIII (+) : {blood_level[2]}\nIV (+) : {blood_level[3]}')
    bot.send_message(message.chat.id, f'I (–) : {blood_level[4]}\nII (–) : {blood_level[5]}\nIII (–) : {blood_level[6]}\nIV (–) : {blood_level[7]}')
    # TODO: apply markup formatting to the text


def get_user_blood_type(self):
    #TODO: send the info about the user to MySQL
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


bot.polling()
