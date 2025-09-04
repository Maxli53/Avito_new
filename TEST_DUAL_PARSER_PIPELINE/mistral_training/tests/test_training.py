"""
Test suite for Mistral training pipeline
"""

import pytest
import torch
from pathlib import Path
import sys
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.prepare_data import SnowmobileDataPreparer
from scripts.train import MistralTrainer

class TestDataPreparation:
    def test_data_preparer_init(self):
        """Test data preparer initialization"""
        preparer = SnowmobileDataPreparer("../docs", "../data")
        assert preparer.docs_path.name == "docs"
        assert preparer.output_path.name == "data"
    
    def test_year_extraction(self):
        """Test year extraction from filenames"""
        preparer = SnowmobileDataPreparer("../docs", "../data")
        
        test_cases = [
            ("LYNX_2024_SPEC.pdf", "2024"),
            ("SKIDOO_2025-PRICE_LIST.pdf", "2025"),
            ("random_file.pdf", "unknown")
        ]
        
        for filename, expected in test_cases:
            result = preparer._extract_year(filename)
            assert result == expected
    
    def test_example_creation(self):
        """Test training example creation"""
        preparer = SnowmobileDataPreparer("../docs", "../data")
        
        sample_page = {
            'file': 'LYNX_2024_SPEC.pdf',
            'page': 1,
            'text': 'Test specification text with model info',
            'doc_type': 'spec_book',
            'brand': 'LYNX',
            'year': '2024'
        }
        
        examples = preparer._create_spec_examples(sample_page)
        assert len(examples) > 0
        assert 'instruction' in examples[0]
        assert 'input' in examples[0]
        assert 'output' in examples[0]

class TestTraining:
    def test_config_loading(self):
        """Test training configuration loading"""
        config_path = "../config/training_config.json"
        
        if Path(config_path).exists():
            trainer = MistralTrainer(config_path)
            assert trainer.model_name is not None
            assert trainer.config['training']['num_train_epochs'] > 0
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_gpu_availability(self):
        """Test GPU setup for training"""
        assert torch.cuda.is_available()
        assert torch.cuda.device_count() > 0
        
        # Test memory
        device = torch.cuda.current_device()
        memory_gb = torch.cuda.get_device_properties(device).total_memory / 1e9
        assert memory_gb >= 20, f"Need at least 20GB VRAM, got {memory_gb:.1f}GB"

class TestInference:
    def test_inference_setup(self):
        """Test inference pipeline setup"""
        # This would test loading a trained model
        # Skip if model doesn't exist yet
        model_path = "../models/checkpoints/final_model"
        if not Path(model_path).exists():
            pytest.skip("Trained model not found")

def test_project_structure():
    """Test that all required directories exist"""
    base_path = Path(__file__).parent.parent
    
    required_dirs = [
        "data", "models", "scripts", "tests", 
        "config", "logs", "production"
    ]
    
    for dir_name in required_dirs:
        assert (base_path / dir_name).exists(), f"Missing directory: {dir_name}"

def test_config_files():
    """Test that configuration files are valid"""
    config_path = Path(__file__).parent.parent / "config" / "training_config.json"
    
    assert config_path.exists(), "Training config not found"
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Test required sections
    assert "model" in config
    assert "training" in config
    assert "lora" in config
    assert "data" in config
    
    # Test model config
    assert "name" in config["model"]
    assert "mistral" in config["model"]["name"].lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])