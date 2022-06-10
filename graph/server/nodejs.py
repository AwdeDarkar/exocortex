"""
nodejs.py
Pythonic wrapper for Node.js utilities.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import json
import os
import shutil
import subprocess

from pathlib import Path
from types import SimpleNamespace

class NodeJS:
    """ Pythonic wrapper for Node.js utilities. """

    def __init__(self, node_project_root: Path):
        self.rootdir = node_project_root

        self.dist = SimpleNamespace()
        self.dist.updated = None
        self.dist.js = None
        self.dist.map = None
        self.dist.css = None

        self.on_update = lambda: None
    
    def _refresh_dist(self):
        with (self.dist_dir / "bundle.js").open("r") as f:
            self.dist.js = self._postprocess_js(f.read())
        with (self.dist_dir / "bundle.js.map").open("r") as f:
            self.dist.map = f.read()
        with (self.dist_dir / "bundle.css").open("r") as f:
            self.dist.css = f.read()
        self.dist.updated = os.path.getmtime(self.dist_dir / "bundle.js")
        self.on_update()
    
    def _postprocess_js(self, jssrc: str):
        """
        Postprocess the JS source.

        This is a bit of a hack, but it's the easiest way to get the source map to have
        the right url.
        """
        lines = jssrc.split("\n")
        lines[1] = lines[1].replace(
            "//# sourceMappingURL=bundle.js.map", "//# sourceMappingURL=bundle.jsmap"
        )
        return "\n".join(lines)
    
    @property
    def node_modules_dir(self):
        """ Get the node_modules directory. """
        return self.rootdir / "node_modules"
    
    @property
    def src_dir(self):
        """ Get the source code directory. """
        return self.rootdir / "src"
    
    @property
    def dist_dir(self):
        """ Get the distribution directory. """
        return self.rootdir / "public" / "build"
    
    @property
    def package_lock_json(self):
        """ Get the package.json file. """
        return self.rootdir / "package-lock.json"
    
    @property
    def package(self):
        """ Get the contents of the package.json file. """
        try:
            return json.loads((self.rootdir / "package.json").read_text())
        except FileNotFoundError:
            return {}
    
    def install_packages(self, force_reinstall=False):
        """ Install dependencies. """
        if force_reinstall and self.node_modules_dir.exists():
            shutil.rmtree(self.node_modules_dir)
            self.package_lock_json.unlink()
        proc = subprocess.Popen(["npm", "install"], cwd=str(self.rootdir))
        proc.wait()

    def build_dist(self):
        """ Build the distribution. """
        proc = subprocess.Popen(["npm", "run", "build"], cwd=str(self.rootdir))
        proc.wait()
        self._refresh_dist()