import threading
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, sleep, get_event_loop, ensure_future
from configparser import ConfigParser
import os
import httpx
from logging import getLogger

from bot import config_dict

RcloneServe = []

LOGGER = getLogger(__name__)


async def rclone_watchdog():
    loop = get_event_loop()
    loop.call_later(60, lambda: ensure_future(rclone_watchdog()))
    if len(RcloneServe) == 0:
        return
    async with httpx.AsyncClient(verify=False) as client:
        try:
            await sleep(60.0)
            r = await client.get(
                url=f"http://localhost:{config_dict['RCLONE_SERVE_PORT']}", follow_redirects=True, timeout=20.0
            )
            if not ((r.status_code >= 200 and r.status_code < 400) or r.status_code != 404):
                LOGGER.error(f"Rclone WatchDog: non-successful response from rclone serve: {r.status_code}")
                await rclone_serve_booter()
        except httpx.RequestError as exc:
            LOGGER.error(f"Rclone WatchDog: An error occurred while requesting {exc.request.url!r}.")
            await rclone_serve_booter()

    return


async def rclone_serve_booter():
    if not config_dict["RCLONE_SERVE_URL"] or not await aiopath.exists("rclone.conf"):
        if RcloneServe:
            try:
                RcloneServe[0].kill()
                RcloneServe.clear()
            except:
                pass
        return
    config = ConfigParser()
    async with aiopen("rclone.conf", "r") as f:
        contents = await f.read()
        config.read_string(contents)
    if not config.has_section("combine"):
        upstreams = " ".join(f"{remote}={remote}:" for remote in config.sections())
        config.add_section("combine")
        config.set("combine", "type", "combine")
        config.set("combine", "upstreams", upstreams)
        with open("rclone.conf", "w") as f:
            config.write(f, space_around_delimiters=False)
    if RcloneServe:
        try:
            RcloneServe[0].kill()
            RcloneServe.clear()
        except:
            pass
    try:
        os.remove("rlogserve.txt")
    except OSError:
        pass
    cmd = [
        "rclone",
        "serve",
        "http",
        "--config",
        "rclone.conf",
        "--no-modtime",
        "combine:",
        "--addr",
        f":{config_dict['RCLONE_SERVE_PORT']}",
        "--vfs-cache-mode",
        "full",
        "--vfs-cache-max-age",
        "1m0s",
        "--buffer-size",
        "64M",
        "--log-file",
        "rlogserve.txt"
    ]
    if (user := config_dict["RCLONE_SERVE_USER"]) and (
            pswd := config_dict["RCLONE_SERVE_PASS"]
    ):
        cmd.extend(("--user", user, "--pass", pswd))
    rcs = await create_subprocess_exec(*cmd)
    RcloneServe.append(rcs)
