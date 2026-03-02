"""Load sample knowledge base data with embeddings.

This script populates the database with sample crops, chemicals, and schemes,
generates embeddings, and creates the unified knowledge_items table for retrieval.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List

from rivaai.config.database import get_database_pool
from rivaai.config.settings import get_settings
from rivaai.knowledge import (
    Chemical,
    Crop,
    KnowledgeBaseLoader,
    Scheme,
    get_embedding_generator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Sample data
SAMPLE_CROPS = [
    Crop(
        id=None,
        name="Wheat",
        local_names={
            "hi": "गेहूं",
            "mr": "गहू",
            "te": "గోధుమ",
            "ta": "கோதுமை",
            "bn": "গম"
        },
        season="Rabi",
        region="North India",
        soil_requirements="Well-drained loamy soil with pH 6.0-7.5",
        water_requirements="Moderate water requirement, 4-5 irrigations during growing season",
    ),
    Crop(
        id=None,
        name="Rice",
        local_names={
            "hi": "चावल",
            "mr": "तांदूळ",
            "te": "వరి",
            "ta": "அரிசி",
            "bn": "চাল"
        },
        season="Kharif",
        region="All India",
        soil_requirements="Clay or clay loam soil with good water retention",
        water_requirements="High water requirement, flooded conditions preferred",
    ),
    Crop(
        id=None,
        name="Cotton",
        local_names={
            "hi": "कपास",
            "mr": "कापूस",
            "te": "పత్తి",
            "ta": "பருத்தி",
            "bn": "তুলা"
        },
        season="Kharif",
        region="Central and South India",
        soil_requirements="Black cotton soil or deep loamy soil",
        water_requirements="Moderate to high water requirement",
    ),
]

SAMPLE_CHEMICALS = [
    Chemical(
        id=None,
        name="Urea",
        type="fertilizer",
        safe_dosage_min=100.0,
        safe_dosage_max=150.0,
        unit="kg/acre",
        safety_warnings=[
            "Do not exceed 150 kg per acre",
            "Apply in split doses for better efficiency",
            "Avoid application during heavy rain"
        ],
    ),
    Chemical(
        id=None,
        name="DAP (Diammonium Phosphate)",
        type="fertilizer",
        safe_dosage_min=50.0,
        safe_dosage_max=100.0,
        unit="kg/acre",
        safety_warnings=[
            "Apply at sowing time for best results",
            "Do not mix with urea",
            "Store in dry place"
        ],
    ),
    Chemical(
        id=None,
        name="Chlorpyrifos",
        type="pesticide",
        safe_dosage_min=400.0,
        safe_dosage_max=600.0,
        unit="ml/acre",
        safety_warnings=[
            "Highly toxic - use protective equipment",
            "Do not spray during flowering",
            "Maintain 15-day pre-harvest interval",
            "Avoid contact with skin and eyes"
        ],
    ),
]

SAMPLE_SCHEMES = [
    Scheme(
        id=None,
        name="PM-KISAN",
        domain="welfare",
        local_names={
            "hi": "प्रधानमंत्री किसान सम्मान निधि",
            "mr": "पंतप्रधान किसान सन्मान निधी",
            "te": "ప్రధాన మంత్రి కిసాన్ సమ్మాన్ నిధి",
            "ta": "பிரதமர் கிசான் சம்மான் நிதி",
            "bn": "প্রধানমন্ত্রী কিষাণ সম্মান নিধি"
        },
        eligibility_criteria=[
            "Must be a farmer with cultivable land",
            "Land ownership required",
            "Small and marginal farmers prioritized"
        ],
        required_documents=[
            "Aadhaar card",
            "Land ownership documents",
            "Bank account details"
        ],
        application_process="Apply online at pmkisan.gov.in or visit nearest Common Service Center",
        contact_info={
            "website": "https://pmkisan.gov.in",
            "helpline": "155261",
            "email": "pmkisan-ict@gov.in"
        },
        last_updated=datetime.now(),
    ),
    Scheme(
        id=None,
        name="Pradhan Mantri Fasal Bima Yojana",
        domain="welfare",
        local_names={
            "hi": "प्रधानमंत्री फसल बीमा योजना",
            "mr": "पंतप्रधान पीक विमा योजना",
            "te": "ప్రధాన మంత్రి ఫసల్ బీమా యోజన",
            "ta": "பிரதமர் பசல் பீமா யோஜனா",
            "bn": "প্রধানমন্ত্রী ফসল বীমা যোজনা"
        },
        eligibility_criteria=[
            "All farmers growing notified crops",
            "Tenant farmers and sharecroppers eligible",
            "Must have insurable interest in crop"
        ],
        required_documents=[
            "Aadhaar card",
            "Land records or tenancy agreement",
            "Bank account details",
            "Sowing certificate"
        ],
        application_process="Apply through bank, CSC, or insurance company within cutoff date",
        contact_info={
            "website": "https://pmfby.gov.in",
            "helpline": "18001801551",
            "email": "pmfby@gov.in"
        },
        last_updated=datetime.now(),
    ),
]


async def load_sample_data():
    """Load sample data into the database."""
    logger.info("Starting sample data loading...")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create loader
    loader = KnowledgeBaseLoader(db_pool, embedding_gen)
    
    # Load crops
    logger.info(f"Loading {len(SAMPLE_CROPS)} crops...")
    crop_ids = []
    for crop in SAMPLE_CROPS:
        try:
            crop_id = loader.load_crop(crop)
            crop_ids.append(crop_id)
            logger.info(f"  ✓ Loaded crop: {crop.name} (ID: {crop_id})")
        except Exception as e:
            logger.error(f"  ✗ Failed to load crop {crop.name}: {e}")
    
    # Load chemicals
    logger.info(f"Loading {len(SAMPLE_CHEMICALS)} chemicals...")
    chemical_ids = []
    for chemical in SAMPLE_CHEMICALS:
        try:
            chemical_id = loader.load_chemical(chemical)
            chemical_ids.append(chemical_id)
            logger.info(f"  ✓ Loaded chemical: {chemical.name} (ID: {chemical_id})")
        except Exception as e:
            logger.error(f"  ✗ Failed to load chemical {chemical.name}: {e}")
    
    # Load schemes
    logger.info(f"Loading {len(SAMPLE_SCHEMES)} schemes...")
    scheme_ids = []
    for scheme in SAMPLE_SCHEMES:
        try:
            scheme_id = loader.load_scheme(scheme)
            scheme_ids.append(scheme_id)
            logger.info(f"  ✓ Loaded scheme: {scheme.name} (ID: {scheme_id})")
        except Exception as e:
            logger.error(f"  ✗ Failed to load scheme {scheme.name}: {e}")
    
    logger.info("Sample data loading completed!")
    logger.info(f"Summary: {len(crop_ids)} crops, {len(chemical_ids)} chemicals, {len(scheme_ids)} schemes")
    
    return crop_ids, chemical_ids, scheme_ids


async def populate_knowledge_items():
    """Populate the unified knowledge_items table from entity tables."""
    logger.info("Populating knowledge_items table...")
    
    settings = get_settings()
    db_pool = get_database_pool(settings)
    
    conn = db_pool.get_connection()
    try:
        with conn.cursor() as cursor:
            # Populate from crops
            cursor.execute("""
                INSERT INTO knowledge_items (content, embedding, metadata, domain, entity_type, source_table, source_id)
                SELECT 
                    name || ' (' || COALESCE(local_names->>'hi', '') || '). ' ||
                    'Season: ' || season || '. Region: ' || region || '. ' ||
                    'Soil: ' || soil_requirements || '. Water: ' || water_requirements as content,
                    embedding,
                    jsonb_build_object(
                        'name', name,
                        'local_names', local_names,
                        'season', season,
                        'region', region
                    ) as metadata,
                    'agriculture' as domain,
                    'crop' as entity_type,
                    'crops' as source_table,
                    id as source_id
                FROM crops
                WHERE embedding IS NOT NULL
                ON CONFLICT DO NOTHING
            """)
            crops_count = cursor.rowcount
            
            # Populate from chemicals
            cursor.execute("""
                INSERT INTO knowledge_items (content, embedding, metadata, domain, entity_type, source_table, source_id)
                SELECT 
                    name || ' - ' || type || '. ' ||
                    'Safe dosage: ' || safe_dosage_min || '-' || safe_dosage_max || ' ' || unit || '. ' ||
                    'Warnings: ' || array_to_string(ARRAY(SELECT jsonb_array_elements_text(safety_warnings)), '. ') as content,
                    embedding,
                    jsonb_build_object(
                        'name', name,
                        'type', type,
                        'safe_dosage_min', safe_dosage_min,
                        'safe_dosage_max', safe_dosage_max,
                        'unit', unit
                    ) as metadata,
                    'agriculture' as domain,
                    'chemical' as entity_type,
                    'chemicals' as source_table,
                    id as source_id
                FROM chemicals
                WHERE embedding IS NOT NULL
                ON CONFLICT DO NOTHING
            """)
            chemicals_count = cursor.rowcount
            
            # Populate from schemes
            cursor.execute("""
                INSERT INTO knowledge_items (content, embedding, metadata, domain, entity_type, source_table, source_id)
                SELECT 
                    name || ' (' || COALESCE(local_names->>'hi', '') || ') - ' || domain || ' scheme. ' ||
                    'Eligibility: ' || array_to_string(ARRAY(SELECT jsonb_array_elements_text(eligibility_criteria)), '. ') || '. ' ||
                    'Required documents: ' || array_to_string(ARRAY(SELECT jsonb_array_elements_text(required_documents)), ', ') || '. ' ||
                    'Process: ' || application_process as content,
                    embedding,
                    jsonb_build_object(
                        'name', name,
                        'local_names', local_names,
                        'domain', domain,
                        'contact_info', contact_info
                    ) as metadata,
                    CASE 
                        WHEN domain = 'welfare' THEN 'welfare'
                        WHEN domain = 'education' THEN 'education'
                        ELSE 'general'
                    END as domain,
                    'scheme' as entity_type,
                    'schemes' as source_table,
                    id as source_id
                FROM schemes
                WHERE embedding IS NOT NULL
                ON CONFLICT DO NOTHING
            """)
            schemes_count = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Populated knowledge_items: {crops_count} crops, {chemicals_count} chemicals, {schemes_count} schemes")
            
    finally:
        db_pool.release_connection(conn)


async def main():
    """Main execution function."""
    try:
        # Load sample data
        await load_sample_data()
        
        # Populate knowledge_items table
        await populate_knowledge_items()
        
        logger.info("✓ Knowledge base setup completed successfully!")
        
    except Exception as e:
        logger.error(f"✗ Knowledge base setup failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
