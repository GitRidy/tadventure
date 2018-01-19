"""
A text-based adventure game by Josh Lock.
A puzzle.
"""

import json
import textwrap
import time
import random


def get_json_dict(filename):
    filename += ('' if filename.endswith('.json') else '.json')
    with open(filename, 'r') as f:
        json_string = f.read()
        json_dict = json.loads(json_string)
    return json_dict


class Session:  # really just to hold variables for global access

    game = None
    player = None
    directions_map = {
        'north': 'north', 'n': 'north',
        'east': 'east', 'e': 'east',
        'south': 'south', 's': 'south',
        'west': 'west', 'w': 'west'}
    go_prepositions_map = {
        'to': 'to', 'beside': 'to', 'near': 'to',
        'under': 'under', 'underneath': 'under',
        'over': 'over',
        'around': 'around',
        'on': 'on', 'onto': 'on',
        'in': 'in', 'into': 'in',
        'through': 'through'}


session = Session()


class Thing:
    # for all game things: rooms, portals, fixtures, furniture, items

    def __init__(self, thing_id, name, short_names, descriptions):
        # todo: test for id duplication
        # if (id duplicated):
        #     raise ValueError("Sorry, ID '{}' already exists.".format(id))
        self.thing_id = thing_id
        self.name = name
        self.short_names = short_names
        self.descriptions = descriptions
        self.relations = {}  # populated later by game.setup. Format example: {'on': (thing), ...}
        # add this object to things list
        session.game.things[thing_id] = self

    def __str__(self):
        return "{} (AKA \"{}\")".format(self.name, '\" or \"'.join(self.short_names))

    def look(self, preposition=''):
        if (preposition == 'at') or (preposition == ''):
            msg = self.description('looks', 0)  # TODO: increment time_index
            for line in textwrap.wrap(msg):
                print(line)
            # list things in 'by', 'with', 'under', 'on' relations with self
            # TODO
        elif preposition in ('in', 'into', 'inside'):
            pass  # TODO
            # check relations['in'][self] for items
            # if any, print 'In the {self.name} you see: {item names}'


    def description(self, aspect, time_index):
        """ Returns room description for an aspect and a time index

        :param aspect. E.g., 'looks', 'sounds', or 'feels'
        :param time_index. E.g., 0 for first time
        :return: string
        """
        if aspect in ('looks', 'sounds', 'feels'):
            return self.descriptions[aspect][time_index]


class Room(Thing):

    @staticmethod
    def to_thing_id(coords):
        try:
            ret = 'rm_' + '{:02d}{:02d}'.format(coords[0], coords[1])
        except:
            raise Exception('coords must be a tuple pair of integers, but {} was given.'.format(coords))
        return ret

    @staticmethod
    def to_coords(thing_id):
        try:
            # convert thing_id to coords tuple
            ret = (int(thing_id[3:5]), int(thing_id[5:7]))
        except:
            raise Exception('thing_id must be in format \"rm_####\", but {} was given.'.format(thing_id))
        return ret

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

        # can't store tuple in json, so store thing_id as string in json and convert to coords tuple here:
        try:
            self.coords = self.to_coords(thing_id)
        except:
            msg = "Couldn't create room '{}'. Thing_id not in format 'rm_####'.".format(thing_id)
            raise Exception(msg)

    def get_portal(self, target_room):
        # loop through portals searching for both this room and target_room
        found_portal = None
        for portal in session.game.portals.values():
            p1 = portal.room1_coords
            p2 = portal.room2_coords
            slf = self.coords
            tgt = target_room.coords
            if (p1==slf and p2==tgt) or (p1==tgt and p2==slf):
                found_portal = portal
                break
        return found_portal

class Player:

    def __init__(self):
        name = ""
        while not name.isalpha():
            name = input("Please enter the player's name:").strip()
        self.name = name.title()
        print("Welcome, {}.".format(self.name))
        self.room = None

    def __str__(self):
        return self.name

    def neighbour_room(self, direction):
        coord_delta_map = {'north': (-1,0), 'east': (0,1), 'south': (1,0), 'west': (0,-1)}
        coord_delta = coord_delta_map.get(direction, None)
        if coord_delta is None:
            raise Exception('Unknown direction, \"{}\"'.format(direction))

        # target coords = current room coords + coords delta
        target_coords = tuple([sum(x) for x in zip(coord_delta, self.room.coords)])
        return session.game.get_room(target_coords)

    def look(self, words=None):
        self.room.look()

    def go(self, words=None):
        unknown = False
        if words is None:
            unknown = True
        else:
            next_word = words.pop()
            if next_word in session.directions_map.keys():  # e.g. go west
                self.go_direction(next_word)
            elif next_word in session.go_prepositions_map.keys():  # e.g. go to X
                print("You go {}.".format(words[0]))  #TODO
            else:
                unknown = True
        if unknown:
            print("Sorry, go where?")

    def change_location(self, destination):
        dest_type = type(destination).__name__
        # if destination is a room
        if dest_type == 'Room':
            print('change_location to room ' + destination.name)
            # del relations betwen player and things in room
            # set player location to destination room
            self.room = destination
            # report room description
            self.room.look()

        elif dest_type == 'Portal':
            print('change_location to portal ' + destination.name)
        # if destination is a portal
            # del relations between player and any things in room (except those with player)
            # add 'by' relation between player and portal
            # report portal state
        elif dest_type == 'Thing':
            print('change_location to thing ' + destination.name)
        # if destination is a thing (except a room)
            # del relations between player and any things in room not by destination thing
            # add 'by' relation between player and thing
            # report new relation

    def go_direction(self, direction):
        direction = session.directions_map[direction]
        print('You go {}.'.format(direction))
        try:
            # 1. does a room exist in the target direction?
            target_room = self.neighbour_room(direction)
        except:
            # 2. no room exists: report error
            msg_list = [
                "Sorry, there is not another room in that direction.",
                "Woops, you bump into a wall. Ouch!",
                "Sorry, it's just a wall there.",
                "Sorry, you can't go in that direction. It's blocked by a rather stubborn wall.",
                "Not possible, sorry. There's a wall in the way."
            ]
            msg = random.choice(msg_list)
            print(msg)
            return

        # 3. room exists: is there a portal between?
        portal = self.room.get_portal(target_room)
        if portal is None:
            # 4. no portal: go into room
            self.change_location(target_room)
        else:
            # 5. portal: portal open?
            if portal.state == "open":
                # 6. portal open: go
                self.change_location(target_room)
            else:
                # 7. portal not open: go to portal
                self.change_location(portal)

    def move(self, words=None):
        print("You move x to y.")  #TODO

    def get(self, words=None):
        print("You get x.")  #TODO

    def drop(self, words=None):
        print("You drop x.")  #TODO

    def listen(self, words=None):
        print("You listen (or listen to x).")  #TODO

    command_map = {
        "look": look, "examine": look, "study": look, "survey": look, "inspect": look,
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
            if not command_words:
                command_words = None
            verb(self, command_words)
            return word1


class Portal(Thing):

    def __init__(self, thing_id, name, short_names, descriptions, room1_thing_id, room2_thing_id, state):
        super().__init__(thing_id, name, short_names, descriptions)
        # NOTE: convention: room1 is n or e of room2
        self.room1_coords = Room.to_coords(room1_thing_id)
        self.room2_coords = Room.to_coords(room2_thing_id)
        self.room1 = None  # Game.setup populates this
        self.room2 = None  # Game.setup populates this
        self.state = state  # e.g. 'open', 'closed', 'locked'


class Game:

    def __init__(self):
        self.start_time = time.time()
        self.rooms = {}  # dict of rooms: {coords tuple: room, ...}
        self.portals = {}  # dict of portals: (thing_id: portal, ...}
        self.relations = {}  # dict of relations: {'in': {(room): [objects...]}, 'has': {...}
        self.things = {} # dict of all things for lookups: {'thing_id': (object), ...}

    def get_room(self, room_coords):
        """Gets room object based on room key (coords tuple)

        :param room_coords: room coords tuple, e.g. (1,2)
        :return: room object
        """
        ret = self.rooms.get(room_coords, None)
        if ret is None:
            raise Exception('No room found for room_key {}.'.format(str(room_coords)))
        else:
            return ret

    def setup(self, initial_room):

        # create objects from json files...
        # ...set up rooms
        json_dict = get_json_dict('rooms')
        for room_tuple in json_dict.items():  # room as tuple: (thing_id, {...room dict...})
            new_room = Room(**room_tuple[1])
            self.rooms[new_room.coords] = new_room  # room keys are coords tuples, e.g. (1,2) for rm_0102

        # ...set up portals
        json_dict = get_json_dict('portals')
        for portal_tuple in json_dict.items():  # portal as tuple: (thing_id, {... portal dict...})
            # create new portal with portal dict
            new_portal = Portal(**portal_tuple[1])
            portal_thing_id = portal_tuple[0]
            self.portals[portal_thing_id] = new_portal
            # associate room objects with portal
            new_portal.room1 = self.get_room(new_portal.room1_coords)
            new_portal.room2 = self.get_room(new_portal.room2_coords)

        # ...set up fixture
        json_dict = get_json_dict('fixtures')
        TODO  # TODO

        # ...set up furniture
        json_dict = get_json_dict('furniture')
        TODO  # TODO

        # ...set up items
        json_dict = get_json_dict('items')
        TODO  # TODO

        # ...set up relations now objects have been created
        json_dict = get_json_dict('relations')
        for relation_tuple in json_dict.items():  # relation dict: {'fr_0010': {'in': 'rm_0307'}, ...}}
            thing1_id = relation_tuple[1].items()[0]
            TODO # TODO

        # initialise player and starting location
        session.player = Player()
        session.player.room = self.get_room(initial_room)

    def run(self):

        session.player.room.look('at')

        while True:
            inp = input("What's next?:").lower()
            if inp in ('q', 'quit', 'exit', 'leave', 'stop', 'end'):
                print("Thanks for playing. Bye.")
                break
            session.player.command_parse(inp)

    def time_passed(self):
        return time.time() - self.start_time


# ********************************* MAIN SCRIPT ********************************

session.game = Game()
session.game.setup((3,7))  # initial room is rm_0307
session.game.run()

# ******************************************************************************
