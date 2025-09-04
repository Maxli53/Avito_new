#!/bin/bash

# Complete training pipeline for RTX 3090
# Run this script to execute the full training process

set -e

echo "=== Mistral 7B Snowmobile Training Pipeline ==="
echo "Optimized for RTX 3090 (24GB VRAM)"
echo

# Check GPU
echo "Checking GPU..."
nvidia-smi
echo

# Check CUDA
echo "CUDA Version:"
nvcc --version
echo

# Install dependencies
echo "Installing dependencies..."
pip install -r ../requirements.txt
echo

# Prepare data
echo "Preparing training data..."
cd scripts
python prepare_data.py
cd ..
echo

# Run tests
echo "Running tests..."
python -m pytest tests/ -v
echo

# Start training
echo "Starting Mistral 7B training..."
echo "This will take several hours on RTX 3090..."
cd scripts
python train.py
cd ..

echo
echo "=== Training Complete! ==="
echo "Model saved in: models/checkpoints/final_model/"
echo "Logs available in: models/checkpoints/logs/"