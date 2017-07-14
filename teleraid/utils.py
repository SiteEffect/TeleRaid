#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

from config.config import config


def telepot_shiny(message):
    text = message.get('text', '')
    entities = message.get('entities', [])

    shinies = {
        'bold': ('<b>', '</b>'),
        'italic': ('<i>', '</i>')
    }

    add_off = 0
    for e in entities:
        if e['type'] in shinies:
            text = (text[:add_off + e['offset']] +
                    shinies[e['type']][0] +
                    text[add_off+e['offset']:])
            add_off += len(shinies[e['type']][0])

            text = (text[:add_off+e['offset']+e['length']] +
                    shinies[e['type']][1] +
                    text[add_off+e['offset']+e['length']:])
            add_off += len(shinies[e['type']][1])
    return text


def i18n(word):
    locale = config.get('locale', 'en')
    if locale == "en":
        return word

    if not hasattr(i18n, 'dictionary'):
        file_path = 'static/locales/{}.json'.format(locale)
        with open(file_path, 'r') as f:
            i18n.dictionary = json.loads(f.read())

    if word in i18n.dictionary:
        return i18n.dictionary[word]
    else:
        return word


def get_pokemon_data(pokemon_id):
    if not hasattr(get_pokemon_data, 'pokemon'):
        file_path = "static/pokemon.json"
        with open(file_path, 'r') as f:
            get_pokemon_data.pokemon = json.loads(f.read())

    return get_pokemon_data.pokemon[str(pokemon_id)]


def get_pokemon_name(pokemon_id):
    return i18n(get_pokemon_data(pokemon_id)['name']).encode('utf-8')


# Needs i18n support
def get_moves_data(move_id):
    if not hasattr(get_moves_data, 'en'):
        file_path = "static/moves_{}.json".format(config.get('locale', 'en'))
        with open(file_path, 'r') as f:
            get_moves_data.moves = json.loads(f.read())

    return get_moves_data.moves[str(move_id)]


def get_move_name(move_id):
    return get_moves_data(move_id)['name'].encode('utf-8')
