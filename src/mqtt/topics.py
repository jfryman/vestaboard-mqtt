"""MQTT topic suffix constants."""


class Topics:
    """MQTT topic suffixes."""
    MESSAGE = "message"
    SAVE = "save/+"
    RESTORE = "restore/+"
    DELETE = "delete/+"
    TIMED_MESSAGE = "timed-message"
    CANCEL_TIMER = "cancel-timer/+"
    LIST_TIMERS = "list-timers"
    TIMERS_RESPONSE = "timers-response"
    STATES = "states"
