"""Load sample data into knowledge base with embeddings.

This script loads initial test data for:
- Farming domain (Wheat crop)
- Welfare schemes (from myScheme.gov.in)
- Chemicals with safety limits
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rivaai.config.database import get_database_pool
from rivaai.config.settings import get_settings
from rivaai.knowledge.data_loader import KnowledgeBaseLoader
from rivaai.knowledge.embeddings import get_embedding_generator
from rivaai.knowledge.models import Chemical, Crop, Scheme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_farming_data(loader: KnowledgeBaseLoader) -> None:
    """Load farming domain sample data."""
    logger.info("Loading farming domain data...")

    # Wheat crop (already in init_database.sql, but we'll update embedding)
    wheat = Crop(
        id=None,
        name="Wheat",
        local_names={
            "hi": "गेहूं",
            "mr": "गहू",
            "te": "గోధుమ",
            "ta": "கோதுமை",
            "bn": "গম",
        },
        season="Rabi",
        region="North India",
        soil_requirements="Well-drained loamy soil with pH 6.0-7.5",
        water_requirements="Moderate water requirement, 4-5 irrigations during growing season",
    )

    # Common pesticides for wheat
    urea = Chemical(
        id=None,
        name="Urea",
        type="fertilizer",
        safe_dosage_min=100.0,
        safe_dosage_max=150.0,
        unit="kg/acre",
        safety_warnings=[
            "Do not exceed 150 kg per acre",
            "Apply in split doses",
            "Avoid direct contact with skin",
            "Store in cool, dry place",
        ],
    )

    chlorpyrifos = Chemical(
        id=None,
        name="Chlorpyrifos",
        type="pesticide",
        safe_dosage_min=400.0,
        safe_dosage_max=500.0,
        unit="ml/acre",
        safety_warnings=[
            "Highly toxic - use protective equipment",
            "Do not spray during flowering",
            "Maintain 15-day pre-harvest interval",
            "Avoid contamination of water sources",
        ],
    )

    try:
        # Check if wheat already exists
        db_pool = loader.db_pool
        conn = db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM crops WHERE name = %s", ("Wheat",))
                existing = cursor.fetchone()
                if existing:
                    logger.info("Wheat crop already exists, updating embedding...")
                    loader.update_embeddings("crops")
                else:
                    wheat_id = loader.load_crop(wheat)
                    logger.info(f"Loaded Wheat crop with ID: {wheat_id}")
        finally:
            db_pool.release_connection(conn)

        urea_id = loader.load_chemical(urea)
        chlor_id = loader.load_chemical(chlorpyrifos)
        logger.info(f"Loaded chemicals: Urea ({urea_id}), Chlorpyrifos ({chlor_id})")

    except Exception as e:
        logger.error(f"Failed to load farming data: {e}")
        raise


def load_welfare_schemes(loader: KnowledgeBaseLoader) -> None:
    """Load welfare scheme sample data from myScheme.gov.in."""
    logger.info("Loading welfare schemes from myScheme.gov.in...")

    # PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)
    pm_kisan = Scheme(
        id=None,
        name="PM-KISAN",
        domain="welfare",
        local_names={
            "hi": "प्रधानमंत्री किसान सम्मान निधि",
            "mr": "पंतप्रधान किसान सन्मान निधी",
            "te": "ప్రధాన మంత్రి కిసాన్ సమ్మాన్ నిధి",
            "ta": "பிரதம மந்திரி கிசான் சம்மான் நிதி",
            "bn": "প্রধানমন্ত্রী কিষাণ সম্মান নিধি",
        },
        eligibility_criteria=[
            "Must be a farmer with cultivable land",
            "Land ownership records required",
            "Applicable to small and marginal farmers",
            "Family income below specified limit",
        ],
        required_documents=[
            "Aadhaar card",
            "Land ownership documents (7/12 extract or equivalent)",
            "Bank account details",
            "Mobile number",
        ],
        application_process=(
            "Apply online at pmkisan.gov.in or visit nearest Common Service Center (CSC). "
            "Submit Aadhaar, land records, and bank details. "
            "Verification done by local revenue officials. "
            "Benefits transferred directly to bank account in 3 installments per year."
        ),
        contact_info={
            "website": "https://pmkisan.gov.in",
            "helpline": "155261 / 011-24300606",
            "email": "pmkisan-ict@gov.in",
        },
        last_updated=datetime.now(),
    )

    # National Scholarship Portal
    nsp_scholarship = Scheme(
        id=None,
        name="National Scholarship Portal - Pre-Matric Scholarship",
        domain="education",
        local_names={
            "hi": "राष्ट्रीय छात्रवृत्ति पोर्टल - प्री-मैट्रिक छात्रवृत्ति",
            "mr": "राष्ट्रीय शिष्यवृत्ती पोर्टल - प्री-मॅट्रिक शिष्यवृत्ती",
            "te": "జాతీయ స్కాలర్‌షిప్ పోర్టల్ - ప్రీ-మెట్రిక్ స్కాలర్‌షిప్",
            "ta": "தேசிய உதவித்தொகை போர்டல் - முன்-மெட்ரிக் உதவித்தொகை",
            "bn": "জাতীয় বৃত্তি পোর্টাল - প্রি-ম্যাট্রিক বৃত্তি",
        },
        eligibility_criteria=[
            "Students from SC/ST/OBC/Minority communities",
            "Studying in classes 9th and 10th",
            "Family income below Rs. 2.5 lakh per annum",
            "Minimum 50% marks in previous class",
        ],
        required_documents=[
            "Aadhaar card",
            "Caste certificate (if applicable)",
            "Income certificate",
            "Previous year mark sheet",
            "Bank account details",
            "School bonafide certificate",
        ],
        application_process=(
            "Register on National Scholarship Portal (scholarships.gov.in). "
            "Fill application form with personal and academic details. "
            "Upload required documents. "
            "Submit application before deadline (usually October-November). "
            "Track status online using application ID."
        ),
        contact_info={
            "website": "https://scholarships.gov.in",
            "helpline": "0120-6619540",
            "email": "helpdesk@nsp.gov.in",
        },
        last_updated=datetime.now(),
    )

    # Ayushman Bharat - PMJAY
    ayushman_bharat = Scheme(
        id=None,
        name="Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (PMJAY)",
        domain="welfare",
        local_names={
            "hi": "आयुष्मान भारत - प्रधानमंत्री जन आरोग्य योजना",
            "mr": "आयुष्मान भारत - पंतप्रधान जन आरोग्य योजना",
            "te": "ఆయుష్మాన్ భారత్ - ప్రధాన మంత్రి జన ఆరోగ్య యోజన",
            "ta": "ஆயுஷ்மான் பாரத் - பிரதம மந்திரி ஜன் ஆரோக்ய யோஜனா",
            "bn": "আয়ুষ্মান ভারত - প্রধানমন্ত্রী জন আরোগ্য যোজনা",
        },
        eligibility_criteria=[
            "Families identified in SECC 2011 database",
            "Economically vulnerable groups",
            "No income limit - based on deprivation criteria",
            "Automatic eligibility for certain categories",
        ],
        required_documents=[
            "Aadhaar card",
            "Ration card",
            "Mobile number",
            "SECC verification (done by authorities)",
        ],
        application_process=(
            "Check eligibility at mera.pmjay.gov.in using mobile number. "
            "Visit nearest Ayushman Mitra or empanelled hospital. "
            "Get Ayushman card issued after verification. "
            "Cashless treatment up to Rs. 5 lakh per family per year at empanelled hospitals."
        ),
        contact_info={
            "website": "https://pmjay.gov.in",
            "helpline": "14555",
            "email": "pmjay@nha.gov.in",
        },
        last_updated=datetime.now(),
    )

    try:
        pm_kisan_id = loader.load_scheme(pm_kisan)
        nsp_id = loader.load_scheme(nsp_scholarship)
        ayushman_id = loader.load_scheme(ayushman_bharat)

        logger.info(
            f"Loaded welfare schemes: PM-KISAN ({pm_kisan_id}), "
            f"NSP Scholarship ({nsp_id}), Ayushman Bharat ({ayushman_id})"
        )
    except Exception as e:
        logger.error(f"Failed to load welfare schemes: {e}")
        raise


def main() -> None:
    """Main function to load all sample data."""
    logger.info("Starting sample data loading...")

    try:
        # Initialize settings and services
        settings = get_settings()
        db_pool = get_database_pool(settings)
        embedding_gen = get_embedding_generator(settings)
        loader = KnowledgeBaseLoader(db_pool, embedding_gen)

        # Load data
        load_farming_data(loader)
        load_welfare_schemes(loader)

        logger.info("Sample data loading completed successfully!")

    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        from rivaai.config.database import close_database_pool

        close_database_pool()


if __name__ == "__main__":
    main()
