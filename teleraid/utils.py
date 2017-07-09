#!/usr/bin/python
# -*- coding: utf-8 -*-

import json


def get_pokemon_data(pokemon_id):
    if not hasattr(get_pokemon_data, 'pokemon'):
        file_path = "static/pokemon.json"

        with open(file_path, 'r') as f:
            get_pokemon_data.pokemon = json.loads(f.read())
    return get_pokemon_data.pokemon[str(pokemon_id)]


def get_pokemon_name(pokemon_id):
    return get_pokemon_data(pokemon_id)['name']


def get_moves_data(move_id):
    if not hasattr(get_moves_data, 'moves'):
        file_path = "static/moves.json"

        with open(file_path, 'r') as f:
            get_moves_data.moves = json.loads(f.read())
    return get_moves_data.moves[str(move_id)]


def get_move_name(move_id):
    return get_moves_data(move_id)['name']
