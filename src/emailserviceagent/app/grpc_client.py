import sys
from pathlib import Path
import grpc

from app.config import settings

REPO_ROOT = Path(__file__).resolve().parents[2]
EMAILSERVICE_SRC = REPO_ROOT / "src" / "emailservice"

if str(EMAILSERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(EMAILSERVICE_SRC))

import demo_pb2  # noqa: E402
import demo_pb2_grpc  # noqa: E402


class EmailServiceClient:
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.EMAILSERVICE_HOST
        self.port = port or settings.EMAILSERVICE_PORT
        self.address = f"{self.host}:{self.port}"

    def _build_order(self, payload: dict):
        shipping = payload.get("shipping_address", {})

        return demo_pb2.OrderResult(
            order_id=payload.get("order_id", ""),
            shipping_tracking_id="",
            shipping_cost=demo_pb2.Money(
                currency_code=payload.get("currency_code", "USD"),
                units=int(payload.get("total", 0)),
                nanos=0,
            ),
            shipping_address=demo_pb2.Address(
                street_address=shipping.get("street_address", ""),
                city=shipping.get("city", ""),
                state=shipping.get("state", ""),
                country=shipping.get("country", ""),
                zip_code=shipping.get("zip_code", 0),
            ),
            items=[],
        )

    def send_confirmation_email(self, payload: dict) -> dict:
        order = self._build_order(payload)

        with grpc.insecure_channel(self.address) as channel:
            stub = demo_pb2_grpc.EmailServiceStub(channel)
            stub.SendOrderConfirmation(
                demo_pb2.SendOrderConfirmationRequest(
                    email=payload["email"],
                    order=order,
                )
            )

        return {
            "status": "sent"
        }