"""
development.py
Development server.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from exo_server import ServerHandler, DefaultSite


class DevelopmentServer(ServerHandler):
    """
    Development server.
    """

    NAME = "dev"
    CONFIG = {
        "host": "localhost",
        "port": "8888",
        "debug": True,
    }


class DevelopmentSite(DefaultSite):
    """
    Development site.
    """
    
    NAME = "development"