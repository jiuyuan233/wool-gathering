"""AI 中转站客户端（OpenAI 兼容协议）。

设计要点：
- 通过环境变量配置 base_url / api_key / model，兼容任意 OpenAI 协议中转站
- 支持普通 chat 和 function calling（结构化输出）
- 失败重试 + 超时控制，Action 里跑不能因为一次抖动就全挂
- 所有调用都打日志，方便在 Action 日志里排查
"""
from __future__ import annotations

import json
import time
from collections import deque
from typing import Any

import requests

from utils import env, log, safe_text


class RateLimiter:
    """滑动窗口速率限制器，防止触发中转站限流。"""

    def __init__(self, max_requests: int = 45, window_seconds: int = 300) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._timestamps: deque[float] = deque()

    def wait_if_needed(self) -> None:
        """如果接近限流阈值，等待到安全位置再继续。"""
        now = time.time()
        while self._timestamps and now - self._timestamps[0] > self.window:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_requests:
            wait = self.window - (now - self._timestamps[0]) + 1
            if wait > 0:
                log(f"速率限制：等待 {wait:.0f}s 避免触发中转站限流")
                time.sleep(wait)
            now = time.time()
            while self._timestamps and now - self._timestamps[0] > self.window:
                self._timestamps.popleft()
        self._timestamps.append(time.time())


class AIClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.base_url = (base_url or env("AI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or env("AI_API_KEY", required=True)
        self.model = model or env("AI_MODEL", "gpt-4o-mini")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        self.rate_limiter = RateLimiter(max_requests=45, window_seconds=300)

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        tools: list[dict] | None = None,
        tool_choice: Any = "auto",
        retries: int = 3,
    ) -> dict:
        """调用 chat completions，返回原始响应 JSON。"""
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        last_err = None
        for attempt in range(1, retries + 1):
            try:
                self.rate_limiter.wait_if_needed()
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                if resp.status_code == 429:
                    wait = 5 * attempt
                    log(f"限流 429，等待 {wait}s 后重试 ({attempt}/{retries})")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                wait = 2 * attempt
                log(f"AI 调用失败 ({attempt}/{retries}): {safe_text(e, 200)}", level="ERROR")
                time.sleep(wait)

        raise RuntimeError(f"AI 调用最终失败: {last_err}")

    def chat_text(self, messages: list[dict], **kwargs) -> str:
        """便捷方法：直接拿文本回复。"""
        data = self.chat(messages, **kwargs)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            return ""

    def chat_json(self, messages: list[dict], *, schema_hint: str = "", **kwargs) -> Any:
        """让模型直接输出 JSON 文本并解析。

        策略：在 system 里要求严格 JSON 输出，然后从回复里抠出 JSON 段。
        比依赖 function calling 更通用（部分中转站不支持 tools）。
        """
        sys_msg = {
            "role": "system",
            "content": (
                "你是一个严格的数据抽取器。只输出合法 JSON，不要任何解释、"
                "Markdown 代码块标记或前后缀文字。"
                + (f"\n期望结构：{schema_hint}" if schema_hint else "")
            ),
        }
        data = self.chat([sys_msg, *messages], **kwargs)
        text = ""
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            pass
        return _extract_json(text)


def _extract_json(text: str) -> Any:
    """从模型回复里抠出 JSON（兼容裸 JSON、```json 代码块、前后有解释文字）。"""
    text = text.strip()
    if not text:
        return None
    # 直接试
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 代码块
    import re
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 找第一个 { 或 [ 到最后一个 } 或 ]
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        i = text.find(open_ch)
        j = text.rfind(close_ch)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except json.JSONDecodeError:
                continue
    return None
