"""Payload Generator Model - T5-based sequence-to-sequence for JSON payload generation"""
import logging
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import T5Tokenizer, T5ForConditionalGeneration
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class PayloadDataset(Dataset):
    """Dataset for payload generation training"""

    def __init__(self, examples: List[Dict], tokenizer, max_input_length=128, max_output_length=256):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        example = self.examples[idx]

        # Input: "generate payload for POST /api/users"
        input_text = f"generate payload for {example['method']} {example['url']}"

        # Output: JSON payload string
        output_text = json.dumps(example['payload']) if isinstance(example['payload'], dict) else str(example['payload'])

        # Tokenize input
        input_encoding = self.tokenizer(
            input_text,
            max_length=self.max_input_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # Tokenize output
        output_encoding = self.tokenizer(
            output_text,
            max_length=self.max_output_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': input_encoding['input_ids'].squeeze(),
            'attention_mask': input_encoding['attention_mask'].squeeze(),
            'labels': output_encoding['input_ids'].squeeze()
        }


class PayloadGeneratorModel:
    """T5-based payload generator for API requests"""

    def __init__(self, model_name: str = 't5-small'):
        """
        Initialize payload generator

        Args:
            model_name: T5 model variant (t5-small, t5-base, etc.)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # Load T5 model and tokenizer
        logger.info(f"Loading {model_name} model...")
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)

        logger.info(f"Model loaded with {sum(p.numel() for p in self.model.parameters())/1e6:.1f}M parameters")

    def generate_payload(self, url: str, method: str, max_length: int = 256) -> Dict:
        """
        Generate JSON payload for an API endpoint

        Args:
            url: API endpoint URL
            method: HTTP method
            max_length: Maximum length of generated payload

        Returns:
            Dict with 'payload' (dict) and 'confidence' (float)
        """
        self.model.eval()

        # Prepare input
        input_text = f"generate payload for {method} {url}"
        input_ids = self.tokenizer(
            input_text,
            return_tensors='pt',
            max_length=128,
            truncation=True
        ).input_ids.to(self.device)

        # Generate output
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                max_length=max_length,
                num_beams=4,
                early_stopping=True,
                return_dict_in_generate=True,
                output_scores=True
            )

        # Decode generated text
        generated_text = self.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)

        # Try to parse as JSON
        try:
            payload = json.loads(generated_text)
        except json.JSONDecodeError:
            # Fallback: return as string or basic structure
            logger.warning(f"Generated text is not valid JSON: {generated_text}")
            payload = {"_raw": generated_text}

        # Calculate confidence (average of generation scores)
        confidence = 0.5  # Placeholder - would need proper calculation from scores

        return {
            'payload': payload,
            'confidence': confidence,
            'raw_text': generated_text
        }

    def generate_batch(self, requests: List[Dict], max_length: int = 256) -> List[Dict]:
        """
        Generate payloads for multiple requests in batch

        Args:
            requests: List of {'url': str, 'method': str} dicts
            max_length: Maximum length of generated payloads

        Returns:
            List of generated payloads
        """
        results = []
        for req in requests:
            result = self.generate_payload(req['url'], req['method'], max_length)
            results.append(result)
        return results

    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int = 3, learning_rate: float = 5e-5):
        """
        Train the payload generator

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Number of training epochs
            learning_rate: Learning rate

        Returns:
            Training metrics
        """
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)

        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0.0

            for batch in train_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)

                # Forward pass
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

                loss = outputs.loss
                train_loss += loss.item()

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            avg_train_loss = train_loss / len(train_loader)

            # Validation
            self.model.eval()
            val_loss = 0.0

            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch['input_ids'].to(self.device)
                    attention_mask = batch['attention_mask'].to(self.device)
                    labels = batch['labels'].to(self.device)

                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )

                    val_loss += outputs.loss.item()

            avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0

            logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

        return {
            'final_train_loss': avg_train_loss,
            'final_val_loss': avg_val_loss
        }

    def save_model(self, path: str):
        """Save model and tokenizer"""
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load model and tokenizer"""
        self.model = T5ForConditionalGeneration.from_pretrained(path)
        self.tokenizer = T5Tokenizer.from_pretrained(path)
        self.model.to(self.device)
        logger.info(f"Model loaded from {path}")


class PayloadGenerator:
    """High-level interface for payload generation"""

    def __init__(self):
        self.model = PayloadGeneratorModel()

    def generate(self, url: str, method: str = 'POST') -> Dict:
        """Generate payload for endpoint"""
        return self.model.generate_payload(url, method)

    def train_from_data(self, examples: List[Dict], epochs: int = 3):
        """Train model from example data"""
        # Create datasets
        train_size = int(len(examples) * 0.7)
        val_size = int(len(examples) * 0.15)

        train_examples = examples[:train_size]
        val_examples = examples[train_size:train_size + val_size]

        train_dataset = PayloadDataset(train_examples, self.model.tokenizer)
        val_dataset = PayloadDataset(val_examples, self.model.tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=8)

        return self.model.train(train_loader, val_loader, epochs)
