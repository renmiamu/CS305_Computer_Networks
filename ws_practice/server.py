import asyncio
import websockets
import datetime

class DanmakuServer:
    def __init__(self):
        self.danmakus = []     # 存储所有弹幕消息（带时间）
        self.users = set()     # 存储所有连接中的用户 WebSocket

    async def reply(self, websocket):
        self.users.add(websocket)
        print(f"[New connection] {websocket.remote_address}")

        try:
            async for message in websocket:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(timestamp, message)

                self.danmakus.append([message, timestamp])

                for u in list(self.users):
                    try:
                        await u.send(message)
                    except websockets.ConnectionClosed:
                        self.users.remove(u)
                    except websockets.InvalidState:
                        self.users.remove(u)
        finally:
            self.users.remove(websocket)
            print(f"[Disconnected] {websocket.remote_address}")

async def main():
    server = DanmakuServer()
    async with websockets.serve(server.reply, '127.0.0.1', 8765):
        print("Danmaku server running at ws://127.0.0.1:8765")
        await asyncio.Future()  # 永久运行

asyncio.run(main())