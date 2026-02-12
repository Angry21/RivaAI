"""Unit tests for PII masking functionality."""

import pytest

from rivaai.session.pii_masker import PIIMasker


class TestPIIMasker:
    """Test suite for PIIMasker class."""

    @pytest.fixture
    def masker(self) -> PIIMasker:
        """Create a PIIMasker instance for testing."""
        return PIIMasker()

    def test_mask_phone_number_indian_format(self, masker: PIIMasker) -> None:
        """Test masking of Indian phone numbers in various formats."""
        # Test +91 format
        text = "My number is +91-9876543210"
        result = masker.mask_pii(text)
        assert "[MASKED_PHONE]" in result
        assert "9876543210" not in result

        # Test 91 format without +
        text = "Call me at 919876543210"
        result = masker.mask_pii(text)
        assert "[MASKED_PHONE]" in result
        assert "9876543210" not in result

        # Test 10-digit format
        text = "My phone is 9876543210"
        result = masker.mask_pii(text)
        assert "[MASKED_PHONE]" in result
        assert "9876543210" not in result

    def test_mask_email_address(self, masker: PIIMasker) -> None:
        """Test masking of email addresses."""
        text = "Contact me at john.doe@example.com for details"
        result = masker.mask_pii(text)
        assert "[MASKED_EMAIL]" in result
        assert "john.doe@example.com" not in result

    def test_mask_aadhaar_number(self, masker: PIIMasker) -> None:
        """Test masking of Aadhaar numbers."""
        # Test with spaces
        text = "My Aadhaar is 2345 6789 0123"
        result = masker.mask_pii(text)
        assert "[MASKED_AADHAAR]" in result
        assert "2345 6789 0123" not in result

        # Test without spaces
        text = "Aadhaar: 234567890123"
        result = masker.mask_pii(text)
        assert "[MASKED_AADHAAR]" in result
        assert "234567890123" not in result

    def test_mask_pan_card(self, masker: PIIMasker) -> None:
        """Test masking of PAN card numbers."""
        text = "My PAN is ABCDE1234F"
        result = masker.mask_pii(text)
        assert "[MASKED_PAN]" in result
        assert "ABCDE1234F" not in result

    def test_mask_bank_account_with_context(self, masker: PIIMasker) -> None:
        """Test masking of bank account numbers when context is present."""
        text = "My bank account number is 12345678901234"
        result = masker.mask_pii(text)
        assert "[MASKED_ACCOUNT]" in result
        assert "12345678901234" not in result

    def test_mask_pincode_with_context(self, masker: PIIMasker) -> None:
        """Test masking of pincodes when context is present."""
        text = "I live in pincode 560001"
        result = masker.mask_pii(text)
        assert "[MASKED_PINCODE]" in result
        assert "560001" not in result

    def test_mask_name_with_indicator(self, masker: PIIMasker) -> None:
        """Test masking of names when name indicators are present."""
        text = "My name is Rajesh Kumar"
        result = masker.mask_pii(text)
        assert "[MASKED_NAME]" in result
        assert "Rajesh Kumar" not in result

        text = "I am Priya Sharma"
        result = masker.mask_pii(text)
        assert "[MASKED_NAME]" in result
        assert "Priya Sharma" not in result

    def test_mask_multiple_pii_types(self, masker: PIIMasker) -> None:
        """Test masking multiple PII types in the same text."""
        text = "My name is John Doe, phone 9876543210, email john@example.com"
        result = masker.mask_pii(text)
        assert "[MASKED_NAME]" in result
        assert "[MASKED_PHONE]" in result
        assert "[MASKED_EMAIL]" in result
        assert "John Doe" not in result
        assert "9876543210" not in result
        assert "john@example.com" not in result

    def test_no_pii_in_text(self, masker: PIIMasker) -> None:
        """Test that text without PII is not modified."""
        text = "I need help with wheat farming"
        result = masker.mask_pii(text)
        assert result == text

    def test_empty_text(self, masker: PIIMasker) -> None:
        """Test handling of empty text."""
        assert masker.mask_pii("") == ""
        assert masker.mask_pii("   ") == "   "

    def test_has_pii_detection(self, masker: PIIMasker) -> None:
        """Test PII detection without masking."""
        # Text with PII
        assert masker.has_pii("Call me at 9876543210")
        assert masker.has_pii("Email: test@example.com")
        assert masker.has_pii("My name is John")

        # Text without PII
        assert not masker.has_pii("I need help with farming")
        assert not masker.has_pii("")

    def test_aadhaar_validation(self, masker: PIIMasker) -> None:
        """Test that Aadhaar validation rejects invalid patterns."""
        # Aadhaar starting with 0 or 1 should not be masked
        text = "Number: 0123 4567 8901"
        result = masker.mask_pii(text)
        # Should not mask as it's not a valid Aadhaar
        assert "[MASKED_AADHAAR]" not in result

    def test_bank_account_without_context(self, masker: PIIMasker) -> None:
        """Test that bank account numbers without context are not masked."""
        # Random number without bank context
        text = "The year 12345678 was important"
        result = masker.mask_pii(text)
        # Should not mask as there's no bank context
        assert "[MASKED_ACCOUNT]" not in result

    def test_pincode_without_context(self, masker: PIIMasker) -> None:
        """Test that 6-digit numbers without pincode context are not masked."""
        # Random 6-digit number without pincode context
        text = "The code is 123456"
        result = masker.mask_pii(text)
        # Should not mask as there's no pincode context
        assert "[MASKED_PINCODE]" not in result

    def test_hindi_name_indicator(self, masker: PIIMasker) -> None:
        """Test name masking with Hindi indicators."""
        text = "Mera naam Rajesh hai"
        result = masker.mask_pii(text)
        assert "[MASKED_NAME]" in result
        assert "Rajesh" not in result

    def test_preserve_non_pii_content(self, masker: PIIMasker) -> None:
        """Test that non-PII content is preserved correctly."""
        text = "I need help with wheat farming in my village"
        result = masker.mask_pii(text)
        assert "wheat" in result
        assert "farming" in result
        assert "village" in result

    def test_complex_conversation_text(self, masker: PIIMasker) -> None:
        """Test masking in a realistic conversation scenario."""
        text = (
            "Hello, my name is Ramesh Kumar. I am calling from pincode 560001. "
            "My phone number is 9876543210. I need help with wheat farming."
        )
        result = masker.mask_pii(text)

        # Check that PII is masked
        assert "[MASKED_NAME]" in result
        assert "[MASKED_PINCODE]" in result
        assert "[MASKED_PHONE]" in result

        # Check that PII values are removed
        assert "Ramesh Kumar" not in result
        assert "560001" not in result
        assert "9876543210" not in result

        # Check that non-PII content is preserved
        assert "wheat farming" in result
        assert "need help" in result
