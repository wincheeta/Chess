class Ranctx:
    def __init__(self):
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0

def rot(x, k):
    return ((x << k) | (x >> (64 - k)))

def ranval(x):
    e = x.a - rot(x.b, 7)
    x.a = x.b ^ rot(x.c, 13)
    x.b = x.c + rot(x.d, 37)
    x.c = x.d + e
    x.d = e + x.a
    return x.d

def raninit(x, seed):
    x.a = 0xf1ea5eed
    x.b = x.c = x.d = seed
    for _ in range(20):
        ranval(x)
