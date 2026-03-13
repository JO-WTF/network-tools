import json


def parse_message(message):
    try:
        return json.loads(message), None
    except json.JSONDecodeError:
        return None, {
            "success": False,
            "errorType": "parse_error",
            "request": "websocket",
            "response": "无法解析请求内容",
        }
