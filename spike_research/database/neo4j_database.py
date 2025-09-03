import logging
import os
from typing import Any, Optional

import pandas as pd

# Environment configuration
from dotenv import load_dotenv
from neo4j import GraphDatabase as Neo4jDriver
from neo4j.exceptions import AuthError, ServiceUnavailable

from ..core.models import (
    Company,
    Employee,
    Fund,
    Investment,
    TransitionEvent,
)


load_dotenv(override=True)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

logger = logging.getLogger(__name__)


class VCGraphDatabase:
    """Simplified Neo4j database interface for VC research platform"""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        """Initialize Neo4j connection"""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._connect()

    def _connect(self) -> bool:
        """Establish database connection"""
        try:
            self.driver = Neo4jDriver.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return True
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
            return False

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def execute_query(
        self, query: str, params: dict[str, Any] = None
    ) -> list[dict[str, Any]]:
        """Execute Cypher query and return results"""
        if not self.driver:
            logger.error("No active database connection")
            return []

        with self.driver.session() as session:
            try:
                result = session.run(query, params or {})
                return [record.data() for record in result]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                return []

    def setup_constraints(self):
        """Create database constraints and indexes"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Employee) REQUIRE e.profile_urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Fund) REQUIRE f.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (e:Employee) ON (e.first_name, e.last_name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Transition) ON (t.transition_date)",
        ]

        for constraint in constraints:
            self.execute_query(constraint)
        logger.info("Database constraints and indexes created")

    # ─── Core Entity Storage ──────────────────────────────────────────────

    def store_employee(self, employee: Employee):
        """Store employee profile"""
        query = """
        MERGE (e:Employee {profile_urn: $profile_urn})
        SET e.profile_id = $profile_id,
            e.first_name = $first_name,
            e.last_name = $last_name,
            e.headline = $headline,
            e.industry_name = $industry_name,
            e.location_name = $location_name,
            e.updated_at = datetime()
        """
        self.execute_query(query, employee.model_dump())

    def store_company(self, company: Company):
        """Store company entity"""
        query = """
        MERGE (c:Company {urn: $urn})
        SET c.name = $name,
            c.industries = $industries,
            c.funding_stage = $funding_stage,
            c.valuation = $valuation,
            c.exit_status = $exit_status,
            c.founded_year = $founded_year,
            c.updated_at = datetime()
        """
        self.execute_query(query, company.model_dump())

    def store_fund(self, fund: Fund):
        """Store fund entity"""
        query = """
        MERGE (f:Fund {id: $id})
        SET f.name = $name,
            f.aum = $aum,
            f.vintage = $vintage,
            f.focus_areas = $focus_areas,
            f.stage_focus = $stage_focus,
            f.status = $status,
            f.updated_at = datetime()
        """
        self.execute_query(query, fund.model_dump())

    def store_transition(self, transition: TransitionEvent):
        """Store career transition event"""
        query = """
        MATCH (from_company:Company {urn: $from_company_urn})
        MATCH (to_company:Company {urn: $to_company_urn})
        MATCH (employee:Employee {profile_urn: $profile_urn})

        CREATE (t:Transition {
            profile_urn: $profile_urn,
            transition_date: datetime($transition_date),
            transition_type: $transition_type,
            old_title: $old_title,
            new_title: $new_title,
            tenure_days: $tenure_days,
            seniority_change: $seniority_change
        })

        CREATE (employee)-[:HAS_TRANSITION]->(t)
        CREATE (t)-[:FROM_COMPANY]->(from_company)
        CREATE (t)-[:TO_COMPANY]->(to_company)
        """
        self.execute_query(query, transition.model_dump())

    def store_investment(self, investment: Investment):
        """Store investment relationship"""
        query = """
        MATCH (fund:Fund {id: $fund_id})
        MATCH (company:Company {urn: $company_id})

        CREATE (inv:Investment {
            id: $id,
            amount: $amount,
            round_type: $round_type,
            date: datetime($date),
            valuation_pre: $valuation_pre,
            valuation_post: $valuation_post,
            ownership_percentage: $ownership_percentage
        })

        CREATE (fund)-[:MADE_INVESTMENT]->(inv)-[:INVESTED_IN]->(company)
        """
        self.execute_query(query, investment.model_dump())

    # ─── Graph Analysis Methods ──────────────────────────────────────────

    def create_talent_flow_projection(
        self, graph_name: str = "talent_flow", delete_existing: bool = False
    ):
        """Create Employee-Company bipartite graph projection for analysis"""
        if delete_existing:
            self.execute_query(
                "CALL gds.graph.drop($name, false)", {"name": graph_name}
            )

        query = """
        CALL gds.graph.project.cypher(
            $name,
            'MATCH (e:Employee) RETURN id(e) AS id, ["Employee"] AS labels
             UNION
             MATCH (c:Company) RETURN id(c) AS id, ["Company"] AS labels',
            'MATCH (e:Employee)-[:HAS_TRANSITION]->(:Transition)-[:FROM_COMPANY|TO_COMPANY]->(c:Company)
             RETURN id(e) AS source, id(c) AS target, count(*) AS weight'
        )
        """
        self.execute_query(query, {"name": graph_name})
        logger.info(f"Created talent flow projection: {graph_name}")

    def run_pagerank(
        self, graph_name: str = "talent_flow", write_property: Optional[str] = None
    ) -> pd.DataFrame:
        """Run PageRank algorithm on talent flow graph"""
        mode = "write" if write_property else "stream"
        config = {"dampingFactor": 0.85, "maxIterations": 20}

        if write_property:
            config["writeProperty"] = write_property

        query = f"CALL gds.pageRank.{mode}($graph, $config)"
        if mode == "stream":
            query += " YIELD nodeId, score"

        results = self.execute_query(query, {"graph": graph_name, "config": config})

        if mode == "stream":
            node_ids = [r["nodeId"] for r in results]
            scores = [r["score"] for r in results]
            return self._attach_node_names(node_ids, scores, "pagerank_score")

        return pd.DataFrame()

    def get_talent_flow_metrics(self, company_urn: str) -> dict[str, Any]:
        """Get talent flow statistics for a company"""
        query = """
        MATCH (c:Company {urn: $company_urn})
        OPTIONAL MATCH (c)<-[:TO_COMPANY]-(:Transition)<-[:HAS_TRANSITION]-(incoming:Employee)
        OPTIONAL MATCH (c)<-[:FROM_COMPANY]-(:Transition)<-[:HAS_TRANSITION]-(outgoing:Employee)

        WITH c, count(DISTINCT incoming) as talent_inflow, count(DISTINCT outgoing) as talent_outflow

        RETURN c.name as company_name,
               talent_inflow,
               talent_outflow,
               (talent_inflow - talent_outflow) as net_talent_flow,
               CASE WHEN talent_outflow > 0 THEN toFloat(talent_inflow) / talent_outflow ELSE null END as talent_ratio
        """
        result = self.execute_query(query, {"company_urn": company_urn})
        return result[0] if result else {}

    def get_company_investment_profile(self, company_urn: str) -> dict[str, Any]:
        """Get investment information for a company"""
        query = """
        MATCH (c:Company {urn: $company_urn})
        OPTIONAL MATCH (c)<-[:INVESTED_IN]-(inv:Investment)<-[:MADE_INVESTMENT]-(f:Fund)

        WITH c, collect({
            fund_name: f.name,
            amount: inv.amount,
            round_type: inv.round_type,
            date: inv.date,
            valuation_post: inv.valuation_post
        }) as investments

        RETURN c.name as company_name,
               c.funding_stage as funding_stage,
               c.valuation as current_valuation,
               c.exit_status as exit_status,
               size(investments) as total_investments,
               investments
        """
        result = self.execute_query(query, {"company_urn": company_urn})
        return result[0] if result else {}

    # ─── Batch Operations ──────────────────────────────────────────────

    def batch_store_employees(self, employees: list[Employee], batch_size: int = 100):
        """Store employees in batches"""
        for i in range(0, len(employees), batch_size):
            batch = employees[i : i + batch_size]
            employee_data = [emp.model_dump() for emp in batch]

            query = """
            UNWIND $employees as emp
            MERGE (e:Employee {profile_urn: emp.profile_urn})
            SET e += emp, e.updated_at = datetime()
            """
            self.execute_query(query, {"employees": employee_data})
            logger.info(f"Stored {len(batch)} employees")

    def batch_store_transitions(
        self, transitions: list[TransitionEvent], batch_size: int = 100
    ):
        """Store transitions in batches"""
        for i in range(0, len(transitions), batch_size):
            batch = transitions[i : i + batch_size]
            transition_data = [t.model_dump() for t in batch]

            # First ensure companies exist
            self._ensure_companies_exist(transition_data)

            # Then create transitions
            query = """
            UNWIND $transitions as trans
            MATCH (from_company:Company {urn: trans.from_company_urn})
            MATCH (to_company:Company {urn: trans.to_company_urn})
            MATCH (employee:Employee {profile_urn: trans.profile_urn})

            CREATE (t:Transition)
            SET t += trans, t.transition_date = datetime(trans.transition_date)

            CREATE (employee)-[:HAS_TRANSITION]->(t)
            CREATE (t)-[:FROM_COMPANY]->(from_company)
            CREATE (t)-[:TO_COMPANY]->(to_company)
            """
            self.execute_query(query, {"transitions": transition_data})
            logger.info(f"Stored {len(batch)} transitions")

    # ─── Utility Methods ──────────────────────────────────────────────

    def _attach_node_names(
        self, node_ids: list[int], scores: list[float], score_col: str
    ) -> pd.DataFrame:
        """Attach human-readable names to node IDs"""
        name_map = {}
        if node_ids:
            query = """
            MATCH (n) WHERE id(n) IN $ids
            RETURN id(n) as id,
                   CASE
                     WHEN labels(n)[0] = 'Employee' THEN n.first_name + ' ' + n.last_name
                     WHEN labels(n)[0] = 'Company' THEN n.name
                     ELSE toString(id(n))
                   END as name,
                   labels(n)[0] as type
            """
            results = self.execute_query(query, {"ids": node_ids})
            name_map = {
                r["id"]: {"name": r["name"], "type": r["type"]} for r in results
            }

        df = pd.DataFrame(
            {
                "node_id": node_ids,
                score_col: scores,
                "name": [
                    name_map.get(nid, {}).get("name", f"Node_{nid}") for nid in node_ids
                ],
                "type": [
                    name_map.get(nid, {}).get("type", "Unknown") for nid in node_ids
                ],
            }
        )
        return df.sort_values(score_col, ascending=False)

    def _ensure_companies_exist(self, transition_data: list[dict]):
        """Ensure all companies referenced in transitions exist"""
        company_urns = set()
        for t in transition_data:
            if t.get("from_company_urn"):
                company_urns.add(t["from_company_urn"])
            if t.get("to_company_urn"):
                company_urns.add(t["to_company_urn"])

        if company_urns:
            query = """
            UNWIND $urns as urn
            MERGE (c:Company {urn: urn})
            ON CREATE SET c.name = urn, c.created_at = datetime()
            """
            self.execute_query(query, {"urns": list(company_urns)})

    def clear_database(self):
        """Clear all data (use with caution!)"""
        self.execute_query("MATCH (n) DETACH DELETE n")
        logger.warning("Database cleared - all data deleted")


# ─── Standalone Functions ──────────────────────────────────────────────


def create_database_connection() -> VCGraphDatabase:
    """Factory function to create database connection"""
    return VCGraphDatabase()


def query_database(query: str, params: dict[str, Any] = None) -> list[dict[str, Any]]:
    """Execute a standalone query"""
    db = create_database_connection()
    try:
        return db.execute_query(query, params)
    finally:
        db.close()
