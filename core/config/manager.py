#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

统一配置管理器:提供全面的配置管理功能,包括环境变量加载、YAML配置文件加载、Windows兼容性支持"""

import os

import yaml

import logging

import sys

from pathlib import Path, PureWindowsPath

from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv

from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigManager:

    """统一配置管理"""

    def __init__(self, project_root: Optional[Path] = None):

        self.project_root = project_root or Path(__file__).parent.parent.parent

        self._configs: Dict[str, Any] = {}

        self._loaded = False

    def load_all(self) -> None:

        """加载所有配置文件"""

        if self._loaded:

            return

        logger.info("开始加载配置...")

        # 1. 加载环境变量

        self._load_env()

        # 2. 加载YAML配置文件

        self._load_yaml_configs()

        self._loaded = True

        logger.info(f"配置加载完成,共加载 {len(self._configs)} 个配置组")

    def _load_env(self) -> None:

        """加载环境变量"""

        env_path = self.project_root / ".env"

        if env_path.exists():

            try:

                load_dotenv(dotenv_path=env_path, override=True)

                logger.info(f"从 {env_path} 加载环境变量")

            except PermissionError as e:

                logger.error(f"权限错误,无法读取env文件: {e}")

                logger.error("💡 Windows检查")

                logger.error("  1. 以管理员身份运行CMD/PowerShell")

                logger.error("  2. 检查文件权限")

            except UnicodeDecodeError as e:

                logger.error(f"编码错误,请确保.env文件使用UTF-8编码: {e}")

        else:

            load_dotenv()

            logger.warning("使用系统环境变量,未找到本地.env文件")

        # 将关键环境变量存入配置

        self._configs["env"] = {

            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),

            "news_api_key": os.getenv("NEWS_API_KEY"),

            "enable_incremental_collection": os.getenv("ENABLE_INCREMENTAL_COLLECTION", "true").lower() in {"1", "true", "yes"},

            # 从旧格式环境变量兼容

            "ai_analysis_provider": os.getenv("AI_ANALYSIS_PROVIDER"),

            "ai_analysis_model": os.getenv("AI_ANALYSIS_MODEL"),

            "ai_analysis_key": os.getenv("AI_ANALYSIS_KEY"),

            "ai_analysis_base_url": os.getenv("AI_ANALYSIS_BASE_URL"),

            "ai_filter_provider": os.getenv("AI_FILTER_PROVIDER"),

            "ai_filter_model": os.getenv("AI_FILTER_MODEL"),

            "ai_filter_key": os.getenv("AI_FILTER_KEY"),

            "ai_filter_base_url": os.getenv("AI_FILTER_BASE_URL"),

            "smtp_host": os.getenv("SMTP_HOST"),

            "smtp_port": int(os.getenv("SMTP_PORT", "465")),

            "smtp_user": os.getenv("SMTP_USER"),

            "smtp_password": os.getenv("SMTP_PASSWORD"),

            "email_to": os.getenv("EMAIL_TO"),

            "http_proxy": os.getenv("HTTP_PROXY"),

            "https_proxy": os.getenv("HTTPS_PROXY"),

            "no_proxy": os.getenv("NO_PROXY"),

            "log_level": os.getenv("LOG_LEVEL", "INFO"),

            "temp_dir": os.getenv("TEMP_DIR"),

            "enable_investment_analysis": os.getenv("ENABLE_INVESTMENT_ANALYSIS", "false").lower() == "true",

            "ai_batch_size": int(os.getenv("AI_BATCH_SIZE", "4"))

        }

        # 验证配置完整性

        self._validate_config()

    def _validate_config(self) -> None:

        """验证配置完整"""

        env_config = self._configs.get("env", {})

        analysis_key = env_config.get('ai_analysis_key') or env_config.get('deepseek_api_key')

        filter_key = env_config.get('ai_filter_key')

        if not analysis_key and not filter_key:

            logger.warning("⚠️  未配置AI分析模型密钥,部分功能可能受影响")

        email_config = {

            'smtp_host': env_config.get('smtp_host'),

            'smtp_port': env_config.get('smtp_port'),

            'smtp_user': env_config.get('smtp_user'),

            'smtp_password': env_config.get('smtp_password'),

            'email_to': env_config.get('email_to')

        }

        if any(email_config.values()) and not all(email_config.values()):

            logger.warning("⚠️  邮件配置不完整,邮件功能可能无法正常工作")

    def _load_yaml_configs(self) -> None:

        """加载YAML配置文件"""

        # sources.yaml

        sources_path = self.project_root / "sources.yaml"

        if sources_path.exists():

            try:

                # Windows特定:使用UTF-8编码读取

                with open(sources_path, 'r', encoding='utf-8') as f:

                    self._configs["sources"] = yaml.safe_load(f) or {}

                logger.info(f"加载 sources.yaml: {len(self._configs.get('sources', {}))} 个源配置")

                # 统计配置项(Windows控制台友好输出)

                self._log_sources_stats()

            except yaml.YAMLError as e:

                logger.error(f"YAML解析失败: {e}")

                logger.error("💡 Windows常见YAML问题:")

                logger.error("  1. 检查缩进(使用空格而非Tab)")

                logger.error("  2. 检查特殊字符(特别是中文字符)")

                logger.error("  3. 检查文件编码(应为UTF-8)")

                self._configs["sources"] = {}

            except PermissionError as e:

                logger.error(f"Windows权限错误,无法读取配置文件: {e}")

                self._configs["sources"] = {}

            except Exception as e:

                logger.error(f"配置文件加载失败: {e}")

                self._configs["sources"] = {}

        else:

            logger.warning(f"未找到sources.yaml: {sources_path}")

            self._configs["sources"] = {}

        # 优先加载合并后的核心配置文件

        config_dir = Path(__file__).parent  # core/config/ 目录

        core_config_path = config_dir / "core_config.yaml"

        # 始终需要加载的配置文件

        required_files = [

            ("parsing_rules", "parsing_rules.yaml"),

            ("report_templates", "report_templates.yaml")

        ]

        if core_config_path.exists():

            try:

                with open(core_config_path, 'r', encoding='utf-8') as f:

                    core_config = yaml.safe_load(f) or {}

                logger.info(f"加载 core_config.yaml")

                # 从核心配置中提取各个配置部分

                if 'ai_providers' in core_config:

                    self._configs['ai_providers'] = core_config['ai_providers']

                if 'hotboard' in core_config:

                    self._configs['hotboard'] = core_config['hotboard']

                if 'scoring' in core_config:

                    self._configs['scoring'] = core_config['scoring']

                    logger.info("加载评分配置: 权重、Tier映射、热度规则")

                if 'ai_processing' in core_config:

                    self._configs['ai_processing'] = core_config['ai_processing']

                if 'token_limits' in core_config:

                    self._configs['token_limits'] = core_config['token_limits']
                    logger.info("加载 token 用量限额配置")

            except Exception as e:

                logger.error(f"加载 core_config.yaml 失败: {e}")

        else:

            # 加载旧的单独配置文件

            legacy_files = [

                ("ai_providers", "ai_providers.yaml"),

                ("hotboard", "hotboard.yaml")

            ]

            for config_name, filename in legacy_files:

                filepath = config_dir / filename

                if filepath.exists():

                    try:

                        with open(filepath, 'r', encoding='utf-8') as f:

                            self._configs[config_name] = yaml.safe_load(f) or {}

                        logger.info(f"加载 {filename}")

                    except Exception as e:

                        logger.error(f"加载 {filename} 失败: {e}")

                        self._configs[config_name] = {}

                else:

                    # 检查是否有.example文件

                    example_path = config_dir / f"{filename}.example"

                    if example_path.exists():

                        try:

                            with open(example_path, 'r', encoding='utf-8') as f:

                                self._configs[config_name] = yaml.safe_load(f) or {}

                            logger.warning(f"使用示例配置 {filename}.example")

                        except Exception as e:

                            logger.error(f"加载示例配置 {filename}.example 失败: {e}")

                            self._configs[config_name] = {}

                    else:

                        logger.warning(f"未找到{filename}")

                        self._configs[config_name] = {}

        # 加载始终需要的配置文件

        for config_name, filename in required_files:

            filepath = config_dir / filename

            if filepath.exists():

                try:

                    with open(filepath, 'r', encoding='utf-8') as f:

                        self._configs[config_name] = yaml.safe_load(f) or {}

                    logger.info(f"加载 {filename}")

                except Exception as e:

                    logger.error(f"加载 {filename} 失败: {e}")

                    self._configs[config_name] = {}

            else:

                # 检查是否有.example文件

                example_path = config_dir / f"{filename}.example"

                if example_path.exists():

                    try:

                        with open(example_path, 'r', encoding='utf-8') as f:

                            self._configs[config_name] = yaml.safe_load(f) or {}

                        logger.warning(f"使用示例配置 {filename}.example")

                    except Exception as e:

                        logger.error(f"加载示例配置 {filename}.example 失败: {e}")

                        self._configs[config_name] = {}

                else:

                    logger.warning(f"未找到{filename}")

                    self._configs[config_name] = {}

    def _log_sources_stats(self) -> None:

        """统计并记录信源配置信息"""

        sources = self._configs.get('sources', {})

        # 统计配置项(Windows控制台友好输出)

        domestic_central = len(sources.get('domestic', {}).get('central', []))

        intl_agency = len(sources.get('international', {}).get('news_agency', []))

        intl_comp = len(sources.get('international', {}).get('comprehensive', []))

        intl_analytical = len(sources.get('international', {}).get('analytical', []))

        intl_regional = len(sources.get('international', {}).get('regional', []))

        intl_finance = len(sources.get('international', {}).get('finance', []))

        intl_technology = len(sources.get('international', {}).get('technology', []))

        domestic_market = len(sources.get('domestic', {}).get('market_professional', []))

        domestic_technology = len(sources.get('domestic', {}).get('technology', []))

        domestic_disabled = len(sources.get('domestic', {}).get('disabled', []))

        logger.info(

            f"📋 配置加载成功\n"

            f"国内中央媒体{domestic_central}个,"

            f"国际通讯社{intl_agency}个"

        )

        logger.info(

            f"   国际综合媒体{intl_comp}个,"

            f"分析媒体{intl_analytical}个,"

            f"区域媒体{intl_regional}个"

        )

        logger.info(

            f"   国际财经媒体{intl_finance}个,"

            f"国际科技媒体{intl_technology}个"

        )

        logger.info(

            f"   国内市场化媒体{domestic_market}个,"

            f"国内科技媒体{domestic_technology}个,"

            f"已禁用媒体{domestic_disabled}个"

        )

    def get(self, key: str, default: Any = None) -> Any:

        """获取配置值

        支持点号分隔的路径,例如:

        - "sources.domestic.central"

        - "env.deepseek_api_key"

        """

        if not self._loaded:

            self.load_all()

        # 简单的路径解析

        parts = key.split('.')

        value = self._configs

        for part in parts:

            if isinstance(value, dict) and part in value:

                value = value[part]

            else:

                return default

        return value

    def get_sources(self) -> Dict[str, Any]:

        """获取源配置(兼容现有接口)"""

        return self.get("sources", {})

    def get_ai_providers(self) -> Dict[str, Any]:

        """获取AI提供者配置"""

        return self.get("ai_providers", {})

    def get_parsing_rules(self) -> Dict[str, Any]:

        """获取解析规则配置"""

        return self.get("parsing_rules", {})

    def get_hotboard_config(self) -> Dict[str, Any]:

        """获取热点板配置"""

        return self.get("hotboard", {})

    def get_env(self, key: str, default: Any = None) -> Any:

        """获取环境变量"""

        if not self._loaded:

            self.load_all()

        env_config = self._configs.get("env", {})

        return env_config.get(key, os.getenv(key, default))

    def get_project_root(self) -> Path:

        """获取项目根目录"""

        return self.project_root

    def is_windows(self) -> bool:

        """检查是否在Windows系统"""

        return sys.platform.startswith('win')

    def get_current_date(self) -> str:

        """获取当前日期(Windows兼容格式: YYYY-MM-DD)"""

        return datetime.now().strftime("%Y-%m-%d")

# 全局单例实例

_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:

    """获取全局配置管理器实例"""

    global _config_manager

    if _config_manager is None:

        _config_manager = ConfigManager()

    return _config_manager

def load_config() -> ConfigManager:

    """加载配置并返回管理器(兼容现有接口)"""

    manager = get_config_manager()

    manager.load_all()

    return manager

def load_sources() -> Dict[str, Any]:

    """加载源配置(兼容现有loader.load_sources)"""

    return get_config_manager().get_sources()

def get_project_root() -> Path:

    """获取项目根目录"""

    return get_config_manager().get_project_root()

def is_windows() -> bool:

    """检查是否在Windows系统"""

    return get_config_manager().is_windows()

def get_current_date() -> str:

    """获取当前日期(Windows兼容格式: YYYY-MM-DD)"""

    return get_config_manager().get_current_date()

if __name__ == "__main__":

    # 测试配置管理器

    logging.basicConfig(level=logging.INFO)

    print("=" * 60)

    print("配置管理器测试")

    print("=" * 60)

    manager = ConfigManager()

    manager.load_all()

    print(f"项目根目录: {manager.project_root}")

    print(f"是否Windows系统: {manager.is_windows()}")

    print(f"当前日期: {manager.get_current_date()}")

    print(f"配置组数: {len(manager._configs)}")

    # 测试获取配置

    test_keys = [

        "sources",

        "ai_providers",

        "parsing_rules",

        "env.deepseek_api_key",

        "hotboard"

    ]

    for key in test_keys:

        value = manager.get(key)

        if value:

            print(f"{key}: 存在 ({type(value).__name__})")

        else:

            print(f"{key}: 未找到或为空")

    print("=" * 60)

    print("测试完成")
