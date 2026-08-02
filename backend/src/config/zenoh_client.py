"""Client for dynamically managing Zenoh credentials and ACLs."""

import json
import logging

import httpx

from src.config.http_client import get_http_client
from src.exceptions import ExternalServiceError

logger = logging.getLogger("config.zenoh_client")


class ZenohAdminClient:
    """Manage Zenoh ACLs and credentials through the admin REST API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_http_client()

    async def _put(self, path: str, payload: dict | str) -> None:
        try:
            if isinstance(payload, str):
                response = await self.client.put(
                    f"{self.base_url}{path}",
                    content=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                response = await self.client.put(
                    f"{self.base_url}{path}", json=payload
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            logger.error("Zenoh REST PUT %s failed: %s", path, err.response.text)
            raise ExternalServiceError(
                f"Zenoh API error (HTTP {err.response.status_code})"
            ) from err
        except httpx.HTTPError as err:
            logger.error("Zenoh REST request failed for %s: %s", path, err)
            raise ExternalServiceError(
                "Failed to communicate with Zenoh router"
            ) from err

    async def _delete(self, path: str) -> None:
        try:
            response = await self.client.delete(f"{self.base_url}{path}")
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()
        except httpx.HTTPError as err:
            logger.error("Zenoh REST DELETE %s failed: %s", path, err)
            raise ExternalServiceError(
                "Failed to communicate with Zenoh router"
            ) from err

    async def _apply_acl_triad(
        self,
        *,
        subject_username: str,
        rule_id: str,
        subject_id: str,
        policy_id: str,
        key_exprs: list[str],
    ) -> None:
        await self._put(
            f"/@/config/access_control/rules/{rule_id}",
            {
                "id": rule_id,
                "permission": "allow",
                "flows": ["ingress", "egress"],
                "messages": [
                    "put",
                    "declare_subscriber",
                    "query",
                    "reply",
                    "delete",
                ],
                "key_exprs": key_exprs,
            },
        )
        await self._put(
            f"/@/config/access_control/subjects/{subject_id}",
            {"id": subject_id, "usernames": [subject_username]},
        )
        await self._put(
            f"/@/config/access_control/policies/{policy_id}",
            {
                "id": policy_id,
                "subjects": [subject_id],
                "rules": [rule_id],
            },
        )

    async def configure_user_app(
        self,
        user_id: str,
        mower_ids: list[str],
        password: str | None = None,
    ) -> None:
        """Configure a user's ACL and optionally provision its password.

        ``password`` is intentionally optional so ACL bootstrap never creates
        preset user credentials. Runtime login supplies the five-minute JWT as
        the Zenoh password.
        """
        if password is not None:
            await self._put(
                f"/@/config/transport/auth/usrpwd/dictionary/{user_id}",
                json.dumps(password),
            )

        key_exprs = (
            [f"mower/{mower_id}/**" for mower_id in mower_ids]
            if mower_ids
            else [f"unassigned/{user_id}/deny"]
        )
        await self._apply_acl_triad(
            subject_username=user_id,
            rule_id=f"rule_{user_id}",
            subject_id=f"subject_{user_id}",
            policy_id=f"policy_{user_id}",
            key_exprs=key_exprs,
        )

    async def configure_mower_device(self, mower_id: str) -> None:
        """Configure a mower ACL without creating a preset credential."""
        await self._apply_acl_triad(
            subject_username=mower_id,
            rule_id=f"rule_mower_{mower_id}",
            subject_id=f"subject_mower_{mower_id}",
            policy_id=f"policy_mower_{mower_id}",
            key_exprs=[f"mower/{mower_id}/**"],
        )

    async def delete_user_password(self, user_id: str) -> None:
        """Remove one dynamically provisioned user credential."""
        await self._delete(
            f"/@/config/transport/auth/usrpwd/dictionary/{user_id}"
        )
