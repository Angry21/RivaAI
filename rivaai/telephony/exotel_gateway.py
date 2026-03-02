"""Exotel gateway for PSTN telephony in India."""

import hashlib
import logging
import uuid
from typing import Optional

import httpx

from rivaai.config.settings import Settings
from rivaai.telephony.models import CallSession, CallStatus

logger = logging.getLogger(__name__)


class ExotelGateway:
    """Exotel telephony gateway for India.

    Exotel is a popular cloud telephony provider in India with good coverage
    and support for Indian phone numbers.
    """

    def __init__(self, settings: Settings):
        """Initialize Exotel gateway.

        Args:
            settings: Application settings with Exotel configuration
        """
        self.settings = settings
        self.api_key = settings.exotel_api_key
        self.api_token = settings.exotel_api_token
        self.sid = settings.exotel_sid
        self.phone_number = settings.exotel_phone_number
        self.base_url = f"https://api.exotel.com/v1/Accounts/{self.sid}"

        self.http_client = httpx.AsyncClient(
            auth=(self.api_key, self.api_token),
            timeout=30.0,
        )

    async def handle_incoming_call(self, call_sid: str, caller_number: str) -> CallSession:
        """Handle incoming call from Exotel.

        Args:
            call_sid: Exotel call SID
            caller_number: Caller's phone number

        Returns:
            CallSession object
        """
        logger.info(f"Incoming call from {caller_number}, call_sid: {call_sid}")

        session = CallSession(
            call_sid=call_sid,
            caller_ani_hash=self._hash_phone_number(caller_number),
            session_id=self._generate_session_id(call_sid),
            websocket_url="",  # Exotel uses HTTP callbacks
            status=CallStatus.ANSWERED,
            started_at=None,
            ended_at=None,
        )

        return session

    async def start_outbound_call(
        self,
        destination_number: str,
        callback_url: str,
    ) -> str:
        """Initiate outbound call via Exotel.

        Args:
            destination_number: Phone number to call
            callback_url: URL for call status callbacks

        Returns:
            Call SID

        Raises:
            httpx.HTTPError: If call initiation fails
        """
        url = f"{self.base_url}/Calls/connect.json"

        data = {
            "From": self.phone_number,
            "To": destination_number,
            "CallerId": self.phone_number,
            "StatusCallback": callback_url,
        }

        try:
            response = await self.http_client.post(url, data=data)
            response.raise_for_status()

            result = response.json()
            call_sid = result["Call"]["Sid"]
            logger.info(f"Outbound call initiated: {call_sid}")
            return call_sid

        except httpx.HTTPError as e:
            logger.error(f"Failed to start outbound call: {e}")
            raise

    async def terminate_call(self, call_sid: str) -> None:
        """Terminate active call.

        Args:
            call_sid: Exotel call SID
        """
        url = f"{self.base_url}/Calls/{call_sid}.json"

        try:
            response = await self.http_client.post(
                url,
                data={"Status": "completed"},
            )
            response.raise_for_status()
            logger.info(f"Call terminated: {call_sid}")

        except httpx.HTTPError as e:
            logger.error(f"Failed to terminate call: {e}")
            raise

    async def get_call_details(self, call_sid: str) -> dict:
        """Get call details from Exotel.

        Args:
            call_sid: Exotel call SID

        Returns:
            Dictionary of call details
        """
        url = f"{self.base_url}/Calls/{call_sid}.json"

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get call details: {e}")
            return {}

    async def send_digits(self, call_sid: str, digits: str) -> None:
        """Send DTMF digits during a call.

        Args:
            call_sid: Exotel call SID
            digits: DTMF digits to send
        """
        url = f"{self.base_url}/Calls/{call_sid}/SendDigits.json"

        try:
            response = await self.http_client.post(
                url,
                data={"Digits": digits},
            )
            response.raise_for_status()
            logger.info(f"Sent DTMF digits to call: {call_sid}")

        except httpx.HTTPError as e:
            logger.error(f"Failed to send DTMF digits: {e}")
            raise

    def _hash_phone_number(self, phone_number: str) -> str:
        """Hash phone number for privacy.

        Args:
            phone_number: Phone number to hash

        Returns:
            SHA-256 hash of phone number
        """
        return hashlib.sha256(phone_number.encode()).hexdigest()

    def _generate_session_id(self, call_sid: str) -> str:
        """Generate session ID from call SID.

        Args:
            call_sid: Exotel call SID

        Returns:
            Session ID
        """
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, call_sid))

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


def get_exotel_gateway(settings: Settings) -> ExotelGateway:
    """Get Exotel gateway instance.

    Args:
        settings: Application settings

    Returns:
        ExotelGateway instance
    """
    return ExotelGateway(settings)
