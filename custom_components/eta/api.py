from enum import Enum

import xmltodict
import asyncio
from typing import Sequence
from homeassistant.helpers.selector import SelectOptionDict
class SensorType(Enum):
    NUMERIC = "numeric"
    TEXT = "text"


FLOAT_SENSOR_UNITS = [
    "%",
    "A",
    "Hz",
    "Ohm",
    "Pa",
    "U/min",
    "V",
    "W",
    "W/m²",
    "bar",
    "kW",
    "kWh",
    "kg",
    "l",
    "l/min",
    "mV",
    "m²",
    "s",
    "°C",
    "%rH",
]


class EtaSensorDesc:
    def __init__(self, id, name, parent, sensor_type=SensorType.NUMERIC):
        self._id = id
        self._name = name
        self._parent = parent
        self._unit = None
        self._sensor_type = sensor_type
        self._states = None  # for text sensors, possible states
        self._canonicalName = None

    def updateName(self, canonicalName):
        self._canonicalName = canonicalName

    def updateUnit(self, unit):
        self._unit = unit
        self._sensor_type = SensorType.NUMERIC

    def updateStates(self, states: dict):
        self._states = states
        self._sensor_type = SensorType.TEXT

    @property
    def id(self):
        return self._id
    
    @property
    def name(self):
        return self._name
    
    @property
    def unit(self):   
        return self._unit

    @property
    def sensor_type(self):
        return self._sensor_type
    
    def getValue(self, data) -> float | str:
        match self._sensor_type:
            case SensorType.TEXT:
                value = data["#text"]
                return self._states.get(value, data["@strValue"])
            case SensorType.NUMERIC:
                unit = data["@unit"]
                if unit in FLOAT_SENSOR_UNITS:
                    scale_factor = int(data["@scaleFactor"])
                    decimal_places = int(data["@decPlaces"])
                    raw_value = float(data["#text"])
                    value = raw_value / scale_factor
                    value = round(value, decimal_places)
                else:
                    # use default text string representation for values that cannot be parsed properly
                    value = data["@strValue"]
                return value

        return -1

    def map(self, value):
        if self._states:
            return self._states.get(value, value)
        else:
            return value

    def canonicalName(self) -> str:
        if self._canonicalName:
            return self._canonicalName
        else:
            cn = ""
            if self._parent:
                cn = cn + self._parent.canonicalName() + " > "

            cn = cn + self._name
            return cn


class SensorDict:
    def __init__(self) -> None:
        # id to sensor
        self._sensors: dict[str, EtaSensorDesc] = {}
        self._label_to_id: dict[str, str] = {}
        self._id_to_label: dict[str, str] = {}

    def add(self, sensor: EtaSensorDesc):
        if not sensor.id in self._sensors:
            self._sensors[sensor.id] = sensor
            self._id_to_label[sensor.id] = sensor.canonicalName()
            self._label_to_id[sensor.canonicalName()] = sensor.id

    def update(self, sensor: EtaSensorDesc):
        oldLabel = self._id_to_label[sensor.id]
        self._id_to_label[sensor.id] = sensor.canonicalName()
        self._label_to_id[sensor.canonicalName()] = sensor.id
        self._label_to_id.pop(oldLabel)

    @property
    def sensors(self) -> dict[str, EtaSensorDesc]:
        return self._sensors

    def byId(self, id: str) -> EtaSensorDesc:
        return self._sensors[id]

    def byName(self, name: str) -> EtaSensorDesc:
        id = self._label_to_id[name]
        return self._sensors[id]

    def names(self) -> list[str]:
        return list(self._label_to_id.keys())
    
    def nameDict(self) -> list[dict[str, str]]:
        options = [{"value": k, "label": v} for k, v in self._id_to_label.items()]
        return options


class EtaAPI:
    def __init__(self, session, host, port):
        self._session = session
        self._host = host
        self._port = port
        self._initialized = False
        self._sensors = SensorDict()

    def _build_uri(self, suffix):
        return "http://" + self._host + ":" + str(self._port) + suffix

    def _evaluate_xml_dict(self, xml_dict, parent):
        if type(xml_dict) is list:
            for child in xml_dict:
                self._evaluate_xml_dict(child, parent)
        else:
            if "object" in xml_dict:
                child = xml_dict["object"]
                id = xml_dict["@uri"]
                s = EtaSensorDesc(id, xml_dict["@name"], parent)
                # add parent to uri_dict and evaluate childs then
                self._sensors.add(s)
                self._evaluate_xml_dict(child, s)
            elif "fub" in xml_dict:
                fub = xml_dict["fub"]
                id = xml_dict["@uri"]
                s = EtaSensorDesc(id, xml_dict["@name"], None)
                # add parent to uri_dict and evaluate childs then
                self._sensors.add(s)
                self._evaluate_xml_dict(fub, s)
            else:
                id = xml_dict["@uri"]
                s = EtaSensorDesc(id, xml_dict["@name"], parent)
                # add parent to uri_dict and evaluate childs then
                self._sensors.add(s)

    async def _get_request(self, suffix):
        data = await self._session.get(self._build_uri(suffix))
        return data

    async def get_data(self, sensor: EtaSensorDesc):
        data = await self._get_request("/user/var" + sensor.id)
        text = await data.text()
        data = xmltodict.parse(text)["eta"]["value"]
        return sensor.getValue(data)

    async def initializeSensor(self, sensor: EtaSensorDesc):
        try:
            data = await self._get_request("/user/varinfo" + sensor.id)
            text = await data.text()
            xml = xmltodict.parse(text)
            varInfo = xml["eta"].get("varInfo", None)
            if varInfo:
                type = varInfo["variable"]["type"]
                name = varInfo["variable"]["@fullName"]
                if name:
                    sensor.updateName(name)
                    # name (canonical has changed, add to dict again)
                    self._sensors.add(sensor)

                match type:
                    case "TEXT":
                        states = {}
                        for v in varInfo["variable"]["validValues"]["value"]:
                            states[v["#text"]] = v["@strValue"]
                        sensor.updateStates(states)
                    case "DEFAULT":
                        unit = varInfo["variable"]["@unit"]
                        if unit in FLOAT_SENSOR_UNITS:
                            sensor.updateUnit(unit)
                    case "TIMESLOT":
                        pass
                    case _:
                        print(f"Unknown ETA Sensor Type: {type}")
        except Exception as e:
            print(f"Failed to update sensor definition {sensor.id}: {e}")

    async def _get_raw_sensor_dict(self):
        data = await self._get_request("/user/menu/")
        text = await data.text()
        data = xmltodict.parse(text)
        raw_dict = data["eta"]["menu"]["fub"]
        return raw_dict

    async def _initialize(self):
        if not self._initialized:
            raw_dict = await self._get_raw_sensor_dict()
            self._evaluate_xml_dict(raw_dict, None)
            self._initialized = True


    async def get_sensors(self) -> SensorDict:
        await self._initialize()
        return self._sensors


class EtaAPIFactory:
    """Factory to manage and cache EtaAPI instances."""

    _instances = {}

    @staticmethod
    def get_instance(session, host, port) -> EtaAPI:
        key = (host, port)
        if key not in EtaAPIFactory._instances:
            EtaAPIFactory._instances[key] = EtaAPI(session, host, port)
        return EtaAPIFactory._instances[key]
