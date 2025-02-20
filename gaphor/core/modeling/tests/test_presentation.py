import pytest
from gaphas.constraint import BaseConstraint
from gaphas.item import Item
from gaphas.solver import Variable

from gaphor.core.eventmanager import event_handler
from gaphor.core.modeling.diagram import Diagram
from gaphor.core.modeling.event import ElementDeleted
from gaphor.core.modeling.presentation import Presentation


class Example(Presentation, Item):
    pass


def test_presentation_implements_item_protocol(diagram):
    presentation = diagram.create(Example)

    assert isinstance(presentation, Item)


def test_presentation_should_have_a_diagram(diagram):
    presentation = diagram.create(Example)

    assert presentation.diagram is diagram


def test_should_emit_event_when_unlinked(diagram, event_manager):
    presentation = diagram.create(Example)
    events = []

    @event_handler(ElementDeleted)
    def handler(event):
        events.append(event)

    event_manager.subscribe(handler)

    presentation.unlink()

    assert events
    assert events[0].diagram is diagram
    assert events[0].element is presentation


def test_presentation_should_unlink_when_diagram_changes(diagram):
    presentation = diagram.create(Example)
    diagram.connections.add_constraint(presentation, BaseConstraint(Variable()))
    assert len(list(diagram.connections.get_connections(item=presentation))) == 1

    presentation.diagram = None

    assert not list(diagram.connections.get_connections(item=presentation))


def test_presentation_can_not_set_new_diagram(diagram, element_factory):
    presentation = diagram.create(Example)
    new_diagram = element_factory.create(Diagram)

    with pytest.raises(ValueError):
        presentation.diagram = new_diagram

    assert presentation.diagram is None


def test_should_emit_event_when_diagram_changes(diagram, event_manager):
    presentation = diagram.create(Example)
    events = []

    @event_handler(ElementDeleted)
    def handler(event):
        events.append(event)

    event_manager.subscribe(handler)

    del presentation.diagram

    assert events
    assert events[0].diagram is diagram
    assert events[0].element is presentation


def test_matrix_i2c_updates_when_matrix_changes(diagram):
    presentation = diagram.create(Example)

    presentation.matrix.translate(1, 1)

    assert tuple(presentation.matrix_i2c) == (1, 0, 0, 1, 1, 1)


def test_parent_matrix_updates(diagram):
    parent = diagram.create(Example)
    presentation = diagram.create(Example)

    presentation.parent = parent
    parent.matrix.scale(2, 2)

    assert tuple(presentation.matrix_i2c) == (2, 0, 0, 2, 0, 0)


def test_set_parent_updates_matrix_i2c(diagram):
    parent = diagram.create(Example)
    presentation = diagram.create(Example)

    parent.matrix.scale(2, 2)
    presentation.parent = parent

    assert tuple(presentation.matrix_i2c) == (1, 0, 0, 1, 0, 0)


def test_unset_parent_updates_matrix_i2c(diagram):
    parent = diagram.create(Example)
    presentation = diagram.create(Example)

    parent.matrix.scale(2, 2)
    presentation.parent = parent
    presentation.parent = None

    assert tuple(presentation.matrix_i2c) == (1, 0, 0, 1, 0, 0)


def test_change_parent_updates_matrix_i2c_and_keeps_coordinates(diagram):
    parent = diagram.create(Example)
    new_parent = diagram.create(Example)
    presentation = diagram.create(Example)

    parent.matrix.scale(2, 2)
    new_parent.matrix.translate(2, 2)
    presentation.parent = parent
    presentation.parent = new_parent

    assert tuple(presentation.matrix_i2c) == (1, 0, 0, 1, 0, 0)
