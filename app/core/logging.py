import json
import logging

logger = logging.getLogger("patient_registration")


def event(name: str, **fields) -> None:
    logger.info(json.dumps({"event": name, **fields}, default=str))
