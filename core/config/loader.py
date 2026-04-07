"""
Windows适配的配置加载与环境验证模块
特别注意：路径处理、权限错误、编码问题
"""
import os
import yaml
import sys
from pathlib import Path, PureWindowsPath
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ====================== 常量定义 ======================
# 历史新闻加载天数
HISTORY_NEWS_DAYS = 90
# 新闻筛选时间窗口（小时）
NEWS_TIME_WINDOW_HOURS = 24
# 默认超时时间（秒）
DEFAULT_TIMEOUT_SECONDS = 30
# 默认重试延迟（秒）
DEFAULT_RETRY_DELAY_SECONDS = 1
# 批处理大小
BATCH_SIZE = 4
# 日志文件大小限制（10MB）
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024

# ====================== Windows环境变量管理 ======================

def load_env() -> Dict[str, str]:
    """Windows环境变量加载与验证"""
    from dotenv import load_dotenv
    
    # Windows路径处理：优先从项目根目录加载.env
    env_path = Path(__file__).parent.parent / ".env"
    
    if env_path.exists():
        try:
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"✅ 从 {env_path} 加载环境变量")
        except PermissionError as e:
            logger.error(f"❌ Windows权限错误，无法读取.env文件: {e}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"❌ 编码错误，请确保.env文件使用UTF-8编码: {e}")
            raise
    else:
        load_dotenv()
        logger.warning("⚠️  使用系统环境变量，未找到本地.env文件")
    
    # 推荐（非强制）的环境变量
    # 兼容新旧两种配置格式：
    #   新格式: AI_ANALYSIS_KEY, AI_FILTER_KEY（当前工作流使用）
    #   旧格式: DEEPSEEK_API_KEY, NEWS_API_KEY（历史遗留）
    RECOMMENDED_ENVS = {
        "AI_ANALYSIS_KEY": "AI分析模型密钥",
        "AI_FILTER_KEY": "AI筛选模型密钥",
        "DEEPSEEK_API_KEY": "DeepSeek API密钥（旧格式）",
        "NEWS_API_KEY": "NewsAPI密钥（旧格式）"
    }

    config = {}

    for key, desc in RECOMMENDED_ENVS.items():
        value = os.getenv(key)
        if value and len(value.strip()) >= 10:
            config[key] = value.strip()
            masked_key = value[:4] + "*" * 6 + value[-4:] if len(value) > 10 else "***"
            logger.info(f"🔑 {desc}加载成功（长度:{len(value)}，示例:{masked_key}）")
        else:
            logger.debug(f"⚠️  未配置 {key} ({desc})")

    has_any_ai_key = any(k in config for k in ['AI_ANALYSIS_KEY', 'AI_FILTER_KEY', 'DEEPSEEK_API_KEY'])
    if not has_any_ai_key:
        logger.warning("⚠️  未配置任何 AI 模型密钥，部分功能可能受影响")
    
    # 可选环境变量（带跨平台默认值）
    import tempfile
    
    optional_envs = {
        "DEEPSEEK_API_BASE": "https://api.deepseek.com/v1",
        "QWEN_API_KEY": None,
        "QWEN_API_BASE": "https://ark.cn-beijing.volces.com/api/v3",
        "LOG_LEVEL": "INFO",
        "TEMP_DIR": tempfile.gettempdir()  # 跨平台临时目录
    }
    
    for key, default in optional_envs.items():
        value = os.getenv(key)
        config[key] = value if value else default
        if value:
            if 'KEY' in key and len(value) > 10:
                masked_key = value[:4] + "*" * 6 + value[-4:]
                logger.info(f"🔑 {key}加载成功（长度:{len(value)}，示例:{masked_key}")
            else:
                logger.info(f"⚙️  {key}: {value[:30]}...")
    
    return config


def get_env(key: str, default: Any = None) -> str:
    """安全获取环境变量"""
    value = os.getenv(key)
    if value:
        return value
    if not hasattr(get_env, '_cache'):
        get_env._cache = load_env()
    return get_env._cache.get(key, default)


# ====================== Windows配置文件管理 ======================

def load_sources() -> Dict[str, Any]:
    """加载 sources.yaml 配置文件（Windows路径兼容）"""
    config_path = Path(__file__).parent.parent / "sources.yaml"
    
    if not config_path.exists():
        logger.error(f"❌ 配置文件不存在: {config_path}")
        logger.error("💡 Windows检查:")
        logger.error(f"  1. 确认文件路径: {config_path.absolute()}")
        logger.error("  2. 检查文件权限")
        logger.error("  3. 确保文件扩展名是.yaml不是.txt")
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
    
    try:
        # Windows特定：使用UTF-8编码读取
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            logger.error("❌ 配置文件格式错误：应为字典类型")
            raise ValueError("配置文件格式错误")
        
        # 统计配置项（Windows控制台友好输出）
        domestic_central = len(config.get('domestic', {}).get('central', []))
        intl_agency = len(config.get('international', {}).get('news_agency', []))
        intl_comp = len(config.get('international', {}).get('comprehensive', []))
        intl_analytical = len(config.get('international', {}).get('analytical', []))
        intl_regional = len(config.get('international', {}).get('regional', []))
        
        logger.info(
            f"📋 配置加载成功："
            f"国内中央媒体{domestic_central}个，"
            f"国际通讯社{intl_agency}个"
        )
        logger.info(
            f"   国际综合媒体{intl_comp}个，"
            f"分析媒体{intl_analytical}个，"
            f"区域媒体{intl_regional}个"
        )
        return config
        
    except yaml.YAMLError as e:
        logger.error(f"❌ YAML解析失败: {e}")
        logger.error("💡 Windows常见YAML问题:")
        logger.error("  1. 检查缩进（使用空格而非Tab）")
        logger.error("  2. 检查特殊字符（特别是中文字符）")
        logger.error("  3. 检查文件编码（应为UTF-8）")
        raise
    except PermissionError as e:
        logger.error(f"❌ Windows权限错误，无法读取配置文件: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 配置文件加载失败: {e}")
        raise


# ====================== Windows系统工具 ======================

def get_current_date() -> str:
    """获取当前日期（Windows兼容格式: YYYY-MM-DD）"""
    return datetime.now().strftime("%Y-%m-%d")


def get_project_root() -> Path:
    """获取项目根目录（Windows绝对路径）"""
    return Path(__file__).parent.parent.parent.resolve()


def is_windows() -> bool:
    """检查是否在Windows系统"""
    return sys.platform.startswith('win')


# 导出常用配置（方便其他模块导入）
DEEPSEEK_API_KEY = lambda: get_env("DEEPSEEK_API_KEY")
NEWS_API_KEY = lambda: get_env("NEWS_API_KEY")
DEEPSEEK_API_BASE = lambda: get_env("DEEPSEEK_API_BASE")
PROJECT_ROOT = get_project_root()

# Windows特殊配置
if is_windows():
    logger.debug("🌐 检测到Windows系统，启用Windows特定配置")

# 测试函数
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    print("=" * 60)
    print("🧪 Windows配置模块自测试")
    print("=" * 60)
    
    try:
        # 测试Windows检测
        print(f"🖥️  操作系统: {'Windows' if is_windows() else '非Windows'}")
        
        # 测试环境变量加载
        env_config = load_env()
        print(f"✅ 环境变量加载: {len(env_config)} 个")
        safe_keys = [k for k in env_config.keys() if 'KEY' not in k]
        print(f"   包含（安全显示）: {', '.join(safe_keys)}...")
        
        # 测试配置文件加载
        sources_config = load_sources()
        print(f"✅ 配置文件加载: {len(sources_config)} 个顶级分类")
        
        # 测试路径函数
        print(f"✅ 当前日期: {get_current_date()}")
        print(f"✅ 项目根目录: {get_project_root()}")
        
        # 测试Windows路径兼容性
        test_path = PROJECT_ROOT / "test" / "file.txt"
        print(f"✅ Windows路径测试: {test_path}")
        print(f"   路径类型: {type(test_path).__name__}")
        
        print("=" * 60)
        print("🎯 Windows配置模块测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        print("💡 Windows调试建议:")
        print("  1. 以管理员身份运行CMD/PowerShell")
        print("  2. 检查Python环境变量")
        print("  3. 确认文件编码为UTF-8") 
