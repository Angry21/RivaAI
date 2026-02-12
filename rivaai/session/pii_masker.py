"""PII masking using NER-based tokenization."""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class PIIMasker:
    """Masks personally identifiable information (PII) using NER-based detection."""

    def __init__(self) -> None:
        """Initialize PII masker with pattern-based detection.

        Note: This implementation uses regex patterns for PII detection.
        For production, consider using spaCy or other NER libraries for
        more robust entity recognition.
        """
        # Compile regex patterns for common PII types
        self._patterns: Dict[str, re.Pattern[str]] = {
            # Indian phone numbers: +91-XXXXXXXXXX, 91XXXXXXXXXX, XXXXXXXXXX
            "phone": re.compile(r"(?:\+91[-\s]?|91[-\s]?)?[6-9]\d{9}(?:\s|$|[^\d])"),
            # Email addresses
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            # Aadhaar numbers: XXXX XXXX XXXX or XXXXXXXXXXXX
            "aadhaar": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
            # PAN card: ABCDE1234F
            "pan": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
            # Bank account numbers (8-18 digits)
            "bank_account": re.compile(r"\b\d{8,18}\b"),
            # Pincode (6 digits)
            "pincode": re.compile(r"\b\d{6}\b"),
        }

        # Common Indian name patterns (simplified)
        # In production, use NER models trained on Indian names
        self._name_indicators = [
            "my name is",
            "i am",
            "this is",
            "naam hai",
            "mera naam",
        ]

    def mask_pii(self, text: str) -> str:
        """Mask PII in text using NER-based tokenization.

        Detects and masks:
        - Phone numbers (Indian format)
        - Email addresses
        - Aadhaar numbers
        - PAN card numbers
        - Bank account numbers
        - Pincodes
        - Names (pattern-based)

        Args:
            text: Input text potentially containing PII

        Returns:
            Text with PII masked using [MASKED_<TYPE>] tokens
        """
        if not text:
            return text

        masked_text = text

        # Track what was masked for logging
        masked_items: List[Tuple[str, str]] = []

        # Mask phone numbers
        def mask_phone(match: re.Match[str]) -> str:
            original = match.group(0)
            masked_items.append(("phone", original.strip()))
            return "[MASKED_PHONE]"

        masked_text = self._patterns["phone"].sub(mask_phone, masked_text)

        # Mask email addresses
        def mask_email(match: re.Match[str]) -> str:
            original = match.group(0)
            masked_items.append(("email", original))
            return "[MASKED_EMAIL]"

        masked_text = self._patterns["email"].sub(mask_email, masked_text)

        # Mask Aadhaar numbers
        def mask_aadhaar(match: re.Match[str]) -> str:
            original = match.group(0)
            # Only mask if it looks like an Aadhaar (not other 12-digit sequences)
            if self._is_likely_aadhaar(original):
                masked_items.append(("aadhaar", original))
                return "[MASKED_AADHAAR]"
            return original

        masked_text = self._patterns["aadhaar"].sub(mask_aadhaar, masked_text)

        # Mask PAN card numbers
        def mask_pan(match: re.Match[str]) -> str:
            original = match.group(0)
            masked_items.append(("pan", original))
            return "[MASKED_PAN]"

        masked_text = self._patterns["pan"].sub(mask_pan, masked_text)

        # Mask bank account numbers (be conservative to avoid false positives)
        def mask_bank_account(match: re.Match[str]) -> str:
            original = match.group(0)
            # Only mask if context suggests it's a bank account
            if self._is_likely_bank_account(text, match.start()):
                masked_items.append(("bank_account", original))
                return "[MASKED_ACCOUNT]"
            return original

        masked_text = self._patterns["bank_account"].sub(mask_bank_account, masked_text)

        # Mask pincodes (be conservative to avoid false positives)
        def mask_pincode(match: re.Match[str]) -> str:
            original = match.group(0)
            # Only mask if context suggests it's a pincode
            if self._is_likely_pincode(text, match.start()):
                masked_items.append(("pincode", original))
                return "[MASKED_PINCODE]"
            return original

        masked_text = self._patterns["pincode"].sub(mask_pincode, masked_text)

        # Mask names (pattern-based, simplified)
        masked_text = self._mask_names(masked_text, masked_items)

        # Log what was masked (without the actual values)
        if masked_items:
            masked_types = [item[0] for item in masked_items]
            logger.info(f"Masked PII types: {', '.join(set(masked_types))}")

        return masked_text

    def _is_likely_aadhaar(self, text: str) -> bool:
        """Check if a 12-digit sequence is likely an Aadhaar number.

        Args:
            text: The matched text

        Returns:
            True if likely an Aadhaar number
        """
        # Remove spaces and hyphens
        digits = re.sub(r"[\s-]", "", text)

        # Aadhaar numbers don't start with 0 or 1
        if len(digits) == 12 and digits[0] not in ["0", "1"]:
            return True

        return False

    def _is_likely_bank_account(self, full_text: str, match_pos: int) -> bool:
        """Check if a number sequence is likely a bank account number.

        Args:
            full_text: The full text being processed
            match_pos: Position of the match in the text

        Returns:
            True if likely a bank account number
        """
        # Look for context words around the match
        context_start = max(0, match_pos - 50)
        context_end = min(len(full_text), match_pos + 50)
        context = full_text[context_start:context_end].lower()

        bank_keywords = ["account", "bank", "khata", "account number"]

        return any(keyword in context for keyword in bank_keywords)

    def _is_likely_pincode(self, full_text: str, match_pos: int) -> bool:
        """Check if a 6-digit sequence is likely a pincode.

        Args:
            full_text: The full text being processed
            match_pos: Position of the match in the text

        Returns:
            True if likely a pincode
        """
        # Look for context words around the match
        context_start = max(0, match_pos - 50)
        context_end = min(len(full_text), match_pos + 50)
        context = full_text[context_start:context_end].lower()

        pincode_keywords = ["pincode", "pin code", "postal code", "zip"]

        return any(keyword in context for keyword in pincode_keywords)

    def _mask_names(self, text: str, masked_items: List[Tuple[str, str]]) -> str:
        """Mask names using pattern-based detection.

        This is a simplified implementation. For production, use NER models
        trained on Indian names (spaCy, Stanza, or custom models).

        Args:
            text: Input text
            masked_items: List to append masked items to

        Returns:
            Text with names masked
        """
        masked_text = text

        # Look for name introduction patterns
        for indicator in self._name_indicators:
            pattern = re.compile(
                rf"{re.escape(indicator)}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.IGNORECASE
            )

            def mask_name(match: re.Match[str]) -> str:
                name = match.group(1)
                masked_items.append(("name", name))
                return f"{match.group(0).split(name)[0]}[MASKED_NAME]"

            masked_text = pattern.sub(mask_name, masked_text)

        return masked_text

    def has_pii(self, text: str) -> bool:
        """Check if text contains PII without masking it.

        Args:
            text: Input text

        Returns:
            True if PII is detected
        """
        if not text:
            return False

        # Check each pattern
        for pattern_name, pattern in self._patterns.items():
            if pattern.search(text):
                # Additional validation for certain types
                if pattern_name == "aadhaar":
                    matches = pattern.findall(text)
                    if any(self._is_likely_aadhaar(m) for m in matches):
                        return True
                elif pattern_name in ["bank_account", "pincode"]:
                    # These need context, so we'll be conservative
                    continue
                else:
                    return True

        # Check for name patterns
        for indicator in self._name_indicators:
            if indicator in text.lower():
                return True

        return False
