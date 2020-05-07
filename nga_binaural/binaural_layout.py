class BinauralOutput(object):
    """Represent binaural output format; eventually Layout and this should be
    subclasses of a common parent OutputFormat carrying screen information etc.
    """
    channels = ("left", "right")
