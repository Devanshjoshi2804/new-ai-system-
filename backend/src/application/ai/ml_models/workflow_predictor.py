"""
Workflow Predictor - Graph Neural Network for optimal API workflow prediction

This model predicts the optimal sequence of API calls to achieve a goal.
Uses Graph Neural Networks to understand endpoint dependencies and data flow.
"""
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv
from torch_geometric.data import Data
from typing import List, Dict, Optional, Tuple
import networkx as nx
import json

logger = logging.getLogger(__name__)


class GraphWorkflowEncoder(nn.Module):
    """
    Graph Neural Network to encode API dependency graph
    Uses Graph Attention Networks (GAT) for learning node relationships
    """

    def __init__(self, node_features: int = 128, hidden_dim: int = 256, num_layers: int = 3):
        super().__init__()

        # Node feature embedding
        self.node_embedding = nn.Linear(node_features, hidden_dim)

        # Graph Attention layers
        self.gat_layers = nn.ModuleList([
            GATConv(hidden_dim, hidden_dim, heads=4, concat=False)
            for _ in range(num_layers)
        ])

        # Layer normalization for stability
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(hidden_dim) for _ in range(num_layers)
        ])

        # Dropout for regularization
        self.dropout = nn.Dropout(0.1)

    def forward(self, x, edge_index):
        """
        Args:
            x: Node features [num_nodes, node_features]
            edge_index: Graph connectivity [2, num_edges]

        Returns:
            Node embeddings [num_nodes, hidden_dim]
        """
        # Initial embedding
        x = self.node_embedding(x)
        x = F.relu(x)

        # Apply GAT layers with residual connections
        for gat_layer, layer_norm in zip(self.gat_layers, self.layer_norms):
            residual = x
            x = gat_layer(x, edge_index)
            x = layer_norm(x + residual)  # Residual connection
            x = F.relu(x)
            x = self.dropout(x)

        return x


class WorkflowSequenceDecoder(nn.Module):
    """
    LSTM-based sequence decoder for predicting workflow execution order
    """

    def __init__(self, input_dim: int = 256, hidden_dim: int = 256, num_layers: int = 2):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1 if num_layers > 1 else 0
        )

        # Attention mechanism for focusing on relevant nodes
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=8,
            dropout=0.1
        )

        # Output projection
        self.output_layer = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, node_embeddings, sequence_length: int = 10):
        """
        Args:
            node_embeddings: Encoded graph nodes [num_nodes, hidden_dim]
            sequence_length: Max workflow steps to predict

        Returns:
            Sequence of node indices representing workflow
        """
        batch_size = 1
        num_nodes = node_embeddings.size(0)
        hidden_dim = node_embeddings.size(1)

        # Initialize LSTM hidden state
        h_0 = torch.zeros(self.lstm.num_layers, batch_size, hidden_dim).to(node_embeddings.device)
        c_0 = torch.zeros(self.lstm.num_layers, batch_size, hidden_dim).to(node_embeddings.device)

        # Start token (learnable)
        start_token = torch.randn(1, 1, hidden_dim).to(node_embeddings.device)

        # Generate sequence
        predicted_sequence = []
        lstm_input = start_token
        h_state, c_state = h_0, c_0

        for step in range(sequence_length):
            # LSTM step
            lstm_out, (h_state, c_state) = self.lstm(lstm_input, (h_state, c_state))

            # Attention over all nodes
            attn_out, attn_weights = self.attention(
                query=lstm_out.transpose(0, 1),
                key=node_embeddings.unsqueeze(0).transpose(0, 1),
                value=node_embeddings.unsqueeze(0).transpose(0, 1)
            )

            # Predict next node
            output = self.output_layer(attn_out.transpose(0, 1))

            # Compute similarity with all nodes
            scores = torch.matmul(output, node_embeddings.t())
            next_node_idx = torch.argmax(scores, dim=-1).item()

            predicted_sequence.append(next_node_idx)

            # Next input is the selected node embedding
            lstm_input = node_embeddings[next_node_idx].unsqueeze(0).unsqueeze(0)

        return predicted_sequence


class WorkflowPredictor:
    """
    Main Workflow Predictor combining Graph Encoding + Sequence Decoding
    """

    def __init__(self, node_features: int = 128, hidden_dim: int = 256):
        """
        Initialize workflow predictor

        Args:
            node_features: Dimension of node features
            hidden_dim: Hidden dimension for GNN and LSTM
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # Initialize encoder and decoder
        self.encoder = GraphWorkflowEncoder(
            node_features=node_features,
            hidden_dim=hidden_dim,
            num_layers=3
        )
        self.decoder = WorkflowSequenceDecoder(
            input_dim=hidden_dim,
            hidden_dim=hidden_dim,
            num_layers=2
        )

        # Move to device
        self.encoder.to(self.device)
        self.decoder.to(self.device)

        logger.info(f"Workflow Predictor initialized with {self._count_parameters()/1e6:.1f}M parameters")

    def _count_parameters(self) -> int:
        """Count total trainable parameters"""
        return sum(p.numel() for p in self.encoder.parameters()) + \
               sum(p.numel() for p in self.decoder.parameters())

    def _build_graph_from_endpoints(self, endpoints: List[Dict]) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
        """
        Build PyTorch Geometric graph from discovered endpoints

        Args:
            endpoints: List of endpoint dicts with 'url', 'method', 'dependencies'

        Returns:
            node_features: [num_nodes, feature_dim]
            edge_index: [2, num_edges]
            node_to_endpoint: Mapping from node index to endpoint
        """
        num_endpoints = len(endpoints)

        # Create node features (one-hot encoding for methods + URL embedding)
        method_encoding = {
            'GET': [1, 0, 0, 0, 0],
            'POST': [0, 1, 0, 0, 0],
            'PUT': [0, 0, 1, 0, 0],
            'DELETE': [0, 0, 0, 1, 0],
            'PATCH': [0, 0, 0, 0, 1]
        }

        node_features = []
        node_to_endpoint = {}

        for idx, endpoint in enumerate(endpoints):
            method = endpoint.get('method', 'GET')
            url = endpoint.get('url', '')

            # Method encoding (5 dims)
            method_vec = method_encoding.get(method, [0, 0, 0, 0, 0])

            # URL features (simple: length, has params, has id pattern)
            url_features = [
                len(url) / 100.0,  # Normalized length
                1.0 if '{' in url or ':' in url else 0.0,  # Has path params
                1.0 if 'auth' in url.lower() else 0.0,  # Is auth endpoint
                1.0 if 'health' in url.lower() else 0.0,  # Is health endpoint
            ]

            # Combine features (pad to 128 dims)
            feature_vec = method_vec + url_features
            feature_vec += [0.0] * (128 - len(feature_vec))

            node_features.append(feature_vec)
            node_to_endpoint[idx] = endpoint

        # Build edges from dependencies
        edge_list = []
        for idx, endpoint in enumerate(endpoints):
            dependencies = endpoint.get('dependencies', [])
            for dep_url in dependencies:
                # Find dependency node
                for dep_idx, dep_endpoint in enumerate(endpoints):
                    if dep_endpoint['url'] == dep_url:
                        edge_list.append([dep_idx, idx])  # dep -> current

        # Add reverse edges for bidirectional message passing
        reverse_edges = [[dst, src] for src, dst in edge_list]
        edge_list.extend(reverse_edges)

        # Convert to tensors
        node_features = torch.tensor(node_features, dtype=torch.float32)
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous() if edge_list else torch.empty((2, 0), dtype=torch.long)

        return node_features, edge_index, node_to_endpoint

    def predict_workflow(
        self,
        endpoints: List[Dict],
        goal: str,
        max_steps: int = 10
    ) -> Dict:
        """
        Predict optimal workflow sequence for achieving a goal

        Args:
            endpoints: List of discovered API endpoints
            goal: User's goal (e.g., "Create and update user")
            max_steps: Maximum workflow steps

        Returns:
            Dict with 'workflow' (list of endpoints) and 'confidence' (float)
        """
        if not endpoints:
            return {
                'workflow': [],
                'confidence': 0.0,
                'error': 'No endpoints provided'
            }

        logger.info(f"Predicting workflow for goal: {goal}")
        logger.info(f"Available endpoints: {len(endpoints)}")

        # Build graph
        node_features, edge_index, node_to_endpoint = self._build_graph_from_endpoints(endpoints)
        node_features = node_features.to(self.device)
        edge_index = edge_index.to(self.device)

        # Encode graph
        self.encoder.eval()
        self.decoder.eval()

        with torch.no_grad():
            # Get node embeddings
            node_embeddings = self.encoder(node_features, edge_index)

            # Decode workflow sequence
            predicted_indices = self.decoder(node_embeddings, sequence_length=min(max_steps, len(endpoints)))

        # Convert indices to workflow
        workflow = []
        seen_indices = set()

        for idx in predicted_indices:
            if idx in node_to_endpoint and idx not in seen_indices:
                endpoint = node_to_endpoint[idx]
                workflow.append({
                    'endpoint': endpoint['url'],
                    'method': endpoint['method'],
                    'order': len(workflow) + 1
                })
                seen_indices.add(idx)

        # Calculate confidence (placeholder - should be based on model's actual confidence)
        confidence = 0.7 if len(workflow) > 0 else 0.0

        return {
            'workflow': workflow,
            'confidence': confidence,
            'goal': goal,
            'steps': len(workflow)
        }

    def learn_from_execution(self, execution_trace: Dict):
        """
        Learn from successful workflow execution

        Args:
            execution_trace: Dict with 'workflow', 'success', 'goal'
        """
        # TODO: Implement online learning
        # Store successful patterns in a buffer
        # Periodically retrain model
        logger.info(f"Learning from execution (success={execution_trace.get('success')})")
        pass

    def train(self, training_data: List[Dict], epochs: int = 50, lr: float = 0.001):
        """
        Train the workflow predictor

        Args:
            training_data: List of dicts with 'endpoints', 'goal', 'correct_workflow'
            epochs: Number of training epochs
            lr: Learning rate
        """
        # Combine encoder and decoder parameters
        parameters = list(self.encoder.parameters()) + list(self.decoder.parameters())
        optimizer = torch.optim.Adam(parameters, lr=lr)
        criterion = nn.CrossEntropyLoss()

        logger.info(f"Training workflow predictor for {epochs} epochs...")

        for epoch in range(epochs):
            total_loss = 0.0

            for example in training_data:
                endpoints = example['endpoints']
                correct_workflow = example['correct_workflow']  # List of node indices

                # Build graph
                node_features, edge_index, node_to_endpoint = self._build_graph_from_endpoints(endpoints)
                node_features = node_features.to(self.device)
                edge_index = edge_index.to(self.device)

                # Forward pass
                self.encoder.train()
                self.decoder.train()

                node_embeddings = self.encoder(node_features, edge_index)
                predicted_sequence = self.decoder(node_embeddings, sequence_length=len(correct_workflow))

                # Compute loss (sequence-level)
                # TODO: Implement proper sequence loss
                # For now, use placeholder
                loss = torch.tensor(0.0, requires_grad=True).to(self.device)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            avg_loss = total_loss / len(training_data) if training_data else 0.0

            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")

        logger.info("Training complete!")

    def save(self, path: str):
        """Save model checkpoint"""
        torch.save({
            'encoder': self.encoder.state_dict(),
            'decoder': self.decoder.state_dict()
        }, path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.encoder.load_state_dict(checkpoint['encoder'])
        self.decoder.load_state_dict(checkpoint['decoder'])
        logger.info(f"Model loaded from {path}")


# Factory function for easy instantiation
def create_workflow_predictor(node_features: int = 128, hidden_dim: int = 256) -> WorkflowPredictor:
    """
    Create and return a WorkflowPredictor instance

    Args:
        node_features: Dimension of node features
        hidden_dim: Hidden dimension for GNN and LSTM

    Returns:
        WorkflowPredictor instance
    """
    return WorkflowPredictor(node_features=node_features, hidden_dim=hidden_dim)
