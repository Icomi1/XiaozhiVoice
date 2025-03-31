import time
import wave
import os
import sys
import io
from config.logger import setup_logging
from typing import Optional, Tuple, List
import uuid
import opuslib_next
from core.providers.asr.base import ASRProviderBase
from core.providers.voiceprint import recognition, register, args
from core.providers.memory.base import MemoryProviderBase

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

TAG = __name__
logger = setup_logging()


# 捕获标准输出
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # 将捕获到的内容通过 logger 输出
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool, memory_provider: Optional[MemoryProviderBase] = None):
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file
        self.memory_provider = memory_provider

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="hf"
                # device="cuda:0",  # 启用GPU加速
            )

    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """将Opus音频数据解码并保存为WAV文件"""
        file_name = f"asr_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        file_path = None
        try:
            # 保存音频文件
            start_time = time.time()
            file_path = self.save_audio_to_file(opus_data, session_id)
            logger.bind(tag=TAG).info(f"音频文件保存完成 | 路径: {file_path} | 耗时: {time.time() - start_time:.3f}s")

            # 声纹识别
            if self.memory_provider:
                logger.bind(tag=TAG).info(
                    f"MemoryProvider 状态: current_user_id={getattr(self.memory_provider, 'current_user_id', None)}, role_id={getattr(self.memory_provider, 'role_id', None)}")
                start_time = time.time()
                logger.bind(tag=TAG).info(f"开始声纹识别 | 当前用户: {getattr(self.memory_provider, 'current_user_id', None)}")
                logger.bind(tag=TAG).info(f"声纹识别文件路径: {file_path}")

                try:
                    # 检查音频长度
                    with wave.open(file_path, 'rb') as wf:
                        frames = wf.getnframes()
                        rate = wf.getframerate()
                        duration = frames / float(rate)
                        logger.bind(tag=TAG).info(f"音频长度: {duration:.2f}秒")

                        if duration < 1.3:
                            logger.bind(tag=TAG).warning(f"音频长度不足1.3秒，跳过声纹识别")
                            # 使用文件名作为用户ID
                            user_id = os.path.splitext(os.path.basename(file_path))[0]
                            self.memory_provider.current_user_id = user_id
                            self.memory_provider.role_id = user_id
                            self.memory_provider.user_id = user_id
                            logger.bind(tag=TAG).info(f"使用默认用户ID: {user_id}")
                            return "", file_path

                    recognized_name, similarity = recognition(file_path)
                    logger.bind(tag=TAG).info(
                        f"声纹识别完成 | 用户: {recognized_name} | 相似度: {similarity:.2f} | 阈值: {args.threshold}")

                    if recognized_name and similarity > args.threshold:
                        # 声纹识别成功，使用声纹识别结果作为用户ID
                        self.memory_provider.current_user_id = recognized_name
                        self.memory_provider.role_id = recognized_name
                        self.memory_provider.user_id = recognized_name
                        # 重新初始化记忆，确保使用新的用户ID
                        self.memory_provider.init_memory(recognized_name, self.memory_provider.llm)
                        logger.bind(tag=TAG).info(
                            f"声纹识别成功 | 用户: {recognized_name} | 相似度: {similarity:.2f} | 耗时: {time.time() - start_time:.3f}s")
                    else:
                        # 如果未识别到或相似度不够，使用识别结果中相似度最高的用户
                        if recognized_name:
                            logger.bind(tag=TAG).info(
                                f"声纹识别未达到阈值，使用相似度最高的用户 | 用户: {recognized_name} | 相似度: {similarity:.2f}")
                            self.memory_provider.current_user_id = recognized_name
                            self.memory_provider.role_id = recognized_name
                            self.memory_provider.user_id = recognized_name
                            # 重新初始化记忆，确保使用新的用户ID
                            self.memory_provider.init_memory(recognized_name, self.memory_provider.llm)
                        else:
                            # 如果完全没有识别到用户，使用设备ID
                            device_id = os.path.splitext(os.path.basename(file_path))[0]
                            logger.bind(tag=TAG).info(f"声纹识别完全失败，使用设备ID: {device_id}")
                            self.memory_provider.current_user_id = device_id
                            self.memory_provider.role_id = device_id
                            self.memory_provider.user_id = device_id
                            # 重新初始化记忆，确保使用新的用户ID
                            self.memory_provider.init_memory(device_id, self.memory_provider.llm)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"声纹识别过程出错: {e}", exc_info=True)
                    # 发生错误时，使用设备ID
                    device_id = os.path.splitext(os.path.basename(file_path))[0]
                    self.memory_provider.current_user_id = device_id
                    self.memory_provider.role_id = device_id
                    self.memory_provider.user_id = device_id
                    # 重新初始化记忆，确保使用新的用户ID
                    self.memory_provider.init_memory(device_id, self.memory_provider.llm)
                    logger.bind(tag=TAG).info(f"声纹识别出错，使用设备ID: {device_id}")
            else:
                logger.bind(tag=TAG).warning("MemoryProvider 未初始化，跳过声纹识别")

            # 语音识别
            start_time = time.time()
            logger.bind(tag=TAG).info(f"开始语音识别 | 文件: {file_path}")
            result = self.model.generate(
                input=file_path,
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
            )
            text = rich_transcription_postprocess(result[0]["text"])
            logger.bind(tag=TAG).info(f"语音识别完成 | 文本: {text} | 耗时: {time.time() - start_time:.3f}s")

            return text, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", None

        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).info(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
