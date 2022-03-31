"""Models for BragerConnect."""
from __future__ import annotations

import json
from pathlib import Path
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Any

from .const import (
    JSON_TYPE,
    POOL_DATA,
    POOLS_TO_PROCESS, # pylint: disable=unused-import
)
from .exceptions import BragerError


class MessageType(IntEnum):
    """TODO: docstring"""

    PROCEDURE_EXEC = 1
    FUNCTION_EXEC = 2
    READY_SIGNAL = 10
    FUNCTION_RESP = 12
    EXCEPTION = 20
    PORT_MESSAGE = 21


class BoilerType(IntEnum):
    """TODO: docstring"""

    OTHER = 0
    FEEDER = 1
    PELLET = 2


class BoilerStatus(IntEnum):
    """TODO: docstring"""

    STOPPED = 0
    WORKING = 1
    MANUAL = 2
    ERROR = 3
    LIGHTING = 4
    DWHPRIORITY = 5
    TEST = 6
    DWHPREPARATION = 7
    NOSTATUS = 8
    DWHDISINFECTION = 9
    NOFUEL = 10


class PelletStatus(IntEnum):
    """TODO: docstring"""

    STOPPED = 0
    CLEANNG = 1
    LIGHTING = 2
    WORKING = 3
    PUTTINGOUT = 4
    STOP = 5
    SUSTAINING = 6


class TestStatus(IntEnum):
    """TODO: docstring"""

    OFF = 0
    ON = 1
    AVAILABLE = 3
    CLOSING = 4
    ERROR = 5
    ZONES = 6
    NOSTATUS = 7


@dataclass
class BragerInfo:
    """Object holding Brager Device information."""

    username: Optional[str] = None  # ":"marpi82",
    sharedfrom_name: Optional[str] = None  # ":null,
    devid: Optional[str] = None  # ":"FTTCTBSLCE",
    distr_group: Optional[str] = None  # ":"ht",
    id_perm_group: Optional[int] = None  # ":1,
    permissions_enabled: Optional[bool] = None  # ":1,
    permissions_time_start: Optional[str] = None  # ":null, # TODO: datetime?
    permissions_time_end: Optional[str] = None  # ":null, # TODO: datetime?
    accepted: Optional[bool] = None  # ":1,
    verified: Optional[bool] = None  # ":1,
    name: Optional[str] = None  # ":"",
    description: Optional[str] = None  # ":"",
    producer_permissions: Optional[int] = None  # ":2,
    producer_code: Optional[int] = None  # ":"67",
    warranty_void: Optional[bool] = None  # ":null,
    last_activity_time: Optional[int] = None  # ":2,  # TODO: int?
    alert: Optional[bool] = None  # ":false

    @staticmethod
    def from_dict(data: JSON_TYPE) -> BragerInfo:
        """Return BragerDeviceInfo object from BragerConnect API response.
        Args:
            data: The data from the BragerConnect service API.
        Returns:
            A BragerDeviceInfo object.
        """

        if not data:
            raise BragerError("Brager info data is incomplete, cannot construct BragerInfo object")

        username = data.get("username")
        devid = data.get("devid")

        name = data.get("name")
        if name == "":
            name = None

        description = data.get("description")
        if description == "":
            description = None

        warranty_void = data.get("warranty_void")
        if warranty_void is not None:
            warranty_void = bool(warranty_void)

        if username is None or devid is None:
            raise BragerError("BragerDeviceInfo data is incomplete, cannot construct info object.")

        return BragerInfo(
            username=username,
            sharedfrom_name=data.get("sharedfrom_name"),
            devid=devid,
            distr_group=data.get("distr_group"),
            id_perm_group=data.get("id_perm_group"),
            permissions_enabled=bool(data.get("permissions_enabled")),
            permissions_time_start=data.get("permissions_time_start"),
            permissions_time_end=data.get("permissions_time_end"),
            accepted=data.get("accepted"),
            verified=data.get("verified"),
            name=name,
            description=description,
            producer_permissions=data.get("producer_permissions"),
            producer_code=int(data.get("producer_code")),
            warranty_void=warranty_void,
            last_activity_time=data.get("last_activity_time"),
            alert=data.get("alert"),
        )


@dataclass
class BragerPool:
    """Object holding Brager Device Pool information."""

    # data[pool_number][field_number][field_type] = value
    data: POOL_DATA
    unit: JSON_TYPE
    name: JSON_TYPE

    @staticmethod
    def from_dict(data: JSON_TYPE, lang: str = "pl") -> BragerPool:
        """TODO: docstring"""
        if not data:
            raise BragerError("BragerPool data is empty, can't create BragerPool object")

        _data: POOL_DATA = {}

        try:
            path = Path(__file__).parent
            unit_f = open(f"{path}/json/{lang}_units.json", "r", encoding="utf-8")
            name_f = open(f"{path}/json/{lang}_pools.json", "r", encoding="utf-8")
        except OSError as exception:
            raise BragerError("Could not open/read JSON file.") from exception
        else:
            _unit = json.load(unit_f)
            _name = json.load(name_f)

            if not _unit or not _name:
                raise BragerError("Error loading data from JSON file.")
        finally:
            unit_f.close()
            name_f.close()

        for pool_name, pool_value in data.items():
            for field_name, field_value in pool_value.items():
                pool_no = int(pool_name[1:])
                field_no = int(field_name[1:])
                field_t = str(field_name[0])
                _data.setdefault(pool_no, {}).setdefault(field_no, {})[field_t] = field_value

        if not _data:
            raise BragerError("BragerPool data is empty, can't create BragerPool object")

        return BragerPool(data=_data, unit=_unit, name=_name)

    def update_from_list(self, data: list[JSON_TYPE]):
        """TODO: docstring"""
        if not data:
            raise BragerError("BragerPool data is empty, can't update BragerPool object")

        for _param in data:
            if any(
                key not in _param and _param[key] is not None for key in ("pool", "field", "value")
            ):
                raise BragerError("BragerPool data is incomplete, cannot update pool object")

            self.set_field_s(_param.get("pool"), _param.get("field"), _param.get("value"))

    def get_field(self, pool_no: int, field_no: int, field_type: str) -> int | float | str:
        """TODO: docstring"""
        return self.data.setdefault(pool_no, {}).setdefault(field_no, {}).get(field_type)

    def get_field_s(self, pool_name: str, field_name: str) -> int | float | str:
        """TODO: docstring"""
        return (
            self.data.setdefault(pool_name[1:], {})
            .setdefault(field_name[1:], {})
            .get(field_name[0])
        )

    def set_field(
        self, pool_no: int, field_no: int, field_type: str, value: int
    ) -> int | float | str:
        """TODO: docstring"""
        self.data.setdefault(pool_no, {}).setdefault(field_no)[field_type] = value

    def set_field_s(self, pool_name: str, field_name: str, value: int) -> int | float | str:
        """TODO: docstring"""
        self.data.setdefault(pool_name[1:], {}).setdefault(field_name[1:])[field_name[0]] = value

    def get_unit_by_no(self, unit_no: int) -> str | None:
        """TODO: docstring"""
        return self.unit.get(str(unit_no))

    def get_unit(self, pool_no: int, field_no: int) -> str | None:
        """TODO: docstring"""
        number = self.data.setdefault(pool_no, {}).setdefault(field_no, {}).get("u")
        return self.unit.get(str(number))

    def get_name(self, pool_no: int, field_no: int) -> str | None:
        """TODO: docstring"""
        return self.name.setdefault(f"P{pool_no}", {}).get(str(field_no))


@dataclass
class BragerTask:
    """Object holding Brager Task information."""

    tid: int
    module_id: int
    ttype: str  # TODO: "A" lub "ALARM"
    state: int
    result_sent: int
    user_owner: str
    producer_app: int
    create_timestamp: int  # timestamp
    start_timestamp: int  # timestamp
    end_timestamp: int  # timestamp
    end_cause: int
    tno: int
    value: int
    name: str
    started_at: str  # date
    finished_at: str  # date
    created_at: str  # date
    updated_at: str  # date

    @staticmethod
    def from_dict(data: JSON_TYPE) -> BragerTask:
        """TODO: docstring"""
        if not data:
            raise BragerError("BragerTask data is empty, can't create BragerTask object")

        return BragerTask(
            tid=data.get("id"),
            module_id=data.get("module_id"),
            ttype=data.get("type"),
            state=data.get("state"),
            result_sent=data.get("result_sent"),
            user_owner=data.get("user_owner"),
            producer_app=data.get("producerApp"),
            create_timestamp=data.get("create_timestamp"),
            start_timestamp=data.get("start_timestamp"),
            end_timestamp=data.get("end_timestamp"),
            end_cause=data.get("end_cause"),
            tno=data.get("nr"),
            value=data.get("value"),
            name=data.get("name"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class BragerAlarm:
    """Object holding Brager Alarm information."""

    name: str  # TODO: typy alarmów! "ERROR_BRAK_PALIWA"
    value: bool
    timestamp: int

    @staticmethod
    def from_dict(data: list[str, Any]) -> BragerAlarm:
        """TODO: docstring"""
        if not data:
            raise BragerError("BragerAlarm data is empty, can't create BragerAlarm object")

        return BragerAlarm(
            name=data.get("name"),
            value=data.get("value"),
            timestamp=data.get("timestamp"),
        )


@dataclass
class BragerStatus:
    """Object holding Brager device status information."""

    _pool: BragerPool

    @staticmethod
    def from_dict(pool: BragerPool) -> BragerStatus:
        """TODO: docstring"""
        # Check if all elements are in the passed dict, else raise an Error
        if any(key not in pool.data and pool.data[key] is not None for key in (4, 5)):
            raise BragerError("Brager pool data is incomplete, cannot construct status object")

        return BragerStatus(_pool=pool)

    def _detect_status(self, value: int) -> int:
        """TODO: decstring
        0 - not present
        1 - present
        3 - not active
        """
        if value is None or value & (1 << 1):
            return 0  # not present
        if value & (1 << 2):
            return 3  # not active
        return 1  # present

    def _detect_pump(self, status: int) -> bool:
        """TODO: docstring"""
        if status & (1 << 1) or status & (1 << 3):
            return True

        return False

    def _detect_fuel(self) -> int:
        """TODO: docstring"""
        return self._pool.get_field_s("P6", "v34")

    def _detect_settings(self) -> int:
        """TODO: docstring"""
        status = self._pool.get_field_s("P6", "s0")
        if status & (1 << 0):
            return 2  # hidden

        if status & (1 << 1):
            return 0  # blocked

        return 1  # enabled

    def _detect_remote_on_off(self, status: int) -> bool:
        """TODO: docstring"""
        return bool(status & (1 << 4))

    # TODO: przenieść ze statusów do nastaw / testowanie czy można zmienić parametr
    def param_status(self, status: int) -> int:
        """TODO: docstring"""
        if status & (1 << 0):  # hidden
            return 0
        elif status & (1 << 1):  # blocked
            return 2
        return 1  # available

    def boiler_type(self) -> BoilerType:
        """TODO: docstring"""

        def _boiler_status(status: int | None) -> bool:
            """TODO: decstring"""
            return status is not None and (status & (1 << 0)) == 1

        if _boiler_status(self._pool.get_field(5, 39, "s")):
            return BoilerType.PELLET  # pellet

        if _boiler_status(self._pool.get_field(5, 13, "s")):
            return BoilerType.FEEDER  # feeder

        return BoilerType.OTHER  # other type

    def boiler_status(self, status: int) -> BoilerStatus | None:
        """TODO: docstring"""
        if not isinstance(status, int):
            return None
        if status == 0:
            return BoilerStatus.STOPPED
        if status & (1 << 0):
            return BoilerStatus.WORKING
        if status & (1 << 1):
            return BoilerStatus.MANUAL
        if status & (1 << 2):
            return BoilerStatus.ERROR
        if status & (1 << 3):
            return BoilerStatus.LIGHTING
        if status & (1 << 4):
            return BoilerStatus.DWHPRIORITY
        if status & (1 << 5):
            return BoilerStatus.TEST
        if status & (1 << 6):
            return BoilerStatus.DWHPREPARATION
        if status & (1 << 7):
            return BoilerStatus.NOSTATUS
        if status & (1 << 9):
            return BoilerStatus.DWHDISINFECTION
        if status & (1 << 10):
            return BoilerStatus.NOFUEL
        return None

    def pellet_status(self, status: int) -> PelletStatus | None:
        """TODO: docstring"""
        if self.boiler_type() == BoilerType.PELLET and isinstance(status, int):
            # extract three bits form nine'th bit
            _status = ((1 << 3) - 1) & (status >> (9 - 1))
            if _status == 0 | status == 0:
                return PelletStatus.STOPPED
            if _status == 1:
                return PelletStatus.CLEANNG
            if _status == 2:
                return PelletStatus.LIGHTING
            if _status == 3:
                return PelletStatus.WORKING
            if _status == 4:
                return PelletStatus.PUTTINGOUT
            if _status == 5:
                return PelletStatus.STOP
            if _status == 6:
                return PelletStatus.SUSTAINING
            return None
        else:
            return None

    def test_status(self, status: int) -> TestStatus | None:
        """TODO: docstring"""
        if not isinstance(status, int):
            return None
        if status == 0:
            return TestStatus.OFF
        if status & (1 << 2):
            return TestStatus.CLOSING
        if status & (1 << 1):
            return TestStatus.ON
        if status & (1 << 3):
            return TestStatus.ON
        if status & (1 << 0):
            return TestStatus.AVAILABLE
        if status & (1 << 4):
            return TestStatus.CLOSING
        if status & (1 << 5):
            return TestStatus.ERROR
        if status & (1 << 6):
            return TestStatus.ZONES
        if status & (1 << 7):
            return TestStatus.NOSTATUS
        return None

    def get(self) -> Optional[POOL_DATA]:
        """TODO: docstring"""

        def set_data(_pool: int, _field: int, _value: str):
            _data.setdefault(_pool, {}).setdefault(_field, {})["name"] = self._pool.get_name(
                _pool, _field
            )
            _data[_pool][_field]["value"] = self._pool.get_field(_pool, _field, _value)
            _data[_pool][_field]["unit"] = self._pool.get_unit(_pool, _field)

        def set_data_status(_pool: int, _field: int, func=lambda a: a):
            status: IntEnum | int = func(self._pool.get_field(_pool, _field, "s"))
            if isinstance(status, (int, IntEnum)):
                _data.setdefault(_pool, {}).setdefault(_field, {})["name"] = self._pool.get_name(
                    _pool, _field
                )
                _data[_pool][_field]["value"] = status

        def units(first: int, second: int) -> set:
            return ("kW", 1) if first == 31 or second else ("kW", 0.1)

        _data: POOL_DATA = {}

        # external temperature sensor
        if isinstance(self._pool.get_field(4, 4, "v"), (int, float)):
            set_data(4, 4, "v")

        # external I/O
        for number in range(72, 77):
            set_data_status(5, number, self.test_status)

        # not known?
        for number in (1, 2, 3, 4, 5, 6, 14, 15, 16, 22, 24, 37, 38, 40, 49):
            set_data_status(5, number, self.test_status)

        # boiler enabled
        if self._detect_status(self._pool.get_field(4, 0, "s")):
            # Pool P4
            set_data(4, 0, "v")
            if self._detect_status(self._pool.get_field(4, 3, "s")):
                set_data(4, 3, "v")
            # Pool P5
            set_data_status(5, 0, self.boiler_status)
            if self.boiler_type() == BoilerType.PELLET:
                set_data_status(5, 5, self.pellet_status)
            elif self.boiler_type() == BoilerType.FEEDER:
                set_data_status(5, 10, self.test_status)
                set_data_status(5, 13, self.test_status)
            set_data_status(5, 11, self.test_status)

        # burner enabled
        if self._detect_status(self._pool.get_field(4, 14, "s")):
            # Pool P4
            for par in (3, 4, 8, 13, 14, 15, 16, 39, 40, 41, 42, 43, 56, 61):
                if self._detect_status(self._pool.get_field(4, par, "s")):
                    set_data(4, par, "v")
                    # change units and convert value for P4.s14 (Boiler power)
                    if par == 14:
                        unit, multiplier = units(
                            self._pool.get_field(4, 14, "s"),
                            self._pool.get_field(6, 152, "s"),
                        )
                        print(f"u:{unit}, m:{multiplier}")
                        _data[4][14]["value"] = round(_data[4][14]["value"] * multiplier, 1)
                        _data[4][14]["unit"] = unit
                    # calculate fuel consumption ever
                    if par == 61:
                        val1 = self._pool.get_field(4, 61, "v")
                        val2 = self._pool.get_field(4, 62, "v")
                        _data[4][61]["value"] = round(
                            (val1 + (0 if val1 < 0 else 65536) + (65536 * val2)) / 1000,
                            3,
                        )
            # Pool P5
            set_data_status(5, 10, self.test_status)

        # return enabled
        if self._detect_status(self._pool.get_field(4, 1, "s")):
            set_data(4, 1, "v")
            set_data_status(5, 12, self.test_status)

        # buffer enabled
        if self._detect_status(self._pool.get_field(4, 6, "s")):
            set_data(4, 6, "v")
            if self._detect_status(self._pool.get_field(4, 30, "s")):
                set_data(4, 30, "v")
            set_data_status(5, 23, self.test_status)

        # DWH enabled
        if self._detect_status(self._pool.get_field(4, 2, "s")):
            set_data(4, 2, "v")
            set_data_status(5, 11, self.test_status)

        _valves: list = [
            {  # Valve 1
                "mode": 52,  # P6 Tryb pracy zaworu
                "valve": 20,  # P5 Zawór
                "valvePump": 21,  # P5 Pompa zawór
                "valveHistereza": 54,  # P6 Nastawa zaworu, gdy +10C na zewnątrz
                "temperature": 5,  # P4 Temperatura zaworu
                "temperatureSetup": 53,  # P6 Nastawa zaworu (tryb normalny)
                "temperatureSetupWheater": 130,  # P6 Nastawa pogodowa zaworu
                "zonesStart": 8,  # P12 Strefy czasowe (parametr początkowy)
            },
            {  # Valve 2
                "mode": 79,
                "valve": 25,
                "valvePump": 26,
                "valveHistereza": 81,
                "temperature": 9,
                "temperatureSetup": 80,
                "temperatureSetupWheater": 131,
                "zonesStart": 12,
            },
            {  # Valve 3
                "mode": 91,
                "valve": 28,
                "valvePump": 29,
                "valveHistereza": 93,
                "temperature": 10,
                "temperatureSetup": 92,
                "temperatureSetupWheater": 132,
                "zonesStart": 16,
            },
            {  # Valve 4
                "mode": 103,
                "valve": 31,
                "valvePump": 32,
                "valveHistereza": 105,
                "temperature": 11,
                "temperatureSetup": 104,
                "temperatureSetupWheater": 133,
                "zonesStart": 20,
            },
            {  # Valve 5
                "mode": 115,
                "valve": 34,
                "valvePump": 35,
                "valveHistereza": 117,
                "temperature": 12,
                "temperatureSetup": 116,
                "temperatureSetupWheater": 134,
                "zonesStart": 24,
            },
            {  # Valve 1.2
                "mode": 305,
                "valve": 51,
                "valvePump": 52,
                "valveHistereza": 307,
                "temperature": 46,
                "temperatureSetup": 306,
                "temperatureSetupWheater": 318,
                "zonesStart": False,
            },
        ]
        for _valve in _valves:
            if self._detect_status(self._pool.get_field(4, _valve["temperature"], "s")):
                set_data(4, _valve["temperature"], "v")
                # TODO: sprawdzić czy się zmienia w trakcie pracy zaworu
                # jeśli nie to uzależnić tylko pompę od tej wartości
                set_data_status(5, _valve["valve"], self.test_status)
                set_data_status(5, _valve["valvePump"], self.test_status)

        # pump enabled
        if self._detect_status(self._pool.get_field(4, 28, "s")):
            set_data(4, 28, "v")
            if self._detect_status(self._pool.get_field(4, 25, "s")):
                set_data(4, 25, "v")

        # Thermostat enabled
        if self._detect_status(self._pool.get_field(17, 0, "s")):
            set_data(17, 0, "v")

        # BCA-02 enabled
        if (
            self._pool.data.get(4) is not None
            and self._pool.data.get(6) is not None
            and self._pool.data.get(11) is not None
            and self._detect_status(self._pool.get_field(11, 13, "s"))
        ):
            # P4.s7  - temperatura spalin (?)
            # P4.s51 - zawartość dwutlenku węgla w spalinach (?)
            # P4.s52 - Lambda (spaliny) (?)
            # P4.s53 - ChimneyLoos (spaliny) (?)
            # P4.s54 - EnergyEfficiency (spaliny) (?)
            # P4.s55 - OptimumCombustionCoefficient (spaliny) (?)
            pass

        # OPS enabled
        if (
            self._pool.data.get(4) is not None
            and self._pool.data.get(6) is not None
            and self._pool.data.get(11) is not None
            and self._detect_status(self._pool.get_field(11, 15, "s"))
        ):
            # P4.s7  - temperatura spalin (?)
            # P4.s51 - zawartość dwutlenku węgla w spalinach (?)
            # P4.s52 - Lambda (spaliny) (?)
            # P4.s53 - ChimneyLoos (spaliny) (?)
            # P4.s54 - EnergyEfficiency (spaliny) (?)
            # P4.s55 - OptimumCombustionCoefficient (spaliny) (?)
            pass

        return _data if _data else None


@dataclass
class BragerDevice:
    """Object holding Brager Device information."""

    info: Optional[BragerInfo] = None
    pool: Optional[BragerPool] = None
    task: Optional[list[BragerTask]] = None
    alarm: Optional[list[BragerAlarm]] = None
    status: Optional[BragerStatus] = None

    def __init__(self, data: JSON_TYPE) -> None:
        """TODO: docstring"""
        # Check if all elements are in the passed dict, else raise an Error
        if any(
            key not in data and data[key] is not None for key in ("info", "pool", "task", "alarm")
        ):
            raise BragerError("BragerDevice data is incomplete, cannot construct device object")

        self.update_from_dict(data)

    def __repr__(self):
        """TODO: docstring"""
        return self.info.devid

    def update_status(self) -> BragerStatus:
        """TODO: docstring"""
        _status = BragerStatus.from_dict(self.pool)

        self.status = _status
        return _status

    def update_from_dict(self, data: JSON_TYPE) -> BragerDevice:
        """TODO: docstring"""
        if _info := data.get("info"):
            self.info = BragerInfo.from_dict(data=_info)

        if isinstance((_pool := data.get("pool")), dict):
            self.pool = BragerPool.from_dict(data=_pool)

        if isinstance((_task := data.get("task")), list):
            if isinstance(self.task, list):
                self.task.clear()
            else:
                self.task: list[BragerTask] = []

            for one_task in _task:
                self.task.append(BragerTask.from_dict(data=one_task))

        if isinstance((_alarm := data.get("alarm")), list):
            if isinstance(self.alarm, list):
                self.alarm.clear()
            else:
                self.alarm: list[BragerAlarm] = []

            for one_alarm in _alarm:
                self.alarm.append(BragerAlarm.from_dict(data=one_alarm))

        self.update_status()

        return self
