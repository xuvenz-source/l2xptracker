"""Binary mask of a verified in-game Large XP line, without background."""
import base64,zlib
import numpy as np
DATA='eJzNkb9KA0EQxmcvQ24jIc5ZqdUmHOnFJsiBmyPFFQFfIEUUSW2RIpWMcZErY2kn6ANYWkYJeEUKH+GCIpZ5BO9PDlMGbPyqnW+X33wzC/DfVJYAWBQagOnSsypxWtRgtMx9xdldISkQ+/Xb5IQl2I04MwWtgRLxhbaEI1OQEmBy07Gl7nmvLREvPt2neCQQ1D7x6NlDILlqcR+acv/c1SWn6XedCpNGWEiYz6Y9wStQjSLtW50x7KDrjitS2FdcdQCNKauazBNBGw2qr5PYVr4fHE+YEOElFlGg29BajYYUaP/M5VIGElKAUlsEM2OQIIJfkNsIoZ6CFDFZljgAGaQg5AKUJPJbU2sN5BCYJBFBUCw4nGPz9EYd0mAQ0B2T6Vh7UI2604YIOZ8fbVv7R+SJ94+HR15+22/XrCYwNEMx3ZbrK85kbfDJoDZ4sxHob/oB/O9R8w=='
EXPECTED='You have acquired 153 XP and 6 SP.'
def reward_mask():
    bits=np.unpackbits(np.frombuffer(zlib.decompress(base64.b64decode(DATA)),dtype=np.uint8),count=21*292)
    return np.where(bits.reshape(21,292),0,255).astype(np.uint8)
