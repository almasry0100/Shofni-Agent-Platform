from __future__ import annotations

import os

from poc.fixtures.provider_server import _FixtureHandler, _FixtureHttpServer


def main() -> None:
    port = int(os.environ.get("SHOFNI_FIXTURE_PORT", "8081"))
    server = _FixtureHttpServer(("0.0.0.0", port), _FixtureHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
