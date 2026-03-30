"""
认证授权模块
提供用户认证、权限管理、JWT token生成和验证
"""

import hashlib
import secrets
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import hmac
import base64
import json


class AuthManager:
    """认证管理器"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self._active_tokens = {}  # 内存中的token存储（生产环境应使用Redis）
    
    def generate_password_hash(self, password: str) -> str:
        """
        生成密码哈希
        
        使用PBKDF2算法生成密码哈希
        """
        if not password:
            raise ValueError("密码不能为空")
        
        # 生成随机salt
        salt = secrets.token_hex(16)
        
        # 使用PBKDF2生成哈希
        hash_value = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )
        
        # 存储格式：salt:hash
        return f"{salt}:{hash_value.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            password_hash: 存储的哈希值（salt:hash格式）
        
        Returns:
            bool: 密码是否匹配
        """
        if not password or not password_hash:
            return False
        
        try:
            parts = password_hash.split(':')
            if len(parts) != 2:
                return False
            
            salt, stored_hash = parts
            
            # 重新计算哈希
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()
            
            # 使用hmac.compare_digest防止时序攻击
            return hmac.compare_digest(stored_hash, computed_hash)
        except Exception:
            return False
    
    def generate_token(self, user_id: str, username: str, role: str = 'staff', 
                      expire_hours: int = 24) -> str:
        """
        生成JWT风格的token
        
        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            expire_hours: 过期时间（小时）
        
        Returns:
            str: token字符串
        """
        # 创建payload
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'iat': datetime.utcnow(),  # 签发时间
            'exp': datetime.utcnow() + timedelta(hours=expire_hours)  # 过期时间
        }
        
        # 简单的JWT实现（生产环境应使用PyJWT库）
        header = {'alg': 'HS256', 'typ': 'JWT'}
        
        # 编码
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload, default=str).encode()
        ).decode().rstrip('=')
        
        # 签名
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{header_encoded}.{payload_encoded}.{signature}"
        
        # 存储活跃token
        self._active_tokens[user_id] = {
            'token': token,
            'created_at': datetime.utcnow(),
            'expires_at': payload['exp']
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证token
        
        Args:
            token: token字符串
        
        Returns:
            dict: 解码后的payload或None
        """
        if not token or '.' not in token:
            return None
        
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature = parts
            
            # 验证签名
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # 解码payload
            # 补齐base64填充
            payload_encoded += '=' * (4 - len(payload_encoded) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_bytes)
            
            # 检查过期时间
            if isinstance(payload.get('exp'), str):
                exp_time = datetime.fromisoformat(payload['exp'])
            else:
                exp_time = payload['exp']
            
            if isinstance(exp_time, datetime) and exp_time < datetime.utcnow():
                return None
            
            # 检查用户是否还在活跃token列表中
            user_id = payload.get('user_id')
            if user_id and user_id in self._active_tokens:
                return payload
            
            return None
            
        except Exception:
            return None
    
    def invalidate_token(self, user_id: str) -> None:
        """
        使token失效（登出）
        
        Args:
            user_id: 用户ID
        """
        if user_id in self._active_tokens:
            del self._active_tokens[user_id]
    
    def clean_expired_tokens(self) -> int:
        """
        清理过期token
        
        Returns:
            int: 清理的token数量
        """
        now = datetime.utcnow()
        expired_users = []
        
        for user_id, token_info in self._active_tokens.items():
            if token_info['expires_at'] < now:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self._active_tokens[user_id]
        
        return len(expired_users)
    
    def get_token_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取token信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            dict: token信息
        """
        return self._active_tokens.get(user_id)
    
    def authenticate(self, username: str, password: str, user_data: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        用户认证（登录）
        
        Args:
            username: 用户名
            password: 密码
            user_data: 用户数据（包含密码哈希等信息）
        
        Returns:
            tuple: (是否认证成功, 用户信息或None)
        """
        if not username or not password or not user_data:
            return False, None
        
        try:
            # 获取存储的密码哈希
            stored_hash = user_data.get('password_hash')
            if not stored_hash:
                return False, None
            
            # 验证密码
            if self.verify_password(password, stored_hash):
                # 密码正确，返回用户信息（不包含密码哈希）
                user_info = {k: v for k, v in user_data.items() if k != 'password_hash'}
                return True, user_info
            
            return False, None
            
        except Exception as e:
            print(f"认证异常: {e}")
            return False, None
    
    def logout(self, user_id: Optional[str] = None) -> None:
        """
        用户登出
        
        Args:
            user_id: 用户ID，如果提供则使该用户的token失效
        """
        if user_id:
            self.invalidate_token(user_id)
        # 清理过期token
        self.clean_expired_tokens()


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        # 角色权限定义
        self.role_permissions = {
            'admin': {
                'can_view_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': True,
                'can_view_reports': True,
                'can_manage_settings': True,
                'can_manage_designs': True,
                'can_manage_users': True,
                'can_export_data': True
            },
            'manager': {
                'can_view_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': True,
                'can_view_reports': True,
                'can_manage_settings': False,
                'can_manage_designs': True,
                'can_manage_users': False,
                'can_export_data': True
            },
            'designer': {
                'can_view_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': False,
                'can_view_reports': True,
                'can_manage_settings': False,
                'can_manage_designs': True,
                'can_manage_users': False,
                'can_export_data': False
            },
            'staff': {
                'can_view_customers': True,
                'can_edit_customers': True,
                'can_delete_customers': False,
                'can_view_reports': True,
                'can_manage_settings': False,
                'can_manage_designs': True,
                'can_manage_users': False,
                'can_export_data': False
            }
        }
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """
        检查用户是否有特定权限
        
        Args:
            user_role: 用户角色
            permission: 权限名称
        
        Returns:
            bool: 是否有权限
        """
        if user_role not in self.role_permissions:
            return False
        
        return self.role_permissions[user_role].get(permission, False)
    
    def get_user_permissions(self, user_role: str) -> Dict[str, bool]:
        """
        获取用户的所有权限
        
        Args:
            user_role: 用户角色
        
        Returns:
            dict: 权限字典
        """
        return self.role_permissions.get(user_role, {})
    
    def add_role(self, role_name: str, permissions: Dict[str, bool]) -> None:
        """
        添加新角色
        
        Args:
            role_name: 角色名称
            permissions: 权限字典
        """
        self.role_permissions[role_name] = permissions
    
    def update_role_permissions(self, role_name: str, permissions: Dict[str, bool]) -> None:
        """
        更新角色权限
        
        Args:
            role_name: 角色名称
            permissions: 权限字典
        """
        if role_name in self.role_permissions:
            self.role_permissions[role_name].update(permissions)
    
    def check_config(self) -> Dict[str, Any]:
        """
        检查配置完整性
        
        Returns:
            dict: 检查结果 {"valid": bool, "message": str}
        """
        try:
            from core.config import config
            
            missing_configs = []
            
            # 检查 Supabase 配置（使用正确的属性路径）
            if not config.db.url:
                missing_configs.append("SUPABASE_URL")
            
            if not config.db.key:
                missing_configs.append("SUPABASE_KEY")
            
            if not config.app.secret_key or config.app.secret_key == "default-secret-key-change-in-production":
                missing_configs.append("SECRET_KEY")
            
            # 检查 AI 服务配置（使用正确的属性路径）
            if not config.ai.api_key:
                missing_configs.append("MIMO_API_KEY")
            
            if not config.ai.base_url:
                missing_configs.append("MIMO_BASE_URL")
            
            if not config.ai.model:
                missing_configs.append("MIMO_MODEL")
            
            if missing_configs:
                message = f"缺少以下必要配置：\n\n"
                message += "\n".join([f"- **{item}**" for item in missing_configs])
                message += f"\n\n请检查 Streamlit Cloud Secrets 配置。"
                message += f"\n\n当前配置值：\n"
                message += f"- SUPABASE_URL: {'已设置' if config.db.url else '未设置'}\n"
                message += f"- SUPABASE_KEY: {'已设置' if config.db.key else '未设置'}\n"
                message += f"- MIMO_API_KEY: {'已设置' if config.ai.api_key else '未设置'}\n"
                message += f"- SECRET_KEY: {'已设置' if config.app.secret_key and config.app.secret_key != 'default-secret-key-change-in-production' else '未设置'}"
                
                return {
                    "valid": False,
                    "message": message,
                    "missing_configs": missing_configs
                }
            
            # 检查配置值的有效性
            invalid_configs = []
            
            if config.db.url and not config.db.url.startswith(("http://", "https://")):
                invalid_configs.append("SUPABASE_URL 格式不正确（必须以 http:// 或 https:// 开头）")
            
            if config.ai.base_url and not config.ai.base_url.startswith(("http://", "https://")):
                invalid_configs.append("AI_BASE_URL 格式不正确")
            
            if invalid_configs:
                message = f"以下配置格式不正确：\n\n"
                message += "\n".join([f"- {item}" for item in invalid_configs])
                
                return {
                    "valid": False,
                    "message": message,
                    "invalid_configs": invalid_configs
                }
            
            # 所有配置都正确
            return {
                "valid": True,
                "message": "✅ 所有必要配置都已正确设置！"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"检查配置时发生错误：{str(e)}",
                "error": str(e)
            }


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self._sessions = {}
        self._lock = threading.Lock()
    
    def create_session(self, user_id: str, username: str, role: str, 
                      expire_hours: int = 24) -> str:
        """
        创建会话
        
        Args:
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            expire_hours: 过期时间（小时）
        
        Returns:
            str: session_id
        """
        session_id = secrets.token_urlsafe(32)
        
        with self._lock:
            self._sessions[session_id] = {
                'user_id': user_id,
                'username': username,
                'role': role,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=expire_hours)
            }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: session_id
        
        Returns:
            dict: 会话信息或None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                return None
            
            # 检查是否过期
            if session['expires_at'] < datetime.utcnow():
                del self._sessions[session_id]
                return None
            
            return session
    
    def destroy_session(self, session_id: str) -> bool:
        """
        销毁会话（登出）
        
        Args:
            session_id: session_id
        
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        now = datetime.utcnow()
        expired_sessions = []
        
        with self._lock:
            for session_id, session in self._sessions.items():
                if session['expires_at'] < now:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
        
        return len(expired_sessions)


# 创建全局实例
auth_manager = AuthManager()
permission_manager = PermissionManager()
session_manager = SessionManager()

# 便捷函数
generate_password_hash = auth_manager.generate_password_hash
verify_password = auth_manager.verify_password
generate_token = auth_manager.generate_token
verify_token = auth_manager.verify_token
has_permission = permission_manager.has_permission
get_user_permissions = permission_manager.get_user_permissions
