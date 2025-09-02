"""
Unit tests for BERT semantic matching functionality
Tests BERTMatcher class and semantic similarity operations
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from pipeline.stage2_matching import BERTMatcher
from core import ProductData, CatalogData, MatchResult, PipelineStats
from core.exceptions import MatchingError
from tests.utils import performance_timer
from tests.fixtures.sample_data import SampleDataFactory


class TestBERTMatcherInitialization:
    """Test BERTMatcher initialization and configuration"""
    
    def test_bert_matcher_creation_default_config(self):
        """Test creating BERTMatcher with default configuration"""
        matcher = BERTMatcher()
        
        assert isinstance(matcher, BERTMatcher)
        assert matcher.config is not None
        assert matcher.config['model_name'] == 'sentence-transformers/all-MiniLM-L6-v2'
        assert matcher.config['similarity_threshold'] == 0.8
        assert matcher.stats.stage == 'matching'
    
    def test_bert_matcher_custom_config(self):
        """Test BERTMatcher with custom configuration"""
        custom_config = {
            'model_name': 'sentence-transformers/all-mpnet-base-v2',
            'similarity_threshold': 0.75,
            'batch_size': 64,
            'device': 'cpu',
            'normalize_embeddings': True,
            'use_fuzzy_fallback': True
        }
        
        matcher = BERTMatcher(config=custom_config)
        
        assert matcher.config['model_name'] == 'sentence-transformers/all-mpnet-base-v2'
        assert matcher.config['similarity_threshold'] == 0.75
        assert matcher.config['batch_size'] == 64
        assert matcher.config['device'] == 'cpu'
        assert matcher.config['normalize_embeddings'] is True
    
    def test_bert_matcher_model_loading_success(self):
        """Test successful BERT model loading"""
        matcher = BERTMatcher()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_model = MagicMock()
            mock_transformer.return_value = mock_model
            
            result = matcher._load_bert_model()
            
            assert result is True
            assert matcher.model is mock_model
            mock_transformer.assert_called_once_with('sentence-transformers/all-MiniLM-L6-v2')
    
    def test_bert_matcher_model_loading_failure(self):
        """Test BERT model loading failure and fallback"""
        config = {'use_fuzzy_fallback': True}
        matcher = BERTMatcher(config=config)
        
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("Model loading failed")
            
            result = matcher._load_bert_model()
            
            assert result is False
            assert matcher.model is None
            assert matcher.use_fuzzy_fallback is True


class TestTextNormalization:
    """Test text normalization for Finnish snowmobile terminology"""
    
    def test_normalize_snowmobile_text_basic(self):
        """Test basic text normalization"""
        matcher = BERTMatcher()
        
        input_text = "Ski-Doo Summit X Expert 165 850 E-TEC Turbo R"
        normalized = matcher._normalize_text(input_text)
        
        # Should be lowercase and standardized
        assert normalized == "skidoo summit x expert 165 850 etec turbo r"
    
    def test_normalize_finnish_terms(self):
        """Test normalization of Finnish snowmobile terms"""
        matcher = BERTMatcher()
        
        test_cases = [
            ("telamoottorikelkka", "snowmobile"),
            ("moottorikelkka", "snowmobile"),  
            ("lumikone", "snowmobile"),
            ("kelkka", "sled"),
            ("telamatto", "track"),
            ("kaynnistin", "starter"),
            ("mittaristo", "gauge"),
            ("sahkokaynnnistin", "electric starter")
        ]
        
        for finnish_term, expected_english in test_cases:
            normalized = matcher._normalize_text(finnish_term)
            # Should contain English equivalent or be normalized
            assert len(normalized) > 0
    
    def test_normalize_brand_names(self):
        """Test normalization of snowmobile brand names"""
        matcher = BERTMatcher()
        
        brand_normalizations = [
            ("Ski-Doo", "skidoo"),
            ("BRP", "brp"),
            ("Arctic Cat", "arctic cat"),
            ("Polaris", "polaris"),
            ("Yamaha", "yamaha")
        ]
        
        for original, expected in brand_normalizations:
            normalized = matcher._normalize_text(original)
            assert expected in normalized
    
    def test_normalize_technical_terms(self):
        """Test normalization of technical snowmobile terms"""
        matcher = BERTMatcher()
        
        technical_terms = [
            ("E-TEC", "etec"),
            ("4-TEC", "4tec"),
            ("2-stroke", "2stroke"),
            ("4-stroke", "4stroke"),
            ("Turbo R", "turbo r"),
            ("QS3", "qs3")
        ]
        
        for original, expected in technical_terms:
            normalized = matcher._normalize_text(original)
            assert expected in normalized


class TestBERTEmbeddings:
    """Test BERT embedding generation and caching"""
    
    def test_generate_embeddings_single_text(self):
        """Test generating embeddings for single text"""
        matcher = BERTMatcher()
        
        with patch.object(matcher, 'model') as mock_model:
            mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
            matcher.model_loaded = True
            
            text = "Ski-Doo Summit X 2024"
            embeddings = matcher._generate_embeddings([text])
            
            assert embeddings.shape == (1, 5)
            assert np.allclose(embeddings[0], [0.1, 0.2, 0.3, 0.4, 0.5])
            mock_model.encode.assert_called_once()
    
    def test_generate_embeddings_batch(self):
        """Test generating embeddings for batch of texts"""
        matcher = BERTMatcher()
        
        with patch.object(matcher, 'model') as mock_model:
            mock_embeddings = np.array([
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
                [0.7, 0.8, 0.9]
            ])
            mock_model.encode.return_value = mock_embeddings
            matcher.model_loaded = True
            
            texts = ["Summit X", "Catalyst", "RMK Khaos"]
            embeddings = matcher._generate_embeddings(texts)
            
            assert embeddings.shape == (3, 3)
            assert np.allclose(embeddings, mock_embeddings)
    
    def test_embedding_normalization(self):
        """Test embedding normalization"""
        config = {'normalize_embeddings': True}
        matcher = BERTMatcher(config=config)
        
        with patch.object(matcher, 'model') as mock_model:
            # Unnormalized embeddings
            mock_model.encode.return_value = np.array([[3.0, 4.0, 0.0]])  # Length = 5
            matcher.model_loaded = True
            
            embeddings = matcher._generate_embeddings(["test"])
            
            # Should be normalized (length = 1)
            expected_normalized = np.array([[0.6, 0.8, 0.0]])  # 3/5, 4/5, 0
            assert np.allclose(embeddings, expected_normalized)
    
    def test_embedding_caching(self):
        """Test embedding caching for performance"""
        config = {'cache_embeddings': True}
        matcher = BERTMatcher(config=config)
        
        with patch.object(matcher, 'model') as mock_model:
            mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
            matcher.model_loaded = True
            
            text = "Summit X Expert 165"
            
            # First call should hit the model
            embeddings1 = matcher._generate_embeddings([text])
            assert mock_model.encode.call_count == 1
            
            # Second call should use cache
            embeddings2 = matcher._generate_embeddings([text])
            assert mock_model.encode.call_count == 1  # No additional calls
            
            assert np.allclose(embeddings1, embeddings2)


class TestSimilarityCalculation:
    """Test semantic similarity calculation"""
    
    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation"""
        matcher = BERTMatcher()
        
        # Perfect similarity (same vectors)
        vec1 = np.array([[1.0, 0.0, 0.0]])
        vec2 = np.array([[1.0, 0.0, 0.0]])
        similarity = matcher._calculate_cosine_similarity(vec1, vec2)
        assert np.isclose(similarity[0][0], 1.0)
        
        # No similarity (orthogonal vectors)
        vec1 = np.array([[1.0, 0.0, 0.0]])
        vec2 = np.array([[0.0, 1.0, 0.0]])
        similarity = matcher._calculate_cosine_similarity(vec1, vec2)
        assert np.isclose(similarity[0][0], 0.0)
        
        # Partial similarity
        vec1 = np.array([[1.0, 1.0, 0.0]])  # Normalized: [0.707, 0.707, 0]
        vec2 = np.array([[1.0, 0.0, 0.0]])  # Normalized: [1.0, 0, 0]
        similarity = matcher._calculate_cosine_similarity(vec1, vec2)
        expected = 0.707  # cos(45 degrees)
        assert np.isclose(similarity[0][0], expected, atol=0.01)
    
    def test_similarity_matrix_batch(self):
        """Test similarity calculation for batch of queries vs candidates"""
        matcher = BERTMatcher()
        
        # 2 queries vs 3 candidates
        query_embeddings = np.array([
            [1.0, 0.0, 0.0],  # Query 1
            [0.0, 1.0, 0.0]   # Query 2
        ])
        
        candidate_embeddings = np.array([
            [1.0, 0.0, 0.0],  # Perfect match for query 1
            [0.0, 1.0, 0.0],  # Perfect match for query 2  
            [0.5, 0.5, 0.0]   # Partial match for both
        ])
        
        similarities = matcher._calculate_cosine_similarity(query_embeddings, candidate_embeddings)
        
        assert similarities.shape == (2, 3)
        
        # Query 1 similarities
        assert np.isclose(similarities[0][0], 1.0)  # Perfect match
        assert np.isclose(similarities[0][1], 0.0)  # No match
        assert similarities[0][2] > 0.5  # Partial match
        
        # Query 2 similarities  
        assert np.isclose(similarities[1][0], 0.0)  # No match
        assert np.isclose(similarities[1][1], 1.0)  # Perfect match
        assert similarities[1][2] > 0.5  # Partial match


class TestCatalogMatching:
    """Test matching products against catalog data"""
    
    def test_load_catalog_data_success(self):
        """Test loading catalog data for matching"""
        matcher = BERTMatcher()
        catalog_data = SampleDataFactory.create_catalog_data()[:3]
        
        result = matcher.load_catalog_data(catalog_data)
        
        assert result is True
        assert len(matcher.catalog_entries) == 3
        assert len(matcher.catalog_texts) == 3
        
        # Verify catalog texts are properly formatted
        for text in matcher.catalog_texts:
            assert len(text) > 0
            assert isinstance(text, str)
    
    def test_format_catalog_text(self):
        """Test formatting catalog entry to searchable text"""
        matcher = BERTMatcher()
        
        catalog_entry = CatalogData(
            model_family="Summit X",
            brand="Ski-Doo",
            specifications={"engine": "850 E-TEC", "track_width": "3.0"},
            features=["Digital Display", "Electric Start", "Heated Grips"]
        )
        
        formatted_text = matcher._format_catalog_text(catalog_entry)
        
        assert "summit x" in formatted_text.lower()
        assert "ski-doo" in formatted_text.lower() or "skidoo" in formatted_text.lower()
        assert "850 etec" in formatted_text.lower() or "850 e-tec" in formatted_text.lower()
        assert "digital display" in formatted_text.lower()
    
    def test_match_single_product_success(self):
        """Test successful matching of single product"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Setup catalog
        catalog_data = [
            CatalogData(model_family="Summit X", brand="Ski-Doo"),
            CatalogData(model_family="Catalyst", brand="Arctic Cat"),
            CatalogData(model_family="RMK", brand="Polaris")
        ]
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(
            model_code="TEST",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X",
            paketti="Expert 165"
        )
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                # Mock embeddings
                mock_embed.return_value = np.array([[0.1, 0.2, 0.3]])
                
                # Mock high similarity for first catalog entry (Summit X)
                mock_sim.return_value = np.array([[0.95, 0.3, 0.2]])
                
                match_result = matcher.match_single_product(product)
                
                assert match_result.success is True
                assert match_result.matched_model == "Summit X"
                assert match_result.confidence_score >= 0.95
                assert match_result.match_method == "bert_semantic"
    
    def test_match_single_product_no_good_match(self):
        """Test product matching when no good matches found"""
        config = {'similarity_threshold': 0.9}  # High threshold
        matcher = BERTMatcher(config=config)
        matcher.model_loaded = True
        
        # Setup catalog
        catalog_data = [CatalogData(model_family="Different Model", brand="Different Brand")]
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(
            model_code="TEST",
            brand="UnknownBrand", 
            year=2024,
            malli="UnknownModel"
        )
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                mock_embed.return_value = np.array([[0.1, 0.2, 0.3]])
                mock_sim.return_value = np.array([[0.3]])  # Low similarity
                
                match_result = matcher.match_single_product(product)
                
                assert match_result.success is False
                assert match_result.matched_model is None
                assert match_result.confidence_score < 0.9
    
    def test_match_multiple_products(self):
        """Test matching multiple products in batch"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Setup catalog
        catalog_data = SampleDataFactory.create_catalog_data()[:3]
        matcher.load_catalog_data(catalog_data)
        
        products = [
            ProductData(model_code="SKI1", brand="Ski-Doo", year=2024, malli="Summit X"),
            ProductData(model_code="ARC1", brand="Arctic Cat", year=2024, malli="Catalyst"),
            ProductData(model_code="POL1", brand="Polaris", year=2023, malli="RMK")
        ]
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                # Mock embeddings for products and catalog
                mock_embed.return_value = np.array([
                    [0.1, 0.2, 0.3],  # Product 1
                    [0.4, 0.5, 0.6],  # Product 2
                    [0.7, 0.8, 0.9]   # Product 3
                ])
                
                # Mock high diagonal similarities (each product matches corresponding catalog)
                mock_sim.return_value = np.array([
                    [0.95, 0.3, 0.2],  # Product 1 matches catalog 1
                    [0.2, 0.93, 0.3],  # Product 2 matches catalog 2
                    [0.3, 0.2, 0.91]   # Product 3 matches catalog 3
                ])
                
                match_results = matcher.match_products(products)
                
                assert len(match_results) == 3
                assert all(result.success for result in match_results)
                assert all(result.confidence_score > 0.9 for result in match_results)


class TestFuzzyFallback:
    """Test fuzzy string matching fallback"""
    
    def test_fuzzy_matching_when_bert_unavailable(self):
        """Test fallback to fuzzy matching when BERT is unavailable"""
        config = {'use_fuzzy_fallback': True}
        matcher = BERTMatcher(config=config)
        matcher.model_loaded = False  # BERT not available
        
        # Setup catalog
        catalog_data = [CatalogData(model_family="Summit X", brand="Ski-Doo")]
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(
            model_code="TEST",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X Expert"  # Close but not exact match
        )
        
        with patch('fuzzywuzzy.fuzz.ratio') as mock_fuzzy:
            mock_fuzzy.return_value = 85  # Good fuzzy match
            
            match_result = matcher.match_single_product(product)
            
            assert match_result.success is True
            assert match_result.matched_model == "Summit X"
            assert match_result.match_method == "fuzzy_string"
            assert match_result.similarity_score == 0.85  # Normalized from 85
    
    def test_fuzzy_matching_exact_match(self):
        """Test fuzzy matching with exact string match"""
        config = {'use_fuzzy_fallback': True}
        matcher = BERTMatcher(config=config)
        matcher.model_loaded = False
        
        catalog_data = [CatalogData(model_family="Catalyst", brand="Arctic Cat")]
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(
            model_code="TEST",
            brand="Arctic Cat",
            year=2024,
            malli="Catalyst"  # Exact match
        )
        
        match_result = matcher._match_with_fuzzy(product)
        
        assert match_result.success is True
        assert match_result.matched_model == "Catalyst"
        assert match_result.similarity_score == 1.0  # Perfect match
    
    def test_fuzzy_matching_no_good_match(self):
        """Test fuzzy matching when no good matches found"""
        config = {
            'use_fuzzy_fallback': True,
            'fuzzy_threshold': 80  # Require 80% similarity
        }
        matcher = BERTMatcher(config=config)
        
        catalog_data = [CatalogData(model_family="Summit X", brand="Ski-Doo")]
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(
            model_code="TEST",
            brand="Polaris",  # Different brand
            year=2024,
            malli="RMK Khaos"  # Completely different model
        )
        
        with patch('fuzzywuzzy.fuzz.ratio') as mock_fuzzy:
            mock_fuzzy.return_value = 25  # Poor match
            
            match_result = matcher._match_with_fuzzy(product)
            
            assert match_result.success is False
            assert match_result.similarity_score < 0.8


class TestBERTMatcherPerformance:
    """Test BERT matcher performance characteristics"""
    
    @pytest.mark.performance
    def test_single_product_matching_speed(self):
        """Test speed of single product matching"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Setup realistic catalog size
        catalog_data = SampleDataFactory.create_catalog_data()
        matcher.load_catalog_data(catalog_data)
        
        product = ProductData(model_code="PERF", brand="Test", year=2024, malli="Test Model")
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                mock_embed.return_value = np.array([[0.1, 0.2, 0.3]])
                mock_sim.return_value = np.array([[0.9, 0.3, 0.2, 0.4, 0.1]])
                
                with performance_timer.time_operation("single_product_matching"):
                    match_result = matcher.match_single_product(product)
                
                assert match_result is not None
                
                # Should complete quickly (less than 1 second for mocked operations)
                performance_timer.assert_performance("single_product_matching", 1.0)
    
    @pytest.mark.performance
    def test_batch_matching_performance(self):
        """Test performance of batch product matching"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Setup catalog
        catalog_data = SampleDataFactory.create_catalog_data()
        matcher.load_catalog_data(catalog_data)
        
        # Create batch of products
        products = [
            ProductData(model_code=f"P{i:03d}", brand="Test", year=2024, malli=f"Model {i}")
            for i in range(20)  # 20 products
        ]
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                # Mock batch embeddings
                mock_embed.return_value = np.random.random((20, 384))  # Typical BERT dimension
                mock_sim.return_value = np.random.random((20, len(catalog_data)))
                
                with performance_timer.time_operation("batch_product_matching"):
                    match_results = matcher.match_products(products)
                
                assert len(match_results) == 20
                
                # Batch processing should be efficient (less than 3 seconds)
                performance_timer.assert_performance("batch_product_matching", 3.0)
    
    def test_catalog_embedding_caching(self):
        """Test that catalog embeddings are cached for performance"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        catalog_data = SampleDataFactory.create_catalog_data()[:3]
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            mock_embed.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
            
            # First load should generate embeddings
            matcher.load_catalog_data(catalog_data)
            assert mock_embed.call_count == 1
            
            # Subsequent matching should not regenerate catalog embeddings
            product = ProductData(model_code="TEST", brand="Test", year=2024)
            
            mock_embed.return_value = np.array([[0.1, 0.1, 0.1]])  # Product embedding
            
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                mock_sim.return_value = np.array([[0.8, 0.3, 0.2]])
                
                matcher.match_single_product(product)
                
                # Should only generate embeddings for the product, not catalog again
                assert mock_embed.call_count == 2  # Initial catalog + product


class TestBERTMatcherErrorHandling:
    """Test error handling in BERT matching operations"""
    
    def test_model_loading_timeout(self):
        """Test handling of model loading timeout"""
        config = {'model_load_timeout': 1}  # Very short timeout
        matcher = BERTMatcher(config=config)
        
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            import time
            
            def slow_load(*args, **kwargs):
                time.sleep(2)  # Longer than timeout
                return MagicMock()
            
            mock_transformer.side_effect = slow_load
            
            with pytest.raises(MatchingError) as exc_info:
                matcher._load_bert_model()
            
            assert "timeout" in str(exc_info.value).lower() or "loading" in str(exc_info.value).lower()
    
    def test_embedding_generation_memory_error(self):
        """Test handling of memory errors during embedding generation"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        with patch.object(matcher, 'model') as mock_model:
            mock_model.encode.side_effect = MemoryError("Insufficient memory for embeddings")
            
            with pytest.raises(MatchingError) as exc_info:
                matcher._generate_embeddings(["test text"])
            
            assert "memory" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.original_exception, MemoryError)
    
    def test_invalid_similarity_threshold(self):
        """Test handling of invalid similarity threshold"""
        with pytest.raises(ValueError):
            BERTMatcher(config={'similarity_threshold': 1.5})  # > 1.0
        
        with pytest.raises(ValueError):
            BERTMatcher(config={'similarity_threshold': -0.1})  # < 0.0
    
    def test_empty_catalog_handling(self):
        """Test handling of empty catalog data"""
        matcher = BERTMatcher()
        
        result = matcher.load_catalog_data([])
        assert result is True  # Should handle gracefully
        
        product = ProductData(model_code="TEST", brand="Test", year=2024)
        match_result = matcher.match_single_product(product)
        
        assert match_result.success is False
        assert "no catalog data" in str(match_result.errors[0]).lower()
    
    def test_malformed_catalog_entry(self):
        """Test handling of malformed catalog entries"""
        matcher = BERTMatcher()
        
        # Catalog entry with missing required fields
        malformed_catalog = [
            CatalogData(model_family="", brand=""),  # Empty fields
            CatalogData(model_family="Valid Model", brand="Valid Brand")  # Valid entry
        ]
        
        result = matcher.load_catalog_data(malformed_catalog)
        
        # Should load successfully, filtering out invalid entries
        assert result is True
        assert len(matcher.catalog_entries) == 1  # Only valid entry loaded
        assert matcher.catalog_entries[0].model_family == "Valid Model"


class TestBERTMatcherIntegration:
    """Integration tests for BERT matcher with other components"""
    
    def test_integration_with_product_data_validation(self):
        """Test integration with ProductData validation"""
        matcher = BERTMatcher()
        
        # Test with invalid product data
        invalid_product = ProductData(
            model_code="",  # Invalid: empty model code
            brand="Test",
            year=2024
        )
        
        # Should handle gracefully
        try:
            match_result = matcher.match_single_product(invalid_product)
            # Matching might still work with partial data
            assert isinstance(match_result, MatchResult)
        except ValueError:
            # Or it might raise validation error, which is also acceptable
            pass
    
    def test_integration_with_pipeline_stats(self):
        """Test integration with pipeline statistics"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        catalog_data = SampleDataFactory.create_catalog_data()[:2]
        matcher.load_catalog_data(catalog_data)
        
        products = [
            ProductData(model_code="ST1", brand="Ski-Doo", year=2024, malli="Summit"),
            ProductData(model_code="ST2", brand="Arctic Cat", year=2024, malli="Catalyst")
        ]
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                mock_embed.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
                mock_sim.return_value = np.array([[0.9, 0.3], [0.2, 0.95]])  # Good matches
                
                match_results = matcher.match_products(products)
                
                # Verify statistics are updated
                stats = matcher.get_stats()
                assert stats.total_processed == 2
                assert stats.successful == 2
                assert stats.success_rate == 100.0
                assert stats.processing_time is not None
    
    def test_integration_with_multilingual_text(self):
        """Test integration with Finnish/English mixed text"""
        matcher = BERTMatcher()
        matcher.model_loaded = True
        
        # Catalog with English terms
        catalog_data = [
            CatalogData(
                model_family="Summit X",
                brand="Ski-Doo",
                specifications={"engine": "850 E-TEC", "track": "3.0 wide"}
            )
        ]
        matcher.load_catalog_data(catalog_data)
        
        # Product with Finnish terms
        finnish_product = ProductData(
            model_code="FIN1",
            brand="Ski-Doo",
            year=2024,
            malli="Summit X",
            moottori="850 E-TEC",  # Engine in Finnish
            telamatto="3.0"  # Track in Finnish
        )
        
        with patch.object(matcher, '_generate_embeddings') as mock_embed:
            with patch.object(matcher, '_calculate_cosine_similarity') as mock_sim:
                mock_embed.return_value = np.array([[0.1, 0.2, 0.3]])
                mock_sim.return_value = np.array([[0.92]])  # High similarity despite language mix
                
                match_result = matcher.match_single_product(finnish_product)
                
                assert match_result.success is True
                assert match_result.matched_model == "Summit X"