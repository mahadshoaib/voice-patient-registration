"""Migrate an empty file DB, run HTTP checks, stop/restart, and verify persistence."""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from scripts.smoke_test import check, fake_patient, run


def start(port: int, env: dict, log):
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=log,
        stderr=log,
    )
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("Server exited; inspect restart-server.log")
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError("Server did not become healthy")


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    Path(".local").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="restart-", dir=".local") as directory:
        db_path = Path(directory).resolve() / "persistence.db"
        database_url = "sqlite:///" + db_path.as_posix()
        env = os.environ | {"DATABASE_URL": database_url, "APP_ENV": "development", "API_KEY": ""}
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
        subprocess.run([sys.executable, "-m", "alembic", "check"], env=env, check=True)
        check(db_path.exists(), "migrations from empty database")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"
        with Path(".local/restart-server.log").open("w") as log:
            process = start(port, env, log)
            try:
                created = httpx.post(base_url + "/patients", json=fake_patient())
                check(created.status_code == 201, "create before process restart")
                patient_id = created.json()["data"]["patient_id"]
                check(httpx.get(base_url + "/docs").status_code == 200, "Swagger docs")
                spec = httpx.get(base_url + "/openapi.json").json()
                check("/patients/{patient_id}" in spec["paths"], "OpenAPI schema")
            finally:
                stop(process)
            process = start(port, env, log)
            try:
                response = httpx.get(base_url + f"/patients/{patient_id}")
                check(response.status_code == 200, "patient survives full server process restart")
                check(
                    httpx.delete(base_url + f"/patients/{patient_id}").status_code == 200,
                    "soft delete persisted patient",
                )
                run(base_url)
            finally:
                stop(process)
        engine = create_engine(database_url)
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT deleted_at FROM patients")).all()
            check(
                bool(rows) and all(row[0] is not None for row in rows),
                "soft-deleted rows physically retained",
            )
        engine.dispose()


if __name__ == "__main__":
    main()
