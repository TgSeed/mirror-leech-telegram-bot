import threading
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, sleep, create_task, ensure_future
from configparser import ConfigParser
import os
import httpx

from bot import config_dict

RcloneServe = []


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = ensure_future(self._job())

    async def _job(self):
        await sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


async def rclone_watchdog():
    t = Timer(60.0, rclone_watchdog)  # set timer for two seconds
    if not config_dict["RCLONE_SERVE_URL"] or not await aiopath.exists("rclone.conf") or len(RcloneServe) == 0:
        return
    async with httpx.AsyncClient() as client:
        try:
            await sleep(60.0)
            r = await client.get(
                url="http://localhost:" + config_dict['RCLONE_SERVE_PORT'], verify=False,
                follow_redirects=True, timeout=20.0
            )
            if not ((r.status_code >= 200 and r.status_code < 400) or r.status_code != 404):
                print(f"Rclone WatchDog: non-successful response from rclone serve: {r.status_code}")
                await rclone_serve_booter()
        except httpx.RequestError as exc:
            print(f"Rclone WatchDog: An error occurred while requesting {exc.request.url!r}.")
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
