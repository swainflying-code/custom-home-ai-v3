"""
数据库抽象层
统一封装Supabase操作，提供类型安全和错误处理
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from functools import wraps
import logging

from supabase import create_client, Client
from .config import config


logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class ValidationError(DatabaseError):
    """数据验证异常"""
    pass


def handle_db_errors(func):
    """数据库操作错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"数据库操作失败 {func.__name__}: {error_msg}")
            
            if "PGRST204" in error_msg:
                raise ValidationError(f"数据库字段错误: {error_msg}")
            elif "429" in error_msg:
                raise DatabaseError("数据库请求过于频繁，请稍后重试")
            elif "401" in error_msg:
                raise DatabaseError("数据库认证失败，请检查配置")
            else:
                raise DatabaseError(f"数据库操作失败: {error_msg}")
    return wrapper


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._table_columns_cache: Dict[str, List[str]] = {}
        self._connect()
    
    def _connect(self):
        """连接数据库"""
        try:
            self.client = create_client(config.db.url, config.db.key)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise DatabaseError(f"无法连接到数据库: {e}")
    
    def _ensure_list(self, value: Any) -> List[Any]:
        """确保值为列表类型"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)]
    
    # uuid 类型字段名集合：这些字段 None 必须保持 None，不能转为空字符串
    _UUID_FIELDS = {
        "id", "store_id", "customer_id", "product_id", "part_id",
        "quote_id", "space_id", "user_id", "owner_id", "parent_id",
    }

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理和标准化数据"""
        cleaned = {}
        for key, value in data.items():
            # 处理时间类型
            if hasattr(value, 'isoformat'):
                cleaned[key] = value.isoformat()
            # 处理数组类型字段
            elif key in ['style_preference', 'color_preference', 'focus_points', 
                        'family_members', 'design_focus', 'custom_spaces', 'companion_type']:
                cleaned[key] = self._ensure_list(value)
            # 处理布尔值
            elif isinstance(value, bool):
                cleaned[key] = value
            # uuid 字段：None 保持 None，空字符串也转为 None（PostgreSQL uuid 列不接受 ""）
            elif key in self._UUID_FIELDS:
                cleaned[key] = value if value else None
            # 其他类型：None 转为空字符串
            else:
                cleaned[key] = value if value is not None else ""
        
        return cleaned
    
    @handle_db_errors
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[str]:
        """插入数据"""
        if not self.client:
            raise DatabaseError("数据库未连接")
        
        # 清理数据
        cleaned_data = self._clean_data(data)
        
        # 添加ID和时间戳
        if 'id' not in cleaned_data:
            cleaned_data['id'] = str(uuid.uuid4())
        
        now = datetime.now().isoformat()
        if 'created_at' not in cleaned_data:
            cleaned_data['created_at'] = now
        if 'updated_at' not in cleaned_data:
            cleaned_data['updated_at'] = now
        
        # 尝试插入
        for attempt in range(config.db.max_retries):
            try:
                result = self.client.table(table).insert(cleaned_data).execute()
                
                if result.data and len(result.data) > 0:
                    logger.info(f"数据插入成功: {table}.{cleaned_data['id']}")
                    return result.data[0].get("id")
                else:
                    logger.warning(f"数据插入返回为空: {table}")
                    return cleaned_data.get("id")
                    
            except Exception as e:
                error_msg = str(e)
                
                # 处理字段不存在错误
                if "PGRST204" in error_msg or "Could not find the" in error_msg:
                    import re
                    col_match = re.search(r"the '(\w+)'", error_msg)
                    if col_match:
                        missing_col = col_match.group(1)
                        if missing_col in cleaned_data:
                            logger.warning(f"数据库缺少列 {missing_col}，自动跳过")
                            del cleaned_data[missing_col]
                            continue  # 重试
                
                if attempt == config.db.max_retries - 1:
                    raise
                
                logger.warning(f"插入失败，重试 {attempt + 1}/{config.db.max_retries}")
        
        return None
    
    @handle_db_errors
    def select(self, table: str, filters: Dict[str, Any] = None,
               order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """查询数据
        
        order_by 支持以下格式：
          - "created_at"          → 升序
          - "created_at.desc"     → 降序（兼容旧写法，自动解析）
          - "created_at.asc"      → 升序（兼容旧写法，自动解析）
        """
        if not self.client:
            raise DatabaseError("数据库未连接")

        query = self.client.table(table).select("*")

        # 添加过滤条件
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        # 添加排序（兼容 "col.desc" / "col.asc" / "col" 三种写法）
        if order_by:
            if order_by.endswith(".desc"):
                col = order_by[:-5]
                query = query.order(col, desc=True)
            elif order_by.endswith(".asc"):
                col = order_by[:-4]
                query = query.order(col, desc=False)
            else:
                query = query.order(order_by, desc=False)

        # 添加限制
        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []
    
    @handle_db_errors
    def get_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取单条记录"""
        results = self.select(table, {"id": record_id})
        return results[0] if results else None
    
    @handle_db_errors
    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """更新数据"""
        if not self.client:
            raise DatabaseError("数据库未连接")
        
        cleaned_data = self._clean_data(data)
        cleaned_data['updated_at'] = datetime.now().isoformat()
        
        result = self.client.table(table).update(cleaned_data).eq("id", record_id).execute()
        
        success = result.data is not None
        if success:
            logger.info(f"数据更新成功: {table}.{record_id}")
        
        return success
    
    @handle_db_errors
    def delete(self, table: str, record_id: str) -> bool:
        """删除数据"""
        if not self.client:
            raise DatabaseError("数据库未连接")
        
        result = self.client.table(table).delete().eq("id", record_id).execute()
        
        success = result.data is not None
        if success:
            logger.info(f"数据删除成功: {table}.{record_id}")
        
        return success
    
    @handle_db_errors
    def count(self, table: str, filters: Dict[str, Any] = None) -> int:
        """统计记录数"""
        if not self.client:
            raise DatabaseError("数据库未连接")
        
        query = self.client.table(table).select("*", count="exact")
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        result = query.execute()
        return len(result.data) if result.data else 0


# 全局数据库实例
db = DatabaseManager()
