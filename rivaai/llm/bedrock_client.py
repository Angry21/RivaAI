"""AWS Bedrock client for LLM and embedding operations."""

import json
import logging
from typing import AsyncIterator, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from rivaai.config.settings import Settings

logger = logging.getLogger(__name__)


class BedrockLLMClient:
    """Client for AWS Bedrock LLM operations."""

    def __init__(self, settings: Settings):
        """Initialize Bedrock LLM client.

        Args:
            settings: Application settings with AWS configuration
        """
        self.settings = settings
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.main_model = settings.bedrock_main_model
        self.fast_model = settings.bedrock_fast_model

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        use_fast_model: bool = False,
    ) -> str:
        """Generate LLM response using Bedrock.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_fast_model: Use fast model (Haiku) instead of main model (Sonnet)

        Returns:
            Generated response text

        Raises:
            ClientError: If Bedrock API call fails
        """
        model_id = self.fast_model if use_fast_model else self.main_model

        try:
            # Claude 3 message format
            messages = [{"role": "user", "content": prompt}]

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                request_body["system"] = system_prompt

            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except ClientError as e:
            logger.error(f"Bedrock LLM error: {e}")
            raise

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        use_fast_model: bool = False,
    ) -> AsyncIterator[str]:
        """Generate streaming LLM response using Bedrock.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            use_fast_model: Use fast model instead of main model

        Yields:
            Response text chunks

        Raises:
            ClientError: If Bedrock API call fails
        """
        model_id = self.fast_model if use_fast_model else self.main_model

        try:
            messages = [{"role": "user", "content": prompt}]

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                request_body["system"] = system_prompt

            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body),
            )

            # Process streaming response
            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])

                if chunk["type"] == "content_block_delta":
                    if "delta" in chunk and "text" in chunk["delta"]:
                        yield chunk["delta"]["text"]

        except ClientError as e:
            logger.error(f"Bedrock streaming error: {e}")
            raise


class BedrockEmbeddingClient:
    """Client for AWS Bedrock embedding operations."""

    def __init__(self, settings: Settings):
        """Initialize Bedrock embedding client.

        Args:
            settings: Application settings with AWS configuration
        """
        self.settings = settings
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.model_id = settings.bedrock_embedding_model
        self.dimensions = settings.embedding_dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector

        Raises:
            ClientError: If Bedrock API call fails
        """
        try:
            request_body = {
                "inputText": text,
                "dimensions": self.dimensions,
                "normalize": True,
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())
            return response_body["embedding"]

        except ClientError as e:
            logger.error(f"Bedrock embedding error: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ClientError: If Bedrock API call fails
        """
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings


def get_bedrock_llm_client(settings: Settings) -> BedrockLLMClient:
    """Get Bedrock LLM client instance.

    Args:
        settings: Application settings

    Returns:
        BedrockLLMClient instance
    """
    return BedrockLLMClient(settings)


def get_bedrock_embedding_client(settings: Settings) -> BedrockEmbeddingClient:
    """Get Bedrock embedding client instance.

    Args:
        settings: Application settings

    Returns:
        BedrockEmbeddingClient instance
    """
    return BedrockEmbeddingClient(settings)
