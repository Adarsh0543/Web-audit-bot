"""
database/setup.py
─────────────────
Creates the database and all required tables.
Run this ONCE before starting the application.

Usage:
    python database/setup.py
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()


def create_database():
    """
    Connects to MySQL (without selecting a DB)
    and creates the seo_agent_db database if it doesn't exist.
    """
    try:
        # Connect WITHOUT specifying a database first
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cursor = conn.cursor()
        db_name = os.getenv("DB_NAME", "seo_agent_db")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        print(f"Database '{db_name}' is ready.")
        cursor.close()
        conn.close()
    except Error as e:
        raise Exception(f"Could not create database: {e}")


def create_tables():
    """
    Creates all required tables inside seo_agent_db.
    Safe to run multiple times — uses IF NOT EXISTS.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "seo_agent_db")
        )
        cursor = conn.cursor()

        # ── Table 1: sites ──────────────────────────────────────────
        # Master record for every website that gets analyzed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                url             VARCHAR(500) NOT NULL UNIQUE,
                domain          VARCHAR(255) NOT NULL,
                first_analyzed  DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_analyzed   DATETIME DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
                total_analyses  INT DEFAULT 1
            )
        """)
        print("Table 'sites' ready.")

        # ── Table 2: seo_reports ─────────────────────────────────────
        # Stores SEO analysis results for each site
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seo_reports (
                id                      INT AUTO_INCREMENT PRIMARY KEY,
                site_id                 INT NOT NULL,
                url                     VARCHAR(500) NOT NULL,
                
                -- Score
                seo_score               FLOAT DEFAULT 0,
                
                -- Meta Tags
                has_meta_title          BOOLEAN DEFAULT FALSE,
                meta_title              VARCHAR(500),
                meta_title_length       INT DEFAULT 0,
                has_meta_description    BOOLEAN DEFAULT FALSE,
                meta_description        VARCHAR(1000),
                meta_description_length INT DEFAULT 0,
                
                -- Headings
                h1_count                INT DEFAULT 0,
                h2_count                INT DEFAULT 0,
                h3_count                INT DEFAULT 0,
                h1_text                 VARCHAR(500),
                
                -- Images
                total_images            INT DEFAULT 0,
                images_with_alt         INT DEFAULT 0,
                images_without_alt      INT DEFAULT 0,
                
                -- Links
                internal_links          INT DEFAULT 0,
                external_links          INT DEFAULT 0,
                
                -- Performance hints
                has_robots_txt          BOOLEAN DEFAULT FALSE,
                has_sitemap             BOOLEAN DEFAULT FALSE,
                page_size_kb            FLOAT DEFAULT 0,
                
                -- Issues found
                issues                  JSON,
                
                -- Timestamp
                analyzed_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_site (site_id),
                FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
            )
        """)
        print("Table 'seo_reports' ready.")

        # ── Table 3: accessibility_reports ──────────────────────────
        # Stores accessibility analysis results for each site
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accessibility_reports (
                id                          INT AUTO_INCREMENT PRIMARY KEY,
                site_id                     INT NOT NULL,
                url                         VARCHAR(500) NOT NULL,
                
                -- Score
                accessibility_score         FLOAT DEFAULT 0,
                
                -- Images
                images_missing_alt          INT DEFAULT 0,
                
                -- Forms
                inputs_missing_labels       INT DEFAULT 0,
                total_form_inputs           INT DEFAULT 0,
                
                -- ARIA
                aria_landmarks_count        INT DEFAULT 0,
                aria_labels_count           INT DEFAULT 0,
                
                -- Semantic HTML
                has_main_tag                BOOLEAN DEFAULT FALSE,
                has_nav_tag                 BOOLEAN DEFAULT FALSE,
                has_header_tag              BOOLEAN DEFAULT FALSE,
                has_footer_tag              BOOLEAN DEFAULT FALSE,
                
                -- Language
                has_lang_attribute          BOOLEAN DEFAULT FALSE,
                lang_value                  VARCHAR(20),
                
                -- Skip Links
                has_skip_link               BOOLEAN DEFAULT FALSE,
                
                -- Issues found
                issues                      JSON,
                
                -- Timestamp
                analyzed_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_site (site_id),
                FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
            )
        """)
        print("Table 'accessibility_reports' ready.")

        # ── Table 4: content_reports ─────────────────────────────────
        # Stores content quality results for each site
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_reports (
                id                      INT AUTO_INCREMENT PRIMARY KEY,
                site_id                 INT NOT NULL,
                url                     VARCHAR(500) NOT NULL,
                
                -- Score
                content_score           FLOAT DEFAULT 0,
                
                -- Readability
                readability_score       FLOAT DEFAULT 0,
                readability_grade       VARCHAR(50),
                
                -- Content stats
                word_count              INT DEFAULT 0,
                sentence_count          INT DEFAULT 0,
                paragraph_count         INT DEFAULT 0,
                avg_words_per_sentence  FLOAT DEFAULT 0,
                
                -- Links
                total_links             INT DEFAULT 0,
                broken_links_count      INT DEFAULT 0,
                broken_links            JSON,
                
                -- Duplicate content
                duplicate_content_flag  BOOLEAN DEFAULT FALSE,
                
                -- Issues found
                issues                  JSON,
                
                -- Timestamp
                analyzed_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE KEY unique_site (site_id),
                FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
            )
        """)
        print("Table 'content_reports' ready.")

        # ── Table 5: db_operation_logs ───────────────────────────────
        # Logs every database operation for auditing and safety
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_operation_logs (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                operation_type  ENUM('SELECT','INSERT','UPDATE','DELETE') NOT NULL,
                table_name      VARCHAR(100) NOT NULL,
                query_executed  TEXT NOT NULL,
                status          ENUM('SUCCESS','FAILED') NOT NULL,
                rows_affected   INT DEFAULT 0,
                error_message   TEXT,
                executed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'db_operation_logs' ready.")

        conn.commit()
        cursor.close()
        conn.close()
        print("\nAll tables created successfully!")

    except Error as e:
        raise Exception(f"Could not create tables: {e}")


if __name__ == "__main__":
    print("Setting up SEO Agent Database...\n")
    create_database()
    create_tables()
    print("\nDatabase setup complete!")