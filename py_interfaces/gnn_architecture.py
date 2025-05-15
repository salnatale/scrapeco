import os
import torch
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, GCNConv, Linear
from neo4j import GraphDatabase
from typing import Dict, Any, List

# Configuration for feature selection (MVP allowances)
ALLOWED_COMPANY_FEATURES = [
    'age_years',       # computed from founding date
    'employee_count',  # if available
]
ALLOWED_PROFILE_FEATURES = [
    'years_experience',  # derived from experience dates
    'education_tier',    # numeric encoding of school prestige
    'num_past_companies',# count of distinct past employers
]

class GNNInfrastructure:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_pass: str, hidden_dim: int = 64):
        # Connect to Neo4j
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
        self.hidden_dim = hidden_dim
        # Placeholder for PyG model
        self.model = None

    def close(self):
        self.driver.close()

    def fetch_graph(self, snapshot_date: str) -> HeteroData:
        """
        Query Neo4j to build a PyTorch Geometric HeteroData object.
        Only include features listed in ALLOWED_*_FEATURES.
        """
        data = HeteroData()
        with self.driver.session() as session:
            # 1) Fetch company nodes and features
            comp_query = '''
            MATCH (c:Company)
             WHERE c.foundingDate <= date($snapshot)  // snapshot filter
             RETURN id(c) AS nid,
                    duration.inMonths(c.foundingDate, date($snapshot)).years AS age_years,
                    c.fundingStage AS funding_stage,
                    coalesce(c.employeeCount, 0) AS employee_count
            '''
            comp_records = session.run(comp_query, {'snapshot': snapshot_date})
            comp_ids, comp_feats = [], []
            for r in comp_records:
                comp_ids.append(r['nid'])
                comp_feats.append([r[f] for f in ALLOWED_COMPANY_FEATURES])
            data['Company'].x = torch.tensor(comp_feats, dtype=torch.float)
            data['Company'].node_id = torch.tensor(comp_ids, dtype=torch.long)

            # 2) Fetch profile nodes and features
            prof_query = '''
            MATCH (p:Profile)
             WHERE p.createdAt <= date($snapshot)
             RETURN id(p) AS nid,
                    duration.inMonths(apoc.date.parse(p.firstJobDate,'ms'), date($snapshot)).years AS years_experience,
                    p.educationTier AS education_tier,
                    size(apoc.coll.toSet([e IN (p)-[:HAS_EXPERIENCE]->() | e])) AS num_past_companies
            '''
            prof_records = session.run(prof_query, {'snapshot': snapshot_date})
            prof_ids, prof_feats = [], []
            for r in prof_records:
                prof_ids.append(r['nid'])
                prof_feats.append([r[f] for f in ALLOWED_PROFILE_FEATURES])
            data['Profile'].x = torch.tensor(prof_feats, dtype=torch.float)
            data['Profile'].node_id = torch.tensor(prof_ids, dtype=torch.long)

            # 3) Fetch edges (HAS_EXPERIENCE, ATTENDED, TRANSITIONS)
            # Example: Profile-[:HAS_EXPERIENCE]->JobExperience->[:AT_COMPANY]->Company
            # Collapse into direct edges Profile->Company
            edge_query = '''
            MATCH (p:Profile)-[:HAS_EXPERIENCE]->(:JobExperience)-[:AT_COMPANY]->(c:Company)
             WHERE p.createdAt <= date($snapshot) AND c.foundingDate <= date($snapshot)
             RETURN id(p) AS pid, id(c) AS cid
            '''
            edges = session.run(edge_query, {'snapshot': snapshot_date})
            p_ids, c_ids = [], []
            for r in edges:
                p_ids.append(r['pid'])
                c_ids.append(r['cid'])
            # Map node_id back to index
            pid_idx = {nid:idx for idx,nid in enumerate(prof_ids)}
            cid_idx = {nid:idx for idx,nid in enumerate(comp_ids)}
            edge_index = torch.tensor([[pid_idx[x] for x in p_ids], [cid_idx[x] for x in c_ids]], dtype=torch.long)
            data['Profile', 'works_at', 'Company'].edge_index = edge_index

        return data

    def define_model(self, data: HeteroData) -> torch.nn.Module:
        """
        Build a simple 2-layer R-GCN-like model over heterogeneous graph.
        """
        conv1 = HeteroConv({
            ('Profile', 'works_at', 'Company'): GCNConv(self.hidden_dim, self.hidden_dim),
            ('Company', 'rev_works_at', 'Profile'): GCNConv(self.hidden_dim, self.hidden_dim)
        }, aggr='sum')
        conv2 = HeteroConv({
            ('Profile', 'works_at', 'Company'): GCNConv(self.hidden_dim, self.hidden_dim),
            ('Company', 'rev_works_at', 'Profile'): GCNConv(self.hidden_dim, self.hidden_dim)
        }, aggr='sum')
        # Final prediction MLP for Company nodes
        lin = Linear(self.hidden_dim, 1)

        class RGCNModel(torch.nn.Module):
            def __init__(self, conv1, conv2, lin):
                super().__init__()
                self.conv1 = conv1
                self.conv2 = conv2
                self.lin = lin

            def forward(self, x_dict, edge_index_dict):
                x_dict = self.conv1(x_dict, edge_index_dict)
                x_dict = {k: x.relu() for k, x in x_dict.items()}
                x_dict = self.conv2(x_dict, edge_index_dict)
                # Predict on Company nodes
                out = self.lin(x_dict['Company'])
                return out.squeeze()

        model = RGCNModel(conv1, conv2, lin)
        self.model = model
        return model

    def train(self, data: HeteroData, train_idx: List[int], labels: torch.Tensor, epochs: int = 50):
        """
        Training loop for binary classification of Company nodes.
        """
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01, weight_decay=5e-4)
        criterion = torch.nn.BCEWithLogitsLoss()
        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            out = self.model(data.x_dict, data.edge_index_dict)
            loss = criterion(out[train_idx], labels[train_idx].float())
            loss.backward()
            optimizer.step()
            print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

    def predict(self, data: HeteroData) -> torch.Tensor:
        """
        Run inference on all Company nodes, returning probability scores.
        """
        self.model.eval()
        with torch.no_grad():
            logits = self.model(data.x_dict, data.edge_index_dict)
            return torch.sigmoid(logits)

# Example usage:
# infra = GNNInfrastructure(os.getenv('NEO4J_URI'), os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
# data = infra.fetch_graph('2023-12-31')
# model = infra.define_model(data)
# infra.train(data, train_idx, train_labels)
# scores = infra.predict(data)
