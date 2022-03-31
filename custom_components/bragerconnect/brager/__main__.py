"""Testing module for BragerConnect."""
import sys
import asyncio
import logging

from . import BragerConnect


async def main() -> None:
    """Main async function"""
    async with BragerConnect() as brager:
        await brager.connect(username, password)


if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)15s - %(funcName)20s() - %(message)s"
    )  # .135s
    handler.setFormatter(formatter)
    root.addHandler(handler)
    # logging.getLogger("bragerconnect").setLevel(logging.DEBUG)

    asyncio.run(main())
