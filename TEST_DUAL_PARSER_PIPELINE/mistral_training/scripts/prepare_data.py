"""
Data Preparation Pipeline for Mistral 7B Training
Extracts and formats snowmobile specification data from PDFs
"""

import os
import json
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datasets import Dataset
import re

class SnowmobileDataPreparer:
    def __init__(self, docs_path: str, output_path: str):
        self.docs_path = Path(docs_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
    def extract_pdf_text(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF with page-level granularity"""
        doc = fitz.open(pdf_path)
        pages = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Basic cleaning
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize whitespace
            text = text.strip()
            
            if len(text) > 50:  # Skip mostly empty pages
                pages.append({
                    'file': pdf_path.name,
                    'page': page_num + 1,
                    'text': text,
                    'doc_type': 'spec_book' if 'SPEC BOOK' in pdf_path.name else 'price_list',
                    'brand': 'LYNX' if 'LYNX' in pdf_path.name else 'SKIDOO',
                    'year': self._extract_year(pdf_path.name)
                })
        
        doc.close()
        return pages
    
    def _extract_year(self, filename: str) -> str:
        """Extract year from filename"""
        years = re.findall(r'20\d{2}', filename)
        return years[0] if years else 'unknown'
    
    def create_training_examples(self, pages: List[Dict]) -> List[Dict]:
        """Convert extracted pages into training examples"""
        examples = []
        
        for page in pages:
            # Create instruction-based examples
            if page['doc_type'] == 'spec_book':
                examples.extend(self._create_spec_examples(page))
            else:
                examples.extend(self._create_price_examples(page))
                
        return examples
    
    def _create_spec_examples(self, page: Dict) -> List[Dict]:
        """Create specification extraction examples"""
        text = page['text']
        examples = []
        
        # Example 1: Extract model information
        examples.append({
            "instruction": f"Extract all snowmobile model information from this {page['brand']} {page['year']} specification page:",
            "input": text,
            "output": "I need to identify model names, engine specifications, track dimensions, and key features from this specification text.",
            "metadata": page
        })
        
        # Example 2: Find technical specifications
        examples.append({
            "instruction": "List all technical specifications with their values:",
            "input": text,
            "output": "I'll extract engine displacement, horsepower, track width, track length, suspension travel, and other technical specifications.",
            "metadata": page
        })
        
        return examples
    
    def _create_price_examples(self, page: Dict) -> List[Dict]:
        """Create pricing extraction examples"""
        text = page['text']
        examples = []
        
        # Example 1: Extract pricing information
        examples.append({
            "instruction": f"Extract all model names and prices from this {page['brand']} {page['year']} price list:",
            "input": text,
            "output": "I'll identify model codes, full model names, and their corresponding prices in the specified currency.",
            "metadata": page
        })
        
        return examples
    
    def format_for_training(self, examples: List[Dict]) -> List[Dict]:
        """Format examples for Mistral instruction tuning"""
        formatted = []
        
        for example in examples:
            # Mistral instruction format
            messages = [
                {"role": "user", "content": example["instruction"] + "\n\n" + example["input"]},
                {"role": "assistant", "content": example["output"]}
            ]
            
            formatted.append({
                "messages": messages,
                "metadata": example["metadata"]
            })
            
        return formatted
    
    def process_all_pdfs(self):
        """Main processing pipeline"""
        print("Starting PDF processing...")
        
        all_pages = []
        
        # Process spec books
        spec_dir = self.docs_path / "Spec_books"
        if spec_dir.exists():
            for pdf_file in spec_dir.glob("*.pdf"):
                print(f"Processing spec book: {pdf_file.name}")
                pages = self.extract_pdf_text(pdf_file)
                all_pages.extend(pages)
        
        # Process price lists  
        price_dir = self.docs_path / "Price_lists"
        if price_dir.exists():
            for pdf_file in price_dir.glob("*.pdf"):
                print(f"Processing price list: {pdf_file.name}")
                pages = self.extract_pdf_text(pdf_file)
                all_pages.extend(pages)
        
        print(f"Extracted {len(all_pages)} pages total")
        
        # Create training examples
        print("Creating training examples...")
        examples = self.create_training_examples(all_pages)
        print(f"Created {len(examples)} training examples")
        
        # Format for training
        formatted_examples = self.format_for_training(examples)
        
        # Save datasets
        self.save_datasets(formatted_examples)
        
        return formatted_examples
    
    def save_datasets(self, examples: List[Dict]):
        """Save train/val/test splits"""
        import random
        random.shuffle(examples)
        
        n = len(examples)
        train_end = int(0.8 * n)
        val_end = int(0.9 * n)
        
        splits = {
            'train': examples[:train_end],
            'validation': examples[train_end:val_end],
            'test': examples[val_end:]
        }
        
        for split_name, split_data in splits.items():
            # Save as JSON
            json_path = self.output_path / f"{split_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(split_data, f, indent=2, ensure_ascii=False)
            
            # Save as HuggingFace dataset
            dataset = Dataset.from_list(split_data)
            dataset.save_to_disk(self.output_path / f"{split_name}_dataset")
            
            print(f"Saved {len(split_data)} examples to {split_name} split")

if __name__ == "__main__":
    docs_path = "docs"
    output_path = "data"
    
    preparer = SnowmobileDataPreparer(docs_path, output_path)
    examples = preparer.process_all_pdfs()
    
    print(f"\nData preparation complete!")
    print(f"Total examples: {len(examples)}")
    print(f"Output directory: {output_path}")