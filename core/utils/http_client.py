"""
Windows适配的HTTP请求工具模块 - 智能代理版本
支持国内/国外网站自动切换代理设置
"""

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib.parse import urlparse
import logging
import time
import sys
import socket
import os

# Windows特定：禁用SSL警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Windows用户代理（模拟Edge/Chrome）
WINDOWS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0"
}

# 通用请求头
HEADERS = WINDOWS_HEADERS if sys.platform.startswith('win') else {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# 国内域名列表（不走代理）
DOMESTIC_DOMAINS = {
    'xinhuanet.com', 'news.cn',  # 新华社
    'people.com.cn', 'people.cn', 'people.com',  # 人民日报
    'cctv.com', 'cntv.cn',  # 央视
    'gov.cn', 'gov.com.cn',  # 政府网站
    'baidu.com', 'qq.com', 'sina.com.cn', 'sohu.com',  # 其他国内站点
    '163.com', 'sina.com', 'ifeng.com', 'so.com',
    'sohu.com', 'zhihu.com', 'bilibili.com', 'jd.com',
    'taobao.com', 'alibaba.com', 'weibo.com', 'douban.com',
    '360.cn', 'csdn.net', 'github.io',  # GitHub Pages有时在国内
    'cnblogs.com', 'oschina.net', '51cto.com'
}

# 代理配置缓存
_proxy_config_cache = None


def test_proxy_connection(proxy_url: str, timeout: int = 10) -> bool:
    """
    测试代理连接是否正常
    
    Args:
        proxy_url: 代理服务器URL
        timeout: 测试超时时间（秒）
        
    Returns:
        bool: 代理连接是否正常
    """
    try:
        session = requests.Session()
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        session.timeout = timeout
        session.headers.update(HEADERS)
        
        # 测试连接到国际网站，确保代理真正工作
        test_urls = [
            "https://www.google.com",  # 国际网站，需要代理
            "https://www.baidu.com"     # 国内网站，作为备用测试
        ]
        
        logger.info(f"🔍 测试代理连接: {proxy_url}")
        
        for test_url in test_urls:
            try:
                logger.debug(f"  测试访问: {test_url}")
                response = session.get(test_url, timeout=timeout)
                if response.status_code == 200:
                    logger.info(f"✅ 代理连接成功: {proxy_url} (测试: {test_url})")
                    return True
                else:
                    logger.warning(f"⚠️  代理连接返回状态码: {response.status_code} (测试: {test_url})")
            except Exception as e:
                logger.debug(f"  测试失败: {test_url} - {type(e).__name__}")
                continue
        
        logger.warning(f"❌ 所有测试URL都无法通过代理访问: {proxy_url}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"❌ 代理连接失败（连接错误）: {proxy_url} - {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.warning(f"❌ 代理连接失败（超时）: {proxy_url} - {e}")
        return False
    except Exception as e:
        logger.warning(f"❌ 代理连接失败: {proxy_url} - {type(e).__name__}: {e}")
        return False


def is_domestic_domain(url: str) -> bool:
    """
    判断URL是否属于国内域名
    
    Args:
        url: 要检查的URL
        
    Returns:
        bool: True表示是国内域名，False表示是国际域名
    """
    try:
        # 解析URL获取域名
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 移除端口号
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # 检查是否为空或本地地址
        if not domain or domain in ('localhost', '127.0.0.1', '::1'):
            return True
        
        # 检查是否匹配国内域名列表
        for domestic_domain in DOMESTIC_DOMAINS:
            if domain.endswith(domestic_domain):
                logger.debug(f"🌍 域名检测: {domain} -> 国内域名 (匹配: {domestic_domain})")
                return True
        
        # 通过IP地址判断（备用方案）
        try:
            hostname = parsed.hostname
            if hostname:
                # 解析IP地址
                ip = socket.gethostbyname(hostname)
                
                # 判断是否为私有IP或本地回环
                if ip.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.', 
                                 '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                                 '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                                 '172.30.', '172.31.', '192.168.', '127.', '169.254.')):
                    logger.debug(f"🌍 IP检测: {hostname} -> 国内 (私有IP: {ip})")
                    return True
                
                # 这里可以添加更精确的中国IP段判断
                # 简单判断：以 1. 开头的部分中国IP（不完整，但可用）
                if ip.startswith('1.'):
                    logger.debug(f"🌍 IP检测: {hostname} -> 可能国内 (IP: {ip})")
                    # 不确定时默认使用代理更安全
                    return False
                    
        except (socket.gaierror, socket.timeout):
            # DNS解析失败，默认使用代理
            pass
        
        logger.debug(f"🌍 域名检测: {domain} -> 国际域名")
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ 域名检测失败: {url} - {e}")
        # 解析失败时默认使用代理（更安全）
        return False


def get_proxy_config():
    """
    获取代理配置（优先从.env文件读取，然后从环境变量读取）
    
    Returns:
        dict: 代理配置
    """
    global _proxy_config_cache
    
    if _proxy_config_cache is None:
        # 优先从.env文件读取代理配置
        http_proxy = None
        https_proxy = None
        no_proxy = ''
        
        # 直接读取.env文件
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                if key == 'HTTP_PROXY':
                                    http_proxy = value
                                elif key == 'HTTPS_PROXY':
                                    https_proxy = value
                                elif key == 'NO_PROXY':
                                    no_proxy = value
                logger.info(f"🔧 从.env文件加载代理配置: HTTP={http_proxy}, HTTPS={https_proxy}")
            except Exception as e:
                logger.warning(f"⚠️  直接读取.env文件失败: {e}，使用环境变量")
        else:
            logger.warning(f"⚠️  .env文件不存在: {env_file}，使用环境变量")
        
        # 如果从.env文件读取失败，从环境变量读取
        if not http_proxy:
            http_proxy = os.getenv('HTTP_PROXY')
        if not https_proxy:
            https_proxy = os.getenv('HTTPS_PROXY')
        if not no_proxy:
            no_proxy = os.getenv('NO_PROXY', '')
        
        # 解析NO_PROXY（逗号分隔的域名列表）
        no_proxy_domains = []
        if no_proxy:
            no_proxy_domains = [domain.strip() for domain in no_proxy.split(',') if domain.strip()]
        
        _proxy_config_cache = {
            'http_proxy': http_proxy,
            'https_proxy': https_proxy,
            'no_proxy': no_proxy_domains,
            'enabled': bool(http_proxy or https_proxy)
        }
        
        logger.debug(f"🔧 代理配置加载完成: HTTP={http_proxy}, HTTPS={https_proxy}, NO_PROXY={no_proxy_domains}")
    
    return _proxy_config_cache


def should_use_proxy_for_url(url: str, force_proxy: bool = None) -> bool:
    """
    判断给定URL是否应该使用代理
    
    Args:
        url: 要访问的URL
        force_proxy: 强制设置代理模式
                    True: 强制使用代理
                    False: 强制不使用代理
                    None: 自动判断
    
    Returns:
        bool: True表示应该使用代理
    """
    # 如果强制指定了代理模式，直接返回
    if force_proxy is not None:
        return force_proxy
    
    # 获取代理配置
    proxy_config = get_proxy_config()
    
    # 如果没有配置代理，直接返回False
    if not proxy_config['enabled']:
        logger.debug(f"🔧 无代理配置，直连访问: {url[:50]}...")
        return False
    
    # 检查是否在NO_PROXY列表中
    try:
        domain = urlparse(url).netloc.lower()
        if ':' in domain:
            domain = domain.split(':')[0]
        
        for no_proxy_domain in proxy_config['no_proxy']:
            if domain.endswith(no_proxy_domain.strip('.')):
                logger.debug(f"🔧 NO_PROXY匹配: {domain} -> 直连")
                return False
    except (KeyError, TypeError, AttributeError):
        pass
    
    # 智能判断：国内域名直连，国际域名使用代理
    use_proxy = not is_domestic_domain(url)
    
    if use_proxy:
        logger.debug(f"🔧 智能代理: {url[:50]}... -> 使用代理")
    else:
        logger.debug(f"🔧 智能代理: {url[:50]}... -> 直连")
    
    return use_proxy


def create_retry_session(
    timeout: int = 30,
    retries: int = 3,
    backoff_factor: float = 1.0,
    ignore_ssl: bool = False,
    force_proxy: bool = None,  # True: 强制代理, False: 强制直连, None: 自动
    proxy_url: str = None      # 自定义代理URL，如 "http://127.0.0.1:10809"
) -> requests.Session:
    """
    创建带重试机制的请求会话（支持智能代理切换）
    
    Args:
        timeout: 请求超时时间（秒）- Windows建议30+
        retries: 最大重试次数
        backoff_factor: 重试间隔因子
        ignore_ssl: 是否忽略SSL验证（Windows有时需要）
        force_proxy: 强制代理模式
        proxy_url: 自定义代理URL
    
    Returns:
        requests.Session: 配置好的会话对象
    """
    session = requests.Session()
    
    # Windows优化：更宽松的重试策略
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "HEAD"],
        raise_on_status=False
    )
    
    # Windows适配：更大的连接池
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,      # Windows需要更多连接
        pool_maxsize=20,
        pool_block=False
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # 会话配置
    session.timeout = timeout
    session.verify = not ignore_ssl
    session.headers.update(HEADERS)
    
    # 保存配置参数供后续使用
    session._force_proxy = force_proxy
    session._proxy_url = proxy_url
    
    # 获取默认代理配置
    proxy_config = get_proxy_config()
    
    # 请求监控和智能代理切换
    original_request = session.request
    
    def smart_request(method, url, **kwargs):
        """
        智能代理请求：根据URL自动决定是否使用代理
        """
        start_time = time.time()
        # Windows路径安全：不记录完整URL中的敏感信息
        safe_url = url[:80] + "..." if len(url) > 80 else url
        
        # 确定是否使用代理
        use_proxy = should_use_proxy_for_url(url, force_proxy)
        
        # 确定使用的代理URL
        actual_proxy_url = None
        if use_proxy:
            # 优先使用传入的proxy_url，然后使用环境变量配置的代理
            if proxy_url:
                actual_proxy_url = proxy_url
            else:
                # 根据协议选择代理
                if url.startswith('https://'):
                    actual_proxy_url = proxy_config['https_proxy']
                else:
                    actual_proxy_url = proxy_config['http_proxy']
        
        # 配置代理
        proxies = {}
        if use_proxy and actual_proxy_url:
            proxies = {
                'http': actual_proxy_url,
                'https': actual_proxy_url
            }
            logger.info(f"🌐 使用代理访问: {method} {safe_url} (代理: {actual_proxy_url})")
        elif use_proxy and not actual_proxy_url:
            # 使用系统代理（如果有）
            logger.info(f"🌐 使用系统代理访问: {method} {safe_url}")
            # 不设置proxies，让requests使用系统代理
        else:
            # 强制不使用代理
            proxies = {'http': None, 'https': None}
            logger.info(f"🌐 直连访问: {method} {safe_url}")
        
        # 应用代理设置
        if proxies:
            kwargs['proxies'] = proxies
        
        # 添加超时设置
        kwargs.setdefault('timeout', timeout)
        
        # 执行请求
        try:
            response = original_request(method, url, **kwargs)
            elapsed = time.time() - start_time
            
            # Windows网络诊断
            if elapsed > 5.0:
                logger.warning(f"⚠️  慢请求: {method} {safe_url} - {elapsed:.2f}s")
            
            logger.debug(f"🌐 HTTP请求完成: {method} {safe_url} - {response.status_code} ({elapsed:.2f}s)")
            return response
            
        except socket.timeout:
            elapsed = time.time() - start_time
            logger.error(f"⏰ Windows套接字超时: {method} {safe_url} ({elapsed:.2f}s)")
            # 如果使用代理时超时，可以尝试直连重试（可选）
            if use_proxy and retries > 0:
                logger.warning(f"🔄 代理超时，尝试直连重试: {safe_url}")
                kwargs['proxies'] = {'http': None, 'https': None}
                return original_request(method, url, **kwargs)
            raise
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_type = type(e).__name__
            logger.error(f"❌ 请求失败: {method} {safe_url} - {error_type} ({elapsed:.2f}s)")
            
            # 特殊错误处理
            if "SOCKS" in str(e) or "proxy" in str(e).lower():
                logger.warning(f"🔧 代理错误，尝试直连: {safe_url}")
                # 尝试不使用代理重试一次
                kwargs['proxies'] = {'http': None, 'https': None}
                return original_request(method, url, **kwargs)
            
            raise
    
    # 替换原始request方法
    session.request = smart_request
    
    return session


def create_direct_session(**kwargs) -> requests.Session:
    """
    创建直连会话（强制不使用代理）
    
    Args:
        **kwargs: 传递给create_retry_session的参数
        
    Returns:
        requests.Session: 直连会话对象
    """
    kwargs['force_proxy'] = False
    return create_retry_session(**kwargs)


def create_proxy_session(proxy_url: str = None, **kwargs) -> requests.Session:
    """
    创建代理会话（强制使用代理）
    
    Args:
        proxy_url: 代理URL，如 "http://127.0.0.1:10809"
        **kwargs: 传递给create_retry_session的参数
        
    Returns:
        requests.Session: 代理会话对象
    """
    kwargs['force_proxy'] = True
    kwargs['proxy_url'] = proxy_url
    return create_retry_session(**kwargs)


def safe_request(
    url: str,
    method: str = "GET",
    session: requests.Session = None,
    force_proxy: bool = None,
    **kwargs
) -> requests.Response:
    """
    安全的HTTP请求包装器（Windows错误处理优化，支持智能代理）
    
    Args:
        url: 请求URL
        method: HTTP方法
        session: 可选的会话对象
        force_proxy: 强制代理模式
        **kwargs: 传递给session.request的参数
        
    Returns:
        requests.Response: 响应对象
    """
    if session is None:
        # 创建智能会话
        session = create_retry_session(force_proxy=force_proxy)
    
    try:
        # Windows特定：增加超时容错
        kwargs.setdefault('timeout', session.timeout)
        
        response = session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
        
    except requests.exceptions.Timeout as e:
        logger.error(f"⏰ 请求超时: {url} (超时设置: {session.timeout}s)")
        # Windows网络诊断建议
        logger.info("💡 Windows网络诊断:")
        logger.info("  1. 检查防火墙设置")
        logger.info("  2. 检查代理配置")
        logger.info("  3. 尝试增加timeout参数")
        raise
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        logger.error(f"🚨 HTTP错误 {status_code}: {url}")
        
        # Windows特定HTTP错误处理
        if status_code == 403:
            logger.warning("🔒 403错误：可能是Windows防火墙或权限问题")
        elif status_code == 407:
            logger.warning("🔒 407错误：需要代理认证")
            
        raise
        
    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        logger.error(f"❌ 请求失败: {url} - {error_type}: {str(e)[:100]}")
        raise


# 导出所有功能
__all__ = [
    'create_retry_session', 
    'create_direct_session',
    'create_proxy_session',
    'safe_request', 
    'HEADERS',
    'is_domestic_domain',
    'should_use_proxy_for_url',
    'get_proxy_config'
]

# 测试函数
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("🧪 Windows HTTP工具模块 - 智能代理版本自测试")
    print("=" * 60)
    
    try:
        # 测试会话创建
        print("1. 测试会话创建...")
        session = create_retry_session(timeout=10, retries=2)
        print(f"   ✅ 智能会话创建成功")
        print(f"      - 超时: {session.timeout}s")
        print(f"      - 重试次数: {session.adapters['https://'].max_retries.total}")
        
        # 测试域名检测
        print("\n2. 测试域名检测...")
        test_urls = [
            ("https://www.xinhuanet.com/politics/", "国内新闻"),
            ("https://www.people.com.cn/", "人民日报"),
            ("https://newsapi.org/v2/sources", "NewsAPI"),
            ("https://www.bbc.com/news", "BBC"),
            ("http://localhost:8000", "本地服务"),
            ("https://www.baidu.com", "百度")
        ]
        
        for url, name in test_urls:
            is_domestic = is_domestic_domain(url)
            proxy_needed = not is_domestic
            print(f"   🔍 {name}: {url[:40]:<40} -> 国内: {is_domestic}, 需要代理: {proxy_needed}")
        
        # 测试代理配置读取
        print("\n3. 测试代理配置...")
        proxy_config = get_proxy_config()
        print(f"   🔧 代理配置:")
        print(f"      - HTTP代理: {proxy_config['http_proxy'] or '无'}")
        print(f"      - HTTPS代理: {proxy_config['https_proxy'] or '无'}")
        print(f"      - NO_PROXY: {proxy_config['no_proxy']}")
        print(f"      - 已启用: {proxy_config['enabled']}")
        
        # 测试不同类型的会话
        print("\n4. 测试会话类型...")
        
        # 测试直连会话
        print("   🟢 直连会话测试...")
        direct_session = create_direct_session(timeout=5)
        try:
            response = direct_session.get("http://httpbin.org/ip", timeout=5)
            print(f"      ✅ 直连成功: IP={response.json().get('origin', '未知')}")
        except Exception as e:
            print(f"      ⚠️  直连测试失败: {type(e).__name__}")
        
        # 测试代理会话（如果配置了代理）
        proxy_url = os.getenv('HTTP_PROXY')
        if proxy_url:
            print(f"   🔵 代理会话测试 (使用: {proxy_url})...")
            proxy_session = create_proxy_session(proxy_url=proxy_url, timeout=5)
            try:
                response = proxy_session.get("http://httpbin.org/ip", timeout=5)
                print(f"      ✅ 代理成功: IP={response.json().get('origin', '未知')}")
            except Exception as e:
                print(f"      ❌ 代理测试失败: {type(e).__name__}")
        else:
            print("   🔵 代理会话测试: ⚠️ 未配置代理，跳过")
        
        # 测试智能会话
        print("   🎯 智能会话测试...")
        smart_session = create_retry_session(timeout=5)
        
        # 测试国内网站（应直连）
        test_domestic = "https://www.baidu.com"
        use_proxy = should_use_proxy_for_url(test_domestic)
        print(f"      🏠 国内网站 {test_domestic[:30]}... -> 使用代理: {use_proxy}")
        
        # 测试国际网站（应使用代理）
        test_international = "https://www.google.com"
        use_proxy = should_use_proxy_for_url(test_international)
        print(f"      🌎 国际网站 {test_international[:30]}... -> 使用代理: {use_proxy}")
        
        print("\n🎯 Windows HTTP工具模块测试完成！")
        print("\n💡 使用说明:")
        print("   1. 配置代理: 在.env文件中设置HTTP_PROXY和HTTPS_PROXY")
        print("   2. 国内域名: 自动直连，无需代理")
        print("   3. 国际域名: 自动使用代理")
        print("   4. 手动控制: 使用force_proxy参数强制指定代理模式")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()