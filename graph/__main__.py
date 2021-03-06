"""
graph/__main__.py
CLI entry-point for the graph generator and related tools.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import os
import logging
import functools
from types import SimpleNamespace
import textwrap

from cookiecutter.main import cookiecutter
from jinja2 import Environment, FileSystemLoader
import click

from logformat import CustomFormatter, print_dicts, EchoHTML as html

from source import SourceHandler
from server import ServerHandler, Site

from storage import SITE_TEMPLATE, SITES_FILE, SITES_ROOT, SNIPPETS_TEMPLATE

# UTILS

def common_params(f):
    """ Decorator to apply common parameters to all commands """
    @click.option("-v", "--verbose", count=True, help="Verbosity level [DEFAULT: ERROR]")
    @functools.wraps(f)
    def wrapper(*args, verbose, **kwargs):
        # Setup logging for verbosity level
        level = 40 - (verbose * 10)
        CustomFormatter.set_level(level)
        return f(*args, verbose, **kwargs)
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

@cli.group(invoke_without_command=True)
@click.pass_context
@common_params
@click.argument("source")
def source(ctx, verbose, source):
    """
    Manage external content source SOURCE.

    The whole point of an exocortex is to integrate disparate sources from many
    modalities into a single interface. These commands are designed to import and
    manage various sources outside of `content/`.
    """
    ctx.obj = SimpleNamespace()
    ctx.obj.name = source
    ctx.obj.source = SourceHandler[source]

    if ctx.invoked_subcommand is None:
        ctx.invoke(view_source_info, verbose=verbose)


@cli.command(name="sources")
@common_params
def list_sources(verbose):
    """
    List all known sources.
    """
    print_dicts(
        SourceHandler.list,
        mapper={
            "name": {"name": "Name"},
            "docs": {"name": "Description", "transform": lambda s: s.split("\n")[1].strip()},
            "last-imported": {"name": "Imported"},
        },
    )


@source.command(name="view")
@click.pass_context
@common_params
def view_source_info(ctx, verbose):
    """
    Get a detailed overview of the source.
    """
    scls = ctx.obj.source
    click.secho(f"Source: {scls.name}", fg="white", bold=True)
    click.secho(f"Class: {scls.__name__}", fg="blue")
    click.secho("Last Import: ", fg="blue", nl=False)
    click.secho(
        scls.info["last-imported"],
        fg=("red" if scls.info["last-imported"] == "NEVER" else "blue")
    )
    click.echo()
    click.secho(textwrap.dedent(scls.info["docs"]).strip(), italic=True)
    click.echo()


@source.command(name="import")
@common_params
@click.option("-d", "--directory",
              default=None,
              type=click.Path(),
              help="Output results to this directory instead of `content/`")
@click.option("--dry-run/--no-dry-run",
              default=True,
              help="Run the import code but don't actually write any files or data")
@click.pass_context
def import_from_source(ctx, verbose, directory, dry_run):
    """
    Import from the source to the content directory.
    """
    src = ctx.obj.source()
    src.import_to_dir(directory, dry_run)


# SITE

@cli.group(invoke_without_command=True)
@click.pass_context
@common_params
@click.argument("site")
def site(ctx, verbose, site):
    """
    Manage the SITE views.

    The second layer of the Exocortex is the server / site layer. These are
    conceptualized as subgraphs of the full content graph with particular specialized
    interfaces. While much of the _details_ of the sites are handled by the code for
    the sites themselves, creating new sites, archiving old ones, or performing certain
    migrations happens through these commands.
    """
    ctx.obj = SimpleNamespace()
    ctx.obj.name = site
    ctx.obj.site = Site[site]
    if ctx.obj.site:
        ctx.obj.nodejs = ctx.obj.site.make_nodejs()

    if ctx.invoked_subcommand is None:
        if ctx.obj.site:
            info = ctx.obj.site.info
            html.echo(
                f"<fg c=white>Site: <b>{info['name']}</b><br />"
                f"<i><fg c=blue>{info['docs']}</fg></i><br />"
                f"Source Location:\t<fg c=teal>{info['source_dir']}<br /></fg>"
                f"Servers Linked:\t\t<fg c=teal>{', '.join([s.name for s in info['servers']])}<br /></fg>"
                "Source Updated:\t\t" +
                ("<fg c=red>NEVER</fg>"
                    if not info['source_dir'].exists()
                    else f"<fg c=teal>{info['source_dir'].times.modified.strftime('%Y-%m-%d %H:%M:%S')}</fg>"
                ) +
                "\n"
                "Last package install:\t" +
                ("<fg c=red>NEVER</fg>"
                    if not info['node_dir'].exists()
                    else f"<fg c=teal>{info['node_dir'].times.modified.strftime('%Y-%m-%d %H:%M:%S')}</fg>"
                ) +
                "\n"
                "Last dist build:\t" +
                ("<fg c=red>NEVER</fg>"
                    if not info['dist_dir'].exists()
                    else f"<fg c=teal>{info['dist_dir'].times.modified.strftime('%Y-%m-%d %H:%M:%S')}</fg>"
                ) +
                "\n"
                "Site Version:\t\t" +
                ("<fg c=red>package.json NOT FOUND</fg>"
                    if not info['package_dict']
                    else f"<fg c=teal>{info['package_dict']['version']}</fg>"
                ) +
                "\n</fg>"
            )
        else:
            click.echo(f"No site named {site}, create it with `exo site {site} make`")


@cli.command(name="sites")
@common_params
def list_sites(verbose):
    """ List all hostable sites. """
    print_dicts(
        Site.list,
        mapper={
            "name": {"name": "Name"},
            "docs": {"name": "Description", "transform": lambda s: s.split("\n")[1].strip()},
            "servers": {
                "name": "Servers",
                "transform": lambda slist: ", ".join([s.NAME for s in slist]),
            },
        },
    )


@site.command(name="make")
@click.pass_context
@common_params
def make_site(ctx, verbose):
    """
    Create a new site.

    TODO: Allow the user to add a description.
    TODO: Allow the user to control auto-adding to servers.
    """

    click.echo(f"Creating site '{ctx.obj.name}'")
    
    os.chdir(SITES_ROOT)
    cookiecutter(
        str(SITE_TEMPLATE),
        extra_context={
            "project_name": ctx.obj.name,
        },
        no_input=True,
        overwrite_if_exists=True,  # Remove when done testing
    )
    
    env = Environment(
        loader=FileSystemLoader(SNIPPETS_TEMPLATE),
        autoescape=False,
    )
    template = env.get_template("new-site-stub.py")
    classname = f"{ctx.obj.name.capitalize()}Site"
    code = template.render(
        name=ctx.obj.name,
        classname=classname,
    )

    with SITES_FILE.open("a") as f:
        f.write("\n\n" + code)

    with (SITES_FILE.parent / "development.py").open("r+") as f:
        src = f.read()
        lines = src.split("\n")
        import_index = lines.index("from sites import (")
        lines.insert(import_index + 1, f"    {classname},")
        lines.append(f"DevelopmentServer.site({ classname })")

        src = "\n".join(lines)
        f.seek(0)
        f.write(src)


@site.command(name="install")
@click.pass_context
@common_params
def install_site_packages(ctx, verbose):
    """ Install required node packages. """
    ctx.obj.nodejs.install_packages()


@site.command(name="build")
@click.pass_context
@common_params
def build_site(ctx, verbose):
    """ Build the site bundles. """
    ctx.obj.nodejs.build_dist()


@site.command(name="delete")
@common_params
def delete_site(verbose):
    """ Delete a site. """
    raise NotImplementedError("Implement this")


# HOST

@cli.group()
@click.pass_context
@common_params
@click.argument("server")
def server(ctx, verbose, server):
    """
    Manage the server hosting and devops cycle.

    These commands are mainly utilities to automate the development, maintenance, and
    lifecycle of the servers hosting the Exocortex.

    This includes typical devops things like setting up a development server,
    dockerizing, pre-prod checks, container building, and pushing containers to whatever
    hosting solution is desired. Additionally, this group has status and networking
    tools for debugging.
    """
    ctx.obj = SimpleNamespace()
    ctx.obj.name = server
    ctx.obj.server = ServerHandler[server]()


@cli.command(name="servers")
@common_params
def list_servers(verbose):
    """ List all hostable servers. """
    print_dicts(
        ServerHandler.list,
        mapper={
            "name": {"name": "Name"},
            "docs": {"name": "Description", "transform": lambda s: s.split("\n")[1].strip()},
            "sites": {
                "name": "Sites",
                "transform": lambda slist: ", ".join([s.NAME for s in slist]),
            },
        },
    )


@server.command(name="host")
@click.pass_context
@common_params
@click.option("-p", "--port", default=5000, help="Port to run the server on")
def host_server(ctx, verbose, port):
    """
    Host the named server.

    This command will create a new server and host it.
    """
    ctx.obj.server.run(port=port)


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

trilium = SourceHandler["trilium"]()

if __name__ == "__main__":
    CustomFormatter.setup_logging()
    cli(prog_name="exo")