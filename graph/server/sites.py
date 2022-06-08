"""
sites.py
All front-end sites

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from exo_server import Site, DefaultSite


class DevelopmentSite(DefaultSite):
    """
    Development site.
    """

    NAME = "development"
