"""Authenticated management API for the sibling Zenoh fork's live ACLs."""

from pathlib import Path
from urllib.parse import quote

import httpx

from src.config.http_client import get_http_client
from src.config.settings import settings
from src.exceptions import ExternalServiceError


def _rule(identifier: str, keys: list[str], messages: list[str], flow: str) -> dict:
    return {
        "id": identifier,
        "permission": "allow",
        "key_exprs": keys,
        "messages": messages,
        "flows": [flow],
    }


class ZenohAdminClient:
    def __init__(
        self,
        app_base_url: str | None = None,
        mower_base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        *,
        admin_token: str | None = None,
    ):
        self.app_base_url = (app_base_url or settings.ZENOH_APP_REST_URL).rstrip("/")
        self.mower_base_url = (mower_base_url or settings.ZENOH_MTLS_REST_URL).rstrip(
            "/"
        )
        self._http_client = http_client
        self._admin_token = admin_token

    @property
    def client(self) -> httpx.AsyncClient:
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_http_client()

    async def _request(
        self, method: str, base: str, path: str, payload=None
    ) -> httpx.Response:
        try:
            token = (
                self._admin_token
                or Path(settings.ZENOH_ADMIN_TOKEN_FILE).read_text().strip()
            )
            if len(token) < 32:
                raise ValueError("Missing or invalid Zenoh management credential")
            response = await self.client.request(
                method,
                f"{base}/@/runtime{path}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            if method != "DELETE" or response.status_code != 404:
                response.raise_for_status()
            return response
        except (httpx.HTTPError, OSError, ValueError) as error:
            # Do not expose credentials, request payloads or router error bodies.
            raise ExternalServiceError("Zenoh runtime administration failed") from error

    async def captured_connections(self) -> list[dict]:
        response = await self._request("GET", self.app_base_url, "/connections")
        return response.json()

    async def configure_user_app(self, user_id: str, mower_ids: list[str]) -> None:
        # Operation-specific flows: an app cannot publish telemetry, create mower
        # liveliness tokens, or declare a queryable impersonating the backend.
        rules = [
            _rule("cutout-upload", ["user/cutouts/uploaded"], ["put"], "ingress"),
            _rule("backend-query", ["user/**"], ["query"], "ingress"),
            _rule("backend-reply", ["user/**"], ["reply"], "egress"),
            # Routing announcements carry no application payload. Native clients
            # need the backend's wildcard subscriber/queryable declarations.
            _rule(
                "routing-announcements",
                ["user/**", "mower/**"],
                ["declare_subscriber", "declare_queryable"],
                "egress",
            ),
        ]
        if mower_ids:
            telemetry = [f"mower/{m}/telemetry" for m in mower_ids]
            liveliness = [f"mower/{m}/liveliness" for m in mower_ids]
            queries = [
                f"mower/{m}/{suffix}"
                for m in mower_ids
                for suffix in (
                    "command",
                    "update_name",
                    "telemetry/*/old",
                    "livekit/consume",
                )
            ]
            commands = [f"mower/{m}/joystick" for m in mower_ids]
            rules.extend(
                [
                    _rule(
                        "telemetry-subscribe",
                        telemetry,
                        ["declare_subscriber"],
                        "ingress",
                    ),
                    _rule("telemetry-read", telemetry, ["put"], "egress"),
                    _rule(
                        "liveliness-subscribe",
                        liveliness,
                        ["declare_liveliness_subscriber", "liveliness_query"],
                        "ingress",
                    ),
                    _rule(
                        "liveliness-read", liveliness, ["liveliness_token"], "egress"
                    ),
                    _rule("mower-query", queries, ["query"], "ingress"),
                    _rule("mower-reply", queries, ["reply"], "egress"),
                    _rule("joystick", commands, ["put"], "ingress"),
                ]
            )
        await self._request(
            "PUT",
            self.app_base_url,
            f"/principals/{quote(user_id, safe='')}",
            {"rules": rules},
        )

    async def authorize_connection(
        self, user_id: str, context: dict, ttl_seconds: int
    ) -> None:
        identifier, nonce = context.get("id", ""), context.get("nonce", "")
        if any(
            not isinstance(value, str)
            or len(value) != 32
            or any(c not in "0123456789abcdef" for c in value)
            for value in (identifier, nonce)
        ):
            raise ValueError("Invalid router connection context")
        await self._request(
            "PUT",
            self.app_base_url,
            f"/connections/{identifier}/authorization",
            {"principal": user_id, "nonce": nonce, "ttl_seconds": ttl_seconds},
        )

    async def revoke_connection(self, connection_id: str) -> None:
        await self._request(
            "DELETE",
            self.app_base_url,
            f"/connections/{quote(connection_id, safe='')}/authorization",
        )

    async def retire_user(self, user_id: str) -> None:
        """Deny old sessions while letting the account-switch reply finish."""
        await self._request(
            "PUT",
            self.app_base_url,
            f"/principals/{quote(user_id, safe='')}",
            {
                "rules": [
                    _rule(
                        "account-switch-reply",
                        ["user/update_email"],
                        ["reply"],
                        "egress",
                    )
                ]
            },
        )

    async def revoke_user(self, user_id: str) -> None:
        await self._request(
            "DELETE", self.app_base_url, f"/principals/{quote(user_id, safe='')}"
        )

    async def configure_mower_device(
        self, mower_id: str, certificate_common_name: str | None = None
    ) -> None:
        keys = [f"mower/{mower_id}/**"]
        rules = [
            _rule(
                "mower",
                keys,
                [
                    "put",
                    "declare_subscriber",
                    "liveliness_token",
                    "declare_queryable",
                    "query",
                    "reply",
                    "delete",
                ],
                flow,
            )
            for flow in ("ingress", "egress")
        ]
        # IDs must be unique within an ACL snapshot.
        for rule, flow in zip(rules, ("ingress", "egress")):
            rule["id"] += f"-{flow}"
        rules.append(
            _rule(
                "routing-announcements",
                ["mower/**"],
                ["declare_subscriber", "declare_queryable"],
                "egress",
            )
        )
        await self._request(
            "PUT",
            self.mower_base_url,
            f"/policies/{quote('mower-' + mower_id, safe='')}",
            {
                "subject": {
                    "id": mower_id,
                    "cert_common_names": [
                        certificate_common_name or f"mower:{mower_id}"
                    ],
                },
                "rules": rules,
            },
        )

    async def remove_mower_permissions(self, mower_id: str) -> None:
        await self._request(
            "DELETE",
            self.mower_base_url,
            f"/policies/{quote('mower-' + mower_id, safe='')}",
        )
