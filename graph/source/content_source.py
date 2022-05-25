"""
content_source.py
Parent class and key utilities for managing sources.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import logging
import datetime

from storage import PersistentDict, CONTENT_ROOT

from fs.memoryfs import MemoryFS


class sh_meta(type):
    """ Python 3.8 doesn't have a nice way to have class properties :( """

    @property
    def records(cls):
        if cls.NAME not in SourceHandler._RECORDS:
            SourceHandler._RECORDS[cls.NAME] = {}
        return SourceHandler._RECORDS[cls.NAME]

    @property
    def name(cls):
        return cls.NAME

    @property
    def list(cls):
        """ Get a list of all sources with status information """
        lst = []
        for sclass in cls._SOURCES.values():
            lst.append(sclass.info)
        return lst

    @property
    def info(cls):
        """ Get a dictionary of basic info for the source """
        return {
            "name": cls.NAME,
            "docs": cls.__doc__,
            "last-imported": cls.records.get("last-imported", "NEVER"),
        }

    @property
    def content_dir(cls):
        return CONTENT_ROOT / cls.NAME

    def __getitem__(cls, name):
        return SourceHandler._SOURCES[name]


class SourceHandler(metaclass=sh_meta):
    """
    Parent and manager class for all sources.

    **Subclassing**: Children are required to implement two methods:
    `collect` and `process`. No `__init__` is defined in the parent
    so children shouldn't need to call the super-init.
    """

    def collect(self, start=None, stop=None):
        """
        Return raw material from the source starting with `start` datetime
        and ending with `stop` (default: forever).

        This can return anything but ideally it should be a true
        representation of the raw material for debugging purposes.
        """
        raise NotImplementedError()

    def process(self, raw):
        """
        Process raw material from the source.

        This must return either a dictionary or a list of dictionaries
        with a filesystem-like format. Specifically,

          + Directory
            + name <string>
            + children <list of dictionaries>
          + File
            + name <string>
            + extension <string>
            + content <string or bytes>
        """
        raise NotImplementedError()

    NAME = "unnamed"
    """ This is the name of the source as referenced in the CLI """

    _SOURCES = {}
    """ This dictionary is used to lookup the source class by name """

    _RECORDS = PersistentDict("source-records")
    """ This dictionary keeps records of when sources were pulled """

    class SourceHandlerException:
        pass

    class AlreadyRegisteredException(SourceHandlerException):
        pass

    class UnknownProcessedFormat(SourceHandlerException):
        pass

    @classmethod
    def register_handlers(cls):
        """
        When SourceHandlers is imported from outside, this is called _once_
        to grab all subclasses and register them as source handlers.
        """
        if cls._SOURCES:
            raise SourceHandler.AlreadyRegisteredException()
        for subclass in cls.__subclasses__():
            cls._SOURCES[subclass.NAME] = subclass

    def write_processed(self, processed, directory):
        """ Write the processed content to the directory """
        if isinstance(processed, dict):
            self.write_node(processed, directory)
        elif isinstance(processed, list):
            for node in processed:
                self.write_node(node, directory)
        else:
            raise SourceHandler.UnknownProcessedFormat(
                f"Unknown format for processed: '{processed}'"
            )

    def write_node(self, node, directory):
        name = node["name"]

        if "children" in node:
            sdir = directory / name
            sdir.mkdir()
            for child in node["children"]:
                self.write_node(child, sdir)
            return

        extension = node["extension"]
        content = node["content"]
        fmt = "wb" if isinstance(content, bytes) else "w"

        with (directory / f"{name}.{extension}").open(fmt) as f:
            f.write(content)

    def import_to_dir(self, directory, dry_run):
        """ Import everything from this source to the directory. """
        raw = self.collect()
        processed = self.process(raw)
        memfs = None

        if dry_run:
            memfs = MemoryFS()
            directory = memfs.makedir(directory or "tempdir")
        else:
            directory = directory or self.content_dir

        self.write_processed(processed, directory)
        if memfs:
            memfs.close()
        else:
            self.__class__.records["last-imported"] = datetime.datetime.now().isoformat()
