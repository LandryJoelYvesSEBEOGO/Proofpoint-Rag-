"""Verify the development Keycloak realm's initial role and API-client contract."""

import json
from pathlib import Path
from typing import TypeGuard

REALM_PATH = Path(__file__).parents[1] / "deploy" / "keycloak" / "proofpoint-local-realm.json"


def load_realm() -> dict[str, object]:
    value: object = json.loads(REALM_PATH.read_text(encoding="utf-8"))
    if not _is_json_object(value):
        raise AssertionError("Keycloak realm configuration must be a JSON object.")
    return value


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _is_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def test_local_realm_defines_required_account_roles() -> None:
    realm = load_realm()
    role_config = realm["roles"]
    assert _is_json_object(role_config)
    realm_roles = role_config["realm"]
    assert _is_list(realm_roles)
    role_names: list[str] = []
    for role in realm_roles:
        assert _is_json_object(role)
        name = role["name"]
        assert isinstance(name, str)
        role_names.append(name)

    assert realm["realm"] == "proofpoint-local"
    assert realm["enabled"] is True
    assert set(role_names) == {"Admin", "Developer", "Reader"}


def test_api_client_is_bearer_only_and_does_not_enable_password_grants() -> None:
    realm = load_realm()
    clients = realm["clients"]
    assert _is_list(clients)
    api_clients: list[dict[str, object]] = []
    for client in clients:
        assert _is_json_object(client)
        if client.get("clientId") == "proofpoint-api":
            api_clients.append(client)
    assert len(api_clients) == 1
    api_client = api_clients[0]

    assert api_client["bearerOnly"] is True
    assert api_client["publicClient"] is False
    assert api_client["standardFlowEnabled"] is False
    assert api_client["directAccessGrantsEnabled"] is False
