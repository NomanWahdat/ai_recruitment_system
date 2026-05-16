import logging
from collections import defaultdict
from threading import RLock
from typing import Any, Callable, DefaultDict, List

logger = logging.getLogger(__name__)
Handler = Callable[[dict], Any]


class EventBus:
    def __init__(self):
        self._lock = RLock()
        self._subscribers: DefaultDict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def emit(self, event_type: str, payload: dict) -> list:
        with self._lock:
            handlers = list(self._subscribers.get(event_type, []))

        results = []
        for handler in handlers:
            try:
                result = handler(payload or {})
                results.append(result)
            except Exception as exc:
                logger.exception("Event handler failed for %s: %s", event_type, exc)
                results.append({"error": str(exc), "event_type": event_type})
        return results


event_bus = EventBus()
