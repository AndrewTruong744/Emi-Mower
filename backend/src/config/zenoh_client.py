import json
import logging
import httpx

from src.config.http_client import get_http_client
from src.exceptions import ExternalServiceError

logger = logging.getLogger("config.zenoh_client")


class ZenohAdminClient:
    """Client for managing Zenoh router configuration and ACLs via Zenoh REST API."""

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
        client = self.client
        url = f"{self.base_url}{path}"
        try:
            if isinstance(payload, str):
                resp = await client.put(
                    url,
                    content=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                resp = await client.put(url, json=payload)

            if resp.status_code >= 400:
                logger.error(
                    f"Zenoh REST PUT {path} failed with HTTP {resp.status_code}: {resp.text}"
                )
                raise ExternalServiceError(
                    f"Zenoh API error (HTTP {resp.status_code})"
                )
        except ExternalServiceError:
            raise
        except httpx.HTTPError as err:
            logger.error(
                f"Network error connecting to Zenoh REST API at {path}: {err}"
            )
            raise ExternalServiceError(
                "Failed to communicate with Zenoh router"
            ) from err

    async def _apply_acl_triad(
        self,
        subject_username: str,
        rule_id: str,
        subject_id: str,
        policy_id: str,
        key_exprs: list[str],
    ) -> None:
        """Helper to create or update the rule -> subject -> policy triad in Zenoh."""
        # 1. Update Rule
        rule_payload = {
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
        }
        await self._put(
            f"/@/config/access_control/rules/{rule_id}", rule_payload
        )

        # 2. Update Subject
        subject_payload = {"id": subject_id, "usernames": [subject_username]}
        await self._put(
            f"/@/config/access_control/subjects/{subject_id}",
            subject_payload,
        )

        # 3. Update Policy
        policy_payload = {
            "id": policy_id,
            "subjects": [subject_id],
            "rules": [rule_id],
        }
        await self._put(
            f"/@/config/access_control/policies/{policy_id}", policy_payload
        )

    # ==========================================
    # 1. USER APP CONFIGURATION
    # ==========================================
    async def configure_user_app(
        self, user_id: str, jwt_token: str, mower_ids: list[str]
    ) -> None:
        """Sets credentials and ACL permissions for a human user app across all their mowers."""
        # Update Password Dictionary
        await self._put(
            f"/@/config/transport/auth/usrpwd/dictionary/{user_id}",
            json.dumps(jwt_token),
        )

        # Key expressions for user app (access to all owned mowers)
        key_exprs = (
            [f"mower/{m_id}/**" for m_id in mower_ids]
            if mower_ids
            else [f"unassigned/{user_id}/deny"]
        )

        # Apply Rule/Subject/Policy
        await self._apply_acl_triad(
            subject_username=user_id,
            rule_id=f"rule_{user_id}",
            subject_id=f"subject_{user_id}",
            policy_id=f"policy_{user_id}",
            key_exprs=key_exprs,
        )

    # ==========================================
    # 2. MOWER DEVICE CONFIGURATION
    # ==========================================
    async def configure_mower_device(
        self, mower_id: str, device_token: str
    ) -> None:
        """Sets credentials and ACL permissions for a mower edge device to access only its own key space."""
        # Update Password Dictionary for Mower
        await self._put(
            f"/@/config/transport/auth/usrpwd/dictionary/{mower_id}",
            json.dumps(device_token),
        )

        # Key expressions for mower (isolated exclusively to mower/{mower_id}/**)
        key_exprs = [f"mower/{mower_id}/**"]

        # Apply Rule/Subject/Policy
        await self._apply_acl_triad(
            subject_username=mower_id,
            rule_id=f"rule_mower_{mower_id}",
            subject_id=f"subject_mower_{mower_id}",
            policy_id=f"policy_mower_{mower_id}",
            key_exprs=key_exprs,
        )