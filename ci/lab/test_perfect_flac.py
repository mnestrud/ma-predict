"""Perfect FLAC in the end-to-end test lab: an album on the DLNA renderer, option on.

Copied into the lab's `scenarios/deep/` by the workflow. Two passes of the lab's own album
check (three tracks heard in order to the end) on the DLNA role, flow mode off:

1. option off, no content length: the server measures the size of each stream;
2. option on, forced content length: the server announces the measured size plus a margin
   and has to fill the stream up to it.

The size estimate itself is not tested here: the lab's tracks are synthetic tones, which the
estimate (made for music) puts at about half their real size.
"""

from __future__ import annotations

from typing import Any

import pytest

from scenarios.checks.context import CheckContext
from scenarios.checks.queue import album_plays_through
from scenarios.checks.streams import PROTOCOL_KEY_SPLITTER, set_flow_mode

pytestmark = [
    pytest.mark.deep,
    pytest.mark.area_streams,
    pytest.mark.roles("dlna-1"),
    pytest.mark.timeout(300),
]

STREAMS_DOMAIN = "streams"
MEASURE_VALUES = {"http_profile": "no_content_length", "output_codec": "flac"}
PERFECT_VALUES = {"http_profile": "forced_content_length", "output_codec": "flac"}


async def _save_player_values(
    ctx: CheckContext, player_id: str, wanted: dict[str, str]
) -> dict[str, Any]:
    """Set the stream settings on the player and its protocol outputs; return what was stored."""
    config = await ctx.client.send_command("config/players/get", player_id=player_id)
    values = {
        key: wanted[key.rsplit(PROTOCOL_KEY_SPLITTER, 1)[-1]]
        for key in config["values"]
        if key.rsplit(PROTOCOL_KEY_SPLITTER, 1)[-1] in wanted
    }
    assert values, f"{player_id} has no http_profile setting"
    await ctx.client.send_command("config/players/save", player_id=player_id, values=values)
    return values


async def test_perfect_flac_album_plays(role: str, ctx: CheckContext) -> None:
    """With Perfect FLAC on, three tracks play in order to the end on a forced content length."""
    player_id = ctx.player_id(role)
    await set_flow_mode(ctx, role, False)
    await ctx.client.send_command(
        "config/core/save", domain=STREAMS_DOMAIN, values={"perfect_flac": False, "log_level": "DEBUG"}
    )
    await _save_player_values(ctx, player_id, MEASURE_VALUES)
    await album_plays_through(ctx, role)

    stored = await _save_player_values(ctx, player_id, PERFECT_VALUES)
    ctx.record_property("player_values", ", ".join(f"{k}={v}" for k, v in stored.items()))
    await ctx.client.send_command(
        "config/core/save", domain=STREAMS_DOMAIN, values={"perfect_flac": True}
    )
    try:
        assert await ctx.client.send_command(
            "config/core/get_value", domain=STREAMS_DOMAIN, key="perfect_flac"
        )
        await album_plays_through(ctx, role)
    finally:
        await ctx.client.send_command(
            "config/core/save", domain=STREAMS_DOMAIN, values={"perfect_flac": False}
        )
