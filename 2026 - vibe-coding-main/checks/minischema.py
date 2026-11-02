"""最小 JSON Schema 驗證器（純內建函式庫，約 70 行）。

為什麼要自己寫一個：
  AGENTS.md §4 說「不准 pip install」。一個需要安裝才能跑的閘門等於沒有閘門。
  這裡只支援本專案 schema 用到的關鍵字，看得懂、改得動。

支援：type（含多型別陣列）／required／properties／additionalProperties
      minimum／maximum／enum／items
正式專案請改用 `jsonschema` 套件——用法與形狀幾乎一樣，換掉這支就好。
"""
from __future__ import annotations

from typing import Any, Dict, List

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


class SchemaError(Exception):
    """資料不符合契約。訊息一律指出「哪一個欄位、為什麼」。"""


def _type_ok(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        py = _TYPES.get(name)
        if py is None:
            continue
        # bool 是 int 的子類；integer/number 不該接受 True/False
        if name in ("integer", "number") and isinstance(value, bool):
            continue
        if name == "boolean" and not isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def validate(data: Any, schema: Dict[str, Any], path: str = "$") -> None:
    """不符合就 raise SchemaError；符合就靜靜回來。"""
    if "type" in schema and not _type_ok(data, schema["type"]):
        raise SchemaError(f"{path} 型別錯誤：需要 {schema['type']}，實際是 {type(data).__name__}")

    if "enum" in schema and data not in schema["enum"]:
        raise SchemaError(f"{path} 不在允許的選項內：{schema['enum']}（實際 {data!r}）")

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            raise SchemaError(f"{path} 太小：最小 {schema['minimum']}，實際 {data}")
        if "maximum" in schema and data > schema["maximum"]:
            raise SchemaError(f"{path} 太大：最大 {schema['maximum']}，實際 {data}")

    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                raise SchemaError(f"{path} 缺少必填欄位：{key}")
        props: Dict[str, Any] = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(data) - set(props))
            if extra:
                raise SchemaError(f"{path} 出現契約沒有定義的欄位：{extra}")
        for key, sub in props.items():
            if key in data:
                validate(data[key], sub, f"{path}.{key}")

    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            validate(item, schema["items"], f"{path}[{i}]")


def violations(data: Any, schema: Dict[str, Any]) -> List[str]:
    """回傳錯誤訊息清單（空清單＝通過）。方便閘門一次印完所有問題。"""
    try:
        validate(data, schema)
    except SchemaError as exc:
        return [str(exc)]
    return []
