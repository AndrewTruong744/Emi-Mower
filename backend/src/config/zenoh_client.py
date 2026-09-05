"""Client for dynamically managing Zenoh credentials and ACLs."""

import json
import logging

import httpx

from src.config.http_client import get_http_client
from src.config.settings import settings
from src.exceptions import ExternalServiceError

logger = logging.getLogger("config.zenoh_client")


class ZenohAdminClient:
    """Manage Zenoh ACLs and credentials through the admin REST API."""

    def __init__(
        self,
        app_base_url: str | None = None,
        mower_base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.app_base_url = (app_base_url or settings.ZENOH_APP_REST_URL).rstrip("/")
        self.mower_base_url = (mower_base_url or settings.ZENOH_MTLS_REST_URL).rstrip(
            "/"
        )
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_http_client()

    async def _put(self, base_url: str, path: str, payload: dict | str) -> None:
        try:
            if isinstance(payload, str):
                response = await self.client.put(
                    f"{base_url}{path}",
                    content=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                response = await self.client.put(f"{base_url}{path}", json=payload)
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

    async def _delete(self, base_url: str, path: str) -> None:
        try:
            response = await self.client.delete(f"{base_url}{path}")
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
        subject_username: str | None = None,
        subject_cert_common_name: str | None = None,
        rule_id: str,
        subject_id: str,
        policy_id: str,
        key_exprs: list[str],
        messages: list[str],
        base_url: str,
    ) -> None:
        if (subject_username is None) == (subject_cert_common_name is None):
            raise ValueError("configure exactly one Zenoh subject identity")

        await self._put(
            base_url,
            f"/@/config/access_control/rules/{rule_id}",
            {
                "id": rule_id,
                "permission": "allow",
                "flows": ["ingress", "egress"],
                "messages": messages,
                "key_exprs": key_exprs,
            },
        )
        subject: dict[str, str | list[str]] = {"id": subject_id}
        if subject_username is not None:
            subject["usernames"] = [subject_username]
        if subject_cert_common_name is not None:
            subject["cert_common_names"] = [subject_cert_common_name]
        await self._put(
            base_url,
            f"/@/config/access_control/subjects/{subject_id}",
            subject,
        )
        await self._put(
            base_url,
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
                self.app_base_url,
                f"/@/config/transport/auth/usrpwd/dictionary/{user_id}",
                json.dumps(password),
            )

        key_exprs = ["user/**"]
        if mower_ids:
            key_exprs.extend(f"mower/{mower_id}/**" for mower_id in mower_ids)
        else:
            key_exprs.append(f"unassigned/{user_id}/deny")
        await self._apply_acl_triad(
            subject_username=user_id,
            rule_id=f"rule_{user_id}",
            subject_id=f"subject_{user_id}",
            policy_id=f"policy_{user_id}",
            key_exprs=key_exprs,
            messages=["put", "declare_subscriber", "query", "reply", "delete"],
            base_url=self.app_base_url,
        )

    async def configure_mower_device(
        self, mower_id: str, certificate_common_name: str | None = None
    ) -> None:
        """Authorize one mTLS mower certificate on only its own routes."""
        await self._apply_acl_triad(
            subject_cert_common_name=certificate_common_name or f"mower:{mower_id}",
            rule_id=f"rule_mower_{mower_id}",
            subject_id=f"subject_mower_{mower_id}",
            policy_id=f"policy_mower_{mower_id}",
            key_exprs=[f"mower/{mower_id}/**"],
            messages=[
                "put",
                "declare_subscriber",
                "declare_queryable",
                "query",
                "reply",
                "delete",
            ],
            base_url=self.mower_base_url,
        )

    async def delete_user_password(self, user_id: str) -> None:
        """Remove one runtime credential, never the startup dictionary file."""
        await self._delete(
            self.app_base_url, f"/@/config/transport/auth/usrpwd/dictionary/{user_id}"
        )
