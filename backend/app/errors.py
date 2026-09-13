class EmbedError(Exception):
    pass


class ModelTimeoutError(Exception):
    pass


class ModelUnavailableError(Exception):
    pass


class ModelRateLimitedError(ModelUnavailableError):
    pass
