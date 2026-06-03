#!/usr/bin/env python3
"""
IP4Move-Aegis v2.0 一键启动脚本

使用方法:
    python start.py              # 开发模式启动
    python start.py --prod       # 生产模式启动
    python start.py --host 0.0.0.0 --port 8080  # 自定义配置

环境变量:
    IP4MOVE_ENV: 运行环境 (development/production)
    AEGIS_MASTER_SECRET: 主密钥 (生产环境必须设置)
    LOG_LEVEL: 日志级别
    PORT: 服务端口
"""

import os
import sys
import argparse
import subprocess
import asyncio
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()
SRC_DIR = PROJECT_ROOT / "src"


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           IP4Move-Aegis v2.0 - 匿名网络系统                  ║
║                                                              ║
║     安全修复版 | 性能优化 | 企业级部署就绪                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import cryptography
        import structlog
        print("✓ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def check_env_file():
    """检查环境变量配置文件"""
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("⚠ 未找到 .env 文件，从 .env.example 创建")
        import shutil
        shutil.copy(env_example, env_file)
        print("✓ 已创建 .env 文件，请根据需要编辑配置")


def load_env():
    """加载环境变量"""
    try:
        from dotenv import load_dotenv
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print("✓ 环境变量加载完成")
    except ImportError:
        print("⚠ python-dotenv 未安装，跳过环境变量文件加载")


def validate_production_config():
    """验证生产环境配置"""
    env = os.environ.get("IP4MOVE_ENV", "development").lower()
    
    if env in ("production", "prod", "live"):
        master_secret = os.environ.get("AEGIS_MASTER_SECRET")
        if not master_secret or master_secret == "your-secure-master-secret-key-here-32chars":
            print("✗ 错误: 生产环境必须设置 AEGIS_MASTER_SECRET 环境变量!")
            print("   生成命令: openssl rand -hex 32")
            return False
        
        if len(master_secret) < 32:
            print("✗ 错误: AEGIS_MASTER_SECRET 必须至少32个字符!")
            return False
        
        print("✓ 生产环境配置验证通过")
    
    return True


def setup_logging(log_level: str = "INFO", json_logs: bool = False):
    """配置日志"""
    sys.path.insert(0, str(SRC_DIR))
    from logging_config import setup_logging as _setup_logging
    _setup_logging(log_level=log_level, json_output=json_logs)


def create_app():
    """创建FastAPI应用"""
    sys.path.insert(0, str(SRC_DIR))
    from api.server import create_app as _create_app
    
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    json_logs = os.environ.get("JSON_LOGS", "false").lower() == "true"
    version = "2.0.0-fixed"
    
    # 解析CORS来源
    cors_origins_str = os.environ.get("CORS_ORIGINS", "")
    cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
    
    return _create_app(
        log_level=log_level,
        json_logs=json_logs,
        version=version,
        cors_origins=cors_origins if cors_origins else None
    )


def run_server(host: str = "0.0.0.0", port: int = 8080, workers: int = 1, reload: bool = False):
    """运行服务器"""
    import uvicorn
    
    print(f"\n🚀 启动服务器: {host}:{port}")
    print(f"   工作进程: {workers}")
    print(f"   热重载: {'开启' if reload else '关闭'}")
    print(f"   环境: {os.environ.get('IP4MOVE_ENV', 'development')}")
    
    uvicorn.run(
        "start:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        factory=True,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="IP4Move-Aegis v2.0 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py                    # 开发模式启动
  python start.py --prod             # 生产模式启动
  python start.py --port 9000        # 使用指定端口
  python start.py --workers 4        # 使用4个工作进程
        """
    )
    
    parser.add_argument("--prod", "--production", action="store_true",
                        help="生产模式启动")
    parser.add_argument("--host", default="0.0.0.0",
                        help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None,
                        help="监听端口 (默认: 8080 或环境变量PORT)")
    parser.add_argument("--workers", type=int, default=None,
                        help="工作进程数 (默认: 1)")
    parser.add_argument("--reload", action="store_true",
                        help="开启热重载 (开发模式)")
    parser.add_argument("--check", action="store_true",
                        help="仅检查配置，不启动服务")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 设置环境
    if args.prod:
        os.environ["IP4MOVE_ENV"] = "production"
        print("🔒 生产模式")
    else:
        env = os.environ.get("IP4MOVE_ENV", "development")
        print(f"🔧 {env.capitalize()}模式")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置文件
    check_env_file()
    load_env()
    
    # 验证生产环境配置
    if not validate_production_config():
        sys.exit(1)
    
    # 仅检查配置
    if args.check:
        print("\n✓ 配置检查完成")
        sys.exit(0)
    
    # 获取配置
    host = args.host or os.environ.get("HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("PORT", "8080"))
    workers = args.workers or int(os.environ.get("WORKERS", "1"))
    reload = args.reload or (os.environ.get("IP4MOVE_ENV") == "development")
    
    # 创建应用（用于uvicorn factory模式）
    global app
    app = create_app
    
    # 运行服务器
    try:
        run_server(host, port, workers, reload)
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
