from bs4 import BeautifulSoup
from functools import lru_cache
import cfg
import requests


class Parser:
    """Parses the page and saves the data that has been collected into the mysqldb"""

    def __init__(self, url: str, db_credentials: tuple):
        self.page_url = url
        self.mysql_credentials = db_credentials

    @lru_cache(maxsize=128)
    def parse_the_page(self):
        page_headers = {
            'User-Agent' :
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/81.0.4044.138 Chrome/81.0.4044.138 Safari/537.36"
        } # headers are necessary to emulate a 'live user' connection
        open_url = requests.get(self.page_url, headers=page_headers).text
        soup = BeautifulSoup(open_url, 'lxml')
        return soup

    def clear_html_tags(self, tag: str) -> list:
        # Search inside <div class="vc_row wpb_row vc_inner vc_row-fluid">
        # Two separate columns have similar structure - data can be collected through indexing of elements
        parsed_tag = [item.string for item in self.parse_the_page().find_all(tag)]
        return parsed_tag

    def save_to_mysqldb(self):
        # TODO: use the same approach as in covid, but with string concatenation, hide db credentials inside cfg module
        pass


class DataFrame:
    def convert_to_dataframe(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


class TelegramBot:

    def __init__(self):
        # Link to the newly-generated bot: t.me/donor_notify_bot
        self.telegram_bot_token = cfg.token

    def start_message(self):
        pass

    def get_user_blood_type(self):
        pass

    def get_user_name(self):
        # TODO: Optional, users may be unwilling to give up personal information
        pass

    def get_user_location(self):
        # TODO: Optional, users may be unwilling to give up personal information
        pass

    def check_blood_availability(self):
        pass

    def notify_if_blood_is_low(self):
        notification_text = f'{bloodtype} is low - we need YOU to save lives'
        incentive_text = 'Short reminder: Blood donation will give you 2 days off and a financial remuneration'
        pass


parser = Parser('http://kmck.kiev.ua/', None).clear_html_tags()