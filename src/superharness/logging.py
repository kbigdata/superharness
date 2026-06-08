"""구조적 로깅 셋업."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """루트 하네스 로거를 한 번만 구성한다.

    레벨은 인자 > SUPERHARNESS_LOG 환경변수 > INFO 순으로 결정.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    resolved = (level or os.environ.get("SUPERHARNESS_LOG") or "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s :: %(message)s")
    )
    root = logging.getLogger("superharness")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"superharness.{name}")
