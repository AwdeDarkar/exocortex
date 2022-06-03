"""
exo_server.py
Parent class and key utilities for managing servers.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

from functools import cached_property
from types import SimpleNamespace
from dataclasses import dataclass
import json

from typing import Callable

from flask import Flask, Response
from jinja2 import Environment, FileSystemLoader

from storage import SITES_ROOT

from server.url import VisitorResolver
from server.nodejs import NodeJS

class sv_meta(type):
    """ Provides class properties for the ServerHandler """

    @property
    def name(cls):
        return cls.NAME

    @property
    def list(cls):
        """ Get a list of all servers with status information """
        lst = []
        for sclass in cls._SERVERS.values():
            lst.append(sclass.name)
        return lst

    @cached_property
    def config(cls):
        """ Get a static configuration for the server """
        return SimpleNamespace(**cls.CONFIG)

    @cached_property
    def app(cls):
        """
        Get the Flask app for the server, creating it if necessary.
        """
        return Flask(cls.NAME)
    
    def __getitem__(cls, name):
        return ServerHandler._SERVERS[name]


class ServerHandler(metaclass=sv_meta):
    """
    Parent and manager class for all servers.
    """

    NAME = "unnamed"

    _SERVERS = {}
    """ All registered servers available to be run """

    SITES = {}
    """ Sites are registered per-server """

    CONFIG = {
        "host": "localhost",
        "port": 5000,
        "static_folder": "static",
        "static_host": None,
    }

    class ServerHandlerException:
        pass

    class AlreadyRegistered(ServerHandlerException):
        pass

    @dataclass(frozen=True)
    class SiteNotFound(ServerHandlerException):
        missing_site_name: str

        def __str__(self):
            return f"No site found for '{missing_site_name}'"

    @classmethod
    def register_servers(cls):
        """
        Register all servers that subclass ServerHandler.
        """
        if cls._SERVERS:
            raise ServerHandler.AlreadyRegisteredException()
        for subclass in cls.__subclasses__():
            cls._SERVERS[subclass.name] = subclass

    @classmethod
    def get_server_list(cls):
        """
        Get a list of all server classes.
        """
        return list(cls._SERVERS.values())
    
    @classmethod
    def site(cls, site_class):
        """ Decorator to register a site with a server """
        cls.SITES[site_class.NAME.lower()] = site_class(cls)
        return site_class
    
    @classmethod
    def simple_site(cls, name, url):
        """ Registers a very simple site that uses the default implementation """
        new_site = type(f"Site_{name}", (Site,), {})
        new_site.NAME = name.lower()
        cls.SITES[new_site.NAME] = new_site(cls)
    
    def __init__(self):
        for site in self.SITES.values():
            site.server = self
        self.setup_routes()
    
    def setup_routes(self):
        """
        Setup routes for the server.

        **Overriding** Servers can override this method to use a different
        routing scheme.
        """
        self.app.route("/", defaults={"path": ""})(self.resolve_path)
        self.app.route("/<path:path>")(self.resolve_path)
    
    def resolve_path(self, path):
        """
        Resolve a path to a semantic target.

        **Overriding** If a server does _not_ follow the semantic URL scheme it can
        override this method to resolve the path however it wants.
        """
        parsed = VisitorResolver.parse(path)
        site = self.get_site(parsed.siteview)

        bundle = parsed.bundle
        if bundle:
            if bundle == "js":
                return Response(site.nodejs.dist.js, mimetype="application/javascript")
            if bundle == "map":
                return Response(site.nodejs.dist.map, mimetype="application/javascript")
            if bundle == "css":
                return Response(site.nodejs.dist.css, mimetype="text/css")

        return site.make_page(parsed)
    
    def generate_content_tree(self, parsed: VisitorResolver):
        """
        Generate a content tree from a parsed URL.

        TODO: Access-checking will happen here when users are implemented.
        """
        raise NotImplementedError("Implement content tree generation")
    
    @classmethod
    def get_site(cls, name):
        """
        Get a site by name.
        """
        try:
            return cls.SITES[name.lower()]
        except KeyError:
            raise ServerHandler.SiteNotFound(name)
    
    def run(self, host=None, port=None, debug=False):
        """
        Run the server.
        """
        self.app.run(
            host=host or self.config.host,
            port=port or self.config.port,
            debug=debug or self.config.debug,
        )

class Site:
    """ Base class for all sites """

    NAME = "unnamed"

    VIEWS = {}
    """ Views describe how a site page is rendered """

    class SiteException(Exception):
        pass

    @dataclass(frozen=True)
    class ViewNotFound(SiteException):
        missing_view_name: str

        def __str__(self):
            return f"No view found for '{missing_view_name}'"

    @classmethod
    def view(cls, name=None):
        """ Decorator to register a view with a site """
        def wrapper(vfunc):
            cls.VIEWS[name or vfunc.__name__] = vfunc
            return vfunc
        return wrapper
    
    @classmethod
    def default_view(cls, vfunc):
        """
        Get the default view for pages.
        """
        cls.VIEWS[""] = vfunc
        return vfunc
    
    def __init__(self, server_class):
        self.server_class = server_class
        self.server = None

        self.nodejs.install_packages()
        self.nodejs.build_dist()
    
    @cached_property
    def template_env(self):
        """
        Get a Jinja2 environment for all sites.
        """
        return Environment(
            loader=FileSystemLoader(SITES_ROOT / "templates"),
            autoescape=True,
        )
    
    @cached_property
    def site_source_dir(self):
        """
        Get the directory containing the site project.
        """
        return SITES_ROOT / self.NAME
    
    @cached_property
    def nodejs(self):
        """
        Get the nodejs wrapper manager.
        """
        return NodeJS(self.site_source_dir)

    def view_for_page(self, viewmask):
        """
        Get the view for a page.
        """
        try:
            return self.VIEWS[viewmask]
        except KeyError:
            raise Site.ViewNotFound(viewmask)
    
    def make_page(self, parsed: VisitorResolver):
        """
        Make a page from a parsed URL.
        """
        content_tree = self.server.generate_content_tree(parsed)
        return self.view_for_page(parsed.viewmask)(content_tree)
    

class DefaultSite(Site):
    @Site.default_view
    @Site.view("full")
    def full_view(self, content_tree):
        """
        Get the full rich javascript view for a page.
        """
        raise NotImplementedError("Implement the svelte view")
    
    @Site.view("flat")
    def flat_view(self, content_tree):
        """
        Get a more reduced, javascript-free view for a page.
        """
        raise NotImplementedError("Implement the flat view")
    
    @Site.view("text")
    def text_view(self, content_tree):
        """
        Get a plaintext view for a page.
        """
        raise NotImplementedError("Implement the text view")
    
    @Site.view("pdf")
    def pdf_view(self, content_tree):
        """
        Get a rendered pdf view for a page.
        """
        raise NotImplementedError("Implement the pdf view")
    
    @Site.view("json")
    def json_view(self, content_tree):
        """
        Get a JSON tree view for a page.
        """
        return Response(
            json.dumps(content_tree),
            mimetype="application/json",
        )