"""地基：這個領域會發生的錯誤。

規矩：domain / application 只丟這裡定義的錯誤，不丟框架的錯誤（例如 HTTP 400）。
理由：同一段流程要能在 CLI、排程、測試、未來的 Web API 裡重用；
      一旦丟了框架錯誤，就只能在那個框架裡活著。
      「錯誤怎麼變成 HTTP 狀態碼」是外牆（adapter）的事。
"""
from __future__ import annotations


class DomainError(Exception):
    """所有領域錯誤的根。外牆只要接這一個就能全部對應。"""


class NotFoodError(DomainError):
    """照片不是餐點。

    這條存在的理由（真實事故）：沒有這個錯誤時，系統的預設行為是
    「回 200 ＋ 0 大卡」，前端會渲染一張漂亮的空卡片還附分享按鈕——產品在說謊。
    """

    def __init__(self, reason: str = "看起來不是餐點，請重新拍攝") -> None:
        super().__init__(reason)
        self.reason = reason


class ImageTooLargeError(DomainError):
    """影像超過上限。在呼叫 AI 之前就擋掉＝零成本快速失敗。"""
