from pathlib import Path
from time import time
import asyncio

import click

from .bot import create_bot
from .manage import (
    get_users_from_backup,
    GRAPH_LAYOUTS,
    reveal,
    RevealFormat,
    RevealGraphLayout,
)
from .settings import settings


@click.group()
def main() -> None:
    pass


async def _run_main(token: str) -> None:
    bot = create_bot()
    await bot.start(token=token, reconnect=True)


@main.command(short_help="run")
def run() -> None:
    if not settings.FILMSWAP_TOKEN:
        raise click.ClickException("FILMSWAP_TOKEN is not set")
    asyncio.run(_run_main(token=settings.FILMSWAP_TOKEN))

    # format: Literal["text", "pretty", "graph"],
    # graph_layout: Literal[
    #     "circle",
    #     "random",
    #     "kamada_kawai",
    #     "spring",
    #     "spectral",
    #     "randomize",  # as in, pick a random layout, don't use the "random" layout
    # ] = "spectral",


@main.command(name="reveal", short_help="manual reveal command")
@click.option(
    "-f",
    "--format",
    "_format",
    type=click.Choice(["text", "pretty", "graph"]),
    default="text",
)
@click.option(
    "--graph-layout", type=click.Choice(list(GRAPH_LAYOUTS.keys())), default="spectral"
)
@click.argument(
    "JSON_BACKUP",
    type=click.Path(exists=True, dir_okay=False),
)
def reveal_cli_cmd(
    _format: RevealFormat, graph_layout: RevealGraphLayout, json_backup: str
) -> None:
    backup_name = Path(json_backup).name
    data = get_users_from_backup(backup_name)
    res = reveal(format=_format, user_data=data, graph_layout=graph_layout)
    if _format == "graph":
        ts = time()
        for i, graph_bytes in enumerate(res):
            assert isinstance(graph_bytes, bytes)
            # save to filenames like reveal_graph_2022-08-11_14-32-16.png
            filename = f"reveal_graph_{ts}_{i}.png"
            with open(filename, "wb") as fp:
                fp.write(graph_bytes)
    else:
        assert isinstance(res, str)
        print(res)


if __name__ == "__main__":
    main(prog_name="filmswap")
