"""
公共异常模块

定义跨模块共享的异常类
"""


class AegisError(Exception):
    """Aegis 基础异常"""
    pass


class NetworkError(AegisError):
    """网络相关错误"""
    pass


class SecurityError(AegisError):
    """安全相关错误"""
    pass


class ConfigurationError(AegisError):
    """配置相关错误"""
    pass
