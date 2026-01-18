"""
LLM 客户端

支持 OpenAI 兼容的 API（NewAPI / OneAPI / OpenAI / Azure 等）
"""

import os
import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    model: str = ""
    usage: Dict[str, int] = None
    finish_reason: str = ""
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {}


class LLMClient:
    """
    LLM 客户端
    
    支持 OpenAI 兼容的 API 格式，可接入：
    - NewAPI / OneAPI
    - OpenAI
    - Azure OpenAI
    - 其他兼容 API
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 LLM 客户端
        
        Args:
            config: LLM 配置字典
        """
        self.config = config or {}
        
        # API 配置（优先使用环境变量）
        self.api_base_url = os.environ.get('LLM_API_BASE_URL') or self.config.get('api_base_url', '')
        self.api_key = os.environ.get('LLM_API_KEY') or self.config.get('api_key', '')
        self.model_name = os.environ.get('LLM_MODEL_NAME') or self.config.get('model_name', 'gpt-4o-mini')
        
        # 请求参数
        self.timeout = self.config.get('timeout', 120)
        self.max_tokens = self.config.get('max_tokens', 4096)
        self.temperature = self.config.get('temperature', 0.7)
        self.max_retries = self.config.get('max_retries', 2)
        
        # 是否启用
        self.enabled = self.config.get('enabled', True)
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if not self.api_base_url:
            logger.warning("LLM API base URL 未配置，AI 功能将不可用")
            self.enabled = False
        
        if not self.api_key:
            logger.warning("LLM API key 未配置，AI 功能将不可用")
            self.enabled = False
    
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return self.enabled and bool(self.api_base_url) and bool(self.api_key)
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> ChatResponse:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大 token 数（可选，覆盖默认值）
            **kwargs: 其他参数
            
        Returns:
            ChatResponse: 聊天响应
        """
        if not self.is_available():
            raise RuntimeError("LLM 客户端不可用，请检查配置")
        
        import aiohttp
        
        # 构建请求
        url = f"{self.api_base_url.rstrip('/')}/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': self.model_name,
            'messages': [{'role': m.role, 'content': m.content} for m in messages],
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
            **kwargs
        }
        
        # 重试逻辑
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise RuntimeError(f"API 请求失败 ({response.status}): {error_text[:500]}")
                        
                        data = await response.json()
                
                # 解析响应
                choice = data.get('choices', [{}])[0]
                message = choice.get('message', {})
                
                return ChatResponse(
                    content=message.get('content', ''),
                    model=data.get('model', self.model_name),
                    usage=data.get('usage', {}),
                    finish_reason=choice.get('finish_reason', '')
                )
                
            except asyncio.TimeoutError:
                last_error = f"请求超时 ({self.timeout}秒)"
                logger.warning(f"LLM 请求超时，重试 {attempt + 1}/{self.max_retries + 1}")
                
            except aiohttp.ClientError as e:
                last_error = f"网络错误: {str(e)}"
                logger.warning(f"LLM 请求网络错误，重试 {attempt + 1}/{self.max_retries + 1}: {e}")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM 请求异常，重试 {attempt + 1}/{self.max_retries + 1}: {e}")
            
            # 等待后重试
            if attempt < self.max_retries:
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError(f"LLM 请求失败（重试 {self.max_retries} 次后）: {last_error}")
    
    async def chat_simple(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        简化的聊天接口
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            **kwargs: 其他参数
            
        Returns:
            str: 响应内容
        """
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role='system', content=system_prompt))
        
        messages.append(ChatMessage(role='user', content=prompt))
        
        response = await self.chat(messages, **kwargs)
        return response.content
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Yields:
            str: 响应片段
        """
        if not self.is_available():
            raise RuntimeError("LLM 客户端不可用，请检查配置")
        
        import aiohttp
        
        url = f"{self.api_base_url.rstrip('/')}/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': self.model_name,
            'messages': [{'role': m.role, 'content': m.content} for m in messages],
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
            'stream': True,
            **kwargs
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"API 请求失败 ({response.status}): {error_text[:500]}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or line == 'data: [DONE]':
                        continue
                    
                    if line.startswith('data: '):
                        try:
                            import json
                            data = json.loads(line[6:])
                            delta = data.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                        except Exception:
                            pass
    
    async def count_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量
        
        使用简单的估算方法：中文按字符计算，英文按空格分词
        """
        # 简单估算：中文每个字符约 1-2 tokens，英文每个单词约 1.3 tokens
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len(text.split()) - chinese_chars // 2
        
        return int(chinese_chars * 1.5 + english_words * 1.3)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            'available': self.is_available(),
            'api_base_url': self.api_base_url[:50] + '...' if len(self.api_base_url) > 50 else self.api_base_url,
            'model': self.model_name,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
        }
