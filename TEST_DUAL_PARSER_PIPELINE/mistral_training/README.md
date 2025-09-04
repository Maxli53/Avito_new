# Mistral 7B Snowmobile Spec Training

Fine-tuning Mistral 7B on snowmobile specifications and price lists for intelligent data extraction.

## Directory Structure

```
mistral_training/
├── data/               # Training and test datasets
├── models/             # Fine-tuned model checkpoints
├── scripts/            # Training and evaluation scripts
├── tests/              # Test files and validation
├── config/             # Configuration files
├── logs/               # Training logs and metrics
└── production/         # Production inference code
```

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Prepare data: `python scripts/prepare_data.py`
3. Start training: `python scripts/train.py`
4. Run inference: `python production/inference.py`

## Data Sources
- Spec books: 6 PDFs, 1,020 pages
- Price lists: 7 PDFs, 30 pages
- Total: 1,243 pages of snowmobile data