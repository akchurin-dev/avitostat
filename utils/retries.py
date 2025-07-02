from utils.logging import TraceLogger


def with_retries(func, retries: int = 3):
    def inner(*args, **kwargs):
        error = None

        tlogger: TraceLogger
        if "tlogger" in kwargs:
            tlogger = kwargs["tlogger"]
        elif "trace_id" in kwargs:
            tlogger = kwargs["trace_id"]
        else:
            tlogger = TraceLogger()

        for _ in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = e
                tlogger.error(e)
        else:
            assert error is not None
            raise error

    return inner
