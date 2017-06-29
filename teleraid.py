#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import Queue

from time import time
from datetime import datetime, timedelta
from copy import deepcopy
from threading import Thread
from gevent import monkey
from gevent import wsgi, spawn
from flask import Flask, request

from telepot import Bot as TelegramBot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

monkey.patch_all()


class WebhookException(Exception):
    pass


class RuntimeException(Exception):
    pass


class NotificationException(Exception):
    pass


class SendingException(Exception):
    pass


class TeleRaid:
    def __init__(self, queue):
        self.__raids = {}
        self.__queue = queue
        self.__bot_token = ''
        self.__target_chat_id = ''
        self.__client = TelegramBot(self.__bot_token)
        spawn(self.__run())

    def __process_request(self, data_json):
        if data_json['type'] == 'raid':
            self.__add_raid(data_json['message'])

    def __add_raid(self, raid):
        if raid['gym_id'] not in self.__raids:
            raid['notified_spawn'] = False
            raid['notified_battle'] = False
            raid['callbacks'] = []
            self.__raids[raid['gym_id']] = raid

    def __update_raids(self):
        updated_raids = deepcopy(self.__raids)
        for r in self.__raids:
            if self.__raids[r]['end'] < time():
                del updated_raids[r]

        self.__raids = updated_raids

    def __check_raids(self):
        raids_to_notify = {}
        for r in self.__raids:
            if (time() > self.__raids[r]['spawn'] and
                    not self.__raids[r]['notified_spawn']):
                raids_to_notify[r] = self.__raids[r]

            if (time() > self.__raids[r]['battle'] and
                    not self.__raids[r]['notified_battle']):
                raids_to_notify[r] = self.__raids[r]

        return raids_to_notify

    def __notify(self, raid):
        try:
            # Setup the message
            boss_level = raid['level']
            boss_hatches = (datetime.utcfromtimestamp(raid['battle']) +
                            timedelta(hours=2)).strftime("%H:%M")
            boss_start = (datetime.utcfromtimestamp(raid['battle']) +
                          timedelta(hours=2, minutes=30)).strftime("%H:%M")
            message = ('''
<b>Raid - Level {}</b>

<i>Raid Boss is yet unknown.</i>

Boss hatches at <b>{}.</b>

<i>Waiting for trainer.
Starting at 10 trainer or {} at latest.</i>
                        '''.format(boss_level, boss_hatches, boss_start))

            inline_keyboard = [
                [InlineKeyboardButton(text="\xF0\x9F\x91\x8D Yes",
                                      callback_data='y'),
                 InlineKeyboardButton(text="\xF0\x9F\x91\x8E No",
                                      callback_data='n')]
            ]
            keyboard_markup = InlineKeyboardMarkup(
                inline_keyboard=inline_keyboard)

            self.__location(self.__target_chat_id,
                            raid['latitude'],
                            raid['longitude'])
            self.__send(message,
                        self.__target_chat_id,
                        parse_mode="HTML",
                        reply_markup=keyboard_markup)

        except Exception as e:
            print "Exception during notification process: {}".format(repr(e))
            raise NotificationException("Failed while notifying.")

    def __send(self, message, chat_id, parse_mode=None, reply_markup=None):
        try:
            self.__client.sendMessage(chat_id=chat_id,
                                      text=message,
                                      parse_mode=parse_mode,
                                      reply_markup=reply_markup)
        except Exception as e:
            print "Exception while sending message: {}".format(repr(e))
            raise SendingException("Failed while sending message.")

    def __location(self, chat_id, latitude, longitude):
        try:
            self.__client.sendLocation(chat_id=chat_id,
                                       latitude=latitude,
                                       longitude=longitude)
        except Exception as e:
            print "Exception while sending location: {}".format(repr(e))
            raise SendingException("Failed while sending location.")

    def __run(self):
        print "TeleRaid is running..."
        while True:
            try:
                data_json = self.__queue.get(block=True)
                self.__process_request(data_json)
                self.__update_raids()
                raids_to_notify = self.__check_raids()
                for rtn in raids_to_notify:
                    self.__notify(raids_to_notify[rtn])
            except Exception as e:
                print "Exception during regular runtime: {}".format(repr(e))
                raise RuntimeException("Failed during runtime.")
            self.__queue.task_done()


app = Flask(__name__)
data_queue = Queue.Queue()


@app.route('/', methods=['POST'])
def accept_webhook():
    try:
        data = json.loads(request.data)
        data_queue.put(data)
    except Exception as e:
        print ("Encountered error while receiving webhook ({}: {})"
               .format(type(e).__name__, e))
        raise WebhookException("Exception while receiving webhook.")
    return "OK"  # request ok


print "TeleRaid starts."
try:
    t = Thread(target=TeleRaid, args=(data_queue,))
    t.daemon = True
    t.start()

    server = wsgi.WSGIServer(('127.0.0.1', 4000), app)
    server.serve_forever()
except KeyboardInterrupt:
    pass
print "TeleRaid ended."
