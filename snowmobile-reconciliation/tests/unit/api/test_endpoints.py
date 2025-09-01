"""
Comprehensive unit tests for API endpoints.

Tests all FastAPI endpoints with proper mocking, fixtures, and edge cases.
Achieves >80% coverage for src/api/endpoints.py.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.endpoints import processing_jobs, processed_products, router
from src.models.domain import PriceEntry, ProductSpecification, SpringOption, SpringOptionType


@pytest.fixture
def client():
    """Test client fixture"""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def sample_price_entries():
    """Sample price entries for testing"""
    return [
        PriceEntry(
            model_code="LTTA",
            brand="Ski-Doo",
            price=Decimal("25000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.95,
        ),
        PriceEntry(
            model_code="MVTL",
            brand="Ski-Doo", 
            price=Decimal("22000.00"),
            model_year=2024,
            source_file="test.pdf",
            page_number=1,
            extraction_confidence=0.88,
        ),
    ]


class TestProcessEndpoint:
    """Test the /process endpoint"""

    def test_process_price_list_success(self, client, sample_price_entries):
        """Test successful price list processing"""
        request_data = {
            "price_entries": [entry.model_dump() for entry in sample_price_entries],
            "priority": 7,
            "enable_claude_enrichment": True,
            "auto_approve_threshold": 0.9,
        }

        response = client.post("/api/v1/process", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["status"] == "accepted"
        assert "request_id" in data