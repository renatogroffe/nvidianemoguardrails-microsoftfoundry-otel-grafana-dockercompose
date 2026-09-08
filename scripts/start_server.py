"""Start the Guardrails API after configuring OpenTelemetry in this process."""

from __future__ import annotations

import logging
import sys

from otel_setup import instrument_fastapi_app, setup_otel

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    setup_otel()

    remaining = sys.argv[1:]
    sys.argv = ["nemoguardrails", "server", *remaining]

    from nemoguardrails.server import api

    instrument_fastapi_app(api.app)

    from nemoguardrails.__main__ import app

    app()


if __name__ == "__main__":
    main()
