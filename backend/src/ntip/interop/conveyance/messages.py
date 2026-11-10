"""Validate conveyance messages against the pinned NENA message schema.

The published ``subscriberMessage`` / ``notifierMessage`` unions are
``oneOf`` lists whose branches each make their single property optional, so
any message satisfies every branch and a strict ``oneOf`` check rejects all of
them. Messages are therefore dispatched on their one top-level key and
validated against that object's own schema (e.g. ``eventObject``), which is
both stricter and unambiguous.
"""

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft7Validator
from referencing import Registry
from referencing.jsonschema import DRAFT7

from ntip.interop.conveyance.profile import CONVEYANCE_PROFILE, ConveyanceProfile
from ntip.interop.eido.fetch import load_documents

_BASE = "https://pinned-conveyance.invalid/"

# Top-level key -> schema object, for the messages a subscriber exchanges.
NOTIFIER_MESSAGES = {
    "subscribeResponse": "subscribeResponseObject",
    "unsubscribeResponse": "unsubscribeResponseObject",
    "response": "responseObject",
    "event": "eventObject",
    "terminate": "terminateObject",
}
SUBSCRIBER_MESSAGES = {
    "subscribe": "subscribeObject",
    "unsubscribe": "unsubscribeObject",
    "eventResponse": "eventResponseObject",
    "terminateResponse": "terminateResponseObject",
}


class InvalidMessage(ValueError):
    pass


@dataclass(frozen=True)
class Message:
    kind: str  # the top-level key, e.g. "event"
    body: dict[str, Any]


_VALIDATORS: dict[str, Draft7Validator] = {}


def _validator(name: str, profile: ConveyanceProfile) -> Draft7Validator:
    key = f"{profile.profile_id}:{name}"
    if key not in _VALIDATORS:
        registry: Registry[Any] = Registry()
        for path, document in load_documents(profile).items():
            registry = registry.with_resource(_BASE + path, DRAFT7.create_resource(document))
        ref = {"$ref": f"{_BASE}{profile.schema_path}#/components/schemas/{name}"}
        _VALIDATORS[key] = Draft7Validator(ref, registry=registry)
    return _VALIDATORS[key]


def check(
    message: Any, kinds: dict[str, str], profile: ConveyanceProfile = CONVEYANCE_PROFILE
) -> Message:
    """The message's kind and body, or InvalidMessage saying what is wrong."""
    if not isinstance(message, dict) or len(message) != 1:
        raise InvalidMessage("a message is a JSON object with exactly one top-level key")
    [(kind, body)] = message.items()
    if kind not in kinds:
        raise InvalidMessage(f"unexpected message {kind!r}")
    errors = sorted(_validator(kinds[kind], profile).iter_errors(message), key=lambda e: e.path)
    if errors:
        raise InvalidMessage(f"{kind}: {errors[0].message[:200]}")
    if not isinstance(body, dict):
        raise InvalidMessage(f"{kind} must be an object")
    return Message(kind, body)
