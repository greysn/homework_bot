class APIErrException(Exception):
    """Custom Exception class for handling Practicum.Homeworks API errors."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class TheAnswerIsNot200Error(APIErrException):
    """Ответ сервера не равен 200."""


class EmptyDictionaryOrListError(APIErrException):
    """Пустой словарь или список."""


class UndocumentedStatusError(APIErrException):
    """Недокументированный статус."""


class RequestExceptionError(APIErrException):
    """Ошибка запроса."""


class LogicExceptionError(APIErrException):
    """Ошибка логики приложения."""
