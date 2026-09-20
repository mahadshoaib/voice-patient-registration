import subprocess
import sys

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port)
