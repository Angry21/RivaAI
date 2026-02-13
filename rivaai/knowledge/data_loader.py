"""Data loader for populating knowledge base with embeddings."""

import json
import logging
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extensions import connection as Connection

from rivaai.config.database import DatabasePool
from rivaai.config.settings import Settings
from rivaai.knowledge.embeddings import EmbeddingGenerator
from rivaai.knowledge.models import Chemical, Crop, Scheme

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Load and manage knowledge base data with embeddings."""

    def __init__(self, db_pool: DatabasePool, embedding_gen: EmbeddingGenerator) -> None:
        """Initialize knowledge base loader.

        Args:
            db_pool: Database connection pool
            embedding_gen: Embedding generator instance
        """
        self.db_pool = db_pool
        self.embedding_gen = embedding_gen

    def _generate_crop_text(self, crop: Crop) -> str:
        """Generate text representation of crop for embedding.

        Args:
            crop: Crop instance

        Returns:
            Text representation
        """
        local_names_str = ", ".join(crop.local_names.values())
        return (
            f"{crop.name} ({local_names_str}). "
            f"Season: {crop.season}. Region: {crop.region}. "
            f"Soil: {crop.soil_requirements}. Water: {crop.water_requirements}"
        )

    def _generate_chemical_text(self, chemical: Chemical) -> str:
        """Generate text representation of chemical for embedding.

        Args:
            chemical: Chemical instance

        Returns:
            Text representation
        """
        warnings_str = ". ".join(chemical.safety_warnings)
        return (
            f"{chemical.name} - {chemical.type}. "
            f"Safe dosage: {chemical.safe_dosage_min}-{chemical.safe_dosage_max} {chemical.unit}. "
            f"Warnings: {warnings_str}"
        )

    def _generate_scheme_text(self, scheme: Scheme) -> str:
        """Generate text representation of scheme for embedding.

        Args:
            scheme: Scheme instance

        Returns:
            Text representation
        """
        local_names_str = ", ".join(scheme.local_names.values())
        eligibility_str = ". ".join(scheme.eligibility_criteria)
        docs_str = ", ".join(scheme.required_documents)
        return (
            f"{scheme.name} ({local_names_str}) - {scheme.domain} scheme. "
            f"Eligibility: {eligibility_str}. "
            f"Required documents: {docs_str}. "
            f"Process: {scheme.application_process}"
        )

    def load_crop(self, crop: Crop) -> int:
        """Load a crop into the database with embedding.

        Args:
            crop: Crop instance to load

        Returns:
            ID of inserted crop

        Raises:
            Exception: If loading fails
        """
        try:
            # Generate embedding
            crop_text = self._generate_crop_text(crop)
            embedding = self.embedding_gen.generate_embedding(crop_text)

            # Insert into database
            conn = self.db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO crops (name, local_names, season, region, 
                                         soil_requirements, water_requirements, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            crop.name,
                            json.dumps(crop.local_names),
                            crop.season,
                            crop.region,
                            crop.soil_requirements,
                            crop.water_requirements,
                            embedding,
                        ),
                    )
                    crop_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Loaded crop: {crop.name} (ID: {crop_id})")
                    return crop_id
            finally:
                self.db_pool.release_connection(conn)
        except Exception as e:
            logger.error(f"Failed to load crop {crop.name}: {e}")
            raise

    def load_chemical(self, chemical: Chemical) -> int:
        """Load a chemical into the database with embedding.

        Args:
            chemical: Chemical instance to load

        Returns:
            ID of inserted chemical

        Raises:
            Exception: If loading fails
        """
        try:
            # Generate embedding
            chemical_text = self._generate_chemical_text(chemical)
            embedding = self.embedding_gen.generate_embedding(chemical_text)

            # Insert into database
            conn = self.db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO chemicals (name, type, safe_dosage_min, safe_dosage_max,
                                             unit, safety_warnings, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            chemical.name,
                            chemical.type,
                            chemical.safe_dosage_min,
                            chemical.safe_dosage_max,
                            chemical.unit,
                            json.dumps(chemical.safety_warnings),
                            embedding,
                        ),
                    )
                    chemical_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Loaded chemical: {chemical.name} (ID: {chemical_id})")
                    return chemical_id
            finally:
                self.db_pool.release_connection(conn)
        except Exception as e:
            logger.error(f"Failed to load chemical {chemical.name}: {e}")
            raise

    def load_scheme(self, scheme: Scheme) -> int:
        """Load a scheme into the database with embedding.

        Args:
            scheme: Scheme instance to load

        Returns:
            ID of inserted scheme

        Raises:
            Exception: If loading fails
        """
        try:
            # Generate embedding
            scheme_text = self._generate_scheme_text(scheme)
            embedding = self.embedding_gen.generate_embedding(scheme_text)

            # Insert into database
            conn = self.db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO schemes (name, domain, local_names, eligibility_criteria,
                                           required_documents, application_process, 
                                           contact_info, last_updated, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            scheme.name,
                            scheme.domain,
                            json.dumps(scheme.local_names),
                            json.dumps(scheme.eligibility_criteria),
                            json.dumps(scheme.required_documents),
                            scheme.application_process,
                            json.dumps(scheme.contact_info),
                            scheme.last_updated,
                            embedding,
                        ),
                    )
                    scheme_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Loaded scheme: {scheme.name} (ID: {scheme_id})")
                    return scheme_id
            finally:
                self.db_pool.release_connection(conn)
        except Exception as e:
            logger.error(f"Failed to load scheme {scheme.name}: {e}")
            raise

    def update_embeddings(self, table: str) -> int:
        """Update embeddings for existing records without embeddings.

        Args:
            table: Table name ('crops', 'chemicals', 'schemes')

        Returns:
            Number of records updated

        Raises:
            Exception: If update fails
        """
        try:
            conn = self.db_pool.get_connection()
            try:
                with conn.cursor() as cursor:
                    # Get records without embeddings
                    cursor.execute(
                        f"SELECT id, name FROM {table} WHERE embedding IS NULL"
                    )
                    records = cursor.fetchall()

                    if not records:
                        logger.info(f"No records to update in {table}")
                        return 0

                    updated = 0
                    for record_id, name in records:
                        # Fetch full record
                        cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
                        row = cursor.fetchone()

                        # Generate text based on table
                        if table == "crops":
                            text = self._generate_crop_text(self._row_to_crop(row))
                        elif table == "chemicals":
                            text = self._generate_chemical_text(self._row_to_chemical(row))
                        elif table == "schemes":
                            text = self._generate_scheme_text(self._row_to_scheme(row))
                        else:
                            continue

                        # Generate and update embedding
                        embedding = self.embedding_gen.generate_embedding(text)
                        cursor.execute(
                            f"UPDATE {table} SET embedding = %s WHERE id = %s",
                            (embedding, record_id),
                        )
                        updated += 1

                    conn.commit()
                    logger.info(f"Updated {updated} embeddings in {table}")
                    return updated
            finally:
                self.db_pool.release_connection(conn)
        except Exception as e:
            logger.error(f"Failed to update embeddings for {table}: {e}")
            raise

    def _row_to_crop(self, row: tuple) -> Crop:
        """Convert database row to Crop instance."""
        return Crop(
            id=row[0],
            name=row[1],
            local_names=row[2] if row[2] else {},
            season=row[3] or "",
            region=row[4] or "",
            soil_requirements=row[5] or "",
            water_requirements=row[6] or "",
        )

    def _row_to_chemical(self, row: tuple) -> Chemical:
        """Convert database row to Chemical instance."""
        return Chemical(
            id=row[0],
            name=row[1],
            type=row[2] or "",
            safe_dosage_min=row[3] or 0.0,
            safe_dosage_max=row[4] or 0.0,
            unit=row[5] or "",
            safety_warnings=row[6] if row[6] else [],
        )

    def _row_to_scheme(self, row: tuple) -> Scheme:
        """Convert database row to Scheme instance."""
        from datetime import datetime

        return Scheme(
            id=row[0],
            name=row[1],
            domain=row[2] or "",
            local_names=row[3] if row[3] else {},
            eligibility_criteria=row[4] if row[4] else [],
            required_documents=row[5] if row[5] else [],
            application_process=row[6] or "",
            contact_info=row[7] if row[7] else {},
            last_updated=row[8] or datetime.now(),
        )
