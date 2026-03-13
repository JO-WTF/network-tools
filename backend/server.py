"""Backward-compatible entrypoint.

Use `python -m server.app` from backend directory for the new architecture.
"""

from server.app import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
