import asyncio
from config.settings import load_config, check_config_file
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed
from fastapi import FastAPI
from core.providers.asr.fun_local import ASRProvider
from core.providers.memory.memory import memory_provider
from core.providers.voiceprint import load_audio_db
import os

TAG = __name__

app = FastAPI()

# 初始化ASR提供者
asr_provider = ASRProvider(
    config={
        "model_dir": "models/SenseVoiceSmall",
        "output_dir": "tmp"
    },
    delete_audio_file=True,
    memory_provider=memory_provider
)

# 加载声纹数据库
load_audio_db('tmp')  # 使用tmp目录作为声纹数据库目录

@app.post("/asr")
async def asr_endpoint(audio_data: bytes, session_id: str):
    text, file_path = await asr_provider.speech_to_text(audio_data, session_id)
    return {"text": text, "file_path": file_path}

async def main():
    check_config_file()
    check_ffmpeg_installed()
    config = load_config()

    # 启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())

    try:
        # 等待 WebSocket 服务器运行
        await ws_task
    finally:
        ws_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
