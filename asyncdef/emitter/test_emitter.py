"""Test suite for the IEmitter implementation."""

import pytest

import iface
from asyncdef.interfaces.emitter import iemitter

from . import emitter


def test_emitter_is_implementation():
    """Check if Emitter is an IEmitter."""
    assert iface.isinstance(
        emitter.Emitter(),
        iemitter.IEmitter,
    )


def test_new_listener_fired_first():
    """Check that new_listener is fired before adding the new listener."""
    instance = emitter.Emitter()
    event = 'an_event'

    def check(*args, **kwargs):
        """Check if the listener list is empty."""
        assert instance.listeners_count(event) == 0

    instance.on('new_listener', check)
    instance.on(event, lambda: None)
    assert instance.listeners_count(event) == 1


def test_on_waits_until_event_over():
    """Check that on defers adding until the specefied event is over."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener():
        """Do nothing."""
        return None

    def add():
        """Add a listener to the event."""
        old_count = instance.listeners_count(event)
        instance.on(event, listener)
        assert old_count == instance.listeners_count(event)

    instance.on(event, add)
    assert instance.listeners_count(event) == 1
    instance.emit(event)
    assert instance.listeners_count(event) == 2


def test_once_waits_until_event_over():
    """Check that once defers adding until the specefied event is over."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener():
        """Do nothing."""
        return None

    def add():
        """Add a listener to the event."""
        old_count = instance.listeners_count(event)
        instance.once(event, listener)
        assert old_count == instance.listeners_count(event)

    instance.on(event, add)
    assert instance.listeners_count(event) == 1
    instance.emit(event)
    assert instance.listeners_count(event) == 2


def test_fires_events_with_arguments():
    """Check that event listeners are fired with arguments."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener(t, f, n):
        assert t is True
        assert f is False
        assert n is None

    instance.on(event, listener)
    instance.emit(event, True, False, None)


def test_fires_events_nested():
    """Check that events can be fired in a nested manner."""
    instance = emitter.Emitter()
    event = 'an_event'
    event2 = 'another_event'
    state = {'count': 0}

    def listener1(t, f, n):
        assert t is True
        assert f is False
        assert n is None
        assert state['count'] == 1
        state['count'] += 1

    def listener2(t, f, n):
        assert state['count'] == 0
        state['count'] += 1
        instance.emit(event, t, f, n)
        assert state['count'] == 2

    instance.on(event, listener1)
    instance.on(event2, listener2)
    instance.emit(event2, True, False, None)


def test_once_fires_once():
    """Check that once listeners only fire once."""
    instance = emitter.Emitter()
    event = 'an_event'
    state = {'count': 0}

    def listener():
        """Increment the state count."""
        state['count'] += 1

    instance.once(event, listener)
    assert instance.emit(event)
    assert not instance.emit(event)
    assert state['count'] == 1


def test_remove_removes_listeners():
    """Check that remove removes listeners."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener():
        """Do nothing."""
        return None

    instance.on(event, listener)
    assert instance.listeners_count(event) == 1
    assert listener in list(instance.listeners(event))
    instance.remove(event, listener)
    assert instance.listeners_count(event) == 0
    assert listener not in list(instance.listeners(event))


def test_remove_removes_method():
    """Check that remove removes object methods."""
    instance = emitter.Emitter()
    event = 'an_event'

    class Listener:

        """An object with a listener method."""

        def listen(self):
            """Do nothing."""
            return None

    listener = Listener()
    instance.on(event, listener.listen)
    assert instance.listeners_count(event) == 1
    assert listener.listen in list(instance.listeners(event))
    instance.remove(event, listener.listen)
    assert instance.listeners_count(event) == 0
    assert listener.listen not in list(instance.listeners(event))


def test_remove_removes_classmethod():
    """Check that remove removes object class methods."""
    instance = emitter.Emitter()
    event = 'an_event'

    class Listener:

        """An object with a listener method."""

        @classmethod
        def listen(cls):
            """Do nothing."""
            return None

    instance.on(event, Listener.listen)
    assert instance.listeners_count(event) == 1
    assert Listener.listen in list(instance.listeners(event))
    instance.remove(event, Listener.listen)
    assert instance.listeners_count(event) == 0
    assert Listener.listen not in list(instance.listeners(event))


def test_remove_allows_missing():
    """Check if remove works when there are no listeners."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener():
        """Do nothing."""
        return None

    assert instance.remove(event, listener) is None


def test_remove_waits_until_event_over():
    """Check that remove defers adding until the specefied event is over."""
    instance = emitter.Emitter()
    event = 'an_event'

    def listener():
        """Do nothing."""
        return None

    def remove():
        """Add a listener to the event."""
        old_count = instance.listeners_count(event)
        instance.remove(event, listener)
        assert old_count == instance.listeners_count(event)

    instance.on(event, listener)
    instance.on(event, remove)
    assert instance.listeners_count(event) == 2
    instance.emit(event)
    assert instance.listeners_count(event) == 1


def test_error_raises_with_no_listener():
    """Check that exceptions raise when there is not error listener."""
    instance = emitter.Emitter()
    event = 'an_event'

    class CheckError(Exception):

        """An error for the test."""

    def listener():
        """Raise the test exception."""
        raise CheckError()

    instance.on(event, listener)
    with pytest.raises(CheckError):

        instance.emit(event)


def test_error_raises_with_broken_listener():
    """Check that exceptions raise when there is not error listener."""
    instance = emitter.Emitter()
    event = 'an_event'

    class CheckError(Exception):

        """An error for the test."""

    def errlistener(*args, **kwargs):
        """Raise the test exception."""
        raise CheckError()

    def listener():
        """Raise any exception."""
        raise Exception()

    instance.on('error', errlistener)
    instance.on(event, listener)
    with pytest.raises(CheckError):

        instance.emit(event)
