# общая ошибка валидации vk

class VkApiError(Exception):
    """
    Единая ошибка для VK API.
    code — код ошибки VK (или наш внутренний код)
    msg  — человекочитаемое сообщение
    raw  — сырой ответ VK (удобно для отладки)
    """
    def __init__(self, code: int, msg: str, *, raw: dict | None = None) -> None:
        super().__init__(f'VK API error {code}: {msg}')
        self.code = code
        self.msg = msg
        self.raw = raw or {}