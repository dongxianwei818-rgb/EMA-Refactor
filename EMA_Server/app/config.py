"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "ema"  # wechat 小程序
    db_name_web: str = "ema_web"
    db_name_app: str = "ema_app"
    db_user: str = "dxw"
    db_password: str = "1qaz!QAZ"

    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    mock_wx_login: bool = True

    jwt_secret: str = "ema-change-this-secret-in-production"
    jwt_expire_minutes: int = 10080

    api_prefix: str = "/api/v1"
    web_api_prefix: str = "/api/web/v1"
    cors_origins: str = "*"
    files_dir: str = "files"

    # 语义向量提取器：
    # EMA 问卷趋势：span 越大曲线越平滑；history_days 为 trend_curves 保留的曲线点数
    # 配置（.env 可选）
    # QUESTIONS_EMA_SPAN=7          # 平滑窗口，越大越平滑
    # QUESTIONS_EMA_HISTORY_DAYS=30 # trend_curves 保留点数
    questions_ema_span: int = 7
    questions_ema_history_days: int = 30

    # 如果未设置 TEXT_EMBEDDING_MODEL，提取器将使用内置的 lexical-proxy-v1 向量。
    # TEXT_EMBEDDING_MODEL=
    # 如果设置了 TEXT_EMBEDDING_MODEL，提取器将使用指定的模型。
    # 首次提取时会从 Hugging Face 下载模型,需要较长时间, 
    # 国内下载模型时可设置HF_ENDPOINT=https://hf-mirror.com（需先 pip install sentence-transformers）：
    # HF_ENDPOINT=https://hf-mirror.com
    # TEXT_EMBEDDING_MODEL=shibing624/text2vec-base-chinese

    # 如果提前下载了模型，可以设置TEXT_EMBEDDING_MODEL=你的模型路径
    # 本地模型（已下载到 models/text2vec-base-chinese，无需联网）
    text_embedding_model: str = ""

    # 语音特性提取（需系统 PATH 中有 ffmpeg 以解码 AAC）
    # VOICE_ASR_MODEL=base 启用 faster-whisper；留空则仅声学特征
    voice_asr_model: str = ""
    voice_asr_language: str = "zh"
    voice_storage_mode: str = "lightweight"  # lightweight | research
    voice_delete_audio_after_extract: bool = False

    # 视频特性提取（OpenCV 解码 MP4；推荐 mediapipe 面部网格）
    video_sample_fps: float = 2.0
    video_max_frames: int = 120
    video_face_backend: str = "mediapipe"  # mediapipe | opencv
    video_storage_mode: str = "lightweight"  # lightweight | research
    video_delete_after_extract: bool = False

    # 步数特性：个体化基线与低步数判定（相对基线比例，非绝对阈值）
    step_baseline_window_days: int = 14
    step_short_avg_days: int = 7
    step_low_ratio: float = 0.4
    step_rhythm_window_days: int = 28

    # 用户小程序使用行为特性：打卡依从性与昼夜节律
    behavior_on_time_minutes: int = 60
    behavior_late_hour_start: int = 22
    behavior_late_hour_end: int = 5

    @property
    def files_path(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        path = Path(self.files_dir)
        if not path.is_absolute():
            path = root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def voice_files_path(self):
        path = self.files_path / "voice"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def video_files_path(self):
        path = self.files_path / "video"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def db_name_for_client(self, client_type: str) -> str:
        from app.client_types import CLIENT_TYPE_APP, CLIENT_TYPE_WEB, CLIENT_TYPE_WECHAT

        mapping = {
            CLIENT_TYPE_WECHAT: self.db_name,
            CLIENT_TYPE_WEB: self.db_name_web,
            CLIENT_TYPE_APP: self.db_name_app,
        }
        if client_type not in mapping:
            raise ValueError(f"未知 client_type: {client_type}")
        return mapping[client_type]

    @property
    def all_db_names(self) -> list[str]:
        return [self.db_name, self.db_name_web, self.db_name_app]

    def database_url_for(self, db_name: str) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{db_name}?charset=utf8mb4"
        )

    @property
    def database_url(self) -> str:
        """默认库（wechat / ema）连接 URL。"""
        return self.database_url_for(self.db_name)

    @property
    def server_url(self) -> str:
        """MySQL 连接 URL（不指定库名，用于建库）。"""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
