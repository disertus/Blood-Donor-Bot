import requests


class Parser:
    """Parses the page and saves the data that has been collected into the mysqldb"""

    def __init__(self, url, db_credentials):
        self.page_url = url
        self.mysql_credentials = db_credentials

    def parse_the_page(self) -> dict:
        # TODO: look up the model used in covid parser and collect the data into a dict
        pass

    def save_to_mysqldb(self):
        # TODO: use the same approach as in covid, but with string concatenation, hide db credentials
        pass


class DataFrame:
    def convert_to_dataframe(self):
        # TODO: read the data from the mysqldb / or just use the latest collected data
        pass


class TelegramBot:

    def start_message(self):
        pass

    def check_users_blood_type(self):
        pass

    def check_blood_availability(self):
        pass

    def notify_if_blood_is_low(self):
        pass