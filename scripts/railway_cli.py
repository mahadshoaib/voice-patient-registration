"""Run Railway CLI with local credentials kept out of command arguments."""

import os
import shutil
import subprocess
import sys

from dotenv import dotenv_values

if __name__ == "__main__":
    values = {key.upper(): value for key, value in dotenv_values(".env").items()}
    token = values.get("RAILWAY_TOKEN") or values.get("RAILWAY_API_TOKEN")
    if not token:
        sys.exit("Missing RAILWAY_API_TOKEN in .env")
    env = os.environ.copy()
    env.pop("RAILWAY_TOKEN", None)
    env.pop("RAILWAY_API_TOKEN", None)
    env["RAILWAY_TOKEN" if values.get("RAILWAY_TOKEN") else "RAILWAY_API_TOKEN"] = token
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        sys.exit("npm is required to run the Railway CLI")
    result = subprocess.run(
        [
            npm,
            "exec",
            "--yes",
            "--cache",
            ".local/npm-cache",
            "--package",
            "@railway/cli",
            "--",
            "railway",
            *sys.argv[1:],
        ],
        env=env,
    )
    sys.exit(result.returncode)
