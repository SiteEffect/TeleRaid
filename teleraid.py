#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import Queue

from time import sleep
from datetime import datetime, timedelta
from copy import deepcopy
from threading import Thread
from gevent import monkey
from gevent import wsgi, spawn
from flask import Flask, request
from telepot import Bot as TelegramBot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from utils import get_pokemon_name, get_move_name
from static.stickers import stickers

monkey.patch_all()


class WebhookException(Exception):
    pass


class RuntimeException(Exception):
    pass


class NotificationException(Exception):
    pass


class SendingException(Exception):
    pass


class UpdateException(Exception):
    pass


class DeleteException(Exception):
    pass


class TeleRaid:
    def __init__(self, queue):
        self.__bot_token = config['bot_token']
        self.__chat_id = config['chat_id']
        self.__client = TelegramBot(self.__bot_token)

        self.__notify_levels = config['notify_levels']
        self.__notify_pokemon = config['notify_pokemon']

        self.__queue = queue
        self.__raids = {}
        self.__messages = {}

        spawn(self.__run())

    def __run(self):
        print "TeleRaid is running..."
        t1 = Thread(target=self.__update_messages, args=())
        t1.daemon = True
        t1.start()
        while True:
            try:
                data_json = self.__queue.get(block=True)
                self.__process_request(data_json)
                self.__update_raids()
                raids_to_notify = self.__check_raids()
                for raid in raids_to_notify:
                    self.__notify(raid)
            except Exception as e:
                print "Exception during regular runtime: {}".format(repr(e))
                raise RuntimeException("Failed during runtime.")
            self.__queue.task_done()

    def __process_request(self, data_json):
        if data_json['type'] == 'raid':
            print "Raid received."
            self.__add_raid(data_json['message'])

    def __add_raid(self, raid):
        if raid['gym_id'] not in self.__raids:
            raid['notified_battle'] = False
            self.__raids[raid['gym_id']] = raid
            print "Raid added."

    def __update_raids(self):
        updated_raids = deepcopy(self.__raids)
        for r in self.__raids:
            if (datetime.utcnow() > datetime.utcfromtimestamp(
                    self.__raids[r]['end'])):
                del updated_raids[r]
                for m in self.__messages:
                    if r == self.__messages[m].get('gym_id', ''):
                        self.__delete_message(chat_id=self.__chat_id,
                                              message_id=m)
                        del self.__messages[m]

        self.__raids = updated_raids
        print "Raids updated."

    def __check_raids(self):
        raids_to_notify = []
        for r in self.__raids:
            if self.__raids[r]['level'] not in self.__notify_levels:
                continue

            if self.__raids[r]['pokemon_id'] not in self.__notify_pokemon:
                continue

            if (datetime.utcnow() > datetime.utcfromtimestamp(
                    self.__raids[r]['start'])):
                if not self.__raids[r]['notified_battle']:
                    print ("Notifying about raid with Pokemon-ID {}."
                           .format(self.__raids[r]['pokemon_id']))
                    raids_to_notify.append(self.__raids[r])
                else:
                    print ("Already notified about raid of Pokemon-ID {}."
                           .format(self.__raids[r]['pokemon_id']))

        print "Raids checked."
        return raids_to_notify

    def __notify(self, raid):
        try:
            # Setup the message
            raid_end = (datetime.utcfromtimestamp(raid['end']) +
                        timedelta(hours=2)).strftime("%H:%M")
            raid_fight = (datetime.utcfromtimestamp(raid['end']) +
                          timedelta(hours=2, minutes=30)).strftime("%H:%M")
            raid_pokemon = get_pokemon_name(raid['pokemon_id'])
            raid_move_1 = get_move_name(raid['move_1'])
            raid_move_2 = get_move_name(raid['move_2'])
            text = (
                       '''
<b>Raid - Level {} - {}</b>
{} / {}
Raid ends at <b>{}</b>.

<i>Waiting for trainer.</i>
<i>Starting at 10 trainer or {} at latest.</i>'''
                       .format(raid['level'], raid_pokemon,
                               raid_move_1, raid_move_2,
                               raid_end, raid_fight))
            inline_keyboard = [[
                InlineKeyboardButton(text="\xF0\x9F\x91\x8D Yes",
                                     callback_data='y'),
                InlineKeyboardButton(text="\xF0\x9F\x91\x8E No",
                                     callback_data='n')
            ]]
            keyboard_markup = InlineKeyboardMarkup(
                inline_keyboard=inline_keyboard)

            self.__send_sticker(chat_id=self.__chat_id,
                                sticker=stickers[raid['pokemon_id']])

            self.__send_location(chat_id=self.__chat_id,
                                 latitude=raid['latitude'],
                                 longitude=raid['longitude'])

            # Keyboard response is not working, yet.
            message = self.__send_message(text=text,
                                          chat_id=self.__chat_id,
                                          parse_mode="HTML",
                                          reply_markup=keyboard_markup)
            self.__messages[message['message_id']] = {
                'gym_id': raid['gym_id'],
                'text': message['text'],
                'poll': {
                    'yes': 0,
                    'no': 0,
                    'users': {}
                }
            }
            raid['notified_battle'] = True
        except Exception as e:
            print "Exception during notification process: {}".format(repr(e))
            raise NotificationException("Failed while notifying.")

    def __update_messages(self):
        offset = None
        while True:
            try:
                updates = self.__client.getUpdates(offset=offset)
                updated_messages = []
                for u in updates:
                    callback_query = u.get('callback_query', {})
                    data = callback_query.get('data', None)
                    message = callback_query.get('message', {})
                    message_id = message.get('message_id', 0)
                    if message_id:
                        updated_messages.append(message_id)
                        if message_id not in self.__messages:
                            self.__messages[message_id] = {
                                'gym_id': '',
                                'text': message['text'],
                                'poll': {
                                    'yes': 0,
                                    'no': 0,
                                    'users': {}
                                }
                            }

                        self.__messages[message_id]['poll']['users'].update({
                            callback_query['from']['id']: data
                        })

                    update_id = u.get('update_id', None)
                    if update_id and update_id >= offset:
                        offset = update_id + 1

                for message_id in updated_messages:
                    poll = self.__messages[message_id]['poll']
                    poll['yes'] = 0
                    poll['no'] = 0

                    for user in poll['users']:
                        if poll['users'][user] == 'y':
                            poll['yes'] += 1
                        elif poll['users'][user] == 'n':
                            poll['no'] += 1

                    if poll['yes'] or poll['no']:
                        inline_keyboard = [[
                            InlineKeyboardButton(
                                text=("\xF0\x9F\x91\x8D Yes ({})"
                                      .format(poll['yes'])),
                                callback_data='y'),
                            InlineKeyboardButton(
                                text=("\xF0\x9F\x91\x8E No ({})"
                                      .format(poll['no'])),
                                callback_data='n')
                        ]]
                        keyboard_markup = InlineKeyboardMarkup(
                            inline_keyboard=inline_keyboard)
                        message = self.__edit_message_reply_markup(
                            msg_identifier=(self.__chat_id, message_id),
                            reply_markup=keyboard_markup
                        )
            except Exception as e:
                print "Exception while updating messages: {}".format(repr(e))
                pass
            finally:
                sleep(1)

    def __send_message(self, text, chat_id,
                       parse_mode=None, reply_markup=None):
        try:
            return self.__client.sendMessage(chat_id=chat_id,
                                             text=text,
                                             parse_mode=parse_mode,
                                             reply_markup=reply_markup)
        except Exception as e:
            print "Exception while sending message: {}".format(repr(e))
            raise SendingException("Failed while sending message.")

    def __send_location(self, chat_id, latitude, longitude):
        try:
            return self.__client.sendLocation(chat_id=chat_id,
                                              latitude=latitude,
                                              longitude=longitude)
        except Exception as e:
            print "Exception while sending location: {}".format(repr(e))
            raise SendingException("Failed while sending location.")

    def __send_sticker(self, chat_id, sticker):
        try:
            return self.__client.sendSticker(chat_id=chat_id,
                                             sticker=sticker)
        except Exception as e:
            print "Exception while sending sticker: {}".format(repr(e))
            raise SendingException("Failed while sending sticker.")

    def __edit_message_reply_markup(self, msg_identifier, reply_markup):
        try:
            return self.__client.editMessageReplyMarkup(
                msg_identifier=msg_identifier,
                reply_markup=reply_markup
            )
        except Exception as e:
            print "Exception while editing keyboard markup: {}".format(repr(e))
            raise UpdateException("Failed while updating keyboard markup.")

    def __delete_message(self, chat_id, message_id):
        try:
            return self.__client.deleteMessage(chat_id=chat_id,
                                               message_id=message_id)
        except Exception as e:
            print "Exception while deleting message: {}".format(repr(e))
            raise DeleteException("Failed while deleting message.")


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

    server = wsgi.WSGIServer((config['host'], config['port']), app)
    server.serve_forever()
except KeyboardInterrupt:
    pass
print "TeleRaid ended."
