import json


def dump_json(data) -> str:
    return json.dumps(data, ensure_ascii=False)
