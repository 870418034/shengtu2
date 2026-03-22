# -*- coding: utf-8 -*-
"""
小米 MiMo API 客户端 - OpenAI 兼容接口
参考: https://platform.xiaomimimo.com/#/docs/api/chat/openai-api

支持功能:
- 对话补全 (chat completion)
- 流式输出 (streaming)
- 提示词优化 (珠宝设计专用)
- 客户需求分析
- 模型列表查询
- 连接测试
"""
import json
import time
import requests
from typing import List, Dict, Optional, Generator
from threading import Lock

from core.config_manager import config
from utils.logger import logger


class MimoApiClient:
    """小米 MiMo API 客户端（OpenAI 兼容）"""

    # MiMo 官方 API 端点（OpenAI 兼容格式）
    DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"

    # 可用模型列表
    AVAILABLE_MODELS = [
        {
            "id": "mimo-v2-flash",
            "name": "MiMo-V2-Flash",
            "description": "小米最新 MoE 架构模型，免费使用",
            "free": True,
            "context_length": 32768,
        },
        {
            "id": "mimo-v2-lite",
            "name": "MiMo-V2-Lite",
            "description": "轻量级模型，响应更快",
            "free": False,
            "context_length": 16384,
        },
        {
            "id": "mimo-v1",
            "name": "MiMo-V1",
            "description": "第一代模型",
            "free": False,
            "context_length": 8192,
        },
    ]

    def __init__(self):
        self._lock = Lock()

    def _get_config(self) -> dict:
        """获取当前 API 配置"""
        mimo_cfg = config.get_section("mimo_api")
        return {
            "api_key": mimo_cfg.get("api_key", ""),
            "base_url": mimo_cfg.get("base_url", self.DEFAULT_BASE_URL).rstrip("/"),
            "model": mimo_cfg.get("model", "mimo-v2-flash"),
            "timeout": mimo_cfg.get("timeout", 60),
            "max_retries": mimo_cfg.get("max_retries", 3),
        }

    def _get_headers(self, api_key: str) -> dict:
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def _make_request(self, endpoint: str, data: dict, stream: bool = False) -> requests.Response:
        """发起 API 请求"""
        cfg = self._get_config()
        if not cfg["api_key"]:
            raise ValueError("MiMo API Key 未配置，请在设置中填入 API Key")

        url = f"{cfg['base_url']}{endpoint}"
        headers = self._get_headers(cfg["api_key"])

        last_error = None
        for attempt in range(cfg["max_retries"]):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=cfg["timeout"],
                    stream=stream,
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 401:
                    raise ValueError("API Key 无效，请检查设置")
                elif response.status_code == 429:
                    # 限流，等待后重试
                    wait = min(2 ** attempt, 10)
                    logger.warning(f"MiMo API 限流，等待 {wait}s 后重试")
                    time.sleep(wait)
                    continue
                elif response.status_code >= 500:
                    last_error = f"服务器错误 ({response.status_code})"
                    time.sleep(1)
                    continue
                else:
                    error_msg = self._parse_error(response)
                    raise ValueError(f"API 请求失败 ({response.status_code}): {error_msg}")
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"MiMo API 超时，第 {attempt + 1} 次重试")
            except requests.exceptions.ConnectionError:
                last_error = "连接失败，请检查网络或 Base URL"
                logger.warning(f"MiMo API 连接失败，第 {attempt + 1} 次重试")
                time.sleep(1)
            except ValueError:
                raise

        raise ValueError(f"MiMo API 请求失败: {last_error}")

    def _parse_error(self, response: requests.Response) -> str:
        """解析错误响应"""
        try:
            err = response.json()
            return err.get("error", {}).get("message", response.text[:200])
        except Exception:
            return response.text[:200]

    # ==================== 核心 API ====================

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict:
        """
        对话补全接口

        Args:
            messages: 消息列表 [{"role": "user/system/assistant", "content": "..."}]
            model: 模型名称，默认使用配置中的模型
            temperature: 温度 (0-2)
            max_tokens: 最大输出 token 数
            stream: 是否流式输出

        Returns:
            完成响应字典
        """
        cfg = self._get_config()
        payload = {
            "model": model or cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_chat(payload)

        response = self._make_request("/chat/completions", payload)
        return response.json()

    def _stream_chat(self, payload: dict) -> Generator[str, None, None]:
        """流式对话"""
        response = self._make_request("/chat/completions", payload, stream=True)
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8").strip()
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def chat(self, message: str, system_prompt: str = None, model: str = None) -> str:
        """简易对话接口"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        result = self.chat_completion(messages, model=model)
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # ==================== 珠宝设计专用 ====================

    def generate_design_description(self, chinese_desc: str) -> str:
        """将中文珠宝描述转为高质量英文 SD 提示词"""
        system = (
            "你是一个专业的珠宝设计AI提示词专家。"
            "将用户的中文珠宝描述转为高质量的英文 Stable Diffusion 提示词。"
            "要求：1) 使用专业珠宝术语 2) 包含材质、工艺、风格细节 "
            "3) 添加摄影和渲染质量关键词 4) 纯英文输出，逗号分隔"
        )
        return self.chat(chinese_desc, system_prompt=system)

    def analyze_customer_need(self, need_desc: str) -> list:
        """分析客户需求，生成设计方案"""
        system = (
            "你是一个珠宝设计师AI助手。根据客户需求分析，生成2-3个设计方案。"
            "每个方案包含：name(方案名)、description(描述)、budget_range(预算区间)、"
            "sd_prompt(英文SD提示词)。以JSON数组格式返回。"
        )
        result = self.chat(need_desc, system_prompt=system)
        try:
            # 尝试解析 JSON
            json_str = result
            if "```" in result:
                # 提取代码块中的 JSON
                start = result.find("```")
                if result.find("```json", start) >= 0:
                    start = result.find("```json") + 7
                else:
                    start = start + 3
                end = result.find("```", start)
                json_str = result[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            # 解析失败，返回结构化文本
            return [{"name": "AI方案", "description": result, "budget_range": "待定", "sd_prompt": ""}]

    def suggest_training_params(self, info: dict) -> dict:
        """根据数据集信息推荐训练参数"""
        system = (
            "你是一个LoRA训练专家。根据数据集信息推荐最佳训练参数。"
            "返回JSON格式：{rank, learning_rate_unet, learning_rate_te, epochs, notes}"
        )
        msg = f"项目: {info.get('project_name', '未知')}, 图片数量: {info.get('image_count', 0)}"
        result = self.chat(msg, system_prompt=system)
        try:
            json_str = result
            if "```" in result:
                start = result.find("```")
                if result.find("```json", start) >= 0:
                    start = result.find("```json") + 7
                else:
                    start = start + 3
                end = result.find("```", start)
                json_str = result[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {"rank": 32, "learning_rate_unet": "1e-4", "learning_rate_te": "5e-5", "epochs": 10, "notes": "默认参数"}

    def generate_trigger_words(self, project_names: list) -> dict:
        """生成 LoRA 触发词"""
        system = (
            "你是一个LoRA触发词专家。根据项目名称生成合适的触发词。"
            "返回JSON格式：{trigger_words: [...], prompt_template: '...'}"
        )
        msg = f"项目名称: {', '.join(project_names)}"
        result = self.chat(msg, system_prompt=system)
        try:
            json_str = result
            if "```" in result:
                start = result.find("```")
                if result.find("```json", start) >= 0:
                    start = result.find("```json") + 7
                else:
                    start = start + 3
                end = result.find("```", start)
                json_str = result[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {"trigger_words": project_names, "prompt_template": f"{', '.join(project_names)}, " + "{}"}

    def search_keywords_from_image(self, image_path: str) -> dict:
        """根据图片生成搜索关键词（纯文本分析）"""
        system = (
            "你是一个珠宝图片分析专家。根据图片描述生成搜索关键词。"
            "返回JSON格式：{cn_keywords: [...], en_keywords: [...]}"
        )
        msg = f"请为这张珠宝图片生成中文和英文搜索关键词"
        result = self.chat(msg, system_prompt=system)
        try:
            json_str = result
            if "```" in result:
                start = result.find("```")
                if result.find("```json", start) >= 0:
                    start = result.find("```json") + 7
                else:
                    start = start + 3
                end = result.find("```", start)
                json_str = result[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {"cn_keywords": ["珠宝设计"], "en_keywords": ["jewelry design"]}

    # ==================== 连接测试 ====================

    def test_connection(self) -> dict:
        """测试 MiMo API 连接"""
        try:
            cfg = self._get_config()
            if not cfg["api_key"]:
                return {"connected": False, "error": "API Key 未配置"}

            # 发送简单请求测试
            result = self.chat("Hi", model=cfg["model"])
            return {
                "connected": True,
                "model": cfg["model"],
                "response": result[:100] if result else "",
            }
        except ValueError as e:
            return {"connected": False, "error": str(e)}
        except Exception as e:
            return {"connected": False, "error": f"未知错误: {e}"}

    @classmethod
    def get_available_models(cls) -> list:
        """获取可用模型列表"""
        return cls.AVAILABLE_MODELS


# ==================== 全局实例 ====================
mimo_api = MimoApiClient()
