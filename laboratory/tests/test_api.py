"""API tests for laboratory ViewSets.

laboratory is a shared equipment catalog with no project relation — every
endpoint here must be reachable by any authenticated user regardless of
project membership (IsAuthenticated only, no IsProjectMember/guardian).
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework.test import APIClient

from laboratory.models import (
    Accessory,
    AccessoryParameter,
    Calibration,
    Device,
    Firmware,
    Manufacturer,
    Method,
)
from prototype.models import Researcher

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests."""

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...


def _make_client() -> _TestClient:
    """Return a new APIClient, cast to the correctly-typed class above."""
    return cast("_TestClient", APIClient())


class _BaseApiTest(TestCase):
    user: ClassVar[User]
    manufacturer: ClassVar[Manufacturer]
    device: ClassVar[Device]
    accessory: ClassVar[Accessory]
    accessory_parameter: ClassVar[AccessoryParameter]
    method: ClassVar[Method]
    researcher: ClassVar[Researcher]
    calibration: ClassVar[Calibration]
    firmware: ClassVar[Firmware]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="lab_api_user", password="pw")
        cls.manufacturer = Manufacturer.objects.create(
            name="Lexsyg", website="https://example.org"
        )
        cls.device = Device.objects.create(
            name="TL/OSL Reader", manufacturer=cls.manufacturer
        )
        cls.accessory = Accessory.objects.create(
            device=cls.device, name="IR-LED array"
        )
        cls.method = Method.objects.create(
            name="Single Aliquot Regeneration", device=cls.device
        )
        cls.accessory_parameter = AccessoryParameter.objects.create(
            method=cls.method,
            accessory=cls.accessory,
            parameter_name="Power",
            parameter_value="90",
            parameter_unit="%",
        )
        auth_user = User.objects.create_user(username="lab_researcher", password="pw")
        cls.researcher = Researcher.objects.create(user=auth_user)
        cls.calibration = Calibration.objects.create(
            device=cls.device,
            date=datetime.date(2024, 1, 1),
            researcher=cls.researcher,
        )
        cls.firmware = Firmware.objects.create(
            device=cls.device,
            version="1.2.0",
            installation_date=datetime.date(2024, 1, 1),
        )

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.user)


class ManufacturerViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/manufacturers/")
        assert resp.status_code == 200

    def test_list_contains_manufacturer(self) -> None:
        resp = self.client.get("/api/v1/manufacturers/")
        names = [item["name"] for item in resp.json()["results"]]
        assert "Lexsyg" in names

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/manufacturers/")
        assert resp.status_code in (401, 403)


class DeviceViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/devices/")
        assert resp.status_code == 200

    def test_detail_returns_200(self) -> None:
        resp = self.client.get(f"/api/v1/devices/{self.device.pk}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "TL/OSL Reader"


class AccessoryViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/accessories/")
        assert resp.status_code == 200


class AccessoryParameterViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/accessory-parameters/")
        assert resp.status_code == 200


class MethodViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/methods/")
        assert resp.status_code == 200

    def test_list_contains_method(self) -> None:
        resp = self.client.get("/api/v1/methods/")
        names = [item["name"] for item in resp.json()["results"]]
        assert "Single Aliquot Regeneration" in names


class CalibrationViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/calibrations/")
        assert resp.status_code == 200


class FirmwareViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/firmwares/")
        assert resp.status_code == 200

    def test_list_contains_firmware(self) -> None:
        resp = self.client.get("/api/v1/firmwares/")
        versions = [item["version"] for item in resp.json()["results"]]
        assert "1.2.0" in versions
