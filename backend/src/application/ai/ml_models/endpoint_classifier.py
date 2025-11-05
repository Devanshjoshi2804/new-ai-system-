"""
Endpoint Classifier Model - Fine-tuned DistilBERT
"""
import logging
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import DistilBertTokenizer, DistilBertModel
from typing import List, Dict, Optional, Tuple
from sklearn.metrics import accuracy_score

logger = logging.getLogger(__name__)

class EndpointDataset(Dataset):
    def __init__(self, examples: List[Dict], tokenizer, label_to_id: Dict):
        self.examples = examples
        self.tokenizer = tokenizer
        self.label_to_id = label_to_id
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        text = f"{example['method']} {example['url']}"
        encoding = self.tokenizer(text, max_length=128, padding='max_length', 
                                 truncation=True, return_tensors='pt')
        label_id = self.label_to_id.get(example['label'], 0)
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'label': torch.tensor(label_id, dtype=torch.long)
        }

class EndpointClassifierModel(nn.Module):
    def __init__(self, num_labels: int):
        super().__init__()
        self.distilbert = DistilBertModel.from_pretrained('distilbert-base-uncased')
        self.classifier = nn.Linear(768, num_labels)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.distilbert(input_ids=input_ids, attention_mask=attention_mask)
        logits = self.classifier(outputs.last_hidden_state[:, 0])
        return logits

class EndpointClassifier:
    LABELS = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'SEARCH', 
              'AUTH', 'WEBHOOK', 'REPORT', 'BATCH', 'HEALTH', 'CONFIG']
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
        self.label_to_id = {label: idx for idx, label in enumerate(self.LABELS)}
        self.id_to_label = {idx: label for label, idx in self.label_to_id.items()}
        self.model = EndpointClassifierModel(num_labels=len(self.LABELS))
        self.model.to(self.device)
    
    def train(self, train_loader, val_loader, epochs=3):
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=2e-5)
        criterion = nn.CrossEntropyLoss()
        best_acc = 0.0
        
        for epoch in range(epochs):
            self.model.train()
            for batch in train_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)
                
                optimizer.zero_grad()
                logits = self.model(input_ids, attention_mask)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()
            
            val_acc = self.evaluate(val_loader)
            if val_acc > best_acc:
                best_acc = val_acc
                torch.save(self.model.state_dict(), 'best_model.pt')
        
        return best_acc
    
    def evaluate(self, dataloader):
        self.model.eval()
        predictions, labels = [], []
        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                logits = self.model(input_ids, attention_mask)
                preds = torch.argmax(logits, dim=1)
                predictions.extend(preds.cpu().numpy())
                labels.extend(batch['label'].numpy())
        return accuracy_score(labels, predictions)
    
    def predict(self, url: str, method: str) -> Dict:
        self.model.eval()
        text = f"{method} {url}"
        encoding = self.tokenizer(text, max_length=128, padding='max_length',
                                 truncation=True, return_tensors='pt')
        with torch.no_grad():
            logits = self.model(encoding['input_ids'].to(self.device),
                              encoding['attention_mask'].to(self.device))
            probs = torch.softmax(logits, dim=1)
            pred_class = torch.argmax(probs, dim=1).item()
        return {
            'label': self.id_to_label[pred_class],
            'confidence': probs[0][pred_class].item()
        }
