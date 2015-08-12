# Utility class
import string
import re
import logging


def debug(msg):
    logger = logging.getLogger("pypedrive")
    logger.debug(msg)


def to_snake_case(label):
    """
    Convert a standard label to snake case variable name.
    >>> to_snake_case("My Label")
    'my_label'
    >>> to_snake_case("State/Country")
    'state_country'
    >>> to_snake_case("my-label")
    'my_label'
    """
    filterpunct = re.compile("[%s\ ]" % string.punctuation)
    alphafilter = re.compile("[%s%s_-]" % (string.digits,
                             string.ascii_letters))
    name = filterpunct.sub("_", label.lower())
    return "".join(alphafilter.findall(name))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
