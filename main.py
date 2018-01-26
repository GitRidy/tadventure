"""
A text-based adventure game by Josh Lock.
A puzzle.
"""

import json
import textwrap
import time
import random
import copy

def get_json_dict(filename):
    filename += ('' if filename.endswith('.json') else '.json')
    with open(filename, 'r') as f:
        json_string = f.read()
        json_dict = json.loads(json_string)
    return json_dict


class Session:  # acts as a gateway for global variables

    game = None
    player = None
    directions_map = {
        'north': 'north', 'n': 'north',
        'east': 'east', 'e': 'east',
        'south': 'south', 's': 'south',
        'west': 'west', 'w': 'west'
        }
    verb_prepositions_map = {
        'go': {
            'to': 'to', 'beside': 'to', 'near': 'to', 'at': 'by',  # TODO: at->by okay?
            'on': 'on', 'onto': 'on',
            'in': 'in', 'into': 'in',
            'over': 'over',
            'under': 'under', 'underneath': 'under',
            'through': 'through',
            'around': 'around'
        },
        'look': {
            'at': 'at',
            'beside': 'by', 'near': 'by', 'around': 'by',
            'over': 'over', 'above': 'over',
            'under': 'under', 'underneath': 'under', 'beneath': 'under', 'below': 'under',
            'on': 'on',
            'in': 'in', 'into': 'in', 'inside': 'in', 'within': 'in'
        }
    }
    size_like_litres = {
        "pea": 0.0002,
        "marble": 0.002,
        "golf ball": 0.04,
        "apple": 0.3,
        "rockmelon": 2.0,
        "basketball": 8.0,
        "jerrycan": 20.0,
        "desktop pc": 60.0,
        "exercise ball": 150.0,
        "wheely bin": 250.0,
        "fridge": 600.0
    }
    '''
    Relations describe geometric relations between things and things or between things and player.
    E.g. player-in-room, room-has-player; torch-in-bag, bag-has-torch; player-by-door, door-by-player...
    Relations are stored with subject of the relation (e.g. with the chair for chair-in-room)
    '''
    inverse_relations = {
        'of': 'has',  # window of room, room has window
        'by': 'by',  # chair by window, window by chair
        'with': 'has',  # key with player, player has key
        'over': 'under',  # jar over candle, candle under jar
        'under': 'over',  # bag under sink, sink over bag
        'on': 'has',  # lamp on desk, desk has lamp
        'in': 'has'  # chair in room, room has chair
    }
    relations_template = {
        'of': set(),
        'by': set(),
        'with': set(), 'has': set(),
        'over': set(), 'under': set(),
        'on': set(),
        'in': set()
    }
    relations_list = ['of', 'by', 'with', 'has', 'over', 'under', 'on', 'in']
    near_relations = ['by', 'with', 'has', 'over', 'under', 'on', 'in']
    verbs_prepositions_relations = {
        # For command in the form [verb x preposition y], e.g. 'put chair by window'
        # This map gives resulting relation for verb-preposition combination,
        # E.g. 'chair-by-window' stores as: (chair).relations['by']={(window)...}
        'go': {
            'to': 'by', 'by': 'by', 'beside': 'by', 'near': 'by',
            'over': 'over',
            'under': 'under', 'underneath': 'under',
            'on': 'on', 'onto': 'on',
            'in': 'in', 'into': 'in'
        },
        'put': {
            'by': 'by', 'beside': 'by', 'near': 'by',  # TODO simplify this by earlier preposition condensing?
            'with': 'with',
            'over': 'over',
            'under': 'under', 'underneath': 'under',
            'on': 'on', 'onto': 'on',
            'in': 'in', 'into': 'in'
        }
    }  # TODO: more content?
    '''
    Verbables describe verb-preposition pairs applicable to a thing.
    E.g. for a chair: put-on, put-by, put-under, move-to, move-by, move-under...
    
    '''
    # verbables_template = {
    #     # e.g. verb: prep: T/F
    #     # condense prepositions and verbs at parse time (e.g.: ('put', 'move') => 'put'))
    #     'put': {
    #         "as_y": ['on', 'in', 'by']
    #     }
    # }

    @staticmethod
    def printw(msg):
        print('')
        for line in textwrap.wrap(msg):
            print(line)

    @staticmethod
    def english_list(strings_list):
        ret = ""
        n = len(strings_list)
        if n == 1:
            ret = str(strings_list[0])
        elif n == 2:
            ret = ' and '.join(strings_list)
        else:
            # Insert 'and' before last name if more than one
            ret = ', '.join(strings_list[0:n-1]) + ', and ' + strings_list[n-1]
        return ret

session = Session()


class Thing:
    # Parent class for all things: rooms, portals, fixtures, furniture, & items

    def __init__(self, thing_id, name, short_names, descriptions,
                 qualities=None,
                 states=None,
                 verbables=None):

        # todo: test for id duplication
        # if (id duplicated):
        #     raise ValueError("Sorry, ID '{}' already exists.".format(id))
        self.thing_id = thing_id
        self.name = name
        self.short_names = short_names

        #dicts
        self.descriptions = descriptions
        self.qualities = qualities
        self.states = states
        self.verbables = verbables

        '''
        Set up relations
        Need to instantiate empty sets) to be populated later by game.setup.
        E.g.: {'in': (thing1, thing2, ...), ...})
        '''
        self.relations = copy.deepcopy(session.relations_template)

        # add this object to things list
        session.game.things[thing_id] = self

    def __str__(self):
        return "{} (AKA \"{}\")".format(self.name, '\" or \"'.join(self.short_names))

    def look(self, preposition=None):

        is_room = isinstance(self, Room)
        is_portal = isinstance(self, Portal)
        give_state = True if is_portal else False
        give_self_description = True if (not preposition or preposition == 'at') else False

        # defaults (changed in some cases below)
        relations_things = {
            'by': set(),
            'over': set(),
            'with': set()
        }

        if is_room or preposition == 'in':
            relations_things = {
                'in': set()
            }
        elif preposition == 'under':
            relations_things = {
                'under': set()
            }
        elif preposition == 'on':
            relations_things = {
                'on': set()
            }

        # DISCOVER
        # discover things in player-visible relations with self:
        # loop through all things to find things in select relations with self
        #   (expensive, but simple and acceptable for a game with just a few things)
        # for through all things...
        no_relations_found = True
        for thing_x in session.game.things.values():
            # for each relation type of interest...
            for relation in relations_things.keys():
                # for each thing_y in this relation type with thing_x...
                for thing_y in thing_x.relations.get(relation, []):
                    if (thing_y == self) and (thing_x != session.player):
                        relations_things[relation].add(thing_x)  # thing_x is in this relation with self
                        no_relations_found = False

        # REPORT
        msg = ''
        if give_self_description:
            # TODO: change state / time index (use thing.states['seen']
            msg = self.description('looks', 0)
        if give_state:  # TODO: need this now only reporting states in list
            states_list = [self.states.get(k, None) for k in ['openness', 'freshness']]  #TODO: 'very stale' for sandwich
            states_list = [i for i in states_list if i is not None]
            msg += " The {} is {}.".format(
                self.short_names[0],
                session.english_list(states_list))
        session.printw(msg)

        if no_relations_found:
            if not give_self_description:
                session.printw("You see nothing of note there.")
        else:
            for relation, things_set in relations_things.items():
                if not not things_set:  # i.e. if things_set not empty
                    thing_names = list(map(lambda x: x.name, things_set))
                    names_csl = session.english_list(thing_names)
                    msg = "{} the {} you see {}.".format(
                        relation.title(),
                        self.short_names[0],
                        names_csl
                    )
                    session.printw(msg)

        # TODO: list fixtures and portals for rooms

    def open(self):  # takes no modifiers

        # 1. check that player is near the thing
        if not session.game.relation_test(session.player, 'near', self):
            session.printw("Sorry, you are not near the {}.".format(self.short_names[0]))
            return

        # 2. check that the thing is not already open
        if self.states['openness'] == 'open':
            session.printw("The {} is already open.".format(self.short_names[0]))
            return

        # 3. check that the thing is openable
        if not self.openable:
            session.printw("Sorry, the {} is not the kind of thing you can open.".format(self.short_names[0]))
            return

        # 4. check that the thing is unlocked
        if self.states['openness'] == 'locked':
            session.printw("Sorry, the {} is locked.".format(self.short_names[0]))
            return

        # 5. change state of the thing
            self.states['openness'] = 'open'
        session.printw("The {} is now open.".format(self.short_names[0]))

    def close(self):  # takes no modifiers

        # 1. check that player is near the thing
        if not session.game.relation_test(session.player, 'near', self):
            session.printw("Sorry, you are not near the {}.".format(self.short_names[0]))
            return

        # 2. check that the thing is not already closed
        if self.states['openness'] == 'closed':
            session.printw("The {} is already closed.".format(self.short_names[0]))
            return

        # 3. check that the thing is openable
        if not self.openable:
            session.printw("Sorry, the {} is not the kind of thing you can close.".format(self.short_names[0]))
            return

        # 4. change state of the thing
        self.states['openness'] = 'closed'
        session.printw("The {} is now closed.".format(self.short_names[0]))

    def description(self, aspect, time_index):
        """ Returns room description for an aspect and a time index

        :param aspect. E.g., 'looks', 'sounds', or 'feels'
        :param time_index. E.g., 0 for first time
        :return: string
        """
        if aspect in ('looks', 'sounds', 'feels'):
            return self.descriptions[aspect][time_index]


class Room(Thing):

    def __init__(
            self, thing_id, name, short_names, descriptions,
            qualities_unique=None,
            states_unique=None,
            verbables_unique=None):
        """
        :param thing_id: string, e.g.: 'rm_0109' for a room
        :param name: string, e.g.: 'a long corridor'
        :param short_names: list, e.g.: ['study', 'office']
        :param descriptions: dict (keys: 'looks', 'sounds', 'feels') of lists (list index as a time index)
        :param verbables: dict with keys: 'as_x', 'as_y'
        """

        states = {  # default states for all rooms
            "seen_count": 0,
            "temperature_C": 22.0,
            "brightness": 0.7,
        }
        if states_unique:
            states.update(states_unique)

        qualities = {  # default qualities for all rooms
            "movable": False,
            "liftable": False,
            "is_vessel": True,
            "openable": False,
            "lockable": False,
        }
        if qualities_unique:
            qualities.update(qualities_unique)

        verbables = {
        }
        if verbables_unique:
            verbables.update((verbables_unique))

        super().__init__(thing_id, name, short_names, descriptions,
                         states=states,
                         qualities=qualities,
                         verbables=verbables
                         )

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


class Player(Thing):

    def __init__(self):

        thing_id = 'player'

        # ask for name
        name = ""
        while not name.isalpha():
            name = input("Please enter your name:").strip()
        name = name.title()
        session.printw("Welcome, {}.".format(name))

        short_names = ['player', 'me', 'self', 'myself', name.lower()]
        descriptions = ["You are somewhat ordinary in appearance, but attractive in your own curious way."
                        " You're a typical height and build for your age. Your hair is getting a little long."
                        " You are wearing blue overalls and old brown boots. You have paint on your chin."]

        states = {  # starting states for player
            "hunger": 0.3,
            "thirst": 0.3,
            "energy": 0.8,
            "health": 0.9,
            "alertness": 0.8,
            "mood": 0.6
        }

        qualities = {  # default qualities for player
            "movable": True,
            "liftable": True,
            "is_vessel": False,
            "openable": False,
            "lockable": False,
            "can_lift_kg": 25.0,
            "weight_kg": 72.0
        }

        verbables = {
        }

        super().__init__(thing_id, name, short_names, descriptions,
                         states=states,
                         qualities=qualities,
                         verbables=verbables
                         )

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

    def look(self, modifiers):
        if len(modifiers) == 0:
            # treat 'look' as 'look at room'
            self.room.look('at')
        elif (modifiers == ['around']) or ('room' in modifiers):
            # treat 'look around' as 'look at room'
            # treat 'look [...] room [...]' as 'look at room'
            self.room.look('at')
        else:
            # 1. determine preposition from first modifier word and reduce
            #   (if not known preposition, assume none)
            preposition = session.verb_prepositions_map['look'].get(modifiers[0], '')
            # drop first modifier word if it was a preposition
            if preposition != '':
                modifiers.pop(0)

            # 2. find object of look (thing_y)
            #   try to identify y from remaining modifier words
            thing_y = session.game.thing_by_words(modifiers)[0]  # returns None or list: [(found thing), (remaining words)]
            if not thing_y:
                session.printw("Sorry, no '{}' around here.".format(' '.join(modifiers)))
                return None

            # 3. thing was found, so call look method of found thing
            thing_y.look(preposition)

    def go(self, modifiers):
        not_understood = False
        if not modifiers:
            not_understood = True
        else:
            next_word = modifiers.pop(0)
            # check if first modifier is known go_preposition
            if next_word in session.verb_prepositions_map['go'].keys():
                # FORM: GO PREP Y
                preposition = session.verb_prepositions_map['go'][next_word]  # reduce to essential prepositions

                # try to identify y from remaining modifier words
                thing_y = session.game.thing_by_words(modifiers)[0]
                if not thing_y:
                    msg = "Sorry, no '{}' around here.".format(' '.join(modifiers))
                    session.printw(msg)
                    return None

                # execute move
                self.go_location(preposition, thing_y)

            elif next_word in session.directions_map.keys():  # e.g. go west
                # FORM: GO DIRECTION
                self.go_direction(next_word)
            else:
                # command not understood
                not_understood = True
        if not_understood:
            session.printw("Sorry, go where?")

    def go_location(self, preposition, destination):
        destination_type = type(destination)

        # delete selected relation types from player
        for relation in self.relations.keys():
            if relation in ['by', 'with', 'over', 'under', 'on']:
                self.relations[relation] = set()

        if destination_type == Room:
            self.room = destination
            self.room.look('at')

        elif destination_type == Portal:
            # add 'by' relation between player and portal
            self.relations['by'].add(destination)
            session.printw("You are now by the {}.".format(destination.short_names[0]))
            destination.look('at')

        elif isinstance(destination, Thing):
            # add new relation between player and thing
            new_relation = session.verbs_prepositions_relations['go'][preposition]
            self.relations[new_relation].add(destination)
            session.printw('You are now {} the {}.'.format(new_relation, destination.short_names[0]))
            destination.look('at')

    def go_direction(self, direction):
        direction = session.directions_map[direction]
        session.printw('(DEV) You go {}.'.format(direction))
        try:
            # 1. does a room exist in the target direction?
            target_room = self.neighbour_room(direction)
        except:
            # 2. no room exists: report error
            msg_list = [
                "Sorry, there is not another room in that direction.",
                "Woops, you bump into a wall. Ouch!",
                "Sorry, it's just a wall there.",
                "You discover... a wall.",
                "Just a wall there, sorry.",
                "Not possible, sorry. There's a wall in the way.",
                "Sorry, you can't go in that direction. It's blocked by a rather stubborn wall.",
                "Hmmm... nowhere to go in that direction.",
                "There's nowhere to go in that direction, sorry."
            ]
            session.printw(random.choice(msg_list))
            return

        # 3. room exists: is there a portal between?
        portal = self.room.get_portal(target_room)
        if portal is None:
            # 4. no portal: go into room
            self.go_location('into', target_room)
        else:
            # 5. portal: portal open?
            if portal.states['openness'] == "open":
                # 6. portal open: go
                self.go_location('into', target_room)
            else:
                # 7. portal not open: go to portal
                session.printw("Your path is blocked by {}.".format(portal.name))
                self.go_location('to', portal)

    def put(self, modifiers=None):

        # PARSE INPUT
        # Looking for thing_x, relation, thing_y
        # Well-formed input e.g.: 'put torch in bag'

        # Check for modifiers
        if not modifiers:
            session.printw("Sorry, put what?")
            return None

        # Determine thing_x
        thing_x, modifiers = session.game.thing_by_words(modifiers)
        if not thing_x:
            session.printw("Sorry, I'm not sure which thing you mean.")
            return None
        if not modifiers:
            session.printw("Sorry, put the {} where?".format(thing_x.short_names[0]))
            return None

        # Find preposition
        preposition = modifiers.pop(0)
        if preposition == 'down':  # 'put x down [...]' => drop x
            self.drop(thing_x)
            return None
        relation = session.verbs_prepositions_relations['put'].get(preposition, None)
        if not relation:
            session.printw("You want to put {} where? Please specify a preposition, "
                           "like 'on' or 'in.'".format(thing_x.short_names[0]))
            return None

        # Find thing_y
        if not modifiers:
            session.printw("You want to put {} {} what?".format(thing_x.short_names[0], preposition))
            return None
        thing_y, modifiers = session.game.thing_by_words(modifiers)
        if not thing_y:
            session.printw("Okay, I know about the {}, but I'm not sure which thing you mean by '{}'.".format(
                thing_x.short_names[0],
                ' '.join(modifiers)
            ))
            return None

        # TEST FOR CONDITIONS
        # 1. check if player has thing_x
        if thing_x not in self.relations['has']:
            session.printw("Sorry, you don't seem to have the {}.".format(thing_x.short_names[0]))
            return None

        # 2. check if player near thing_y
        if not session.game.relation_test(self, 'near', thing_y):
            session.printw("Sorry, you are not near the {}.".format(thing_y.short_names[0]))
            return None

        # 3. check if thing_y can accept requested relation
        if not thing_y.qualities.get("can_put_things_on_it", False):
            session.printw("Sorry, things can't be put on the {}.".format(thing_y.short_names[0]))
            return None

        # EXECUTE

        # Remove...
        #   from player 'has' relation to thing_x
        self.relations['has'].discard(thing_x)
        #   from thing_x 'with' relation to player
        thing_x.relations['with'].discard(self)

        # Add...
        #   to thing_x relation to thing_y
        thing_x.relations[relation].add(thing_y)
        #   to thing_y inverse relation to thing_x
        inverse_relation = session.inverse_relations[relation]
        thing_y.relations[inverse_relation].add(thing_x)

        session.printw("The {} is now {} the {}.".format(
            thing_x.short_names[0],
            relation,
            thing_y.short_names[0]))

    def get(self, modifiers):

        # determine thing_x
        thing_x = session.game.thing_by_words(modifiers)[0]
        if not thing_x:
            session.printw("Sorry, I don't know which thing you mean by '{}'.".format('.'.join(modifiers)))
            return None

        # check if player near thing_x
        if not session.game.relation_test(self, 'by', thing_x):
            session.printw("Sorry, you don't seem to be near the {}.".format(thing_x.short_names[0]))
            return None

        # check if thing_x can be gotten
        if not isinstance(thing_x, Furniture) and not isinstance(thing_x, Item):
            session.printw("Sorry, the {} is not the kind of thing you can get.".format(thing_x.short_names[0]))
            return None
        if not thing_x.qualities.get('movable', False):
            session.printw("Sorry, the {} can't be moved.".format(thing_x.short_names[0]))
            return None
        if not thing_x.qualities.get('liftable', False):
            session.printw("Sorry, the {} can't be lifted.".format(thing_x.short_names[0]))
            return None
        thing_x_kg = thing_x.qualities.get('weight_kg', 0)
        can_lift_kg = self.qualities.get('can_lift_kg', 0)
        if thing_x_kg > can_lift_kg:
            msg = "Sorry, you don't seem strong enough to lift the {}. It weighs {}kg and you can only lift {}kg."
            session.printw(msg.format(
                thing_x.short_names[0],
                thing_x_kg,
                can_lift_kg))
            return None

        # EXECUTE
        # remove non-owning relations from thing_x (leave owning relations intact, like bag has torch)
        for R in ['by', 'with', 'over', 'on', 'in']:
            # first remove inverse relations from related things
            for related_thing in thing_x.relations[R]:
                iR = session.inverse_relations[R]
                related_thing.relations[iR].discard(thing_x)
            # remove relation R from thing_x
            thing_x.relations[R] = set()
        # add to thing_x a 'with' relation with player,
        #   and to player a matching 'has' relation with thing_x
        thing_x.relations['with'].add(self)
        self.relations['has'].add(thing_x)

        # report
        session.printw("(TODO finish this) You now have the {}.".format(thing_x.short_names[0]))

    def drop(self, modifiers):

        if not modifiers:
            session.printw("Sorry, drop what?")
            return None

        # determine thing_x
        if not isinstance(modifiers, Thing):
            thing_x = session.game.thing_by_words(modifiers)[0]
            if not thing_x:
                session.printw("Sorry, I don't know which thing you mean by '{}'.".format('.'.join(modifiers)))
                return None
        else:  # Thing was sent in, not string(s)
            thing_x = modifiers

        # 1. does player have thing_x?
        if not thing_x in self.relations['has']:  # TODO add indirect relation check (e.g. in bag, bag with or on player)
            session.printw("Sorry, you don't seem to have the {}.".format(thing_x.short_names[0]))
            return None

        # 2. Execute
        #   for player, remove 'has' relation to thing_x (and inverse ('with') from thing_x)
        self.relations['has'].remove(thing_x)
        thing_x.relations['with'].discard(self)

        #   for thing_x, add 'in' relation to current room (and inverse ('has') to room)
        thing_x.relations['in'].add(self.room)
        self.room.relations['has'].add(thing_x)

        # 3. Report
        session.printw("You have dropped the {}.".format(thing_x.short_names[0]))

    def listen(self, modifiers):
        session.printw("(DEV) You listen (or listen to x).")  #TODO

    def open(self, modifiers):
        # TODO: add context test
        if not modifiers:
            session.printw("Open what?")
            return
        # determine thing to open
        thing_x = session.game.thing_by_words(modifiers)[0]
        if not thing_x:  # if no thing found:
            msg = "Sorry, you can't open '{}' here.".format(' '.join(modifiers))
            session.printw(msg)
        else:  # a thing was found
            # run open function of found thing
            thing_x.open()  # pass no modifiers

    def close(self, modifiers):
        # TODO: add context test
        if not modifiers:
            session.printw("Close what?")
            return
        # determine thing to open
        thing_x = session.game.thing_by_words(modifiers)[0]
        if not thing_x:  # if no thing found:
            msg = "Sorry, you can't close '{}' here.".format(' '.join(modifiers))
            session.printw(msg)
        else:  # a thing was found
            # run open function of found thing
            thing_x.close()  # pass no modifiers

    def test(self, modifiers):

        thing_y, relation = None, None

        thing_x, modifiers = session.game.thing_by_words(modifiers)

        if not not modifiers:
            relation = modifiers.pop(0)
            if not relation in set().union({'near'}, session.relations_list):
                relation = None

        if not not modifiers:
            thing_y, modifiers = session.game.thing_by_words(modifiers)

        if not thing_x or not relation or not thing_y:
            session.printw("Sorry, I didn't get that. Try a question like, 'is the key on the bed'.")

        tf = session.game.relation_test(thing_x, relation, thing_y)

        session.printw("{}, the {} is {}{} the {}.".format(
            'No' if not tf else 'Yes',
            thing_x.short_names[0],
            'not ' if not tf else '',
            relation,
            thing_y.short_names[0]
        ))

    command_map = {
        'look': look, 'examine': look, 'study': look, 'survey': look, 'inspect': look,
        'go': go, 'head': go, 'walk': go, 'run': go, 'jog': go, 'crawl': go,
        'put': put, 'shift': put, 'move': put,
        'get': get,
        'drop': drop, 'release': drop,
        'listen': listen, 'hear': listen,
        'open': open, 'close': close,
        'is': test, 'test': test
    }

    def command_parse(self, command_phrase):
        # split input into lowercase words
        command_words = list(map(lambda x: x.lower(), command_phrase.split()))

        # drop articles, if found
        if 'the' in command_words: command_words.remove('the')
        if 'a' in command_words: command_words.remove('a')
        if 'an' in command_words: command_words.remove('an')

        word1 = command_words.pop(0)
        verb_fn = self.command_map.get(word1, None)
        if verb_fn is None:
            session.printw("Sorry, you don't know how to \"{}\" here.".format(word1))
            return None
        else:
            verb_fn(self, command_words)
            return True


class Portal(Thing):

    def __init__(self, thing_id, name, short_names, descriptions,
                 room1_thing_id, room2_thing_id,
                 qualities_unique=None,
                 states_unique=None,
                 verbables_unique=None):

        states = {  # default states for all portals
            "openness": "closed"
        }
        if states_unique:
            states.update(states_unique)

        qualities = {  # default qualities for all portals
            "movable": False,
            "liftable": False,
            "is_vessel": False,
            "openable": True,
            "lockable": False
        }
        if qualities_unique:
            qualities.update(qualities_unique)

        verbables = {
        }
        if verbables_unique:
            verbables.update((verbables_unique))

        super().__init__(thing_id, name, short_names, descriptions,
                         qualities=qualities,
                         states=states,
                         verbables=verbables
                         )

        # NOTE: convention: room1 is n or e of room2
        self.room1_coords = Room.to_coords(room1_thing_id)
        self.room2_coords = Room.to_coords(room2_thing_id)
        self.room1 = None  # Game.setup populates this
        self.room2 = None  # Game.setup populates this


class Fixture(Thing):

    def __init__(self, thing_id, name, short_names, descriptions,
                 qualities_unique=None,
                 states_unique=None,
                 verbables_unique=None):

        states = {  # default states for all fixtures
        }
        if states_unique:
            states.update(states_unique)

        qualities = {  # default qualities for all fixtures
            "movable": False,
            "liftable": False,
            "is_vessel": False,
            "openable": False,
            "lockable": False
        }
        if qualities_unique:
            qualities.update(qualities_unique)

        verbables = {
        }
        if verbables_unique:
            verbables.update((verbables_unique))

        super().__init__(thing_id, name, short_names, descriptions,
                         qualities=qualities,
                         states=states,
                         verbables=verbables
                         )


class Furniture(Thing):

    def __init__(self, thing_id, name, short_names, descriptions,
                 qualities_unique=None,
                 states_unique=None,
                 verbables_unique=None):

        states = {  # default states for all furniture
        }
        if states_unique:
            states.update(states_unique)

        qualities = {  # default qualities for all furniture
            "movable": True,
            "liftable": False,
            "is_vessel": True,
            "openable": False,
            "lockable": False,
            "size_like": None,  # ref session.litres_map
            "weight_kg": None,
            "can_hold_L": None,
            "can_put_things_on_it": True
        }
        if qualities_unique:
            qualities.update(qualities_unique)

        verbables = {
        }
        if verbables_unique:
            verbables.update((verbables_unique))

        super().__init__(thing_id, name, short_names, descriptions,
                         qualities=qualities,
                         states=states,
                         verbables=verbables
                         )


class Item(Thing):

    def __init__(self, thing_id, name, short_names, descriptions,
                 qualities_unique=None,
                 states_unique=None,
                 verbables_unique=None):

        states = {  # default states for all items
        }
        if states_unique:
            states.update(states_unique)

        qualities = {  # default qualities for all itesm
            "movable": True,
            "liftable": True,
            "is_vessel": False,
            "openable": False,
            "lockable": False,
            "size_like": None,  # ref session.litres_map
            "weight_kg": None,
            "can_hold_L": None
        }
        if qualities_unique:
            qualities.update(qualities_unique)

        verbables = {
        }
        if verbables_unique:
            verbables.update((verbables_unique))

        super().__init__(thing_id, name, short_names, descriptions,
                         qualities=qualities,
                         states=states,
                         verbables=verbables
                         )


class Game:

    def __init__(self):
        self.start_time = time.time()
        # set up dicts for later population of rooms, portals, fixtures, furniture, and items
        self.things = {}  # key: thing_id
        self.rooms = {}  # key: room coords tuple
        self.portals = {}  # key: thing_id
        self.fixtures = {}  # key: thing_id
        self.furniture = {}  # key: thing_id
        self.items = {}  # key: thing_id

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
            self.portals[portal_thing_id] = new_portal  # key is thing_id
            # associate room objects with portal
            new_portal.room1 = self.get_room(new_portal.room1_coords)
            new_portal.room2 = self.get_room(new_portal.room2_coords)

        # ...set up fixture
        json_dict = get_json_dict('fixtures')
        for fx_tuple in json_dict.items():  # tuple: (thing_id, {...fixture dict...})
            new_fx = Fixture(**fx_tuple[1])
            self.fixtures[fx_tuple[0]] = new_fx  # key is thing_id

        # ...set up furniture
        json_dict = get_json_dict('furniture')
        for fr_tuple in json_dict.items():  # tuple: (thing_id, {...furniture dict...})
            new_fr = Furniture(**fr_tuple[1])
            self.furniture[fr_tuple[0]] = new_fr  # key is thing_id

        # ...set up items
        json_dict = get_json_dict('items')
        for it_tuple in json_dict.items():  # tuple: (thing_id, {...item dict...})
            new_it = Item(**it_tuple[1])
            self.items[it_tuple[0]] = new_it  # key is thing_id

        # ...set up relations now objects have been created
        json_dict = get_json_dict('relations')
        for relation_tuple in json_dict.items():
            thing_id_x = relation_tuple[0]
            # tuple form: ('fr_0099', {'in': ['rm_1010', ...]}, ...)
            # ..............|............|...........|
            # ..............thing_id_x...relation....thing_id_y
            for relation in relation_tuple[1].keys():
                for thing_id_y in relation_tuple[1][relation]:
                    self.things[thing_id_x].relations[relation].add(self.things[thing_id_y])
                    # e.g. (thing_x).relations['in'] = {thing_y, ... }
                    # Add inverse relation? (e.g. for bed-in-room, inverse: room-has-bed)
                    inverse_relation = session.inverse_relations[relation]
                    self.things[thing_id_y].relations[inverse_relation].add(self.things[thing_id_x])

        # initialise player and starting location
        session.player = Player()
        session.player.room = self.get_room(initial_room)

    def run(self):

        session.player.room.look('at')

        while True:
            print('')
            inp = input("What's next?:").lower()
            if inp in ('q', 'quit', 'exit', 'leave', 'stop', 'end'):
                session.printw("Thanks for playing. Bye.")
                break
            session.player.command_parse(inp)

    def thing(self, thing_id):
        try:
            thing = self.things[thing_id]
        except KeyError:
            print("(DEV) Game.thing: thing_id '{}' not found.".format(thing_id))
            return None
        return thing

    def thing_by_shortname(self, short_name):
        # TODO filter by context? (so 'door' yields nearby door?")
        if type(short_name) == str:
            for thing in self.things.values():  # loop through objects in things dict TODO can do this smarter
                for nm in thing.short_names:
                    if nm == short_name:
                        return thing
        return None

    def thing_by_words(self, words):

        if not words:
            return [None, words]

        # try as short name for a thing: a. first two words, b. second word, c. first word
        # this allows for two word names, like 'north window', and getting 'bed' from 'old bed'

        thing = None
        remaining_words = []

        # a. try first word
        thing = self.thing_by_shortname(words[0])
        if not not thing:  # a thing was just found
            remaining_words = words[1:]
        elif len(words) > 1:
            # b. try first two words
            thing = self.thing_by_shortname(' '.join(words[0:2]))
            if not thing:  # no thing found
                # c. try second word
                thing = self.thing_by_shortname(words[1])
            if not not thing:  # a thing has been found
                remaining_words = words[2:]

        return [None, words] if thing is None else [thing, remaining_words]

    def relation_test(self, thing_x, relation_arg, thing_y):

        """
        > question: is X in a direct or indirect R relation with Y?
            direct R relation:
                X-R-Y
                    e.g.
                        player-by-key
            indirect R relation mode un (IR_un): (akin to uncle-nephew)
                X-R-Z, Y-IR_un-Z => X-R-Y
                    e.g.: for R = by, IR_un = [by/on/under/over]:
                        player-by-table, key-[by/on/under/over]-table => player by key
            indirect R relation mode s (IR_ss): (akin to sibling-sibling)
                X-IR_ss-Z, Y-IR_ss-Z => X-R-Y
                    e.g.: for R = by, IR_ss = [by/with/on/in/under/over]:
                        key-[by/with/on/in/under/over]-table, lock-[by/with/on/in/under/over]-table => key-by-lock

        TEST SCENARIOS:
        > bat on table, ball on table:
            bat by ball = True (IR_ss)
            bat on ball = False
        > bat by table, ball on table:
            bat by ball = True (IR_un)
            ball by bat = True (IR_un)
            ball on bat = False
        """

        IR_un_map = {
            'by': ['by', 'with', 'has', 'over', 'under', 'on', 'in'],
            'over': ['under', 'with', 'in', 'on'],
            'under': ['over', 'with', 'in', 'on']
        }
        IR_ss_map = {
            'by': ['by', 'with', 'over', 'under', 'on', 'in']
        }

        # test for valid inputs
        if thing_x not in self.things.values():
            msg = "(DEV) '{}' is not a known thing.".format(str(thing_x))
            raise Exception(msg)
        if thing_y not in self.things.values():
            msg = "(DEV) '{}' is not a known thing.".format(str(thing_y))
            raise Exception(msg)
        if relation_arg not in set().union({'near'}, session.relations_list):
            msg = "Sorry, I don't know the relation '{}'.".format(str(relation_arg))
            raise Exception(msg)

        if relation_arg == 'near':
            relations = session.near_relations.copy()
        else:
            relations = [relation_arg]

        for relation in relations:

            # A. TEST DIRECT RELATION
            if thing_y in thing_x.relations.get(relation, []):
                return True

            # B. TEST INDIRECT RELATION

            # B1. TEST INDIRECT_UN RELATION (UNCLE-NEPHEW)
            IR_un = IR_un_map.get(relation, None)
            if not not IR_un:  # relation is in IR_un_map
                # find any Z for which X-R-Z and Y-IR_un-Z

                # get things in R relation to X
                s1 = thing_x.relations.get(relation, set())

                # get things in IR_un relation to Y
                s2 = set().union(*[things for (R, things) in thing_y.relations.items() if R in IR_un])

                # any things in both (Z)?
                if s1.intersection(s2):
                    return True

            # B2. TEST INDIRECT_SS RELATION (SIBLING-SIBLING)
            IR_ss = IR_ss_map.get(relation, None)
            if not not IR_ss:  # relation is in IR_ss_map
                # find any Z for which X-IR_ss-Z and Y-IR_ss-Z

                # get things in IR_ss relation to X
                s1 = set().union(*[things for (R, things) in thing_x.relations.items() if R in IR_ss])

                # get things in IR_ss relation to Y
                s2 = set().union(*[things for (R, things) in thing_y.relations.items() if R in IR_ss])

                # any things in both (Z)?
                if s1.intersection(s2):
                    return True

        return False

    @staticmethod
    def time_passed(self):
        return time.time() - self.start_time


# ********************************* MAIN SCRIPT ********************************

session.game = Game()
session.game.setup((1,7))  # initial room is rm_0307
session.game.run()

# ******************************************************************************
