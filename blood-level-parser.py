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


# Parser and Database code ###########################
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

        return [item.string for item in self.parse_a_page().find_all(self.tag)]


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


class DataFrame:
    def convert_into_data_frame(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


# Performs the parsing and returns the results as a list
parser = Parser('http://kmck.kiev.ua/', 'h4')
parser.clear_html_tags()

# Part responsible for the communication with MySQL database
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


def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        t1 = time.time()
        func(*args, **kwargs)
        t2 = time.time()
        return print(t2 - t1, time.strftime('%H:%M, %d.%m'))

    return wrapper


class Notifier:

    def __init__(self, notify_date, notify_time, json_dict):
        self.date = notify_date
        self.time = notify_time
        self.user_table = json_dict
        self.lock = threading.Lock()

    def check_if_blood_is_low(self, user_id: str, json_dict: dict):
        """Checks if parsed blood level, that is corresponding to user's blood type is low"""

        blood_types = ['I(+)', 'II(+)', 'III(+)', 'IV(+)', 'I(-)', 'II(-)', 'III(-)', 'IV(-)']
        blood_levels = {key: value for key, value in
                        zip(blood_types, parser.clear_html_tags())}  # transforming two lists into a dict
        user_blood = f"{json_dict[user_id]['blood_type']}{json_dict[user_id]['blood_rh']}"
        if blood_levels[user_blood] != 'Достатньо':
            return True
        elif blood_levels[user_blood] == 'Достатньо':
            return False
        else:
            pass

    def check_if_scheduled_date_is_today(self, user_id, json_dict):
        """Checks if the scheduled notification date is today"""

        if json_dict[user_id]['notify_date'] == str(datetime.date.today()):
            return True
        else:
            return False

    def reschedule_notification(self, user_id: str, json_dict: dict, delay: int):
        """Reschedules the notification by a specified period of time (delay)"""

        self.lock.acquire()
        json_dict[user_id]['notify_date'] = str(datetime.date.today() + datetime.timedelta(days=delay))
        with open('user-table.json', 'w+') as json_file:
            json.dump(json_dict, json_file, indent=4)  # added indents make the json file more readable
        self.lock.release()
        print(f'Notification postponed by {delay} days')

    def notify_the_user(self, user_id):
        """Sends a notification each monday including the blood centre location"""

        keyboard = telebot.types.InlineKeyboardMarkup()
        dont_disturb_week = telebot.types.InlineKeyboardButton(text='Нагадай пізніше (Тиждень)',
                                                               callback_data='add_one_week')
        dont_disturb_two_months = telebot.types.InlineKeyboardButton(text='Щойно здав :) (Два місяці)',
                                                                     callback_data='add_two_months')
        keyboard.row(dont_disturb_week)
        keyboard.row(dont_disturb_two_months)
        emoji = u'\U0001F609'
        incentive_text = 'Не забувай: здача крові це 3 врятованих життя, ' \
                         f'довідка на 2 вихідних, і чай з печивком {emoji}'
        bot.send_message(user_id,
                         'Привіт! З моменту твоєї останньої донації пройшло більше двох місяців, '
                         'а у Київського Центру Крові закінчується '
                         f'{self.user_table[user_id]["blood_type"]} {self.user_table[user_id]["blood_rh"]}\n\n'
                         f'{incentive_text}',
                         reply_markup=keyboard)

    @measure_execution_time
    def decide_when_to_notify(self):
        """Compares the scheduled date with current one, notifies if blood is low and the date is right
        reschedules the notification if previous conditions are not met"""

        for cid in self.user_table.keys():
            if self.check_if_scheduled_date_is_today(cid, self.user_table):
                if self.check_if_blood_is_low(cid, self.user_table):
                    if time.strftime('%a') == self.date:
                        if time.strftime('%H') == self.time:
                            self.notify_the_user(cid)
                            self.reschedule_notification(cid, self.user_table, 7)
                        else:
                            pass
                    else:
                        self.reschedule_notification(cid, self.user_table, 1)
                else:
                    self.reschedule_notification(cid, self.user_table, 1)
            else:
                pass

    def infinite_update_loop(self, delay):
        try:
            schedule.every(delay).minutes.do(self.decide_when_to_notify)
            while 1:
                schedule.run_pending()
                time.sleep(300)
        except Exception as e:
            print(f'Error in the background thread: \n{e}')
            time.sleep(60)
            return background_processing()


def handle_unexpected_entry(chat_id):
    lock = threading.Lock()
    lock.acquire()
    user[str(chat_id)]['bot_stage'] = 0
    lock.release()

    back_to_start = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    back_to_start.add('/start')
    bot.send_message(chat_id, 'Натисни /start і вкажи свої дані знову',
                     reply_markup=back_to_start)


def send_dummy_bot_error(chat_id):
    bot.send_message(chat_id, 'Дурник-бот не зрозумів :( ')


def save_to_json_db(dictionary: dict):
    lock = threading.Lock()
    lock.acquire()
    with open('user-table.json', 'w+') as json_file:
        json.dump(dictionary, json_file, indent=4)
    lock.release()


def send_greeting_message(message):
    cid = message.chat.id
    blood_types_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    blood_types_keyboard.row('I - перша', 'II - друга')
    blood_types_keyboard.row('III - третя', 'IV - четверта')
    msg = bot.send_message(
        cid, 'Привіт! Готовий рятувати життя? \nВкажи свою групу крові: ', reply_markup=blood_types_keyboard)
    bot.register_next_step_handler(msg, ask_blood_rh)
    lock = threading.Lock()
    lock.acquire()
    user[str(cid)] = dict(blood_type=None,
                          blood_rh=None,
                          last_donated=None,
                          bot_stage=0,
                          notify_date=None)
    lock.release()

    # Displays the Telegram @username and f-l-names of the user, this info is not stored anywhere
    print(
        '*' * 10,
        f'@{message.chat.username} ',
        f'first logged in on {datetime.date.today()}',
        '*' * 10)


def calculate_last_donation_date(message):
    """Defines the date of last donation in datetime format"""

    cid = message.chat.id
    msg = message.text
    if msg == '2+ місяців тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=60))
        return str(last_donated_date)
    elif msg == 'Місяць тому':
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=30))
        return str(last_donated_date)
    elif msg == "Два тижні тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=14))
        return str(last_donated_date)
    elif msg == "Тиждень тому":
        last_donated_date = (datetime.date.today() - datetime.timedelta(days=7))
        return str(last_donated_date)
    else:
        return handle_unexpected_entry(cid)


def schedule_notification(last_donation_date: str) -> str:
    """Defines the notification date based on the date of last donation"""

    date_object = datetime.datetime.strptime(last_donation_date, '%Y-%m-%d')
    return str(date_object.date() + datetime.timedelta(days=60))


@bot.message_handler(commands=['help'])
def bot_info(message):
    """Shows all available commands when user types '/help' """
    rst = '/reset - повторно вказати свою групу крові'
    upd = '/update - перевірити запаси крові'
    itr = '/intervals - інтервали між кроводачами'
    inf = '/info - довідкова інформація'
    loc = '/location - місцезнаходження Банку Крові на карті'
    bot.send_message(message.chat.id, f'{rst}\n{upd}\n{itr}\n{loc}\n{inf}')


@bot.message_handler(commands=['info'])
def donor_info(message):
    """Sends a link to the Municipal Blood Centre for more information"""
    bot.send_message(message.chat.id, 'Більше інформації про процедуру та пункти здачі крові на kmck.kiev.ua')


@bot.message_handler(commands=['intervals'])
def donation_intervals_info(message):
    """Sends the information about the acceptable intervals between donations"""
    bot.send_message(message.chat.id,
                     'За даними donor.ua, оптимальним є інтервал 2-3 місяці між кровоздачами.\n\n'
                     'Бот сповіщуватиме тебе якщо: \n'
                     '1) з моменту останньої здачі пройшло мінімум 2 місяці'
                     '\n2) запас крові твоєї групи у Банку низький або критичний'
                     '\n3) якщо попередні умови задоволено - сповіщення прийде у найближчий Понеділок о 10:00\n\n'
                     'Отримавши сповіщення, ти можеш відкласти його на тиждень (кров не здав, нагадайте ще раз)'
                     ', або на два місяці (кров здав, до зустрічі через 2+ місяці)')


@bot.message_handler(commands=['location'])
def send_blood_bank_location(message):
    cid = message.chat.id
    bot.send_location(cid, 50.475870, 30.441694)


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


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'add_one_week':
        notifier.reschedule_notification(str(call.message.chat.id), user, 7)
        bot.send_message(call.message.chat.id, u'\U0001F44D')
        bot.send_message(call.message.chat.id, 'Відкладаю на тиждень')
    elif call.data == 'add_two_months':
        notifier.reschedule_notification(str(call.message.chat.id), user, 60)
        bot.send_message(call.message.chat.id, u'\U0001F44D')
        bot.send_message(call.message.chat.id, 'Відкладаю на два місяці')
    else:
        print('An error in call back handler has occurred')


@bot.message_handler(commands=['reset'])
def delete_user_id(message):
    """Resets the bot_stage info in the user dict and json db"""

    cid = message.chat.id
    return handle_unexpected_entry(cid)


@bot.message_handler(commands=['start'])
def welcome_message(message):
    """Displays available blood types and asks to choose one from the list"""

    cid = message.chat.id
    # TODO: check the bot_stage of the user
    # Implement a try/except statement, reverse the if/else conditions
    try:
        if user[str(cid)]['bot_stage'] == 3:
            bot.send_message(cid, 'Схоже, ти вже в базі користувачів.\n'
                                  'Дякую що допомагаєш рятувати життя!\n\n'
                                  'Якщо хочеш оновити дані про себе - тисни /reset')
        elif user[str(cid)]['bot_stage'] != 3:
            return send_greeting_message(message)
    except KeyError:
        return send_greeting_message(message)

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

        lock = threading.Lock()
        lock.acquire()
        user[str(cid)]['blood_type'] = str(message.text)
        user[str(cid)]['bot_stage'] = 1
        lock.release()
        print(f'Blood type: {message.text}')
    else:
        send_dummy_bot_error(cid)
        handle_unexpected_entry(cid)


def last_donated(message):
    """Asks when approximately the user last donated blood. Info is used for reminders"""

    cid = message.chat.id
    if message.text in {'(+)', '(-)'}:
        donation_dates_keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        donation_dates_keyboard.row("2+ місяців тому", "Місяць тому")
        donation_dates_keyboard.row("Два тижні тому", "Тиждень тому")
        msg = bot.send_message(cid,
                               'Коли приблизно ти востаннє здавав кров?\n'
                               'Від цього залежатиме коли ти отримаєш сповіщення',
                               reply_markup=donation_dates_keyboard)
        bot.register_next_step_handler(msg, thank_you_for_answers)

        lock = threading.Lock()
        lock.acquire()
        user[str(cid)]['blood_rh'] = str(message.text)
        user[str(cid)]['bot_stage'] = 2
        lock.release()
        print(f'Blood Rh: {message.text}')

    else:
        send_dummy_bot_error(cid)
        handle_unexpected_entry(cid)


def thank_you_for_answers(message):
    """Thanks for the information, shows a list of available commands, saves the answers locally to users-info.json"""

    cid = message.chat.id
    possible_dates = {"2+ місяців тому", "Місяць тому", "Два тижні тому", "Тиждень тому"}
    if message.text in possible_dates:
        emoji = u'\U0001F618'
        quest = 'Переглянути повний список функцій - тисни /help'
        keyboard_remove = telebot.types.ReplyKeyboardRemove(selective=True)
        bot.send_message(cid, 'All done!\nТепер я надсилатиму тобі сповіщення, '
                              f'якщо виникне необхідність у крові твоєї групи! {emoji}\n\n{quest}',
                         reply_markup=keyboard_remove)

        print(f'Last donated: {message.text}\n', '*' * 80)

        lock = threading.Lock()
        lock.acquire()
        user[str(cid)]['last_donated'] = calculate_last_donation_date(message)
        user[str(cid)]['notify_date'] = schedule_notification(user[str(cid)]['last_donated'])
        user[str(cid)]['bot_stage'] = 3
        save_to_json_db(user)
        lock.release()
    else:
        send_dummy_bot_error(cid)
        handle_unexpected_entry(cid)


# Turns on the notifications with specific parameters
notifier = Notifier('Mon', '10', user)


# Launches the infinite update loop scheduling and checking notification statuses in a separate thread
def background_processing():
    task1 = threading.Thread(target=notifier.infinite_update_loop, args=(10,))
    return task1.start()


background_processing()

# Hack ensuring that the bot will not crush when a connection error happens on Telegram's side
while 1:
    try:
        bot.polling(none_stop=True, interval=1.5)
    except Exception as e:
        print(f'Error in the polling process: \n{e}')
        time.sleep(5)
