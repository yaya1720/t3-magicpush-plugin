from __future__ import annotations
from typing import Any
import requests
from core.sdk import AutomationProvider, BasePlugin, OperationResult

DEFAULT_EVENTS = ["task.completed", "task.failed"]

class MagicPushAutomationPlugin(BasePlugin, AutomationProvider):
    plugin_id = "automation.magicpush"
    plugin_name = "魔法推送通知"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._runtime_config: dict[str, Any] = {}

    def set_runtime_config(self, config: dict[str, Any]) -> None:
        self._runtime_config = self._normalize_runtime_config(config)

    def validate_runtime_config(self, config: dict[str, Any]) -> OperationResult:
        normalized = self._normalize_runtime_config(config)
        errors: list[str] = []
        if not str(normalized.get("url") or "").strip():
            errors.append("缺少必填配置：url")
        if not str(normalized.get("token") or "").strip():
            errors.append("缺少必填配置：token")
        if errors:
            return OperationResult(success=False, message="插件配置校验失败。", errors=errors)
        return OperationResult(success=True, message="插件配置校验通过。", data=normalized)

    def health(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "message": "魔法推送通知插件运行正常。",
            "details": {
                "configured": self._is_configured(),
                "subscribed_events": self.subscribed_events(),
            },
        }

    def subscribed_events(self) -> list[str]:
        raw = str(self._runtime_config.get("enabled_events") or ",".join(DEFAULT_EVENTS))
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return values or list(DEFAULT_EVENTS)

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = str(event.get("event_type") or "unknown")
        title, content = self._build_message(event)
        url = self._runtime_config.get("url")
        token = self._runtime_config.get("token")

        payload = {
            "title": title,
            "content": content,
            "type": "text"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            success = True
            message = f"通知发送成功，状态码：{response.status_code}"
        except requests.exceptions.RequestException as e:
            success = False
            message = f"通知发送失败：{str(e)}"

        return OperationResult(
            success=success,
            message=f"{self.plugin_name} 已处理事件：{event_type}。{message}",
            data={
                "configured": self._is_configured(),
                "request_payload": payload,
                "response_status": response.status_code if 'response' in locals() else None,
            },
        ).model_dump(mode="json")

    def _is_configured(self) -> bool:
        return bool(str(self._runtime_config.get("url") or "").strip()) and \
               bool(str(self._runtime_config.get("token") or "").strip())

    @staticmethod
    def _normalize_runtime_config(config: dict[str, Any] | None) -> dict[str, Any]:
        return dict(config or {})

    @staticmethod
    def _build_message(event: dict[str, Any]) -> tuple[str, str]:
        event_type = str(event.get("event_type") or "unknown")
        payload = dict(event.get("payload") or {})
        task_name = str(
            payload.get("task_name")
            or payload.get("title")
            or event.get("task_id")
            or "未命名任务"
        )
        summary = str(payload.get("summary") or "").strip()
        error_message = str(
            payload.get("error_message")
            or payload.get("error")
            or summary
            or "未知错误"
        ).strip()

        if event_type == "task.completed":
            content = f"{task_name} 已执行完成。"
            if summary:
                content = f"{content} {summary}"
            return "[任务完成]", content

        if event_type == "task.failed":
            return "[任务失败]", f"{task_name} 执行失败：{error_message}"

        if summary:
            return "[系统通知]", f"{task_name}：{summary}"
        return "[系统通知]", f"{task_name} 触发事件：{event_type}"

plugin = MagicPushAutomationPlugin()