#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import config
import datetime
import requests
from bs4 import BeautifulSoup
from config import username, password, api_key, payment_method

# взаимодействие реализовано по HTTP - притворяемся браузер-клиентом
# возможна реализация через SOAP: http://www.drebedengi.ru/soap/dd.wsdl

http_login_url = "https://www.drebedengi.ru/?module=v2_start&action=login"
http_csv_send_url = "https://www.drebedengi.ru/?module=v2_homeBuhPrivateImport&action=csv_submit"
http_csv_confirm_url = "https://www.drebedengi.ru/?module=v2_homeBuhPrivateImport&action=confirm"
http_search_url = "https://www.drebedengi.ru/?module=v2_homeBuhPrivateReport"
http_delete_item_url = "https://www.drebedengi.ru/?module=v2_homeBuhPrivateTextReportMain"

class Drebedengi:
    session = None
    categories = []


    def __init__(self, user, password):
        session = requests.Session()

        data = {
            "o": "",
            "email": user,
            "password": password,
            "ssl": "on"
        }

        login = session.post(http_login_url, data)
        soup = BeautifulSoup(login.content, 'html.parser')
        categories = [option.text.encode(
            'utf-8') for option in soup.find(id="add_w_category_id").find_all("option")]

        self.categories = categories[1:]
        self.session = session


    def logged_in(self):
        return self.session != None


    def get_categories(self):
        return self.categories


    def send_csv(self, filename):
        data = {
            'imp_fmt': 'imp_in_fmt',
            'csvFile': (filename,
                        open(filename, 'rb'),
                        'text/csv')

        }
        r = self.session.post(http_csv_send_url, files=data)
        post1 = r.status_code
        r = self.session.post(http_csv_confirm_url)
        post2 = r.status_code

        if post1 == 200 and post2 == 200:       # TODO: improve error checking by page content 
            print("Successfully imported!")
            return True
        else:
            print("Something went wrong...")
            return False


    def delete_item(self, id):
        payload = {
            'action': 'delete_item',
            'wasteId': id,
            'is_report': '1',
            'pref': 'waste'
        }
        r = self.session.post(http_delete_item_url, data=payload)
        if r.status_code == 200:
            print("Old SMS item successfully removed!")


    def search(self, date, sum):
        date = date.split()[0]

        payload = {
            'r_what': '3',
            'r_how': '1',
            'r_period': '0',
            'r_who': '0',
            'period_to': date,
            'period_from': date,
            'r_middle': '0',
            'r_is_place': '0',
            'r_is_category': '0',
            'r_currency': '0',
            'r_search_comment': '',
            'r_is_tag': '0',
            'is_cat_childs': 'true',
            'is_with_rest': 'false',
            'is_with_planned': 'false',
            'is_course_hist': 'false',
            'r_duty': '0',
            'r_sum': '1',
            'r_sum_from': sum,
            'r_sum_to': '',
            'r_place[]': '0',
            'r_category[]': '0',
            'r_tag[]': '0',
            'action': 'show_report',
        }

        request = self.session.post(http_search_url, data=payload)
        soup = BeautifulSoup(request.content, 'html.parser')

        # remove totally sum of results from html
        total_sum_tag = soup.find("div", text="Итого")

        if total_sum_tag is None:
            return None
        else:
            total_sum_tag.next_sibling.next_sibling.decompose()
        
        sum_blocks = soup.find_all("span", class_="red")
        
        for sum_block in sum_blocks:
            if sum_block.text == "-"+str(sum):
                print("SMS with the receipt was found, it will be deleted after import")

                parent_tag = sum_block.parent.parent.parent
                desc_tag = parent_tag.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling
                id_tag = parent_tag.previous_sibling.previous_sibling
                
                item_text = desc_tag.text
                item_id = id_tag.get('id').split('_')[1]

                method = payment_method["default"]

                for substr in payment_method['sms_based']:      # TODO: additional detecting by payment method of item (if SMS text was not saved) 
                    if item_text.find(substr) != -1:
                        method = payment_method['sms_based'][substr]
                        print("Detected payment method by SMS text: "+method)

                return {
                    "payment_method": method,
                    "id": item_id
                }