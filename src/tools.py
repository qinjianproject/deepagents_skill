from langchain_core.tools import tool
import json
import akshare as ak
import baostock as bs
import pandas as pd
import logging
from tavily import TavilyClient
import requests
import os
from datetime import datetime
from markdownify import markdownify
from dotenv import load_dotenv
load_dotenv()

# 禁用代理，避免连接问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

print("当前工作目录:", os.getcwd())
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
print(TAVILY_API_KEY)
SEARXNG_URL = os.getenv("SEARXNG_URL", "").strip()

# 初始化 Tavily 客户端（如果有 API key）
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

def web_search(query: str, max_results: int = 5):
    """网络搜索：优先使用 Tavily，失败或不可用时降级到 SearXNG"""
    
    # 尝试使用 Tavily
    if tavily_client:
        try:
            result = tavily_client.search(query, max_results=max_results)
            logging.debug(f"使用 Tavily 搜索成功: {query}")
            return result
        except Exception as e:
            logging.warning(f"Tavily 搜索失败，降级到 SearXNG: {str(e)}")
    
    # 使用 SearXNG 后备或主搜索
    if not SEARXNG_URL:
        error_msg = "未配置搜索引擎（需要 TAVILY_API_KEY 或 SEARXNG_URL）"
        logging.error(error_msg)
        return {"error": error_msg}
    
    try:
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": query,
                "format": "json"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])[:max_results]
        
        logging.debug(f"使用 SearXNG 搜索成功: {query}")
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0)
                }
                for r in results
            ]
        }
    except Exception as e:
        error_msg = f"SearXNG 搜索失败: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}

# 启动日志
if tavily_client and SEARXNG_URL:
    logging.info("✅ 搜索引擎已配置：Tavily（主）+ SearXNG（后备）")
elif tavily_client:
    logging.info("✅ 搜索引擎已配置：Tavily（仅）")
elif SEARXNG_URL:
    logging.info("✅ 搜索引擎已配置：SearXNG（仅）")
else:
    logging.warning("⚠️ 未配置任何搜索引擎")

@tool
def search(query: str, max_results: int = 5) -> str:
    """通用网络搜索工具（优先使用Tavily，失败时降级到SearXNG）
    
    参数:
        query: 搜索查询语句，支持中英文
        max_results: 返回的最大结果数量，默认5条
    
    返回值:
        JSON字符串，包含搜索结果列表：
        - title: 标题
        - url: 链接
        - content: 内容摘要
        - score: 相关性评分（仅SearXNG）
    
    使用场景:
        适用于任何需要网络搜索的场景，如查找资料、获取最新信息等
    """
    try:
        results = web_search(query, max_results=max_results)
        return json.dumps({
            "query": query,
            "max_results": max_results,
            "results": results
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)
    

@tool
def fetch_url(url: str, timeout: int = 30) -> dict[str, str]:
    """从 URL 获取内容并将 HTML 转换为 Markdown 格式。

    此工具获取网页内容并将其转换为干净的 Markdown 文本，
    便于阅读和处理 HTML 内容。收到 Markdown 后，
    你必须将信息综合成自然、有帮助的回复给用户。

    参数:
        url: 要获取的 URL（必须是有效的 HTTP/HTTPS URL）
        timeout: 请求超时时间，单位秒（默认：30）

    返回值:
        包含以下内容的字典：
        - success: 请求是否成功
        - url: 重定向后的最终 URL
        - markdown_content: 转换为 Markdown 的页面内容
        - status_code: HTTP 状态码
        - content_length: Markdown 内容的字符长度

    重要提示：使用此工具后：
    1. 阅读 Markdown 内容
    2. 提取回答用户问题所需的相关信息
    3. 将其综合成清晰、自然的语言回复
    4. 除非用户特别要求，否则切勿向用户展示原始 Markdown
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DeepAgents/1.0)"},
        )
        response.raise_for_status()

        # Convert HTML content to markdown
        markdown_content = markdownify(response.text)

        return {
            "url": str(response.url),
            "markdown_content": markdown_content,
            "status_code": response.status_code,
            "content_length": len(markdown_content),
        }
    except Exception as e:
        return {"error": f"Fetch URL error: {e!s}", "url": url}
