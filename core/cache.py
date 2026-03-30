"""
缓存管理模块
提供统一的缓存接口，支持多种缓存后端
"""

import functools
import hashlib
import json
from typing import Any, Optional, Callable, Union
from datetime import datetime, timedelta
import threading


class CacheBackend:
    """缓存后端基类"""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError
    
    def delete(self, key: str) -> None:
        raise NotImplementedError
    
    def clear(self) -> None:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            
            # 检查是否过期
            if 'expires_at' in item and item['expires_at'] < datetime.now():
                del self._cache[key]
                return None
            
            return item.get('value')
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            item = {'value': value}
            
            if ttl is not None:
                item['expires_at'] = datetime.now() + timedelta(seconds=ttl)
            
            self._cache[key] = item
    
    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class StreamlitCache(CacheBackend):
    """Streamlit缓存后端（使用session_state）"""
    
    def __init__(self):
        try:
            import streamlit as st
            self._st = st
        except ImportError:
            self._st = None
    
    def _get_cache_key(self, key: str) -> str:
        return f"_cache_{key}"
    
    def get(self, key: str) -> Optional[Any]:
        if not self._st:
            return None
        
        cache_key = self._get_cache_key(key)
        if cache_key not in self._st.session_state:
            return None
        
        item = self._st.session_state[cache_key]
        
        # 检查是否过期
        if isinstance(item, dict) and 'expires_at' in item:
            if item['expires_at'] < datetime.now():
                del self._st.session_state[cache_key]
                return None
            return item.get('value')
        
        return item
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self._st:
            return
        
        cache_key = self._get_cache_key(key)
        
        if ttl is not None:
            item = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl)
            }
            self._st.session_state[cache_key] = item
        else:
            self._st.session_state[cache_key] = value
    
    def delete(self, key: str) -> None:
        if not self._st:
            return
        
        cache_key = self._get_cache_key(key)
        if cache_key in self._st.session_state:
            del self._st.session_state[cache_key]
    
    def clear(self) -> None:
        if not self._st:
            return
        
        keys_to_delete = []
        for key in self._st.session_state.keys():
            if key.startswith('_cache_'):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._st.session_state[key]


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, backend: Optional[str] = None):
        if backend == 'memory':
            self._backend = MemoryCache()
        elif backend == 'streamlit':
            self._backend = StreamlitCache()
        else:
            # 自动选择
            try:
                import streamlit as st
                self._backend = StreamlitCache()
            except ImportError:
                self._backend = MemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        return self._backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        self._backend.set(key, value, ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        self._backend.delete(key)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._backend.clear()
    
    def get_or_set(self, key: str, func: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """获取缓存，如果不存在则执行函数并缓存结果"""
        value = self.get(key)
        if value is None:
            value = func()
            self.set(key, value, ttl)
        return value


# 创建全局缓存实例
cache = CacheManager()


def cache_result(ttl: Optional[int] = 3600):
    """
    缓存装饰器
    
    使用示例：
    @cache_result(ttl=3600)
    def expensive_function(arg1, arg2):
        # ... 耗时操作
        return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_streamlit_data(ttl: Optional[int] = 3600):
    """
    Streamlit 数据缓存装饰器
    
    使用示例：
    @cache_streamlit_data(ttl=3600)
    def load_data():
        # ... 数据加载
        return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                import streamlit as st
                
                # 使用 Streamlit 内置缓存
                cache_key = f"st_data_{func.__name__}_{_generate_cache_key('', args, kwargs)}"
                
                if cache_key not in st.session_state:
                    result = func(*args, **kwargs)
                    st.session_state[cache_key] = {
                        'data': result,
                        'expires_at': datetime.now() + timedelta(seconds=ttl) if ttl else None
                    }
                else:
                    cache_item = st.session_state[cache_key]
                    
                    # 检查过期
                    if isinstance(cache_item, dict) and 'expires_at' in cache_item:
                        if cache_item['expires_at'] and cache_item['expires_at'] < datetime.now():
                            result = func(*args, **kwargs)
                            st.session_state[cache_key] = {
                                'data': result,
                                'expires_at': datetime.now() + timedelta(seconds=ttl) if ttl else None
                            }
                        else:
                            result = cache_item['data']
                    else:
                        result = cache_item
                
                return result
                
            except ImportError:
                # 如果没有 Streamlit，使用普通缓存
                return cache_result(ttl)(func)(*args, **kwargs)
        
        return wrapper
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存key"""
    try:
        # 将参数序列化为字符串
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        
        # 生成hash
        key_string = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(key_string.encode()).hexdigest()
    except Exception:
        # 如果序列化失败，使用简单key
        return f"{func_name}:{str(args)}:{str(kwargs)}"


def clear_cache(pattern: Optional[str] = None) -> int:
    """
    清除缓存
    
    Args:
        pattern: 如果提供，只删除key包含该模式的缓存
    
    Returns:
        删除的缓存数量
    """
    if pattern is None:
        cache.clear()
        return -1  # 表示全部清除
    else:
        try:
            import streamlit as st
            keys_to_delete = []
            for key in st.session_state.keys():
                if pattern in key:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del st.session_state[key]
            
            return len(keys_to_delete)
        except ImportError:
            return 0


# 便捷函数
get_cache = cache.get
set_cache = cache.set
delete_cache = cache.delete
clear_all_cache = cache.clear
