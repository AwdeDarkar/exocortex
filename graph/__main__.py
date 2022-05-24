"""
__main__.py
CLI entry-point for the graph generator and related tools.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import functools

import click


# UTILS

def common_params(f):
    """ Decorator to apply common parameters to all commands """
    @click.option("-v", "--verbose", count=True, help="Verbosity level [DEFAULT: ERROR]")
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


# GENERAL-PURPOSE

@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@common_params
def cli(verbose):
    """
    Manage the Exocortex.

    This application aims to be my one-stop-shop for developing, deploying, and
    maintaing the exocortex. Instead of disparate scripts and libraries, everything
    (including dev ops) should be accessible through the 'exo' interface.
    """
    pass


# GRAPH

@cli.group()
@common_params
def graph(verbose):
    """
    Manage the graph-level content.

    The basic model of the Exocortex deals with three levels and the 'graph' level is
    where the ground-truth content lives. Creating and managing that content, as well
    as generating the database used by the server, happens through these commands.
    """
    pass


@graph.command(name="list")
@common_params
def list_content(verbose):
    """
    List all known content.

    This command gets a list of all the content material the Exocortex knows about.
    """
    raise NotImplementedError("Implement this")


@graph.command()
@common_params
def build(verbose):
    """ Build the content graph. """
    raise NotImplementedError("Implement this")


# SOURCE

@cli.group()
@common_params
def source(verbose):
    """
    Manage external content sources.

    The whole point of an exocortex is to integrate disparate sources from many
    modalities into a single interface. These commands are designed to import and
    manage various sources outside of `content/`.
    """
    pass


# SITE

@cli.group()
@common_params
def site(verbose):
    """
    Manage the site views.

    The second layer of the Exocortex is the server / site layer. These are
    conceptualized as subgraphs of the full content graph with particular specialized
    interfaces. While much of the _details_ of the sites are handled by the code for
    the sites themselves, creating new sites, archiving old ones, or performing certain
    migrations happens through these commands.
    """
    pass


@graph.command(name="list")
@common_params
def list_sites(verbose):
    """ List all current sites. """
    raise NotImplementedError("Implement this")


# HOST

@cli.group()
@common_params
def host(verbose):
    """
    Manage the server hosting and devops cycle.

    These commands are mainly utilities to automate the development, maintenance, and
    lifecycle of the servers hosting the Exocortex.

    This includes typical devops things like setting up a development server,
    dockerizing, pre-prod checks, container building, and pushing containers to whatever
    hosting solution is desired. Additionally, this group has status and networking
    tools for debugging.
    """
    pass


@graph.command(name="list")
@common_params
def list_servers(verbose):
    """ List all hostable servers. """
    raise NotImplementedError("List servers command")


# CODE

@cli.group()
@common_params
def code(verbose):
    """
    Track and manage the codebase development.

    These commands are development-helper commands aimed at finding and tracking the
    development process. The aim here is to provide an easy place to create and track
    goals, bugs, and other key parts of the codebase in a low-friction and reasonably
    automated fashion.
    """
    pass


@code.command()
@common_params
def tasks(verbose):
    """
    Show all tasks found in the codebase.

    This command shows all tasks that need to be accomplished marked anywhere in the
    code. Specifically, it looks for the following:

    \b
      + Comments
        + TODO (small features that need to be implemented, may be linked to a goal)
        + BUG (known problems in a part of the code)
      + Code
        + `NotImplementedError` with a message (for functions that need to be implemented;
          if no message is given it is assumed to be an abstract method)
      + Checks (by phase)
        + Linting
        + Documentation Coverage
        + Testing Coverage
        + Automation Coverage
      + Active Goals
    """
    raise NotImplementedError("Tasks overview command")


@code.command()
@common_params
def phase(verbose):
    """
    View or set the current phase.

    Phases manage code standard 'levels' so that as the codebase matures the quality
    becomes more strict. For example, while a codebase is in early development
    tests and comments can be cumbersome. But once a stable release approaches, they
    are necessary to prevent technical debt.

    So, we can step the project 'phase' forward to activate a set of requirements
    that will then be interpreted as tasks.
    """
    raise NotImplementedError("Phase management command")


@code.command()
@common_params
def goal(verbose):
    """
    List or manage broad goals.

    Goals manage related feature sets, often cross-cutting multiple parts of the
    codebase.

    Goals also have both a _state_ and a _plan status_.

    \b
    The _state_ describes how a goal is prioritized (kanban-analogous) and may be:
      + BACKLOG
      + ACTIVE
      + BLOCKED
      + COMPLETE
      + ABANDONDED

    \b
    The _plan status_ relates to how much detail the goal has.
      + BLURB (just a quick description sentence)
      + DESCRIPTION (several paragraphs of explanation with detailed goals)
      + SKETCH (directories and code stubbed out with tasks and todos)
    """
    raise NotImplementedError("Goal management command")


if __name__ == "__main__":
    cli(prog_name="exo")
