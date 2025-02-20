"""Factory for and registration of model elements."""

from __future__ import annotations

import uuid
from collections import OrderedDict
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Iterator, TypeVar, overload

from gaphor.abc import Service
from gaphor.core.modeling.diagram import Diagram
from gaphor.core.modeling.element import (
    Element,
    EventWatcherProtocol,
    Handler,
    UnlinkEvent,
)
from gaphor.core.modeling.elementdispatcher import ElementDispatcher, EventWatcher
from gaphor.core.modeling.event import (
    ElementCreated,
    ElementDeleted,
    ModelFlushed,
    ModelReady,
)
from gaphor.core.modeling.presentation import Presentation

if TYPE_CHECKING:
    from gaphor.core.eventmanager import EventManager  # noqa


T = TypeVar("T", bound=Element)
P = TypeVar("P", bound=Presentation)


class ElementFactory(Service):
    """The ElementFactory is used to create elements and do lookups to
    elements.

    Notifications are sent as arguments (name, element, `*user_data`).
    The following names are used:
    create - a new model element is created (element is newly created element)
    remove - a model element is removed (element is to be removed element)
    model - a new model has been loaded (element is None) flush - model is
      flushed: all element are removed from the factory (element is None)
    """

    def __init__(
        self,
        event_manager: EventManager | None = None,
        element_dispatcher: ElementDispatcher | None = None,
    ):
        self.event_manager = event_manager
        self.element_dispatcher = element_dispatcher
        self._elements: dict[str, Element] = OrderedDict()
        self._block_events = 0

    def shutdown(self) -> None:
        self.flush()

    def create(self, type: type[T]) -> T:
        """Create a new model element of type ``type``."""
        return self.create_as(type, str(uuid.uuid1()))

    def create_as(self, type: type[T], id: str, diagram: Diagram = None) -> T:
        """Create a new model element of type 'type' with 'id' as its ID.

        This method should only be used when loading models, since it
        does not emit an ElementCreated event.
        """
        if not type:
            raise TypeError(f"Type {type} not defined")
        elif issubclass(type, Presentation):
            if not diagram:
                raise TypeError("Presentation types require a diagram")

            # Avoid events that reference this element before its created-event is emitted.
            with self.block_events():
                item = type(diagram=diagram, id=id)
            self._elements[id] = item
            self.handle(ElementCreated(self, item, diagram))
            return item
        elif issubclass(type, Element):
            if diagram:
                raise TypeError("Element types require no diagram")
            obj = type(id, self)
            self._elements[id] = obj
            self.handle(ElementCreated(self, obj))
            return obj
        else:
            raise TypeError(f"Type {type} is not a valid model element")

    def size(self) -> int:
        """Return the amount of elements currently in the factory."""
        return len(self._elements)

    def lookup(self, id: str) -> Element | None:
        """Find element with a specific id."""
        return self._elements.get(id)

    __getitem__ = lookup

    def __contains__(self, element: Element) -> bool:
        assert isinstance(element.id, str)
        return self.lookup(element.id) is element

    @overload
    def select(self, expression: Callable[[Element], bool]) -> Iterator[Element]:
        ...

    @overload
    def select(self, expression: type[T]) -> Iterator[T]:
        ...

    @overload
    def select(self, expression: None) -> Iterator[Element]:
        ...

    def select(self, expression=None):
        """Iterate elements that comply with expression."""
        if expression is None:
            yield from self._elements.values()
        elif isinstance(expression, type):
            yield from (e for e in self._elements.values() if isinstance(e, expression))
        else:
            yield from (e for e in self._elements.values() if expression(e))

    def lselect(
        self, expression: Callable[[Element], bool] | type[T] | None = None
    ) -> list[Element]:
        """Get a list of elements that comply with expression.

        The expression can be one of:
        - None: return all elements
        - class name: return all elements of type `class name`
        - expression(e: Element) -> bool: return elements that comply with expression
        """
        return list(self.select(expression))

    def keys(self) -> Iterator[str]:
        """Return a list with all id's in the factory."""
        return iter(self._elements.keys())

    def values(self) -> Iterator[Element]:
        """Return a list with all elements in the factory."""
        return iter(self._elements.values())

    def is_empty(self) -> bool:
        """Returns True if the factory holds no elements."""
        return bool(self._elements)

    def watcher(
        self, element: Element, default_handler: Handler | None = None
    ) -> EventWatcherProtocol:
        element_dispatcher = self.element_dispatcher
        return EventWatcher(element, element_dispatcher, default_handler)

    def flush(self) -> None:
        """Flush all elements (remove them from the factory).

        Diagram elements are flushed first. The remaining elements are
        flushed next.
        """
        with self.block_events():
            for element in self.lselect(Diagram):
                assert isinstance(element, Diagram)
                element.unlink()

            for element in self.lselect():
                element.unlink()

        self.handle(ModelFlushed(self))

    def model_ready(self) -> None:
        """Send notification that a new model has been loaded by means of the
        ModelReady event from gaphor.core.modeling.event."""
        self.handle(ModelReady(self))

    @contextmanager
    def block_events(self):
        """Block events from being emitted."""
        self._block_events += 1

        try:
            yield self
        finally:
            self._block_events -= 1

    def handle(self, event: object) -> None:
        """Handle events coming from elements."""
        if isinstance(event, UnlinkEvent):
            element = event.element
            assert isinstance(element.id, str)
            try:
                del self._elements[element.id]
            except KeyError:
                return
            event = ElementDeleted(self, event.element, event.diagram)
        if self.event_manager and not self._block_events:
            self.event_manager.handle(event)
