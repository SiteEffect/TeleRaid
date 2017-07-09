#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import Queue
import logging

from threading import Thread
from gevent import monkey
from gevent import wsgi
from flask import Flask, request

# Custom files and packages
from config.config import config
from teleraid.teleraid import TeleRaid


monkey.patch_all()
logging.basicConfig(
    format='%(asctime)s [%(threadName)18s][%(module)14s][%(levelname)8s] ' +
    '%(message)s')
log = logging.getLogger()
if config.get('debug', False):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

app = Flask(__name__)
data_queue = Queue.Queue()


@app.route('/', methods=['POST'])
def accept_webhook():
    try:
        data = json.loads(request.data)
        data_queue.put(data)
    except Exception as e:
        log.exception("Encountered error while receiving webhook ({}: {})"
                      .format(type(e).__name__, e))
        pass

    return "OK"  # request ok


log.info("TeleRaid starts.")
try:
    t = Thread(target=TeleRaid, name='TeleRaid', args=(data_queue,))
    t.daemon = True
    t.start()

    server = wsgi.WSGIServer((config['host'], config['port']), app)
    server.serve_forever()
except KeyboardInterrupt:
    pass
log.info("TeleRaid ended.")
