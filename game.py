'''
A text-based adventure game by Josh Lock.
A puzzle.
'''

# imports


# classes
class GameObject:

    def __init__(self, id, name, appearance):
        # todo: test for id duplication
        # if :
        #     raise ValueError("Sorry, ID '%s' already exists." % id)
        self.id = id
        self.name = name
        self.appearance = appearance

    def __str__(self):
        return self.name

class Room(GameObject):

    def __init__(self, id, name, appearance, feel, sound):
        super().__init__(id, name, appearance)
        self.feel = feel
        self. sound = sound


# scripts
room1 = Room('F8','a creepy hallway', 'You are in a long hallway.', "It feels creepy.", "Echoes like crazy.")
print(room1)
print("id: {}, a: {}, f:{}, s:{}".format(room1.id, room1.appearance, room1.feel, room1.sound))