class TypeErrorHTTPStatus(Exception):
    """Исключение статуса сервиса."""

    pass


class DictKeyError(Exception):
    """Исключение ключа словаря."""

    pass


class KeyErrorStatus(Exception):
    """Исключение отсутсвия ключа в статусе."""

    pass


class NetError(Exception):
    """Исключене отуствия нтернета."""

    pass


class JsonError(Exception):
    """Исключене отуствия Json."""

    pass
