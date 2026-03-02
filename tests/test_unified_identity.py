"""
Tests for UnifiedIdentity
=========================

Tests for cross-channel identity resolution and contact management.
"""

import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestContact:
    """Tests for Contact dataclass."""
    
    def test_initialization(self):
        """Should initialize with required fields."""
        from openclaw.agents.ira.skills.identity.unified_identity import Contact
        
        contact = Contact(
            contact_id="c_abc123",
            name="John Doe",
            email="john@example.com",
        )
        
        assert contact.contact_id == "c_abc123"
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
    
    def test_default_values(self):
        """Should have default values for optional fields."""
        from openclaw.agents.ira.skills.identity.unified_identity import Contact
        
        contact = Contact(contact_id="c_abc123")
        
        assert contact.name is None
        assert contact.email is None
        assert contact.telegram_id is None
        assert contact.phone is None
        assert contact.company is None
        assert contact.metadata == {}
    
    def test_to_dict(self):
        """Should convert to dictionary."""
        from openclaw.agents.ira.skills.identity.unified_identity import Contact
        
        contact = Contact(
            contact_id="c_abc123",
            name="John Doe",
            email="john@example.com",
            company="ABC Corp",
        )
        
        d = contact.to_dict()
        
        assert d["contact_id"] == "c_abc123"
        assert d["name"] == "John Doe"
        assert d["email"] == "john@example.com"
        assert d["company"] == "ABC Corp"


class TestUnifiedIdentityService:
    """Tests for UnifiedIdentityService class."""
    
    @pytest.fixture
    def identity_service(self, temp_dir):
        """Create identity service with temp database."""
        db_path = str(temp_dir / "test_identity.db")
        
        with patch("openclaw.agents.ira.skills.identity.unified_identity.CONFIG_AVAILABLE", False):
            from openclaw.agents.ira.skills.identity.unified_identity import UnifiedIdentityService
            service = UnifiedIdentityService(db_path=db_path)
            yield service
    
    def test_initialization_creates_db(self, identity_service, temp_dir):
        """Should create database file on initialization."""
        assert Path(identity_service.db_path).exists()
    
    def test_schema_created(self, identity_service):
        """Should create required tables."""
        with identity_service._get_conn() as conn:
            # Check contacts table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'"
            )
            assert cursor.fetchone() is not None
            
            # Check identity_mappings table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='identity_mappings'"
            )
            assert cursor.fetchone() is not None
    
    def test_resolve_new_email_creates_contact(self, identity_service):
        """Should create new contact for unknown email."""
        contact_id = identity_service.resolve("email", "new@example.com")
        
        assert contact_id is not None
        assert contact_id.startswith("c_")
    
    def test_resolve_existing_email(self, identity_service):
        """Should return existing contact for known email."""
        # Create first contact
        id1 = identity_service.resolve("email", "test@example.com")
        
        # Resolve same email
        id2 = identity_service.resolve("email", "test@example.com")
        
        assert id1 == id2
    
    def test_resolve_case_insensitive(self, identity_service):
        """Should be case insensitive for email."""
        id1 = identity_service.resolve("email", "Test@Example.com")
        id2 = identity_service.resolve("email", "test@example.com")
        
        assert id1 == id2
    
    def test_resolve_telegram(self, identity_service):
        """Should resolve Telegram IDs."""
        contact_id = identity_service.resolve("telegram", "123456789")
        
        assert contact_id is not None
    
    def test_resolve_phone(self, identity_service):
        """Should resolve phone numbers."""
        contact_id = identity_service.resolve("phone", "+91 98765 43210")
        
        assert contact_id is not None
    
    def test_resolve_create_if_missing_false(self, identity_service):
        """Should return None when create_if_missing is False."""
        contact_id = identity_service.resolve(
            "email",
            "nonexistent@example.com",
            create_if_missing=False
        )
        
        assert contact_id is None
    
    def test_resolve_with_name(self, identity_service):
        """Should set name when creating contact."""
        contact_id = identity_service.resolve(
            "email",
            "john@example.com",
            name="John Doe"
        )
        
        contact = identity_service.get_contact(contact_id)
        assert contact is not None
        assert contact.name == "John Doe"
    
    def test_resolve_auto_generates_name_from_email(self, identity_service):
        """Should auto-generate name from email."""
        contact_id = identity_service.resolve("email", "john.doe@example.com")
        
        contact = identity_service.get_contact(contact_id)
        assert contact is not None
        assert "John" in contact.name or "john" in contact.name.lower()
    
    def test_resolve_empty_identifier(self, identity_service):
        """Should return None for empty identifier."""
        contact_id = identity_service.resolve("email", "")
        assert contact_id is None
        
        contact_id = identity_service.resolve("email", None)
        assert contact_id is None
    
    def test_link_creates_unified_contact(self, identity_service):
        """Should link two identifiers to same contact."""
        contact_id = identity_service.link(
            "email", "john@example.com",
            "telegram", "123456"
        )
        
        # Both should resolve to same contact
        email_id = identity_service.resolve("email", "john@example.com", create_if_missing=False)
        telegram_id = identity_service.resolve("telegram", "123456", create_if_missing=False)
        
        assert contact_id == email_id
        assert contact_id == telegram_id
    
    def test_link_merges_existing_contacts(self, identity_service):
        """Should merge when both identifiers have separate contacts."""
        # Create separate contacts
        id1 = identity_service.resolve("email", "john@example.com")
        id2 = identity_service.resolve("telegram", "123456")
        
        # Link them (should merge)
        merged_id = identity_service.link(
            "email", "john@example.com",
            "telegram", "123456"
        )
        
        # Should now resolve to same ID
        email_id = identity_service.resolve("email", "john@example.com", create_if_missing=False)
        telegram_id = identity_service.resolve("telegram", "123456", create_if_missing=False)
        
        assert email_id == telegram_id
    
    def test_get_contact(self, identity_service):
        """Should retrieve contact by ID."""
        from openclaw.agents.ira.skills.identity.unified_identity import Contact
        
        contact_id = identity_service.resolve("email", "test@example.com")
        contact = identity_service.get_contact(contact_id)
        
        assert contact is not None
        assert isinstance(contact, Contact)
        assert contact.email == "test@example.com"
    
    def test_get_contact_nonexistent(self, identity_service):
        """Should return None for nonexistent contact."""
        contact = identity_service.get_contact("c_nonexistent")
        
        assert contact is None
    
    def test_update_contact(self, identity_service):
        """Should update contact fields."""
        contact_id = identity_service.resolve("email", "test@example.com")
        
        identity_service.update_contact(
            contact_id,
            name="Updated Name",
            company="New Company"
        )
        
        contact = identity_service.get_contact(contact_id)
        assert contact.name == "Updated Name"
        assert contact.company == "New Company"
    
    def test_get_all_identifiers(self, identity_service):
        """Should get all identifiers for a contact."""
        contact_id = identity_service.resolve("email", "test@example.com")
        identity_service.link(
            "email", "test@example.com",
            "telegram", "123456"
        )
        
        identifiers = identity_service.get_all_identifiers(contact_id)
        
        # Returns list of tuples (channel, identifier)
        assert len(identifiers) >= 2
        channels = [i[0] for i in identifiers]
        assert "email" in channels
        assert "telegram" in channels
    
    def test_search_contacts_by_name(self, identity_service):
        """Should search contacts by name."""
        identity_service.resolve("email", "john@example.com", name="John Doe")
        identity_service.resolve("email", "jane@example.com", name="Jane Smith")
        
        results = identity_service.search_contacts("John")
        
        assert len(results) >= 1
        assert any(c.name == "John Doe" for c in results)
    
    def test_search_contacts_by_company(self, identity_service):
        """Should search contacts by company."""
        contact_id = identity_service.resolve("email", "john@example.com")
        identity_service.update_contact(contact_id, company="ABC Corp")
        
        results = identity_service.search_contacts("ABC Corp")
        
        assert len(results) >= 1
    
    def test_connection_context_manager(self, identity_service):
        """Connection should properly commit and close."""
        # This tests the _get_conn context manager
        with identity_service._get_conn() as conn:
            conn.execute(
                "INSERT INTO contacts (contact_id, name) VALUES (?, ?)",
                ("c_test", "Test User")
            )
        
        # Should be committed
        with identity_service._get_conn() as conn:
            row = conn.execute(
                "SELECT name FROM contacts WHERE contact_id = ?",
                ("c_test",)
            ).fetchone()
        
        assert row is not None
        assert row["name"] == "Test User"
    
    def test_connection_rollback_on_error(self, identity_service):
        """Connection should rollback on error."""
        try:
            with identity_service._get_conn() as conn:
                conn.execute(
                    "INSERT INTO contacts (contact_id, name) VALUES (?, ?)",
                    ("c_rollback", "Rollback Test")
                )
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should not be committed
        with identity_service._get_conn() as conn:
            row = conn.execute(
                "SELECT name FROM contacts WHERE contact_id = ?",
                ("c_rollback",)
            ).fetchone()
        
        assert row is None


class TestIdentityServiceSingleton:
    """Tests for get_identity_service singleton."""
    
    def test_get_identity_service_returns_instance(self, temp_dir):
        """Should return UnifiedIdentityService instance."""
        with patch("openclaw.agents.ira.skills.identity.unified_identity.CONFIG_AVAILABLE", False):
            # Reset singleton
            import openclaw.agents.ira.skills.identity.unified_identity as module
            if hasattr(module, '_identity_service'):
                module._identity_service = None
            
            with patch.object(
                module.UnifiedIdentityService,
                '__init__',
                lambda self, db_path=None: setattr(self, 'db_path', str(temp_dir / "test.db")) or None
            ):
                from openclaw.agents.ira.skills.identity.unified_identity import get_identity_service
                
                service = get_identity_service()
                assert service is not None


class TestCrossChannelResolution:
    """Integration tests for cross-channel identity resolution."""
    
    @pytest.fixture
    def identity_service(self, temp_dir):
        """Create identity service with temp database."""
        db_path = str(temp_dir / "test_identity.db")
        
        with patch("openclaw.agents.ira.skills.identity.unified_identity.CONFIG_AVAILABLE", False):
            from openclaw.agents.ira.skills.identity.unified_identity import UnifiedIdentityService
            service = UnifiedIdentityService(db_path=db_path)
            yield service
    
    def test_email_to_telegram_linking(self, identity_service):
        """Should link email and Telegram correctly."""
        # User starts on email
        email_id = identity_service.resolve("email", "user@company.com", name="User")
        
        # Later links Telegram
        identity_service.link("email", "user@company.com", "telegram", "987654")
        
        # Telegram should resolve to same contact
        telegram_id = identity_service.resolve("telegram", "987654", create_if_missing=False)
        
        assert email_id == telegram_id
    
    def test_multiple_email_addresses(self, identity_service):
        """Should handle multiple email addresses for same contact."""
        # Primary email
        contact_id = identity_service.resolve("email", "john@company.com", name="John")
        
        # Link personal email
        identity_service.link("email", "john@company.com", "email", "john.personal@gmail.com")
        
        # Both should resolve to same contact
        work_id = identity_service.resolve("email", "john@company.com", create_if_missing=False)
        personal_id = identity_service.resolve("email", "john.personal@gmail.com", create_if_missing=False)
        
        assert work_id == personal_id == contact_id
    
    def test_phone_email_telegram_chain(self, identity_service):
        """Should handle chain of linked identifiers."""
        # Start with email
        identity_service.resolve("email", "user@example.com", name="User")
        
        # Link phone to email
        identity_service.link("email", "user@example.com", "phone", "+1234567890")
        
        # Link telegram to phone (indirect link to email)
        identity_service.link("phone", "+1234567890", "telegram", "tg_user_123")
        
        # All should resolve to same contact
        email_id = identity_service.resolve("email", "user@example.com", create_if_missing=False)
        phone_id = identity_service.resolve("phone", "+1234567890", create_if_missing=False)
        telegram_id = identity_service.resolve("telegram", "tg_user_123", create_if_missing=False)
        
        assert email_id == phone_id == telegram_id
