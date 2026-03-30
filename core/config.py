"""
配置管理模块
集中管理所有配置项，支持环境变量、配置文件和 Streamlit secrets
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def _get_config_value(key: str, default: Any = None) -> Any:
    """
    获取配置值，支持多种来源
    优先级：1. 环境变量 2. Streamlit secrets 3. 默认值
    """
    # 1. 先检查环境变量
    value = os.getenv(key)
    if value is not None and value != "":
        # 清理可能的换行符和空格
        return value.replace('\n', '').replace('\r', '').strip()
    
    # 2. 检查 Streamlit secrets（如果在 Streamlit 环境中）
    try:
        import streamlit as st
        # Streamlit Cloud 会将 secrets 注入为 st.secrets
        if hasattr(st, 'secrets'):
            secrets_dict = dict(st.secrets)
            if key in secrets_dict:
                val = secrets_dict[key]
                if isinstance(val, str):
                    # 清理可能的换行符和空格
                    return val.replace('\n', '').replace('\r', '').strip()
                return val
            # 也检查小写版本
            if key.lower() in secrets_dict:
                val = secrets_dict[key.lower()]
                if isinstance(val, str):
                    return val.replace('\n', '').replace('\r', '').strip()
                return val
    except Exception:
        pass
    
    # 3. 返回默认值
    return default


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str
    key: str
    timeout: int = 30
    max_retries: int = 3


@dataclass
class AIConfig:
    """AI服务配置"""
    api_key: str
    base_url: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.6
    timeout: int = 60


@dataclass
class AppConfig:
    """应用配置"""
    debug: bool = False
    secret_key: str = "default-secret-key-change-in-production"
    session_timeout: int = 3600  # 1小时
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_image_types: tuple = ('.png', '.jpg', '.jpeg', '.webp')


class Config:
    """配置管理器"""
    
    def __init__(self):
        # 延迟加载，确保 Streamlit secrets 已准备好
        self._db = None
        self._ai = None
        self._app = None
    
    @property
    def db(self) -> DatabaseConfig:
        """数据库配置（延迟加载）"""
        if self._db is None:
            self._db = self._load_db_config()
        return self._db
    
    @property
    def ai(self) -> AIConfig:
        """AI服务配置（延迟加载）"""
        if self._ai is None:
            self._ai = self._load_ai_config()
        return self._ai
    
    @property
    def app(self) -> AppConfig:
        """应用配置（延迟加载）"""
        if self._app is None:
            self._app = self._load_app_config()
        return self._app
    
    def _load_db_config(self) -> DatabaseConfig:
        """加载数据库配置"""
        url = _get_config_value("SUPABASE_URL") or _get_config_value("NEXT_PUBLIC_SUPABASE_URL")
        key = _get_config_value("SUPABASE_KEY") or _get_config_value("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not url or not key:
            # 在 Streamlit Cloud 中，如果 secrets 还没准备好，返回空配置
            # 让应用显示配置错误页面而不是崩溃
            return DatabaseConfig(url="", key="", timeout=30, max_retries=3)
        
        return DatabaseConfig(
            url=url,
            key=key,
            timeout=int(_get_config_value("DB_TIMEOUT", "30")),
            max_retries=int(_get_config_value("DB_MAX_RETRIES", "3"))
        )
    
    def _load_ai_config(self) -> AIConfig:
        """加载AI服务配置"""
        api_key = _get_config_value("MIMO_API_KEY") or _get_config_value("AI_API_KEY")
        base_url = _get_config_value("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
        model = _get_config_value("MIMO_MODEL", "mimo-v2-pro")
        
        if not api_key:
            # 返回空配置，让应用显示配置错误页面
            return AIConfig(api_key="", base_url=base_url, model=model)
        
        return AIConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=int(_get_config_value("AI_MAX_TOKENS", "4096")),
            temperature=float(_get_config_value("AI_TEMPERATURE", "0.6")),
            timeout=int(_get_config_value("AI_TIMEOUT", "60"))
        )
    
    def _load_app_config(self) -> AppConfig:
        """加载应用配置"""
        return AppConfig(
            debug=_get_config_value("DEBUG", "false").lower() == "true",
            secret_key=_get_config_value("SECRET_KEY", "default-secret-key-change-in-production"),
            session_timeout=int(_get_config_value("SESSION_TIMEOUT", "3600")),
            max_upload_size=int(_get_config_value("MAX_UPLOAD_SIZE", "10485760")),
            allowed_image_types=tuple(_get_config_value("ALLOWED_IMAGE_TYPES", ".png,.jpg,.jpeg,.webp").split(","))
        )
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        try:
            # 检查数据库配置
            if not self.db.url or not self.db.key:
                return False
            # 检查AI配置
            if not self.ai.api_key:
                return False
            return True
        except Exception:
            return False
    
    def get_missing_configs(self) -> list:
        """获取缺失的配置项列表"""
        missing = []
        
        if not self.db.url:
            missing.append("SUPABASE_URL")
        if not self.db.key:
            missing.append("SUPABASE_KEY")
        if not _get_config_value("SUPABASE_JWT_SECRET"):
            missing.append("SUPABASE_JWT_SECRET")
        if not self.ai.api_key:
            missing.append("MIMO_API_KEY")
        if not _get_config_value("MIMO_BASE_URL"):
            missing.append("MIMO_BASE_URL")
        if not _get_config_value("MIMO_MODEL"):
            missing.append("MIMO_MODEL")
        if not self.app.secret_key:
            missing.append("SECRET_KEY")
        
        return missing
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（兼容旧代码）"""
        keys = key.split(".")
        value = self
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            elif isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value


# 创建全局配置实例（使用延迟加载）
config = Config()
