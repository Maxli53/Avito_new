"""
Mistral 7B Fine-tuning Script for RTX 3090
Optimized for 24GB VRAM with LoRA and Flash Attention
"""

import os
import json
import torch
from pathlib import Path
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, 
    TrainingArguments, Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_from_disk
import wandb
from datetime import datetime

class MistralTrainer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.model_name = self.config['model']['name']
        self.output_dir = Path(self.config['training']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set environment for optimal RTX 3090 performance
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
        
    def load_model_and_tokenizer(self):
        """Load Mistral model optimized for RTX 3090"""
        print("Loading Mistral 7B model...")
        
        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side="right"
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # Model with optimizations
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Enable gradient checkpointing for memory efficiency
        self.model.gradient_checkpointing_enable()
        
        print(f"Model loaded on device: {self.model.device}")
        print(f"Model dtype: {self.model.dtype}")
        
    def setup_lora(self):
        """Configure LoRA for efficient fine-tuning"""
        lora_config = LoraConfig(
            r=self.config['lora']['r'],
            lora_alpha=self.config['lora']['lora_alpha'],
            target_modules=self.config['lora']['target_modules'],
            lora_dropout=self.config['lora']['lora_dropout'],
            bias=self.config['lora']['bias'],
            task_type=TaskType.CAUSAL_LM,
        )
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
    def load_datasets(self):
        """Load prepared training datasets"""
        data_path = Path("../data")
        
        # Check if datasets exist
        train_path = data_path / "train_dataset"
        eval_path = data_path / "validation_dataset"
        
        if not train_path.exists():
            raise FileNotFoundError(f"Training dataset not found at {train_path}. Please run prepare_data.py first.")
        if not eval_path.exists():
            raise FileNotFoundError(f"Validation dataset not found at {eval_path}. Please run prepare_data.py first.")
        
        self.train_dataset = load_from_disk(train_path)
        self.eval_dataset = load_from_disk(eval_path)
        
        print(f"Train dataset: {len(self.train_dataset)} examples")
        print(f"Eval dataset: {len(self.eval_dataset)} examples")
        
    def tokenize_dataset(self, dataset):
        """Tokenize dataset for training"""
        def tokenize_function(examples):
            # Format messages for Mistral
            texts = []
            for messages in examples['messages']:
                text = self.tokenizer.apply_chat_template(
                    messages, 
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
                
            # Tokenize with consistent padding and truncation
            tokenized = self.tokenizer(
                texts,
                truncation=True,
                padding="max_length",
                max_length=self.config['data']['max_seq_length'],
                return_overflowing_tokens=False,
                return_tensors=None,  # Keep as lists for now
            )
            
            # Set labels for causal LM
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            return tokenized
        
        return dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
            desc="Tokenizing dataset"
        )
    
    def setup_training_args(self):
        """Configure training arguments for RTX 3090"""
        training_config = self.config['training']
        
        # Create unique run name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"mistral_snowmobile_{timestamp}"
        
        self.training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            run_name=run_name,
            num_train_epochs=training_config['num_train_epochs'],
            per_device_train_batch_size=training_config['per_device_train_batch_size'],
            per_device_eval_batch_size=training_config['per_device_eval_batch_size'],
            gradient_accumulation_steps=training_config['gradient_accumulation_steps'],
            learning_rate=float(training_config['learning_rate']),
            warmup_steps=training_config['warmup_steps'],
            logging_steps=training_config['logging_steps'],
            save_steps=training_config['save_steps'],
            eval_steps=training_config['eval_steps'],
            save_total_limit=training_config['save_total_limit'],
            bf16=training_config['bf16'],
            dataloader_pin_memory=training_config['dataloader_pin_memory'],
            remove_unused_columns=training_config['remove_unused_columns'],
            gradient_checkpointing=training_config['gradient_checkpointing'],
            
            # Evaluation and logging
            eval_strategy="steps",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            
            # Memory optimizations for RTX 3090 - disable multiprocessing to avoid hanging
            dataloader_num_workers=0,
            ddp_find_unused_parameters=False,
            
            # Logging
            report_to="tensorboard",
            logging_dir=str(self.output_dir / "logs"),
        )
        
    def train(self):
        """Main training loop"""
        print("Starting training setup...")
        
        # Initialize wandb - disable for now
        # wandb.init(
        #     project="mistral-snowmobile",
        #     name=self.training_args.run_name,
        #     config=self.config
        # )
        
        # Load and prepare data
        self.load_datasets()
        train_dataset = self.tokenize_dataset(self.train_dataset)
        eval_dataset = self.tokenize_dataset(self.eval_dataset)
        
        # Data collator without additional padding since we pad to max_length during tokenization
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
            pad_to_multiple_of=None,  # Disable to avoid conflicts
            return_tensors="pt",
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=self.training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            data_collator=data_collator,
        )
        
        # Start training
        print(f"Starting training with {len(train_dataset)} examples...")
        print(f"Effective batch size: {self.training_args.per_device_train_batch_size * self.training_args.gradient_accumulation_steps}")
        print(f"Total steps: {len(train_dataset) // (self.training_args.per_device_train_batch_size * self.training_args.gradient_accumulation_steps) * self.training_args.num_train_epochs}")
        
        trainer.train()
        
        # Save final model
        final_path = self.output_dir / "final_model"
        trainer.save_model(str(final_path))
        self.tokenizer.save_pretrained(str(final_path))
        
        print(f"Training complete! Model saved to {final_path}")
        
        # Cleanup
        # wandb.finish()

def main():
    # Check GPU availability
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available!")
        return
    
    print(f"GPU: {torch.cuda.get_device_name()}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Initialize trainer
    config_path = "config/training_config.json"
    trainer = MistralTrainer(config_path)
    
    # Setup model
    trainer.load_model_and_tokenizer()
    trainer.setup_lora()
    trainer.setup_training_args()
    
    # Start training
    trainer.train()

if __name__ == "__main__":
    main()