"""
A text-based adventure game by Josh Lock.
A puzzle.
"""

import json
import textwrap
import time


class Thing:

    def __init__(self, thing_id, name, short_names, descriptions):
        # todo: test for id duplication
        # if (id duplicated):
        #     raise ValueError("Sorry, ID '%s' already exists." % id)
        self.thing_id = thing_id
        self.name = name
        self.short_names = short_names
        self.descriptions = descriptions

    def __str__(self):
        return "{} (AKA \"{}\")".format(self.name, '\" or \"'.join(self.short_names))

    def description(self, aspect, time_index):
        """ Returns room description for an aspect and a time index

        :param aspect. E.g., 'looks', 'sounds', or 'feels'
        :param time_index. E.g., 0 for first time
        :return: string
        """
        if aspect in ['looks', 'sounds', 'feels']:
            return self.descriptions[aspect][time_index]


class Room(Thing):

    def __init__(
            self, thing_id, name, short_names, descriptions, verbables, fixtures=None):
        """
        :param thing_id: string, e.g.: 'rm_0109' for a room
        :param name: string, e.g.: 'a long corridor'
        :param short_names: list, e.g.: ['study', 'office']
        :param descriptions: dict (keys: 'looks', 'sounds', 'feels') of lists (list index as a time index)
        :param verbables: dict with keys: 'as_x', 'as_y'
        """
        super().__init__(thing_id, name, short_names, descriptions)
        self.verbables = verbables
        self.fixtures = fixtures

        # can't store tuple in json, hence convert thing_id to coords tuple
        try:
            self.coords = (int(thing_id[3:5]), int(thing_id[5:7]))
        except:
            msg = "Couldn't create room '%s'. Thing_id not in format 'rm_####'." % thing_id
            raise Exception(msg)

class Player:

    go_prepositions = (
        'beside', 'near', 'to', 'under', 'underneath', 'over', 'around', 'onto', 'on', 'in', 'into', 'through'
    )
    directions = ('n', 'north', 'e', 'east', 's', 'south', 'w', 'west')

    def __init__(self, game):
        name = ""
        while not name.isalpha():
            name = input("Please enter the player's name:").strip()
        self.name = name.title()
        print("Welcome, {}.".format(self.name))
        self.room = None
        self.game = game

    def __str__(self):
        return self.name

    def neighbour_room(self, direction):
        coord_delta_map = {'n': (-1,0), 'e': (0,1), 's': (1,0), 'w': (0,-1)}
        coord_delta = coord_delta_map.get(direction, None)
        if coord_delta is None:
            raise Exception('Unknown direction, \"%s\"' % direction)

        # target coords = current room coords + coords delta
        target_coords = tuple([sum(x) for x in zip(coord_delta, self.room.coords)])
        return self.game.get_room(target_coords)

    def look(self, words=None):
        # survey room
        description = self.in_room.description('looks', 0)  # todo: increment time_index
        for line in textwrap.wrap(description):
            print(line)

    def go(self, words=None):
        unknown = False
        if words is None:
            unknown = True
        else:
            next_word = words.pop()
            if next_word in self.directions:  # e.g. go west
                self.go_direction(next_word)
            elif next_word in self.go_prepositions:  # e.g. go to X
                print("You go %s" % words[0])  #TODO
            else:
                unknown = True
        if unknown:
            print("Sorry, go where?")

    def go_direction(self, direction):
        print("You go %s." % direction)  # TODO

        # 1. room exist in target direction?
        target_room = self.neighbour_room(direction)
        print(target_room.coords)  # WASHERE

        # 2. no room: report error

        # 3. room: portal between?

        # 4. no portal: go into room

        # 5. portal: portal open?

        # 6. portal open: go

        # 7. portal not open: go to portal, report portal closed

    def move(self, words=None):
        print("You move x to y.")  #TODO

    def get(self, words=None):
        print("You get x.")  #TODO

    def drop(self, words=None):
        print("You drop x.")  #TODO

    def listen(self, words=None):
        print("You listen (or listen to x).")  #TODO

    command_map = {
        "look": look, "examine": look, "study": look, "survey": look,
        "go": go, "head": go, "walk": go, "run": go, "jog": go, "crawl": go,
        "move": move, "shift": move,
        "get": get,
        "drop": drop, "release": drop,
        "listen": listen, "hear": listen
    }

    def command_parse(self, command_phrase):
        command_words = command_phrase.split()
        word1 = command_words.pop(0)
        verb = self.command_map.get(word1, None)
        if verb is None:
            print("Sorry, you don't know how to \"{}\" here.".format(word1))
            return None
        else:
            if command_words==[]: command_words = None
            verb(self, command_words)
            return word1


class Portal(Thing):

    def __init__(self, thing_id, name, short_names, descriptions, room1_thing_id, room2_thing_id, state):
        super().__init__(thing_id, name, short_names, descriptions)
        self.room1 = room1_thing_id  # convention: room1 is n or e of room2
        self.room2 = room2_thing_id
        self.state = state  # e.g. 'open', 'closed', 'ajar', 'locked', 'unlocked'


class Game:

    def __init__(self):
        self.rooms = {}  # dict of rooms: {thing_id: room, ...}
        self.portals = {}  # dict of portals: (thing_id: portal, ...}
        self.player = None

    def get_room(self, room_key):
        """Gets room object based on room key (coords tuple)

        :param key: room coords tuple, e.g. (1,2)
        :return: room object
        """
        ret = self.rooms.get(room_key, None)
        if ret is None:
            raise Exception('No room found for room_key %s.' % str(room_key))
        else:
            return ret

    def setup(self):

        # set up rooms
        filename='rooms'
        filename += ('' if filename.endswith('.json') else '.json')
        with open(filename, 'r') as f:
            json_s = f.read()
            json_d = json.loads(json_s)
            for room_tuple in json_d.items():  # room as tuple: (thing_id, {...}) | (json can't do tuples)
                new_room = Room(**room_tuple[1])
                self.rooms[new_room.coords] = new_room  # room keys are coords tuples, e.g. (1,2) for rm_0102

        # set up portals
        filename='portals'
        filename += ('' if filename.endswith('.json') else '.json')
        with open(filename, 'r') as f:
            json_s = f.read()
            json_d = json.loads(json_s)
            for portal_tuple in json_d.items():  # portal as tuple: (thing_id, {...})
                new_portal = Portal(**portal_tuple[1])
                self.portals[portal_tuple[0]] = new_portal  # portal[0] is thing_id

        # initialise player and starting location
        self.player = Player(self)
        self.player.room = self.get_room((3,7))  # initial room is rm_0307

    def run(self):
        player = self.player

        while True:
            inp = input("What's next?:").lower()
            if inp in ('q', 'quit', 'exit', 'leave', 'stop', 'end'):
                print("Thanks for playing. Bye.")
                break
            player.command_parse(inp)

class Session:

    def __init__(self):
        self.start_time = time.time()
        self.game = Game()

    def time_passed(self):
        return time.time() - self.start_time


# ********************************* MAIN SCRIPT ********************************

session = Session()
session.game.setup()
session.game.run()

# ******************************************************************************
