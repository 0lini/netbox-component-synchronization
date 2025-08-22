from dataclasses import dataclass, field
from django.conf import settings

config = settings.PLUGINS_CONFIG["netbox_component_synchronization"]


@dataclass(frozen=True)
class ParentComparison:
    """Common fields of a device component"""

    id: int
    name: str
    label: str
    description: str
    is_template: bool = field(default=False, kw_only=True)

    def _compare_attributes(self, other, extra_attrs=()) -> bool:
        if not hasattr(other, "name") or not hasattr(other, "label"):
            return NotImplemented

        eq = (self.name == other.name) and (self.label == other.label)

        for attr in extra_attrs:
            if not hasattr(other, attr):
                return NotImplemented
            eq = eq and (getattr(self, attr) == getattr(other, attr))

        if config["compare_description"]:
            eq = eq and (self.description == other.description)

        return eq

    def __eq__(self, other):
        return self._compare_attributes(other, ())

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f"Label: {self.label}\nDescription: {self.description}"


@dataclass(frozen=True)
class ParentTypedComparison(ParentComparison):
    """Common fields of a device typed component"""

    type: str
    type_display: str

    def __eq__(self, other):
        return self._compare_attributes(other, ("type",))

    def __hash__(self):
        return hash((self.name, self.type))

    def __str__(self):
        return f"{super().__str__()}\nType: {self.type_display}"


@dataclass(frozen=True)
class InterfaceComparison(ParentTypedComparison):
    """A unified way to represent the interface and interface template"""

    enabled: bool
    mgmt_only: bool = False
    poe_mode: str = ""
    poe_type: str = ""
    rf_role: str = ""

    def __eq__(self, other):
        return self._compare_attributes(
            other,
            ("type", "enabled", "mgmt_only", "poe_mode", "poe_type", "rf_role"),
        )

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return f"{super().__str__()}\nManagement only: {self.mgmt_only}\nEnabled: {self.enabled}\nPoE mode: {self.poe_mode}\nPoE type: {self.poe_type}\nWireless role: {self.rf_role}"


@dataclass(frozen=True)
class FrontPortComparison(ParentTypedComparison):
    """A unified way to represent the front port and front port template"""

    color: str
    rear_port_position: int

    def __eq__(self, other):
        return self._compare_attributes(other, ("type", "color", "rear_port_position"))

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return f"{super().__str__()}\nColor: {self.color}\nRear port position: {self.rear_port_position}"


@dataclass(frozen=True)
class RearPortComparison(ParentTypedComparison):
    """A unified way to represent the rear port and rear port template"""

    color: str
    positions: int

    def __eq__(self, other):
        return self._compare_attributes(other, ("type", "color", "positions"))

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return f"{super().__str__()}\nColor: {self.color}\nPositions: {self.positions}"


@dataclass(frozen=True, eq=False)
class ConsolePortComparison(ParentTypedComparison):
    """A unified way to represent the consoleport and consoleport template"""

    pass


@dataclass(frozen=True, eq=False)
class ConsoleServerPortComparison(ParentTypedComparison):
    """A unified way to represent the consoleserverport and consoleserverport template"""

    pass


@dataclass(frozen=True)
class PowerPortComparison(ParentTypedComparison):
    """A unified way to represent the power port and power port template"""

    maximum_draw: str
    allocated_draw: str

    def __eq__(self, other):
        return self._compare_attributes(
            other, ("type", "maximum_draw", "allocated_draw")
        )

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return f"{super().__str__()}\nMaximum draw: {self.maximum_draw}\nAllocated draw: {self.allocated_draw}"


@dataclass(frozen=True)
class PowerOutletComparison(ParentTypedComparison):
    """A unified way to represent the power outlet and power outlet template"""

    power_port_name: str
    feed_leg: str

    def __eq__(self, other):
        return self._compare_attributes(other, ("type", "power_port_name", "feed_leg"))

    def __hash__(self):
        return hash((self.name, self.type, self.power_port_name))

    def __str__(self):
        return f"{super().__str__()}\nPower port name: {self.power_port_name}\nFeed leg: {self.feed_leg}"


@dataclass(frozen=True, eq=False)
class DeviceBayComparison(ParentComparison):
    """A unified way to represent the device bay and device bay template"""

    pass


@dataclass(frozen=True, eq=False)
class ModuleBayComparison(ParentComparison):
    """A unified way to represent the module bay and module bay template"""

    position: str

    def __eq__(self, other):
        return self._compare_attributes(other, ("position",))

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return f"{super().__str__()}\nPosition: {self.position}"
