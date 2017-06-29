# TeleRaid
a RocketMap extension.

## What is this?
TeleRaid focuses on receiving webhook data from RocketMap to display upcoming Raids in a Telegram Channel to notify its Users and let them vote for attendence.

## How to install?
```bash
git clone https://github.com/Arengo/TeleRaid.git & cd TeleRaid
pip install requirements.txt
```

## How to use?
1. Put your Telegram ``Bot-ID`` as well as the ``Chat-ID`` you want to send notifications to, into the ``config.example.py`` file by replacing the placeholders ``#Placeholder#``.
2. Rename ``config.example.py`` to ``config.py``.
3. Specify a webhook address to listen to into ``config.example.py``, default is ``127.0.0.1:4001``.
4. Setup RocketMap with raid support to send webhooks to above's address.
5. Run the bot with
```bash
python teleraid.py
```

Have fun :-)
