"""Run the NENA-STA-024 conveyance subscriber.

    NTIP_CONVEYANCE_URL=wss://notifier.example/IncidentData/ent \
    NTIP_CONVEYANCE_TENANT=psap-a NTIP_CONVEYANCE_TOKEN=... \
    NTIP_DATABASE_URL=postgresql://... python -m ntip.interop.conveyance

Optional: NTIP_CONVEYANCE_INCIDENT (subscribe to one incident only),
NTIP_CONVEYANCE_EXPIRES_S (default 3600), NTIP_CONVEYANCE_ALLOW_INSECURE=1
(accept ws:// for local testing only). Model settings (NTIP_INFERENCE_*) apply
as they do for the API.
"""

import asyncio
import contextlib
import logging
import os
import signal
import time
import uuid

from ntip.api.settings import Settings
from ntip.interop.conveyance.client import run
from ntip.interop.conveyance.subscriber import Subscriber
from ntip.interop.gateway import EidoGateway
from ntip.pipeline import Pipeline


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    url = os.environ["NTIP_CONVEYANCE_URL"]
    tenant = os.environ["NTIP_CONVEYANCE_TENANT"]
    settings = Settings.from_env(serves_api=False)
    store = settings.build_store()
    pipeline = Pipeline(
        store=store,
        inference_mode=settings.inference_mode,
        extractor=settings.build_extractor(),
        reference=settings.build_reference(),
    )
    gateway = EidoGateway(pipeline)

    def subscriber() -> Subscriber:
        return Subscriber(
            gateway=gateway,
            tenant_id=tenant,
            new_id=lambda prefix: f"{prefix}_{uuid.uuid4().hex}",
            clock=time.monotonic,
            expires_s=int(os.environ.get("NTIP_CONVEYANCE_EXPIRES_S", "3600")),
            incident_id=os.environ.get("NTIP_CONVEYANCE_INCIDENT") or None,
        )

    async def serve() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):  # not available on Windows
                loop.add_signal_handler(sig, stop.set)
        await run(
            url,
            subscriber,
            stop=stop,
            token=os.environ.get("NTIP_CONVEYANCE_TOKEN") or None,
            require_tls=os.environ.get("NTIP_CONVEYANCE_ALLOW_INSECURE") != "1",
        )

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
