
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Location:
    location_id: str
    name: str

@dataclass
class Device:
    device_id: str
    location_id: str
    serial_id: str
    name: str
    type: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DeviceConfiguration:
    config_id: str
    device_id: str
    config_name: str
    config_value: str
    config_type: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class LocationToDevice:
    device_id: str
    user_id: str
    type: str