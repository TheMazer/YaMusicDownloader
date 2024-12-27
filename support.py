import random


def shuffleString(s):
    s_list = list(s)
    random.shuffle(s_list)
    return ''.join(s_list)