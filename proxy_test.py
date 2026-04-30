import aiohttp
import asyncio
from aiohttp import BasicAuth


async def test_proxy():
    auth = BasicAuth(login='rFDKijWA', password='JkPpU6CY')

    # Тестируем SOCKS5
    try:
        async with aiohttp.ClientSession(
                proxy=f"socks5://157.22.94.3:63954",
                proxy_auth=auth
        ) as session:
            async with session.get('https://api.telegram.org/bot8761490117:AAH0Jgdno-ExIKKxCe_IZr9TVld094FW0zA/getMe',
                                   timeout=10) as resp:
                print(f"SOCKS5 работает! Статус: {resp.status}")
    except Exception as e:
        print(f"SOCKS5 не работает: {e}")

    # Тестируем HTTP
    try:
        async with aiohttp.ClientSession(
                proxy=f"http://157.22.94.3:63954",
                proxy_auth=auth
        ) as session:
            async with session.get('https://api.telegram.org/bot8761490117:AAH0Jgdno-ExIKKxCe_IZr9TVld094FW0zA/getMe',
                                   timeout=10) as resp:
                print(f"HTTP работает! Статус: {resp.status}")
    except Exception as e:
        print(f"HTTP не работает: {e}")


asyncio.run(test_proxy())