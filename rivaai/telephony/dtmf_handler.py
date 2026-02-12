"""DTMF (Dual-Tone Multi-Frequency) handler for fallback input mode."""

import logging
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DTMFOption(Enum):
    """DTMF menu options."""
    
    # Language selection
    HINDI = "1"
    MARATHI = "2"
    TELUGU = "3"
    TAMIL = "4"
    BENGALI = "5"
    
    # Domain selection
    FARMING = "1"
    EDUCATION = "2"
    WELFARE = "3"
    
    # Yes/No
    YES = "1"
    NO = "2"
    
    # Repeat/Help
    REPEAT = "9"
    HELP = "0"


class DTMFHandler:
    """
    Handles DTMF input for fallback mode when STT fails.
    
    Provides voice prompts and processes DTMF digit inputs for:
    - Language selection when detection fails
    - Domain selection when STT is unavailable
    - Yes/No confirmations
    """
    
    # Language code mapping
    LANGUAGE_MAP: Dict[str, str] = {
        "1": "hi-IN",  # Hindi
        "2": "mr-IN",  # Marathi
        "3": "te-IN",  # Telugu
        "4": "ta-IN",  # Tamil
        "5": "bn-IN",  # Bengali
    }
    
    # Domain mapping
    DOMAIN_MAP: Dict[str, str] = {
        "1": "farming",
        "2": "education",
        "3": "welfare",
    }
    
    def __init__(self):
        """Initialize DTMF handler."""
        logger.info("DTMFHandler initialized")
    
    def get_language_selection_prompt(self, language_code: Optional[str] = None) -> str:
        """
        Generate voice prompt for language selection.
        
        Args:
            language_code: Optional language code for localized prompt
            
        Returns:
            Prompt text for TTS
        """
        # Default to Hindi if no language specified
        if not language_code or language_code == "hi-IN":
            return (
                "कृपया अपनी भाषा चुनें। "
                "हिंदी के लिए 1 दबाएं। "
                "मराठी के लिए 2 दबाएं। "
                "तेलुगु के लिए 3 दबाएं। "
                "तमिल के लिए 4 दबाएं। "
                "बंगाली के लिए 5 दबाएं।"
            )
        elif language_code == "mr-IN":
            return (
                "कृपया तुमची भाषा निवडा। "
                "हिंदीसाठी 1 दाबा। "
                "मराठीसाठी 2 दाबा। "
                "तेलुगूसाठी 3 दाबा। "
                "तमिळसाठी 4 दाबा। "
                "बंगालीसाठी 5 दाबा।"
            )
        elif language_code == "te-IN":
            return (
                "దయచేసి మీ భాషను ఎంచుకోండి। "
                "హిందీ కోసం 1 నొక్కండి। "
                "మరాఠీ కోసం 2 నొక్కండి। "
                "తెలుగు కోసం 3 నొక్కండి। "
                "తమిళం కోసం 4 నొక్కండి। "
                "బెంగాలీ కోసం 5 నొక్కండి।"
            )
        elif language_code == "ta-IN":
            return (
                "தயவுசெய்து உங்கள் மொழியைத் தேர்ந்தெடுக்கவும். "
                "இந்திக்கு 1 அழுத்தவும். "
                "மராத்திக்கு 2 அழுத்தவும். "
                "தெலுங்குக்கு 3 அழுத்தவும். "
                "தமிழுக்கு 4 அழுத்தவும். "
                "வங்காளத்திற்கு 5 அழுத்தவும்।"
            )
        elif language_code == "bn-IN":
            return (
                "অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন। "
                "হিন্দির জন্য 1 টিপুন। "
                "মারাঠির জন্য 2 টিপুন। "
                "তেলুগুর জন্য 3 টিপুন। "
                "তামিলের জন্য 4 টিপুন। "
                "বাংলার জন্য 5 টিপুন।"
            )
        else:
            # Fallback to English
            return (
                "Please select your language. "
                "Press 1 for Hindi. "
                "Press 2 for Marathi. "
                "Press 3 for Telugu. "
                "Press 4 for Tamil. "
                "Press 5 for Bengali."
            )
    
    def get_domain_selection_prompt(self, language_code: str) -> str:
        """
        Generate voice prompt for domain selection.
        
        Args:
            language_code: Language code for localized prompt
            
        Returns:
            Prompt text for TTS
        """
        if language_code == "hi-IN":
            return (
                "मैं आपकी बात सुनने में परेशानी हो रही है। "
                "कृपया अपनी आवश्यकता चुनें। "
                "खेती के लिए 1 दबाएं। "
                "शिक्षा के लिए 2 दबाएं। "
                "कल्याण योजनाओं के लिए 3 दबाएं।"
            )
        elif language_code == "mr-IN":
            return (
                "मला तुमचे ऐकण्यात अडचण येत आहे। "
                "कृपया तुमची गरज निवडा। "
                "शेतीसाठी 1 दाबा। "
                "शिक्षणासाठी 2 दाबा। "
                "कल्याण योजनांसाठी 3 दाबा।"
            )
        elif language_code == "te-IN":
            return (
                "నేను మీ మాటలు వినడంలో ఇబ్బంది పడుతున్నాను। "
                "దయచేసి మీ అవసరాన్ని ఎంచుకోండి। "
                "వ్యవసాయం కోసం 1 నొక్కండి। "
                "విద్య కోసం 2 నొక్కండి। "
                "సంక్షేమ పథకాల కోసం 3 నొక్కండి।"
            )
        elif language_code == "ta-IN":
            return (
                "உங்கள் பேச்சைக் கேட்பதில் எனக்கு சிரமம் உள்ளது। "
                "தயவுசெய்து உங்கள் தேவையைத் தேர்ந்தெடுக்கவும். "
                "விவசாயத்திற்கு 1 அழுத்தவும். "
                "கல்விக்கு 2 அழுத்தவும். "
                "நலத்திட்டங்களுக்கு 3 அழுத்தவும்।"
            )
        elif language_code == "bn-IN":
            return (
                "আমি আপনার কথা শুনতে সমস্যা হচ্ছে। "
                "অনুগ্রহ করে আপনার প্রয়োজন নির্বাচন করুন। "
                "কৃষির জন্য 1 টিপুন। "
                "শিক্ষার জন্য 2 টিপুন। "
                "কল্যাণ প্রকল্পের জন্য 3 টিপুন।"
            )
        else:
            return (
                "I am having trouble hearing you. "
                "Please select your need. "
                "Press 1 for Farming. "
                "Press 2 for Education. "
                "Press 3 for Welfare schemes."
            )
    
    def get_stt_failure_prompt(self, language_code: str) -> str:
        """
        Generate voice prompt when STT service fails.
        
        Args:
            language_code: Language code for localized prompt
            
        Returns:
            Prompt text for TTS
        """
        return self.get_domain_selection_prompt(language_code)
    
    def parse_language_selection(self, dtmf_digit: str) -> Optional[str]:
        """
        Parse DTMF digit to language code.
        
        Args:
            dtmf_digit: DTMF digit pressed by user
            
        Returns:
            Language code (e.g., 'hi-IN') or None if invalid
        """
        language_code = self.LANGUAGE_MAP.get(dtmf_digit)
        
        if language_code:
            logger.info(f"Language selected via DTMF: {dtmf_digit} -> {language_code}")
        else:
            logger.warning(f"Invalid language selection DTMF: {dtmf_digit}")
        
        return language_code
    
    def parse_domain_selection(self, dtmf_digit: str) -> Optional[str]:
        """
        Parse DTMF digit to domain.
        
        Args:
            dtmf_digit: DTMF digit pressed by user
            
        Returns:
            Domain name (e.g., 'farming') or None if invalid
        """
        domain = self.DOMAIN_MAP.get(dtmf_digit)
        
        if domain:
            logger.info(f"Domain selected via DTMF: {dtmf_digit} -> {domain}")
        else:
            logger.warning(f"Invalid domain selection DTMF: {dtmf_digit}")
        
        return domain
    
    def parse_yes_no(self, dtmf_digit: str) -> Optional[bool]:
        """
        Parse DTMF digit to yes/no boolean.
        
        Args:
            dtmf_digit: DTMF digit pressed by user
            
        Returns:
            True for yes, False for no, None if invalid
        """
        if dtmf_digit == "1":
            logger.info("User selected: Yes")
            return True
        elif dtmf_digit == "2":
            logger.info("User selected: No")
            return False
        else:
            logger.warning(f"Invalid yes/no DTMF: {dtmf_digit}")
            return None
    
    def get_invalid_input_prompt(self, language_code: str) -> str:
        """
        Generate prompt for invalid DTMF input.
        
        Args:
            language_code: Language code for localized prompt
            
        Returns:
            Prompt text for TTS
        """
        if language_code == "hi-IN":
            return "गलत विकल्प। कृपया फिर से प्रयास करें।"
        elif language_code == "mr-IN":
            return "चुकीचा पर्याय। कृपया पुन्हा प्रयत्न करा।"
        elif language_code == "te-IN":
            return "తప్పు ఎంపిక। దయచేసి మళ్లీ ప్రయత్నించండి।"
        elif language_code == "ta-IN":
            return "தவறான தேர்வு। தயவுசெய்து மீண்டும் முயற்சிக்கவும்."
        elif language_code == "bn-IN":
            return "ভুল বিকল্প। অনুগ্রহ করে আবার চেষ্টা করুন।"
        else:
            return "Invalid option. Please try again."
    
    def get_timeout_prompt(self, language_code: str) -> str:
        """
        Generate prompt for DTMF input timeout.
        
        Args:
            language_code: Language code for localized prompt
            
        Returns:
            Prompt text for TTS
        """
        if language_code == "hi-IN":
            return "कोई इनपुट नहीं मिला। कृपया एक विकल्प चुनें।"
        elif language_code == "mr-IN":
            return "कोणताही इनपुट मिळाला नाही। कृपया एक पर्याय निवडा।"
        elif language_code == "te-IN":
            return "ఇన్‌పుట్ అందలేదు। దయచేసి ఒక ఎంపికను ఎంచుకోండి।"
        elif language_code == "ta-IN":
            return "உள்ளீடு இல்லை. தயவுசெய்து ஒரு விருப்பத்தைத் தேர்ந்தெடுக்கவும்."
        elif language_code == "bn-IN":
            return "কোনো ইনপুট পাওয়া যায়নি। অনুগ্রহ করে একটি বিকল্প নির্বাচন করুন।"
        else:
            return "No input received. Please select an option."
