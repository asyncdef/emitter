"""IEmitter implementation."""

import collections
import typing


class _Once:

    """Internal container for one-time listeners."""

    __slots__ = ('func')

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Emitter:

    """Subscribe to asynchronous events.

    Events are case-sensitive strings defined by the emitter. Consumers bind
    callbacks using `on("event", callback)`. Callbacks are executed with
    exactly the same args and kwargs as the call to
    `emit("event", *args, **kwargs)` that triggered them. Which events are
    available and with what signature listeners will be called must be defined
    and documented by emitters. All emitters produce the following events:

        -   new_listener

            Triggered immediately before a new listener is attached for an
            event. Listeners are called with the following signature:

                def listener(event: str, new_listener: typing.Callable)

        -   remove_listener

            Triggered immediately after a listener is removed from the emitter.
            Listeners are called with the following signature:

                def listener(event: str, removed: typing.Callable)

        -   error

            Triggered any time an exception is raised within the emitter while
            calling listener functions. Listeners are called wit hthe following
            siganture:

                def listener(event: str, exc: Exception)

            Listeners are called from within an `except` block and
            `sys.exc_info` is available if needed. If there are no listeners
            for this event then the exception is allowed to bubble up. Any
            additional exceptions raised by error listeners are not handled.
    """

    default_max_listeners = 10

    def __init__(self, *args, **kwargs):
        """Initialize the mixin values."""
        super().__init__(*args, **kwargs)
        self._events = collections.defaultdict(list)
        self._removals = collections.defaultdict(list)
        self._additions = collections.defaultdict(list)
        self._max_listeners = self.default_max_listeners
        self._emitting = []

    @property
    def max_listeners(self) -> int:
        """Get the max listeners per event before this instance warns."""
        return self._max_listeners

    @max_listeners.setter
    def max_listeners(self, value: int):
        """Set the max listeners value."""
        self._max_listeners = int(value)

    def listeners(self, event: str) -> typing.Iterable[typing.Callable]:
        """Get an iterable of listeners for a given event.

        Args:
            event (str): The case-sensitive name of an event.

        Returns:
            typing.Iterable[typing.Callable]: An iterable of listeners.
        """
        return (
            listener.func if isinstance(listener, _Once) else listener
            for listener in self._events.get(event, ())
        )

    def listeners_count(self, event: str) -> int:
        """Get the number of listeners for a given event.

        Args:
            event (str): The case-sensitive name of an event.

        Returns:
            int: The number of listeners for the event.
        """
        return len(self._events.get(event, ()))

    def _on(self, event: str, listener: typing.Callable) -> None:
        """Add a listener and fire the new_listener event."""
        self.emit('new_listener', event, listener)
        self._events[event].append(listener)

    def on(self, event: str, listener: typing.Callable) -> None:
        """Add a listener for the given event.

        This method will not add listeners while the event is being emitted.
        If called while emitting the same event, the emitter will queue the
        request and process it after all listerners are called.

        Args:
            event (str): The case-sensitive name of an event.
            listener (typing.Callable): The function to execute when the event
                is emitted.
        """
        if event not in self._emitting:

            return self._on(event, listener)

        self._additions[event].append(listener)

    def once(self, event: str, listener: typing.Callable) -> None:
        """Add a one time listener for the given event.

        This method will not add listeners while the event is being emitted.
        If called while emitting the same event, the emitter will queue the
        request and process it after all listerners are called.

        Args:
            event (str): The case-sensitive name of an event.
            listener (typing.Callable): The function to execute when the event
                is emitted.
        """
        if event not in self._emitting:

            return self._on(event, _Once(listener))

        self._additions[event].append(_Once(listener))

    def _remove(self, event: str, listener: typing.Callable) -> None:
        """Remove a listener and fire the remove_listener event."""
        raw_listeners = (
            listener.func if isinstance(listener, _Once) else listener
            for listener in self._events.get(event, ())
        )
        for offset, _listener in enumerate(raw_listeners):

            if listener == _listener:

                break

        else:

            return None

        self._events[event].pop(offset)
        self.emit('remove_listener', event, listener)

    def remove(self, event: str, listener: typing.Callable) -> None:
        """Remove a listener from an event.

        This method removes, at most, one listener from the given event.
        Listeners are removed in the order in which they were registered.

        This method will not remove listeners while the event is being emitted.
        If called while emitting the same event, the emitter will queue the
        request and process it after all listeners are called.

        Args:
            event (str): The case-sensitive name of an event.
            listener (typing.Callable): A reference to the listener function
                to be removed.
        """
        if event not in self._emitting:

            return self._remove(event, listener)

        self._removals[event].append(listener)

    def emit(self, event: str, *args, **kwargs) -> bool:
        """Call all listeners attached to the given event.

        All listeners are called with the args and kwargs given to this method.

        Returns:
            bool: True if the event has listeners else False.
        """
        if not self._events.get(event, None):

            return False

        self._emitting.append(event)
        for offset, listener in enumerate(self._events[event]):

            try:

                listener(*args, **kwargs)

            except Exception as exc:

                if event == 'error' or not self._events.get('error', None):

                    raise

                self.emit('error', event, exc)

            finally:

                if isinstance(listener, _Once):

                    self._events[event][offset] = None

        self._events[event] = list(filter(bool, self._events[event]))
        self._emitting.pop()
        if event not in self._emitting:

            removals = self._removals.pop(event, ())
            additions = self._additions.pop(event, ())
            for listener in removals:

                self._remove(event, listener)

            for listener in additions:

                self._on(event, listener)

        return True
