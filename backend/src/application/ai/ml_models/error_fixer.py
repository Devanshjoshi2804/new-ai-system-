"""Error Fixer Model - BART-based error correction for API requests"""
import logging
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BartTokenizer, BartForConditionalGeneration
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class ErrorFixDataset(Dataset):
    """Dataset for error correction training"""

    def __init__(self, examples: List[Dict], tokenizer, max_input_length=256, max_output_length=256):
        """
        Args:
            examples: List of dicts with 'error_request', 'error_message', 'fixed_request'
        """
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        example = self.examples[idx]

        # Input: "Fix request: POST /api/users {bad_json} | Error: 400 Bad Request - Invalid JSON"
        error_request = example.get('error_request', '')
        error_message = example.get('error_message', '')

        input_text = f"Fix request: {error_request} | Error: {error_message}"

        # Output: Corrected request
        output_text = example.get('fixed_request', '')

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


class ErrorFixerModel:
    """BART-based error correction model for API requests"""

    def __init__(self, model_name: str = 'facebook/bart-base'):
        """
        Initialize error fixer

        Args:
            model_name: BART model variant (facebook/bart-base, facebook/bart-large)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # Load BART model and tokenizer
        logger.info(f"Loading {model_name} model...")
        self.tokenizer = BartTokenizer.from_pretrained(model_name)
        self.model = BartForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)

        logger.info(f"Model loaded with {sum(p.numel() for p in self.model.parameters())/1e6:.1f}M parameters")

    def fix_error(self, error_request: str, error_message: str, max_length: int = 256) -> Dict:
        """
        Fix an API request based on error message

        Args:
            error_request: The failed request (method + URL + payload)
            error_message: Error message from API response
            max_length: Maximum length of corrected request

        Returns:
            Dict with 'fixed_request' (str) and 'confidence' (float)
        """
        self.model.eval()

        # Prepare input
        input_text = f"Fix request: {error_request} | Error: {error_message}"
        input_ids = self.tokenizer(
            input_text,
            return_tensors='pt',
            max_length=256,
            truncation=True
        ).input_ids.to(self.device)

        # Generate corrected request
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
        fixed_request = self.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)

        # Calculate confidence (simplified - would need proper calculation)
        confidence = 0.6  # Placeholder

        return {
            'fixed_request': fixed_request,
            'confidence': confidence,
            'original_request': error_request,
            'error_message': error_message
        }

    def fix_batch(self, requests: List[Dict], max_length: int = 256) -> List[Dict]:
        """
        Fix multiple requests in batch

        Args:
            requests: List of {'error_request': str, 'error_message': str} dicts
            max_length: Maximum length of corrected requests

        Returns:
            List of fixed requests
        """
        results = []
        for req in requests:
            result = self.fix_error(
                req['error_request'],
                req['error_message'],
                max_length
            )
            results.append(result)
        return results

    def train(self, train_loader: DataLoader, val_loader: DataLoader, epochs: int = 3, learning_rate: float = 5e-5):
        """
        Train the error fixer model

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

    def analyze_error_pattern(self, error_message: str) -> Dict:
        """
        Analyze error message to determine fix strategy

        Args:
            error_message: Error message from API

        Returns:
            Dict with error type and suggested fix strategy
        """
        error_lower = error_message.lower()

        patterns = {
            'invalid_json': ['invalid json', 'json parse error', 'malformed json'],
            'missing_field': ['required field', 'missing field', 'field is required'],
            'invalid_type': ['invalid type', 'type mismatch', 'expected'],
            'authentication': ['unauthorized', 'authentication', 'invalid token'],
            'not_found': ['not found', '404', 'does not exist'],
            'validation': ['validation error', 'invalid value', 'constraint'],
            'rate_limit': ['rate limit', 'too many requests', '429'],
        }

        detected_types = []
        for error_type, keywords in patterns.items():
            if any(keyword in error_lower for keyword in keywords):
                detected_types.append(error_type)

        return {
            'error_types': detected_types if detected_types else ['unknown'],
            'message': error_message,
            'fixable': len(detected_types) > 0
        }

    def save_model(self, path: str):
        """Save model and tokenizer"""
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load model and tokenizer"""
        self.model = BartForConditionalGeneration.from_pretrained(path)
        self.tokenizer = BartTokenizer.from_pretrained(path)
        self.model.to(self.device)
        logger.info(f"Model loaded from {path}")


class ErrorFixer:
    """High-level interface for error correction"""

    def __init__(self):
        self.model = ErrorFixerModel()

    def fix(self, error_request: str, error_message: str) -> Dict:
        """Fix an error in an API request"""
        # Analyze error first
        error_analysis = self.model.analyze_error_pattern(error_message)

        # Generate fix
        fix_result = self.model.fix_error(error_request, error_message)

        # Combine results
        return {
            **fix_result,
            'error_analysis': error_analysis
        }

    def train_from_data(self, examples: List[Dict], epochs: int = 3):
        """
        Train model from error/fix examples

        Args:
            examples: List of dicts with 'error_request', 'error_message', 'fixed_request'
        """
        # Create datasets
        train_size = int(len(examples) * 0.7)
        val_size = int(len(examples) * 0.15)

        train_examples = examples[:train_size]
        val_examples = examples[train_size:train_size + val_size]

        train_dataset = ErrorFixDataset(train_examples, self.model.tokenizer)
        val_dataset = ErrorFixDataset(val_examples, self.model.tokenizer)

        train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=8)

        return self.model.train(train_loader, val_loader, epochs)
