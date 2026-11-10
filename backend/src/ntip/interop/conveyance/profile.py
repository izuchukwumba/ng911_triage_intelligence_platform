"""The pinned NENA-STA-024 conveyance profile (design v1.2, section 3B.2).

The platform takes the *subscriber* role of NENA's WebSocket subscribe/notify
conveyance: it connects to an authorised notifier (for example a CAD system's
EIDO service), subscribes to EIDOs, acknowledges each notification, and feeds
every EIDO through the import gateway. It never notifies, pushes or writes
back (ADR-INT-002).

Messages are validated against NENA's published message schema, pinned to a
commit and a sha256. Like the EIDO schema it is fetched, never vendored: the
NENA911/WebSocket-Subscribe-Notify repository publishes no licence. Only the
message schema has been reviewed, not the normative text of NENA-STA-024, so
no conveyance compliance is claimed.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConveyanceProfile:
    profile_id: str
    description: str
    repository: str
    commit: str
    schema_path: str
    files: dict[str, str] = field(default_factory=dict)
    # The MIME type this subscriber asks for in requestAccepts.
    request_accepts: str = "application/emergency.eido+json"

    def raw_url(self, path: str) -> str:
        return f"https://raw.githubusercontent.com/{self.repository}/{self.commit}/{path}"


CONVEYANCE_PROFILE = ConveyanceProfile(
    profile_id="ntip-sta024-ws-subscriber-v1",
    description="NENA WebSocket Subscribe/Notify message schema v1.1, subscriber role",
    repository="NENA911/WebSocket-Subscribe-Notify",
    # Tag v1.1 (2025-03-14).
    commit="518ad6c6e9ce0f0fe20a3c54548af39abe34b2c0",
    schema_path="schema/websocket.yaml",
    files={
        "schema/websocket.yaml": "8d257503d899f939acf251075b1879cfd52bfdd590e00afcfe475c5377e392cf"
    },
)
