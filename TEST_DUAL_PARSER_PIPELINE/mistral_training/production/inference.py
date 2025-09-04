"""
Production Inference Pipeline for Fine-tuned Mistral 7B
Optimized for RTX 3090 with efficient memory usage
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
from pathlib import Path
from typing import Dict, List, Optional
import time

class SnowmobileMistral:
    def __init__(self, model_path: str, base_model: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        self.model_path = Path(model_path)
        self.base_model = base_model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.tokenizer = None
        self.model = None
        
    def load_model(self):
        """Load the fine-tuned model for inference"""
        print(f"Loading model from {self.model_path}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model,
            trust_remote_code=True,
            padding_side="left"  # For inference
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Load LoRA weights
        self.model = PeftModel.from_pretrained(
            base_model,
            str(self.model_path),
            torch_dtype=torch.bfloat16,
        )
        
        self.model.eval()
        print(f"Model loaded on {self.device}")
        
    def extract_specifications(self, text: str, brand: str = "", year: str = "") -> Dict:
        """Extract specifications from snowmobile text"""
        prompt = f"""Extract all technical specifications from this {brand} {year} snowmobile specification text. 
        
Return a JSON object with the following structure:
{{
    "models": [
        {{
            "model_name": "...",
            "model_code": "...",
            "engine": {{
                "displacement": "...",
                "horsepower": "...",
                "cylinders": "...",
                "cooling": "..."
            }},
            "track": {{
                "width": "...",
                "length": "...",
                "profile": "..."
            }},
            "dimensions": {{
                "length": "...",
                "width": "...",
                "height": "..."
            }},
            "features": ["...", "..."]
        }}
    ]
}}

Text: {text}"""
        
        return self._generate_response(prompt)
    
    def extract_pricing(self, text: str, brand: str = "", year: str = "") -> Dict:
        """Extract pricing information from price list text"""
        prompt = f"""Extract all model pricing from this {brand} {year} price list text.

Return a JSON object with the following structure:
{{
    "pricing": [
        {{
            "model_code": "...",
            "model_name": "...",
            "price": "...",
            "currency": "...",
            "category": "..."
        }}
    ]
}}

Text: {text}"""
        
        return self._generate_response(prompt)
    
    def find_similar_models(self, query: str, context: str) -> Dict:
        """Find models matching specific criteria"""
        prompt = f"""Based on this snowmobile specification data, find all models that match the following criteria: {query}

Context: {context}

Return a JSON object with matching models and their key specifications."""
        
        return self._generate_response(prompt)
    
    def _generate_response(self, prompt: str, max_new_tokens: int = 2048) -> str:
        """Generate response using the fine-tuned model"""
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Format for Mistral
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096
        ).to(self.device)
        
        # Generate
        start_time = time.time()
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        generation_time = time.time() - start_time
        
        # Decode response
        response = self.tokenizer.decode(
            outputs[0][len(inputs.input_ids[0]):],
            skip_special_tokens=True
        )
        
        print(f"Generation time: {generation_time:.2f}s")
        return response.strip()
    
    def batch_process_pdfs(self, pdf_texts: List[Dict]) -> List[Dict]:
        """Process multiple PDF pages in batch"""
        results = []
        
        for pdf_data in pdf_texts:
            print(f"Processing {pdf_data['file']} page {pdf_data['page']}")
            
            if pdf_data['doc_type'] == 'spec_book':
                result = self.extract_specifications(
                    pdf_data['text'],
                    pdf_data.get('brand', ''),
                    pdf_data.get('year', '')
                )
            else:
                result = self.extract_pricing(
                    pdf_data['text'],
                    pdf_data.get('brand', ''),
                    pdf_data.get('year', '')
                )
            
            results.append({
                'source': pdf_data,
                'extracted_data': result
            })
            
        return results

# Example usage and testing
def main():
    # Initialize model
    model_path = "../models/checkpoints/final_model"  # Update path as needed
    
    mistral = SnowmobileMistral(model_path)
    mistral.load_model()
    
    # Test extraction
    sample_text = """
    2025 LYNX RAVE RE 600R E-TEC
    Engine: Rotax 600R E-TEC, 599.4 cc, 125 HP
    Track: 15" x 146", 2.25" profile
    Suspension: rMotion X with KYB Pro 40 shock
    Features: SHOT starting, tMotion suspension
    """
    
    print("Testing specification extraction...")
    result = mistral.extract_specifications(sample_text, "LYNX", "2025")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()