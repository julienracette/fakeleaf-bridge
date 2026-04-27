import asyncio
from .OverleafBridge import OverleafBridge
def main() -> None:
    asyncio.run(OverleafBridge().run())

if __name__ == "__main__":
    main()
