"""Amazon Connect gateway for PSTN telephony in India."""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from rivaai.config.settings import Settings
from rivaai.telephony.models import CallSession, CallStatus

logger = logging.getLogger(__name__)


class AmazonConnectGateway:
    """Amazon Connect telephony gateway for India."""

    def __init__(self, settings: Settings):
        """Initialize Amazon Connect gateway.

        Args:
            settings: Application settings with Amazon Connect configuration
        """
        self.settings = settings
        self.client = boto3.client(
            "connect",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.instance_id = settings.amazon_connect_instance_id
        self.contact_flow_id = settings.amazon_connect_contact_flow_id
        self.phone_number = settings.amazon_connect_phone_number

    async def handle_incoming_call(self, contact_id: str, caller_number: str) -> CallSession:
        """Handle incoming call from Amazon Connect.

        Args:
            contact_id: Amazon Connect contact ID
            caller_number: Caller's phone number

        Returns:
            CallSession object

        Note:
            Amazon Connect uses contact flows to route calls
            This method is called from the contact flow webhook
        """
        logger.info(f"Incoming call from {caller_number}, contact_id: {contact_id}")

        session = CallSession(
            call_sid=contact_id,
            caller_ani_hash=self._hash_phone_number(caller_number),
            session_id=self._generate_session_id(contact_id),
            websocket_url="",  # Amazon Connect uses different streaming mechanism
            status=CallStatus.ANSWERED,
            started_at=None,  # Will be set by caller
            ended_at=None,
        )

        return session

    async def start_outbound_call(
        self,
        destination_number: str,
        contact_flow_id: Optional[str] = None,
    ) -> str:
        """Initiate outbound call via Amazon Connect.

        Args:
            destination_number: Phone number to call
            contact_flow_id: Optional contact flow ID override

        Returns:
            Contact ID

        Raises:
            ClientError: If call initiation fails
        """
        flow_id = contact_flow_id or self.contact_flow_id

        try:
            response = self.client.start_outbound_voice_contact(
                DestinationPhoneNumber=destination_number,
                ContactFlowId=flow_id,
                InstanceId=self.instance_id,
                SourcePhoneNumber=self.phone_number,
            )

            contact_id = response["ContactId"]
            logger.info(f"Outbound call initiated: {contact_id}")
            return contact_id

        except ClientError as e:
            logger.error(f"Failed to start outbound call: {e}")
            raise

    async def terminate_call(self, contact_id: str) -> None:
        """Terminate active call.

        Args:
            contact_id: Amazon Connect contact ID
        """
        try:
            self.client.stop_contact(
                ContactId=contact_id,
                InstanceId=self.instance_id,
            )
            logger.info(f"Call terminated: {contact_id}")

        except ClientError as e:
            logger.error(f"Failed to terminate call: {e}")
            raise

    async def get_contact_attributes(self, contact_id: str) -> dict:
        """Get contact attributes for a call.

        Args:
            contact_id: Amazon Connect contact ID

        Returns:
            Dictionary of contact attributes
        """
        try:
            response = self.client.get_contact_attributes(
                InstanceId=self.instance_id,
                InitialContactId=contact_id,
            )
            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(f"Failed to get contact attributes: {e}")
            return {}

    def _hash_phone_number(self, phone_number: str) -> str:
        """Hash phone number for privacy.

        Args:
            phone_number: Phone number to hash

        Returns:
            SHA-256 hash of phone number
        """
        import hashlib

        return hashlib.sha256(phone_number.encode()).hexdigest()

    def _generate_session_id(self, contact_id: str) -> str:
        """Generate session ID from contact ID.

        Args:
            contact_id: Amazon Connect contact ID

        Returns:
            Session ID
        """
        import uuid

        return str(uuid.uuid5(uuid.NAMESPACE_DNS, contact_id))


def get_amazon_connect_gateway(settings: Settings) -> AmazonConnectGateway:
    """Get Amazon Connect gateway instance.

    Args:
        settings: Application settings

    Returns:
        AmazonConnectGateway instance
    """
    return AmazonConnectGateway(settings)
