import os
from typing import List, Dict, Any, Optional, Union, Literal
from datetime import datetime
import json

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# Import existing models
from models import (
    LinkedInProfile,
    LinkedInCompany,
    Experience,
    Company,
    TimePeriod,
    Location,
    School,
    Education,
    Skill,
    TransitionEvent,
)

# imports for pagerank
import numpy as np
import pandas as pd
from scipy import sparse

# Load environment variables
from dotenv import load_dotenv

load_dotenv(override=True)

# Neo4j connection settings
# TODO: Set up neo4j database outside of the code
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")


# TODO: GO through and test the Neo4jDatabase and Neo4jProfileAnalyzer queries on
class Neo4jDatabase:
    """
    Handles interactions with Neo4j graph database for LinkedIn profile data.
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        """
        Initialize the Neo4j database connection.

        Args:
            uri: Neo4j database URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.connect()

    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # Verify connection
            self.driver.verify_connectivity()
            print(f"Successfully connected to Neo4j database at {self.uri}")
            return True
        except (ServiceUnavailable, AuthError) as e:
            print(f"Failed to connect to Neo4j database: {e}")
            self.driver = None
            return False

    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")

    def _run_query(
        self, query: str, params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Run a Cypher query on the Neo4j database.

        Args:
            query: Cypher query string
            params: Query parameters

        Returns:
            List of query results as dictionaries
        """
        if not self.driver:
            print("No active connection to Neo4j database")
            return []

        with self.driver.session() as session:
            try:
                result = session.run(query, params or {})
                return [record.data() for record in result]
            except Exception as e:
                print(f"Error executing Neo4j query: {e}")
                print(f"Query: {query}")
                print(f"Params: {params}")
                return []

    # ─────────── Bipartite pagerank helpers ──────────────────────────

    def create_emp_company_projection(
        self,
        graph_name: str = "empCompany",
        weight_scheme: Literal["count", "binary"] = "count",
        delete_existing: bool = False,
    ) -> None:
        """
        Build (or rebuild) a *collapsed* Employee ↔ Company projection in Neo4j GDS.
        It flattens (Employee)-[:HAS_TRANSITION]->(:Transition)-[:FROM|TO]->(Company)
        into one weighted edge Employee‑[:WORKED_AT]->Company.
        """
        rel_weight = "count(*)" if weight_scheme == "count" else "1"
        if delete_existing:
            self._run_query("CALL gds.graph.drop($name, false)", {"name": graph_name})

        query = f"""
        CALL gds.graph.project.cypher(
          $name,
          // -------- nodes --------
          'MATCH (p:Profile) RETURN id(p) AS id, ["Profile"] AS labels
           UNION
           MATCH (c:Company)  RETURN id(c) AS id, ["Company"]  AS labels',
          // -------- relationships (collapse Transition) --------
          'MATCH (p:Profile)-[:HAS_TRANSITION]->(:Transition)
                -[:FROM_COMPANY|TO_COMPANY]->(c:Company)
           WITH id(p) AS source, id(c) AS target, {rel_weight} AS weight
           RETURN source, target, weight'
        )
        """
        self._run_query(query, {"name": graph_name})
        print(f"Projection '{graph_name}' created (weight_scheme={weight_scheme})")

    # ---------------------------------------------------------------------

    def pagerank_emp_company(
        self,
        graph_name: str = "empCompany",
        damping: float = 0.85,
        iterations: int = 20,
        write_property: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Run **native GDS PageRank** on the collapsed Employee–Company graph.
        Returns a DataFrame (nodeId, name, pagerank) when streaming.
        """
        mode = "write" if write_property else "stream"
        config = {"dampingFactor": damping, "maxIterations": iterations}
        if write_property:
            config["writeProperty"] = write_property
        call = f"CALL gds.pageRank.{mode}($graph, $config) " + (
            "YIELD nodeId, score" if mode == "stream" else ""
        )
        res = self._run_query(call, {"graph": graph_name, "config": config})
        if mode == "stream":
            node_ids = [r["nodeId"] for r in res]
            scores = [r["score"] for r in res]
            return self._attach_names(node_ids, scores, "pagerank")
        return pd.DataFrame()

    # ---------------------------------------------------------------------

    def birank_emp_company(
        self,
        graph_name: str = "empCompany",
        alpha: float = 0.85,
        beta: float = 0.85,
        max_iter: int = 20,
        tol: float = 1e-6,
        write_prefix: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        **BiRank** (degree‑balanced) on the same projection, implemented in NumPy/SciPy.
        Returns a DataFrame (nodeId, score, label) and can write scores back as
        <prefix>_emp / <prefix>_comp.
        """
        # 1. fetch edges
        edges = self._run_query(
            "CALL gds.graph.relationships.stream($g) "
            "YIELD sourceNodeId AS s, targetNodeId AS t "
            "RETURN s, t",
            {"g": graph_name},
        )
        if not edges:
            raise RuntimeError(f"Graph '{graph_name}' has no relationships")

        emp_ids = {
            r["id"] for r in self._run_query("MATCH (p:Profile) RETURN id(p) AS id")
        }
        comp_ids = {
            r["id"] for r in self._run_query("MATCH (c:Company)  RETURN id(c) AS id")
        }
        ei, ci = {nid: i for i, nid in enumerate(emp_ids)}, {
            nid: j for j, nid in enumerate(comp_ids)
        }
        m, n = len(emp_ids), len(comp_ids)

        rows, cols, data = [], [], []
        for r in edges:
            (
                s,
                t,
            ) = (
                r["s"],
                r["t"],
            )
            if s in ei and t in ci:
                rows.append(ei[s])
                cols.append(ci[t])
                data.append(1.0)
            elif t in ei and s in ci:
                rows.append(ei[t])
                cols.append(ci[s])
                data.append(1.0)
        W = sparse.coo_matrix((data, (rows, cols)), shape=(m, n)).tocsr()

        Du = np.array(W.sum(axis=1)).ravel()
        Dp = np.array(W.sum(axis=0)).ravel()
        Su = np.power(Du, -0.5, where=Du > 0)
        Sp = np.power(Dp, -0.5, where=Dp > 0)
        S = W.multiply(Su[:, None]).multiply(Sp)

        u = np.full(m, 1 / m)
        p = np.full(n, 1 / n)
        u0, p0 = u.copy(), p.copy()
        for _ in range(max_iter):
            p_next = alpha * (S.T @ u) + (1 - alpha) * p0
            u_next = beta * (S @ p_next) + (1 - beta) * u0
            if max(np.abs(p_next - p).max(), np.abs(u_next - u).max()) < tol:
                break
            p, u = p_next, u_next

        emp_df = pd.DataFrame({"nodeId": list(emp_ids), "score": u, "label": "Profile"})
        comp_df = pd.DataFrame(
            {"nodeId": list(comp_ids), "score": p, "label": "Company"}
        )
        df = pd.concat([emp_df, comp_df], ignore_index=True)

        if write_prefix:
            self._write_scores(df, write_prefix)
        return df

    # ---------------------------------------------------------------------
    # small helpers -------------------------------------------------------

    def _attach_names(self, node_ids, scores, col):
        name_map = {
            r["id"]: r["name"]
            for r in self._run_query(
                "MATCH (n) WHERE id(n) IN $ids "
                "RETURN id(n) AS id, coalesce(n.name, toString(id(n))) AS name",
                {"ids": node_ids},
            )
        }
        df = pd.DataFrame({"nodeId": node_ids, col: scores})
        df["name"] = df["nodeId"].map(name_map)
        return df[["nodeId", "name", col]]

    def _write_scores(self, df, prefix):
        emp_prop, comp_prop = f"{prefix}_prof", f"{prefix}_comp"
        emp_rows = df[df.label == "Profile"][["nodeId", "score"]].to_dict("records")
        comp_rows = df[df.label == "Company"][["nodeId", "score"]].to_dict("records")
        self._run_query(
            f"UNWIND $rows AS r MATCH (n) WHERE id(n)=r.nodeId SET n.{emp_prop}=r.score",
            {"rows": emp_rows},
        )
        self._run_query(
            f"UNWIND $rows AS r MATCH (n) WHERE id(n)=r.nodeId SET n.{comp_prop}=r.score",
            {"rows": comp_rows},
        )
        print(f"BiRank scores written ({emp_prop}/{comp_prop})")

    # end pagerank helpers ───────────────────────────────────────────────────────────────────

    def setup_constraints(self):
        """Set up necessary constraints and indexes for performance."""

        # Create constraints to ensure uniqueness where needed
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Profile) REQUIRE p.urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:School) REQUIRE s.urn IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Profile) ON (p.profileId)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Profile) ON (p.firstName, p.lastName)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Experience) ON (e.title)",
        ]

        for constraint in constraints:
            self._run_query(constraint)

        print("Neo4j constraints and indexes created successfully")

    def store_profile(self, profile: LinkedInProfile):
        """
        Store a LinkedIn profile in the Neo4j database.

        Args:
            profile: LinkedInProfile model instance
        """
        # Convert Pydantic model to dict if necessary
        profile_data = (
            profile.model_dump() if hasattr(profile, "model_dump") else profile
        )

        # Create Profile node
        create_profile_query = """
        MERGE (p:Profile {urn: $urn})
        ON CREATE SET 
            p.profileId = $profileId,
            p.firstName = $firstName,
            p.lastName = $lastName,
            p.headline = $headline,
            p.summary = $summary,
            p.locationName = $locationName,
            p.industryName = $industryName,
            p.publicId = $publicId,
            p.createdAt = datetime()
        ON MATCH SET
            p.firstName = $firstName,
            p.lastName = $lastName,
            p.headline = $headline,
            p.summary = $summary,
            p.locationName = $locationName,
            p.industryName = $industryName,
            p.updatedAt = datetime()
        RETURN p
        """

        self._run_query(
            create_profile_query,
            {
                "urn": profile_data["profile_urn"],
                "profileId": profile_data["profile_id"],
                "firstName": profile_data["first_name"],
                "lastName": profile_data["last_name"],
                "headline": profile_data.get("headline"),
                "summary": profile_data.get("summary"),
                "locationName": profile_data.get("location_name"),
                "industryName": profile_data.get("industry_name"),
                "publicId": profile_data.get("public_id"),
            },
        )

        # helper methods to process specific profile data

        # Process skills
        if "skills" in profile_data and profile_data["skills"]:
            self.store_skills(profile_data["profile_urn"], profile_data["skills"])

        # Process education
        if "education" in profile_data and profile_data["education"]:
            for edu in profile_data["education"]:
                self.store_education(profile_data["profile_urn"], edu)

        # Process experience
        if "experience" in profile_data and profile_data["experience"]:
            for exp in profile_data["experience"]:
                self.store_experience(profile_data["profile_urn"], exp)

    def store_skills(self, profile_urn: str, skills: List[Dict[str, str]]):
        """
        Store skills for a profile and create relationships.

        Args:
            profile_urn: Profile URN
            skills: List of skill dictionaries
        """
        for skill in skills:
            skill_query = """
            MATCH (p:Profile {urn: $profileUrn})
            MERGE (s:Skill {name: $skillName})
            MERGE (p)-[r:HAS_SKILL]->(s)
            RETURN s
            """

            self._run_query(
                skill_query, {"profileUrn": profile_urn, "skillName": skill["name"]}
            )

    def store_education(self, profile_urn: str, education: Dict[str, Any]):
        """
        Store education information and create school relationships.

        Args:
            profile_urn: Profile URN
            education: Education dictionary
        """
        # Extract data
        school = education["school"]
        school_urn = (
            school.get("urn")
            or f"urn:li:school:{school['name'].replace(' ', '').lower()}"
        )

        # Create School node
        school_query = """
        MERGE (s:School {urn: $schoolUrn})
        ON CREATE SET
            s.name = $schoolName,
            s.active = $active
        ON MATCH SET
            s.name = $schoolName,
            s.active = $active
        
        WITH s
        
        MATCH (p:Profile {urn: $profileUrn})
        MERGE (p)-[r:ATTENDED]->(s)
        ON CREATE SET
            r.degreeName = $degreeName,
            r.fieldOfStudy = $fieldOfStudy,
            r.startYear = $startYear,
            r.startMonth = $startMonth,
            r.endYear = $endYear,
            r.endMonth = $endMonth
        
        RETURN s, r, p
        """

        time_period = education["time_period"]
        start_date = time_period.get("start_date", {}) or {}
        end_date = time_period.get("end_date", {}) or {}

        self._run_query(
            school_query,
            {
                "schoolUrn": school_urn,
                "schoolName": school["name"],
                "active": school.get("active", True),
                "profileUrn": profile_urn,
                "degreeName": education.get("degree_name"),
                "fieldOfStudy": education.get("field_of_study"),
                "startYear": start_date.get("year"),
                "startMonth": start_date.get("month"),
                "endYear": end_date.get("year"),
                "endMonth": end_date.get("month"),
            },
        )

    def store_company(self, company: Union[LinkedInCompany, Dict[str, Any]]):
        """
        Store a company in the Neo4j database.

        Args:
            company: LinkedInCompany model instance or dictionary
        """
        # Convert Pydantic model to dict if necessary
        company_data = (
            company.model_dump() if hasattr(company, "model_dump") else company
        )

        # Create Company node
        company_query = """
        MERGE (c:Company {urn: $urn})
        ON CREATE SET
            c.name = $name,
            c.description = $description,
            c.url = $url,
            c.staffCount = $staffCount,
            c.staffCountRange = $staffCountRange,
            c.createdAt = datetime()
        ON MATCH SET
            c.name = $name,
            c.description = $description,
            c.url = $url,
            c.staffCount = $staffCount,
            c.staffCountRange = $staffCountRange,
            c.updatedAt = datetime()
        RETURN c
        """

        staff_count_range = None
        if "staff_count_range" in company_data and company_data["staff_count_range"]:
            staff_count_range = json.dumps(company_data["staff_count_range"])

        self._run_query(
            company_query,
            {
                "urn": company_data.get("entity_urn")
                or company_data.get("entityUrn")
                or company_data.get("urn"),
                "name": company_data.get("name"),
                "description": company_data.get("description", ""),
                "url": company_data.get("url", ""),
                "staffCount": company_data.get("staff_count")
                or company_data.get("staffCount")
                or 0,
                "staffCountRange": staff_count_range,
            },
        )

        # Add industry relationships
        if "company_industries" in company_data and company_data["company_industries"]:
            for industry in company_data["company_industries"]:
                industry_query = """
                MATCH (c:Company {urn: $companyUrn})
                MERGE (i:Industry {name: $industryName.localized_name})
                MERGE (c)-[r:IN_INDUSTRY]->(i)
                RETURN i
                """

                self._run_query(
                    industry_query,
                    {
                        "companyUrn": company_data.get("entity_urn")
                        or company_data.get("entityUrn")
                        or company_data.get("urn"),
                        "industryName": industry.get("localizedName") or industry,
                    },
                )

    def store_experience(self, profile_urn: str, experience: Dict[str, Any]):
        """
        Store work experience and create company relationships.

        Args:
            profile_urn: Profile URN
            experience: Experience dictionary
        """
        # Extract and store company data first
        company_data = experience["company"]
        company_urn = (
            company_data.get("urn")
            or company_data.get("companyUrn")
            or f"urn:li:company:{company_data['name'].replace(' ', '').lower()}"
        )

        # Store company if needed
        company_query = """
        MERGE (c:Company {urn: $companyUrn})
        ON CREATE SET
            c.name = $companyName,
            c.createdAt = datetime()
        RETURN c
        """

        self._run_query(
            company_query,
            {
                "companyUrn": company_urn,
                "companyName": company_data.get("name")
                or company_data.get("companyName"),
            },
        )

        # Extract date information
        time_period = experience["time_period"]
        start_date = time_period.get("start_date", {}) or {}
        end_date = time_period.get("end_date", {}) or {}
        is_current = not end_date or not (
            end_date.get("year") and end_date.get("month")
        )

        # Create unique ID for experience node
        exp_urn = (
            experience.get("entity_urn")
            or experience.get("entityUrn")
            or f"exp-{profile_urn}-{company_urn}-{start_date.get('year')}-{start_date.get('month')}"
        )

        # Store experience with relationships to profile and company
        exp_query = """
        MATCH (p:Profile {urn: $profileUrn})
        MATCH (c:Company {urn: $companyUrn})
        
        MERGE (e:Experience {urn: $expUrn})
        ON CREATE SET
            e.title = $title,
            e.description = $description,
            e.startYear = $startYear,
            e.startMonth = $startMonth,
            e.endYear = $endYear,
            e.endMonth = $endMonth,
            e.isCurrent = $isCurrent,
            e.locationName = $locationName,
            e.createdAt = datetime()
        ON MATCH SET
            e.title = $title,
            e.description = $description,
            e.startYear = $startYear,
            e.startMonth = $startMonth,
            e.endYear = $endYear,
            e.endMonth = $endMonth,
            e.isCurrent = $isCurrent,
            e.locationName = $locationName,
            e.updatedAt = datetime()
        
        MERGE (p)-[r1:HAS_EXPERIENCE]->(e)
        MERGE (e)-[r2:AT_COMPANY]->(c)
        
        RETURN e, p, c
        """

        # Extract location data
        location = experience.get("location", {}) or {}
        location_name = None
        if location:
            location_name = location.get("name") or location.get("locationName")

        self._run_query(
            exp_query,
            {
                "profileUrn": profile_urn,
                "companyUrn": company_urn,
                "expUrn": exp_urn,
                "title": experience["title"],
                "description": experience.get("description", ""),
                "startYear": start_date.get("year"),
                "startMonth": start_date.get("month"),
                "endYear": end_date.get("year"),
                "endMonth": end_date.get("month"),
                "isCurrent": is_current,
                "locationName": location_name,
            },
        )

    def store_transition(self, transition_event: Union[TransitionEvent, dict]):
        """
        Store a job transition event in the Neo4j database.

        Args:
            transition_event: Dictionary containing transition data
        """
        transition_query = """
        MATCH (p:Profile {urn: $profileUrn})
        MATCH (oldCompany:Company {urn: $fromCompanyUrn})
        MATCH (newCompany:Company {urn: $toCompanyUrn})
        
        CREATE (t:Transition {
            date: datetime($transitionDate),
            type: $transitionType,
            oldTitle: $oldTitle,
            newTitle: $newTitle,
            locationChange: $locationChange,
            tenureDays: $tenureDays
        })
        
        CREATE (p)-[:HAS_TRANSITION]->(t)
        CREATE (t)-[:FROM_COMPANY]->(oldCompany)
        CREATE (t)-[:TO_COMPANY]->(newCompany)
        
        RETURN t
        """
        transition_event = (
            transition_event.model_dump()  # if it **is** a model …
            if isinstance(transition_event, TransitionEvent)
            else transition_event
        )

        # Format transition date
        transition_date = transition_event["transition_date"]
        if isinstance(transition_date, str):
            # If it's already a string, ensure it's in ISO format
            if "T" not in transition_date:
                transition_date = f"{transition_date}T00:00:00"
        else:
            # If it's a datetime object, convert to ISO format string
            transition_date = transition_date.isoformat()

        self._run_query(
            transition_query,
            {
                "profileUrn": transition_event["profile_urn"],
                "fromCompanyUrn": transition_event["from_company_urn"],
                "toCompanyUrn": transition_event["to_company_urn"],
                "transitionDate": transition_date,
                "transitionType": transition_event["transition_type"],
                "oldTitle": transition_event["old_title"],
                "newTitle": transition_event["new_title"],
                "locationChange": transition_event["location_change"],
                "tenureDays": transition_event["tenure_days"],
            },
        )

    def batch_store_profiles(self, profiles: List[LinkedInProfile]):
        """
        Complete batch processing solution for storing LinkedIn profiles in Neo4j.
        Added defensive programming to prevent failures when processing bad data.

        Args:
            profiles: List of LinkedInProfile model instances
        """
        # Process profile nodes first
        profile_dicts = []

        # Track errors for logging
        errors = []
        processed_profiles = 0

        for i, profile in enumerate(profiles):
            try:
                # Handle None profiles
                if profile is None:
                    errors.append(f"Profile at index {i} is None, skipping")
                    continue

                profile_data = (
                    profile.model_dump() if hasattr(profile, "model_dump") else profile
                )

                # Handle None profile_data
                if profile_data is None:
                    errors.append(
                        f"Profile data at index {i} is None after model_dump, skipping"
                    )
                    continue

                # Check for required fields
                required_fields = [
                    "profile_urn",
                    "profile_id",
                    "first_name",
                    "last_name",
                ]
                missing_fields = [f for f in required_fields if f not in profile_data]

                if missing_fields:
                    errors.append(
                        f"Profile at index {i} missing required fields: {', '.join(missing_fields)}"
                    )
                    continue

                # All checks passed, add to profile_dicts
                profile_dicts.append(
                    {
                        "urn": profile_data["profile_urn"],
                        "profileId": profile_data["profile_id"],
                        "firstName": profile_data["first_name"],
                        "lastName": profile_data["last_name"],
                        "headline": profile_data.get("headline"),
                        "summary": profile_data.get("summary"),
                        "locationName": profile_data.get("location_name"),
                        "industryName": profile_data.get("industry_name"),
                        "publicId": profile_data.get("public_id"),
                    }
                )
                processed_profiles += 1

            except Exception as e:
                errors.append(f"Error processing profile at index {i}: {str(e)}")
                continue

        # Create all Profile nodes in a single batch operation
        if profile_dicts:
            try:
                create_profiles_query = """
                UNWIND $profiles AS profile
                MERGE (p:Profile {urn: profile.urn})
                ON CREATE SET 
                    p.profileId = profile.profileId,
                    p.firstName = profile.firstName,
                    p.lastName = profile.lastName,
                    p.headline = profile.headline,
                    p.summary = profile.summary,
                    p.locationName = profile.locationName,
                    p.industryName = profile.industryName,
                    p.publicId = profile.publicId,
                    p.createdAt = datetime()
                ON MATCH SET
                    p.firstName = profile.firstName,
                    p.lastName = profile.lastName,
                    p.headline = profile.headline,
                    p.summary = profile.summary,
                    p.locationName = profile.locationName,
                    p.industryName = profile.industryName,
                    p.updatedAt = datetime()
                """
                self._run_query(create_profiles_query, {"profiles": profile_dicts})
            except Exception as e:
                errors.append(f"Error creating profile nodes: {str(e)}")

        # Process skills
        all_skills = []
        # Process education
        all_education = []
        # Process experience and companies
        all_companies = []
        all_experiences = []

        for i, profile in enumerate(profiles):
            try:
                # Handle None profiles
                if profile is None:
                    continue

                profile_data = (
                    profile.model_dump() if hasattr(profile, "model_dump") else profile
                )

                # Handle None profile_data
                if profile_data is None:
                    continue

                # Skip if no profile_urn
                if "profile_urn" not in profile_data:
                    continue

                profile_urn = profile_data["profile_urn"]

                # Collect skills - defensively
                if "skills" in profile_data and profile_data["skills"]:
                    for skill_idx, skill in enumerate(profile_data["skills"]):
                        try:
                            if not isinstance(skill, dict):
                                continue

                            if "name" not in skill:
                                continue

                            all_skills.append(
                                {"profileUrn": profile_urn, "skillName": skill["name"]}
                            )
                        except Exception as e:
                            errors.append(
                                f"Error processing skill at index {skill_idx} for profile {profile_urn}: {str(e)}"
                            )

                # Collect education - defensively
                # In batch_store_profiles - education collection section
                if "education" in profile_data and profile_data["education"]:
                    for edu_idx, edu in enumerate(profile_data["education"]):
                        try:
                            # Check required keys - REMOVED mandatory school check
                            school = edu.get("school", {})

                            # Handle None school or string school
                            if not school:
                                if isinstance(edu.get("schoolName"), str):
                                    school = {"name": edu.get("schoolName")}
                                else:
                                    continue
                            elif not isinstance(school, dict):
                                if isinstance(school, str):
                                    school = {"name": school}
                                else:
                                    continue

                            # Ensure school has a name - try both keys
                            school_name = None
                            if isinstance(school, dict):
                                school_name = school.get("name") or school.get(
                                    "schoolName"
                                )

                            if not school_name:
                                continue

                            # Generate school URN safely
                            school_urn = None
                            if isinstance(school, dict):
                                school_urn = school.get("urn") or school.get(
                                    "schoolUrn"
                                )

                            if not school_urn:
                                school_urn = f"urn:li:school:{school_name.replace(' ', '').lower()}"

                            # Get time_period safely (handle both snake_case and camelCase)
                            time_period = (
                                edu.get("time_period", {})
                                or edu.get("timePeriod", {})
                                or {}
                            )

                            # Handle non-dict time_period or missing time_period
                            if not isinstance(time_period, dict):
                                time_period = {}

                            # process appending to all_education
                            all_education.append(
                                {
                                    "profileUrn": profile_urn,
                                    "schoolUrn": school_urn,
                                    "schoolName": school_name,
                                    "degreeName": edu.get("degree_name")
                                    or edu.get("degreeName")
                                    or "",
                                    "fieldOfStudy": edu.get("field_of_study")
                                    or edu.get("fieldOfStudy")
                                    or "",
                                    "startYear": time_period.get("start_year")
                                    or time_period.get("startYear"),
                                    "startMonth": time_period.get("start_month")
                                    or time_period.get("startMonth"),
                                    "endYear": time_period.get("end_year")
                                    or time_period.get("endYear"),
                                    "endMonth": time_period.get("end_month")
                                    or time_period.get("endMonth"),
                                }
                            )

                        except Exception as e:
                            errors.append(
                                f"Error processing education at index {edu_idx} for profile {profile_urn}: {str(e)}"
                            )
                            continue

                # Collect experience and companies - defensively
                if "experience" in profile_data and profile_data["experience"]:
                    for exp_idx, exp in enumerate(profile_data["experience"]):
                        try:
                            # First check if experience exists and is a dict
                            if not exp or not isinstance(exp, dict):
                                continue

                            # Handle company safely
                            company_data = exp.get("company")
                            if not company_data:
                                continue

                            if not isinstance(company_data, dict):
                                # Try to handle case where company might be a string
                                if isinstance(company_data, str):
                                    company_data = {"name": company_data}
                                else:
                                    continue

                            # Ensure company has a name through various possible keys
                            company_name = (
                                company_data.get("name")
                                or company_data.get("companyName")
                                or company_data.get("company_name")
                            )

                            if not company_name:
                                continue

                            # Generate company URN safely
                            company_urn = (
                                company_data.get("urn")
                                or company_data.get("companyUrn")
                                or company_data.get("company_urn")
                                or f"urn:li:company:{company_name.replace(' ', '').lower()}"
                            )

                            # Add company safely
                            all_companies.append(
                                {
                                    "urn": company_urn,
                                    "name": company_name,
                                }
                            )

                            # Get title with fallbacks
                            title = (
                                exp.get("title") or exp.get("role") or "Unknown Title"
                            )

                            # Handle time_period which could be completely missing
                            time_period = exp.get("time_period") or exp.get(
                                "timePeriod"
                            )

                            # Initialize empty dicts for dates if time_period is None
                            if not time_period:
                                start_date = {}
                                end_date = {}
                                is_current = True  # Assume current if no dates provided
                            else:
                                # Handle non-dict time_period
                                if not isinstance(time_period, dict):
                                    if isinstance(time_period, str):
                                        # Try to parse string time periods like "2020-Present"
                                        try:
                                            if "-" in time_period:
                                                parts = time_period.split("-")
                                                start_year = int(parts[0].strip())
                                                start_date = {"year": start_year}
                                                end_date = (
                                                    {}
                                                    if "present" in parts[1].lower()
                                                    else {"year": int(parts[1].strip())}
                                                )
                                            else:
                                                start_date = {
                                                    "year": int(time_period.strip())
                                                }
                                                end_date = {}
                                        except:
                                            # If parsing fails, use empty dicts
                                            start_date = {}
                                            end_date = {}
                                    else:
                                        # Not a dict or parsable string
                                        start_date = {}
                                        end_date = {}
                                    is_current = not end_date
                                else:
                                    # Normal case - time_period is a dict
                                    # Get date safely with multiple possible key formats
                                    start_date = (
                                        time_period.get("start_date")
                                        or time_period.get("startDate")
                                        or time_period.get("start")
                                        or {}
                                    )

                                    # Handle non-dict start_date
                                    if not isinstance(start_date, dict):
                                        if isinstance(start_date, str):
                                            # Try to parse string like "2020"
                                            try:
                                                start_date = {
                                                    "year": int(start_date.strip())
                                                }
                                            except:
                                                start_date = {}
                                        else:
                                            start_date = {}

                                    end_date = (
                                        time_period.get("end_date")
                                        or time_period.get("endDate")
                                        or time_period.get("end")
                                        or {}
                                    )

                                    # Handle non-dict end_date
                                    if not isinstance(end_date, dict):
                                        if isinstance(end_date, str):
                                            if end_date.lower() in [
                                                "present",
                                                "current",
                                            ]:
                                                end_date = {}
                                            else:
                                                # Try to parse string like "2022"
                                                try:
                                                    end_date = {
                                                        "year": int(end_date.strip())
                                                    }
                                                except:
                                                    end_date = {}
                                        else:
                                            end_date = {}

                                    # Determine if current position
                                    is_current = not end_date or not (
                                        end_date.get("year") and end_date.get("month")
                                    )

                            # Get location safely
                            location = exp.get("location") or {}
                            if not isinstance(location, dict):
                                if isinstance(location, str):
                                    location = {"name": location}
                                else:
                                    location = {}

                            location_name = None
                            if location:
                                location_name = location.get("name") or location.get(
                                    "locationName"
                                )

                            # Generate experience URN safely, with fallbacks if data is missing
                            start_year = start_date.get("year", "unknown")
                            start_month = start_date.get("month", "unknown")
                            exp_urn = (
                                exp.get("entity_urn")
                                or exp.get("entityUrn")
                                or exp.get("urn")
                                or f"exp-{profile_urn}-{company_urn}-{start_year}-{start_month}"
                            )

                            # Create the experience record
                            all_experiences.append(
                                {
                                    "profileUrn": profile_urn,
                                    "companyUrn": company_urn,
                                    "expUrn": exp_urn,
                                    "title": title,
                                    "description": exp.get("description", ""),
                                    "startYear": start_date.get("year"),
                                    "startMonth": start_date.get("month"),
                                    "endYear": end_date.get("year"),
                                    "endMonth": end_date.get("month"),
                                    "isCurrent": is_current,
                                    "locationName": location_name,
                                }
                            )
                        except Exception as e:
                            errors.append(
                                f"Error processing experience at index {exp_idx} for profile {profile_urn}: {str(e)}"
                            )
            except Exception as e:
                errors.append(
                    f"Error processing profile details at index {i}: {str(e)}"
                )

        # Execute batch operations
        failed_operations = 0

        # 1. Skills
        if all_skills:
            try:
                skills_query = """
                UNWIND $skills AS skill
                MATCH (p:Profile {urn: skill.profileUrn})
                MERGE (s:Skill {name: skill.skillName})
                MERGE (p)-[r:HAS_SKILL]->(s)
                """
                self._run_query(skills_query, {"skills": all_skills})
            except Exception as e:
                errors.append(f"Error creating skills: {str(e)}")
                failed_operations += 1

        # 2. Schools and education
        if all_education:
            try:
                education_query = """
                UNWIND $education AS edu
                MERGE (s:School {urn: edu.schoolUrn})
                ON CREATE SET
                    s.name = edu.schoolName

                WITH edu, s
                MATCH (p:Profile {urn: edu.profileUrn})
                MERGE (p)-[r:ATTENDED]->(s)
                ON CREATE SET
                    r.degreeName = edu.degreeName,
                    r.fieldOfStudy = edu.fieldOfStudy,
                    r.startYear = edu.startYear,
                    r.startMonth = edu.startMonth,
                    r.endYear = edu.endYear,
                    r.endMonth = edu.endMonth
                
                """
                self._run_query(education_query, {"education": all_education})
            except Exception as e:
                errors.append(f"Error creating education: {str(e)}")
                failed_operations += 1

        # 3. Companies
        if all_companies:
            try:
                companies_query = """
                UNWIND $companies AS company
                MERGE (c:Company {urn: company.urn})
                ON CREATE SET
                    c.name = company.name,
                    c.createdAt = datetime()
                ON MATCH SET
                    c.name = company.name,
                    c.updatedAt = datetime()
                """
                self._run_query(companies_query, {"companies": all_companies})
            except Exception as e:
                errors.append(f"Error creating companies: {str(e)}")
                failed_operations += 1

        # 4. Experience
        if all_experiences:
            try:
                experience_query = """
                UNWIND $experiences AS exp
                
                MATCH (p:Profile {urn: exp.profileUrn})
                MATCH (c:Company {urn: exp.companyUrn})
                
                MERGE (e:Experience {urn: exp.expUrn})
                ON CREATE SET
                    e.title = exp.title,
                    e.description = exp.description,
                    e.startYear = exp.startYear,
                    e.startMonth = exp.startMonth,
                    e.endYear = exp.endYear,
                    e.endMonth = exp.endMonth,
                    e.isCurrent = exp.isCurrent,
                    e.locationName = exp.locationName,
                    e.createdAt = datetime()
                ON MATCH SET
                    e.title = exp.title,
                    e.description = exp.description,
                    e.startYear = exp.startYear,
                    e.startMonth = exp.startMonth,
                    e.endYear = exp.endYear,
                    e.endMonth = exp.endMonth,
                    e.isCurrent = exp.isCurrent,
                    e.locationName = exp.locationName,
                    e.updatedAt = datetime()
                
                MERGE (p)-[r1:HAS_EXPERIENCE]->(e)
                MERGE (e)-[r2:AT_COMPANY]->(c)
                """
                self._run_query(experience_query, {"experiences": all_experiences})
            except Exception as e:
                errors.append(f"Error creating experiences: {str(e)}")
                failed_operations += 1

        # Print summary statistics
        print(f"Processed {processed_profiles}/{len(profiles)} profiles successfully.")
        print(
            f"Created {len(all_skills)} skills, {len(all_education)} education records, {len(all_companies)} companies, and {len(all_experiences)} experiences."
        )

        if errors:
            print(f"Encountered {len(errors)} errors during processing:")
            for i, error in enumerate(errors[:10]):  # Show only first 10 errors
                print(f"  {i+1}. {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        if failed_operations > 0:
            print(f"WARNING: {failed_operations} database operations failed!")
        else:
            print("All database operations completed successfully.")

    def batch_store_companies(self, companies: List[LinkedInCompany]):
        """
        Store multiple LinkedIn companies in Neo4j efficiently using batch operations.
        Added defensive programming to prevent failures when processing bad data.

        Args:
            companies: List of LinkedInCompany model instances
        """
        # Convert all companies to dictionaries with normalized property names
        company_dicts = []
        industry_relationships = []

        # Track errors for logging
        errors = []
        processed_companies = 0

        for i, company in enumerate(companies):
            try:
                # Handle None companies
                if company is None:
                    errors.append(f"Company at index {i} is None, skipping")
                    continue

                company_data = (
                    company.model_dump() if hasattr(company, "model_dump") else company
                )

                # Handle None company_data
                if company_data is None:
                    errors.append(
                        f"Company data at index {i} is None after model_dump, skipping"
                    )
                    continue

                # Extract primary company data
                company_urn = (
                    company_data.get("entity_urn")
                    or company_data.get("entityUrn")
                    or company_data.get("urn")
                )

                # Skip if no valid URN
                if not company_urn:
                    errors.append(f"Company at index {i} has no valid URN, skipping")
                    continue

                # Prepare company data
                company_dict = {
                    "urn": company_urn,
                    "name": company_data.get("name") or "Unknown Company",
                    "description": company_data.get("description", ""),
                    "url": company_data.get("url", ""),
                    "staffCount": company_data.get("staff_count")
                    or company_data.get("staffCount")
                    or 0,
                    "staffCountRange": None,
                }

                # Safely process staff count range
                try:
                    staff_count_range = company_data.get(
                        "staff_count_range"
                    ) or company_data.get("staffCountRange")

                    if staff_count_range and isinstance(staff_count_range, dict):
                        company_dict["staffCountRange"] = json.dumps(staff_count_range)
                except Exception as e:
                    # Just don't set staffCountRange if there's an error
                    errors.append(
                        f"Error processing staff count range for company {company_urn}: {str(e)}"
                    )

                company_dicts.append(company_dict)
                processed_companies += 1

                # Extract industry relationships
                if (
                    "company_industries" in company_data
                    and company_data["company_industries"]
                ):
                    try:
                        for industry_idx, industry in enumerate(
                            company_data["company_industries"]
                        ):
                            try:
                                industry_name = None
                                if (
                                    isinstance(industry, dict)
                                    and "localized_name" in industry
                                ):
                                    industry_name = industry["localized_name"]
                                elif isinstance(industry, str):
                                    industry_name = industry

                                if industry_name:
                                    industry_relationships.append(
                                        {
                                            "companyUrn": company_urn,
                                            "industryName": industry_name,
                                        }
                                    )
                            except Exception as e:
                                errors.append(
                                    f"Error processing industry at index {industry_idx} for company {company_urn}: {str(e)}"
                                )
                    except Exception as e:
                        errors.append(
                            f"Error processing industries for company {company_urn}: {str(e)}"
                        )

            except Exception as e:
                errors.append(f"Error processing company at index {i}: {str(e)}")

        # Execute batch operations
        failed_operations = 0

        # 1. Create all Company nodes
        if company_dicts:
            try:
                companies_query = """
                UNWIND $companies AS company
                MERGE (c:Company {urn: company.urn})
                ON CREATE SET
                    c.name = company.name,
                    c.description = company.description,
                    c.url = company.url,
                    c.staffCount = company.staffCount,
                    c.staffCountRange = company.staffCountRange,
                    c.createdAt = datetime()
                ON MATCH SET
                    c.name = company.name,
                    c.description = company.description,
                    c.url = company.url,
                    c.staffCount = company.staffCount,
                    c.staffCountRange = company.staffCountRange,
                    c.updatedAt = datetime()
                """
                self._run_query(companies_query, {"companies": company_dicts})
            except Exception as e:
                errors.append(f"Error creating company nodes: {str(e)}")
                failed_operations += 1

        # 2. Create Industry nodes and relationships
        if industry_relationships:
            try:
                industries_query = """
                UNWIND $industries AS industry
                MATCH (c:Company {urn: industry.companyUrn})
                MERGE (i:Industry {name: industry.industryName})
                MERGE (c)-[r:IN_INDUSTRY]->(i)
                """
                self._run_query(
                    industries_query, {"industries": industry_relationships}
                )
            except Exception as e:
                errors.append(f"Error creating industry relationships: {str(e)}")
                failed_operations += 1

        # Print summary statistics
        print(
            f"Processed {processed_companies}/{len(companies)} companies successfully."
        )
        print(f"Created {len(industry_relationships)} industry relationships.")

        if errors:
            print(f"Encountered {len(errors)} errors during processing:")
            for i, error in enumerate(errors[:10]):  # Show only first 10 errors
                print(f"  {i+1}. {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        if failed_operations > 0:
            print(f"WARNING: {failed_operations} database operations failed!")
        else:
            print("All database operations completed successfully.")

    def batch_store_transitions(self, transitions: List[Union[TransitionEvent, Dict]]):
        """
        Store multiple job transition events in Neo4j efficiently using batch operations.
        Added defensive programming to prevent failures when processing bad data.

        Args:
            transitions: List of transition event dictionaries
        """
        # Normalize transition data
        transition_dicts = []

        # Track errors for logging
        errors = []
        processed_transitions = 0

        for i, transition in enumerate(transitions):
            try:
                # Handle None transitions
                if transition is None:
                    errors.append(f"Transition at index {i} is None, skipping")
                    continue

                data = (
                    transition.model_dump(by_alias=True)
                    if isinstance(transition, TransitionEvent)
                    else transition
                )

                # Handle None data
                if data is None:
                    errors.append(
                        f"Transition data at index {i} is None after model_dump, skipping"
                    )
                    continue

                # Check required fields
                required_fields = [
                    "profile_urn",
                    "from_company_urn",
                    "to_company_urn",
                    "transition_date",
                    "transition_type",
                    "old_title",
                    "new_title",
                ]
                missing_fields = [f for f in required_fields if f not in data]

                if missing_fields:
                    errors.append(
                        f"Transition at index {i} missing required fields: {', '.join(missing_fields)}"
                    )
                    continue

                # Safely normalize the date
                try:
                    td = data["transition_date"]
                    if td is None:
                        errors.append(
                            f"Transition at index {i} has None transition_date, skipping"
                        )
                        continue

                    if isinstance(td, str):
                        td = td if "T" in td else f"{td}T00:00:00"
                    else:
                        td = td.isoformat()
                except Exception as e:
                    errors.append(
                        f"Error processing transition_date for transition at index {i}: {str(e)}"
                    )
                    continue

                # Build the dict that Neo4j will consume
                transition_dict = {
                    "profileUrn": data["profile_urn"],
                    "fromCompanyUrn": data["from_company_urn"],
                    "toCompanyUrn": data["to_company_urn"],
                    "transitionDate": td,
                    "transitionType": data["transition_type"],
                    "oldTitle": data["old_title"] or "Unknown Title",
                    "newTitle": data["new_title"] or "Unknown Title",
                    "locationChange": data.get("location_change", False),
                    "tenureDays": data.get("tenure_days", 0),
                }

                # Double-check the minimum required data
                if (
                    transition_dict["profileUrn"]
                    and transition_dict["fromCompanyUrn"]
                    and transition_dict["toCompanyUrn"]
                    and transition_dict["transitionDate"]
                ):
                    transition_dicts.append(transition_dict)
                    processed_transitions += 1
                else:
                    errors.append(
                        f"Transition at index {i} failed validation checks, skipping"
                    )

            except Exception as e:
                errors.append(f"Error processing transition at index {i}: {str(e)}")

        # Execute batch operation for transitions
        if transition_dicts:
            try:
                transitions_query = """
                UNWIND $transitions AS t
                
                MATCH (p:Profile {urn: t.profileUrn})
                MATCH (oldCompany:Company {urn: t.fromCompanyUrn})
                MATCH (newCompany:Company {urn: t.toCompanyUrn})
                
                CREATE (transition:Transition {
                    date: datetime(t.transitionDate),
                    type: t.transitionType,
                    oldTitle: t.oldTitle,
                    newTitle: t.newTitle,
                    locationChange: t.locationChange,
                    tenureDays: t.tenureDays
                })
                
                CREATE (p)-[:HAS_TRANSITION]->(transition)
                CREATE (transition)-[:FROM_COMPANY]->(oldCompany)
                CREATE (transition)-[:TO_COMPANY]->(newCompany)
                """
                self._run_query(transitions_query, {"transitions": transition_dicts})
            except Exception as e:
                errors.append(f"Error creating transition nodes: {str(e)}")

        # Print summary statistics
        print(
            f"Processed {processed_transitions}/{len(transitions)} transitions successfully."
        )

        if errors:
            print(f"Encountered {len(errors)} errors during processing:")
            for i, error in enumerate(errors[:10]):  # Show only first 10 errors
                print(f"  {i+1}. {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        if processed_transitions == len(transitions):
            print("All transitions processed successfully.")
        else:
            print(
                f"WARNING: {len(transitions) - processed_transitions} transitions skipped due to errors!"
            )

    def batch_store_chunked(self, func, data: List, batch_size=500):
        """Store profiles,companies,or transitions in smaller batches for better performance"""
        total = len(data)
        for i in range(0, total, batch_size):
            chunk = data[i : i + batch_size]
            # Process this smaller chunk using your existing batch method
            func(chunk)
            print(f"Processed {float(min(i+batch_size, total))/float(total)}% of data")

    def find_profile_by_urn(self, profile_urn: str) -> Dict[str, Any]:
        """
        Find a profile by its URN.

        Args:
            profile_urn: Profile URN

        Returns:
            Profile data as a dictionary
        """
        query = """
        MATCH (p:Profile {urn: $urn})
        RETURN p {
            .*,
            skills: [(p)-[:HAS_SKILL]->(s) | s.name],
            education: [(p)-[edu:ATTENDED]->(school) | {
                school: school.name,
                schoolUrn: school.urn,
                degreeName: edu.degreeName,
                fieldOfStudy: edu.fieldOfStudy,
                startYear: edu.startYear,
                startMonth: edu.startMonth,
                endYear: edu.endYear,
                endMonth: edu.endMonth
            }],
            experience: [(p)-[:HAS_EXPERIENCE]->(e)-[r:AT_COMPANY]->(c) | {
                title: e.title,
                company: c.name,
                companyUrn: c.urn,
                description: e.description,
                startYear: e.startYear,
                startMonth: e.startMonth,
                endYear: e.endYear,
                endMonth: e.endMonth,
                isCurrent: e.isCurrent,
                locationName: e.locationName
            }]
        } as profile
        """

        results = self._run_query(query, {"urn": profile_urn})
        return results[0]["profile"] if results else None

    def find_company_by_urn(self, company_urn: str) -> Dict[str, Any]:
        """
        Find a company by its URN.

        Args:
            company_urn: Company URN

        Returns:
            Company data as a dictionary
        """
        query = """
        MATCH (c:Company {urn: $urn})
        RETURN c {
            .*,
            industries: [(c)-[:IN_INDUSTRY]->(i) | i.name]
        } as company
        """

        results = self._run_query(query, {"urn": company_urn})
        return results[0]["company"] if results else None

    def find_transitions_by_profile(self, profile_urn: str) -> List[Dict[str, Any]]:
        """
        Find all transitions for a profile.

        Args:
            profile_urn: Profile URN

        Returns:
            List of transition events
        """
        query = """
        MATCH (p:Profile {urn: $urn})-[:HAS_TRANSITION]->(t)-[:FROM_COMPANY]->(fc),
              (t)-[:TO_COMPANY]->(tc)
        RETURN t {
            .*,
            profile: p.urn,
            fromCompany: fc.name,
            fromCompanyUrn: fc.urn,
            toCompany: tc.name,
            toCompanyUrn: tc.urn
        } as transition
        ORDER BY t.date DESC
        """

        results = self._run_query(query, {"urn": profile_urn})
        return [r["transition"] for r in results]

    def search_profiles(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        title: Optional[str] = None,
        skill: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for profiles based on various criteria.

        Args:
            first_name: First name to search for
            last_name: Last name to search for
            company_name: Company name to search for
            title: Job title to search for
            skill: Skill to search for
            limit: Maximum number of results to return

        Returns:
            List of matching profiles
        """
        conditions = []
        params = {}

        # Build dynamic query based on provided parameters
        if first_name:
            conditions.append("p.firstName =~ $firstName")
            params["firstName"] = f"(?i).*{first_name}.*"

        if last_name:
            conditions.append("p.lastName =~ $lastName")
            params["lastName"] = f"(?i).*{last_name}.*"

        if company_name:
            conditions.append(
                "EXISTS { MATCH (p)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) WHERE c.name =~ $companyName }"
            )
            params["companyName"] = f"(?i).*{company_name}.*"

        if title:
            conditions.append(
                "EXISTS { MATCH (p)-[:HAS_EXPERIENCE]->(e) WHERE e.title =~ $title }"
            )
            params["title"] = f"(?i).*{title}.*"

        if skill:
            conditions.append(
                "EXISTS { MATCH (p)-[:HAS_SKILL]->(s) WHERE s.name =~ $skill }"
            )
            params["skill"] = f"(?i).*{skill}.*"

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        params["limit"] = limit

        query = f"""
        MATCH (p:Profile)
        WHERE {where_clause}
        RETURN p {{
            .*,
            skills: [(p)-[:HAS_SKILL]->(s) | s.name],
            currentExperience: head([
                (p)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) 
                WHERE e.isCurrent = true OR e.endYear IS NULL
                | {{ title: e.title, company: c.name }}
            ])
        }} as profile
        LIMIT $limit
        """

        results = self._run_query(query, params)
        return [r["profile"] for r in results]

    def get_company_transition_stats(self, company_urn: str) -> Dict[str, Any]:
        """
        Get transition statistics for a company.

        Args:
            company_urn: Company URN

        Returns:
            Dictionary with transition statistics
        """
        query = """
        MATCH (c:Company {urn: $companyUrn})
        
        // Incoming transitions (people joining)
        OPTIONAL MATCH (p1:Profile)-[:HAS_TRANSITION]->(t1:Transition)-[:TO_COMPANY]->(c)
        WITH c, count(t1) as incomingCount, collect(t1) as incomingTransitions
        
        // Outgoing transitions (people leaving)
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t2:Transition)-[:FROM_COMPANY]->(c)
        
        // Top companies people come from
        OPTIONAL MATCH (t1in:Transition)-[:TO_COMPANY]->(c),
                      (t1in)-[:FROM_COMPANY]->(fromCompany)
        WITH c, incomingCount, incomingTransitions, count(t2) as outgoingCount,
             fromCompany, count(t1in) as fromCount
        
        // Top companies people go to
        OPTIONAL MATCH (t2out:Transition)-[:FROM_COMPANY]->(c),
                      (t2out)-[:TO_COMPANY]->(toCompany)
        WITH c, incomingCount, outgoingCount, 
             fromCompany, fromCount, toCompany, count(t2out) as toCount
        
        // Aggregate top companies
        WITH c, incomingCount, outgoingCount,
             collect({company: fromCompany.name, count: fromCount}) as topSourceCompanies,
             collect({company: toCompany.name, count: toCount}) as topDestinationCompanies
        
        RETURN {
            companyName: c.name,
            incomingTransitions: incomingCount,
            outgoingTransitions: outgoingCount,
            topSourceCompanies: [x in topSourceCompanies WHERE x.company IS NOT NULL | x],
            topDestinationCompanies: [x in topDestinationCompanies WHERE x.company IS NOT NULL | x]
        } as stats
        """

        results = self._run_query(query, {"companyUrn": company_urn})
        return results[0]["stats"] if results else {}

        # def get_skill_trends(self, limit: int = 10) -> List[Dict[str, Any]]:
        #     """
        #     Get trending skills based on recent transitions.

        #     Args:
        #         limit: Maximum number of trending skills to return

        #     Returns:
        #         List of trending skills with counts
        #     """
        #     query = """
        #     MATCH (p:Profile)-[:HAS_SKILL]->(s:Skill)
        #     WITH s, count(p) as profileCount

        #     // Find transitions from profiles with this skill in the last year
        #     OPTIONAL MATCH (p2:Profile)-[:HAS_SKILL]->(s)
        #                   -[:HAS_TRANSITION]->(t:Transition)
        #     WHERE datetime(t.date) >= datetime.truncate('year', datetime()) - duration('P1Y')

        #     WITH s, profileCount, count(t) as transitionCount

        #     // Calculate a trend score (higher is more trending)
        #     WITH s, profileCount, transitionCount,
        #          toFloat(transitionCount) / toFloat(profileCount + 1) as trendScore

        #     RETURN {
        #         skillName: s.name,
        #         profileCount: profileCount,
        #         recentTransitions: transitionCount,
        #         trendScore: trendScore
        #     } as skill
        #     ORDER BY skill.trendScore DESC, skill.profileCount DESC
        #     LIMIT $limit
        #     """

        #     results = self._run_query(query, {"limit": limit})
        #     return [r["skill"] for r in results]

        # def recommend_connections(self, profile_urn: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recommend potential connections for a profile based on common companies, schools, etc.
        
        Args:
            profile_urn: Profile URN to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended profiles with connection strength
        """
        query = """
        MATCH (p:Profile {urn: $profileUrn})
        
        // Find other profiles that share companies
        OPTIONAL MATCH (p)-[:HAS_EXPERIENCE]->(e1)-[:AT_COMPANY]->(c)<-[:AT_COMPANY]-(e2)<-[:HAS_EXPERIENCE]-(other)
        WHERE p <> other
        WITH p, other, count(c) as sharedCompanies
        
        // Find other profiles that share schools
        OPTIONAL MATCH (p)-[:ATTENDED]->(s)<-[:ATTENDED]-(other)
        WHERE p <> other
        WITH p, other, sharedCompanies, count(s) as sharedSchools
        
        // Find other profiles that share skills
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(skill)<-[:HAS_SKILL]-(other)
        WHERE p <> other
        WITH p, other, sharedCompanies, sharedSchools, count(skill) as sharedSkills
        
        // Calculate connection strength score
        WITH p, other, 
             5 * sharedCompanies + 3 * sharedSchools + sharedSkills as connectionStrength
        WHERE connectionStrength > 0
        
        RETURN other {
            .*,
            currentExperience: head([
                (other)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) 
                WHERE e.isCurrent = true OR e.endYear IS NULL
                | { title: e.title, company: c.name }
            ]),
            connectionStrength: connectionStrength,
            sharedCompanies: [(p)-[:HAS_EXPERIENCE]->()-[:AT_COMPANY]->(c)<-[:AT_COMPANY]-()<-[:HAS_EXPERIENCE]-(other) | c.name],
            sharedSkills: [(p)-[:HAS_SKILL]->(s)<-[:HAS_SKILL]-(other) | s.name]
        } as recommendation
        ORDER BY recommendation.connectionStrength DESC
        LIMIT $limit
        """

        results = self._run_query(query, {"profileUrn": profile_urn, "limit": limit})
        return [r["recommendation"] for r in results]

    def clear_database(self):
        """WARNING: Clear the entire database. Use with caution!"""
        query = """
        MATCH (n)
        DETACH DELETE n
        """
        self._run_query(query)
        print("Neo4j database cleared")


## _________________________________________________________________________________________________________________________
## Module Wide Methods for Neo4j
## _________________________________________________________________________________________________________________________


def send_to_neo4j(profiles: List[LinkedInProfile], companies: List[LinkedInCompany]):
    """
    Send LinkedIn profiles and companies to Neo4j database.
    Compatible with the existing send_to_druid function interface.

    Args:
        profiles: List of LinkedInProfile objects
        companies: List of LinkedInCompany objects
    """
    db = Neo4jDatabase()

    try:
        # Set up database constraints if needed
        db.setup_constraints()

        # Store companies first to ensure they exist
        print(f"Storing {len(companies)} companies in Neo4j...")
        db.batch_store_chunked(db.batch_store_companies, companies)

        # Store profiles and their relationships
        print(f"Storing {len(profiles)} profiles in Neo4j...")
        db.batch_store_chunked(db.batch_store_profiles, profiles)

        print("Successfully stored data in Neo4j database")
    finally:
        # Ensure database connection is closed
        db.close()


def send_transition_to_neo4j(transition_event: TransitionEvent) -> bool:
    """
    Send a transition event to Neo4j.
    Compatible with the existing send_transition_update function interface.

    Args:
        transition_event: Dictionary containing transition data

    Returns:
        True if successful, False otherwise
    """
    db = Neo4jDatabase()

    try:
        # Store transition
        db.store_transition(transition_event)
        print(
            f"Successfully stored transition for profile: {transition_event['profile_urn']}"
        )
        return True
    except Exception as e:
        print(f"Error storing transition in Neo4j: {e}")
        return False
    finally:
        db.close()


def query_neo4j(
    cypher_query: str, params: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Execute a custom Cypher query on the Neo4j database.

    Args:
        cypher_query: Cypher query string
        params: Query parameters

    Returns:
        Query results as a list of dictionaries
    """
    db = Neo4jDatabase()

    try:
        results = db._run_query(cypher_query, params)
        return results
    finally:
        db.close()


## _________________________________________________________________________________________________________________________
## Second Order Analysis Class for Neo4j db
## _________________________________________________________________________________________________________________________


class Neo4jProfileAnalyzer:
    """
    Helper class for analyzing LinkedIn profile data in Neo4j.
    Provides higher-level functions for common analysis tasks.
    """

    def __init__(self):
        """Initialize the analyzer with a database connection."""
        self.db = Neo4jDatabase()

    def close(self):
        """Close the database connection."""
        self.db.close()

    def get_career_path_analysis(self, profile_urn: str) -> Dict[str, Any]:
        """
        Analyze the career path of a profile.

        Args:
            profile_urn: Profile URN

        Returns:
            Dictionary with career path analysis
        """
        query = """
        MATCH (p:Profile {urn: $profileUrn})-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
                
        WITH p, e, c
        ORDER BY e.startYear, e.startMonth
                
        WITH p, collect({
            title: e.title,
            company: c.name,
            startYear: e.startYear,
            startMonth: e.startMonth,
            endYear: e.endYear,
            endMonth: e.endMonth,
            isCurrent: e.isCurrent,
            duration: CASE
                WHEN e.endYear IS NULL THEN 
                    (datetime().year - e.startYear) * 12 + (datetime().month - e.startMonth)
                ELSE 
                    (e.endYear - e.startYear) * 12 + (e.endMonth - e.startMonth)
            END
        }) as experiences
                
        // Calculate average tenure
        WITH p, experiences,
            reduce(total = 0, exp in [x in experiences WHERE x.duration IS NOT NULL] | total + exp.duration) / 
            size([x in experiences WHERE x.duration IS NOT NULL]) as averageTenureMonths
                
        // Get education
        OPTIONAL MATCH (p)-[edu:ATTENDED]->(s:School)
        WITH p, experiences, averageTenureMonths, 
            collect({school: s.name, degree: edu.degreeName, field: edu.fieldOfStudy}) as education
                
        // Get skills
        MATCH (p)-[:HAS_SKILL]->(skill)
        WITH p, experiences, averageTenureMonths, education, collect(skill.name) as skills
                
        // Final return with all calculations
        RETURN {
            profileName: p.firstName + ' ' + p.lastName,
            headline: p.headline,
            careerPath: experiences,
            education: education,
            skills: skills,
            averageTenureMonths: averageTenureMonths,
            totalExperience: reduce(total = 0, exp in experiences | total + exp.duration),
            numberOfCompanies: size(experiences),
            titleProgression: [exp in experiences | exp.title]
        } as analysis
        """

        results = self.db._run_query(query, {"profileUrn": profile_urn})
        return results[0]["analysis"] if results else {}

    def get_company_talent_flow(
        self, company_urn: str, time_period: str = "P1Y"
    ) -> Dict[str, Any]:
        """
        Analyze talent flow for a company over a specified time period.

        Args:
            company_urn: Company URN
            time_period: Time period for analysis (ISO-8601 format)
            - "1 YEAR" → "P1Y"
            - "6 MONTHS" → "P6M"
            - "3 MONTHS" → "P3M"
            - "1 MONTH" → "P1M"
            - "1 WEEK" → "P7D"

        Returns:
            Dictionary with talent flow analysis
        """
        query = """
        MATCH (c:Company {urn: $companyUrn})
                
        // Calculate time threshold
        WITH c, datetime() - duration($timePeriod) as cutoffDate
                
        // Incoming transitions (people joining)
        OPTIONAL MATCH (p1:Profile)-[:HAS_TRANSITION]->(t1:Transition)-[:TO_COMPANY]->(c)
        WHERE datetime(t1.date) >= cutoffDate
        WITH c, cutoffDate, count(t1) as hiringCount
                
        // Outgoing transitions (people leaving)
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t2:Transition)-[:FROM_COMPANY]->(c)
        WHERE datetime(t2.date) >= cutoffDate
        WITH c, cutoffDate, hiringCount, count(t2) as attritionCount
                
        // Calculate net talent flow
        WITH c, hiringCount, attritionCount, hiringCount - attritionCount as netTalentFlow
                
        // Get current employee count (approximation based on experiences)
        MATCH (p3:Profile)-[:HAS_EXPERIENCE]->(e3)-[:AT_COMPANY]->(c)
        WHERE e3.isCurrent = true OR e3.endYear IS NULL

        // Collect employee count before creating final return
        WITH c, hiringCount, attritionCount, netTalentFlow, count(p3) as currentEmployeeCount
                
        RETURN {
            companyName: c.name,
            companyUrn: c.urn,
            hiringCount: hiringCount,
            attritionCount: attritionCount,
            netTalentFlow: netTalentFlow,
            currentEmployeeCount: currentEmployeeCount,
            talentFlowRate: round(100.0 * toFloat(netTalentFlow) / toFloat(currentEmployeeCount + 1), 2),
            timePeriod: $timePeriod
        } as analysis
        """

        results = self.db._run_query(
            query, {"companyUrn": company_urn, "timePeriod": time_period}
        )
        return results[0]["analysis"] if results else {}

    def get_skill_cluster_analysis(self) -> List[Dict[str, Any]]:
        """
        Perform skill cluster analysis to identify related skill groups.

        Returns:
            List of skill clusters with related skills
        """
        query = """
        // Find pairs of skills that frequently appear together
        MATCH (s1:Skill)<-[:HAS_SKILL]-(p:Profile)-[:HAS_SKILL]->(s2:Skill)
        WHERE s1 <> s2
        WITH s1, s2, count(p) as coOccurrence
        WHERE coOccurrence > 5  // Minimum co-occurrence threshold

        // Calculate similarity score (Jaccard similarity)
        MATCH (pa:Profile)-[:HAS_SKILL]->(s1)
        WITH s1, s2, coOccurrence, count(pa) as s1Count

        MATCH (pb:Profile)-[:HAS_SKILL]->(s2)
        WITH s1, s2, coOccurrence, s1Count, count(pb) as s2Count

        WITH s1, s2, coOccurrence, s1Count, s2Count,
            1.0 * coOccurrence / (s1Count + s2Count - coOccurrence) as similarity
        WHERE similarity > 0.1  // Minimum similarity threshold

        // Group skills into clusters using connected components
        WITH collect({skill1: s1.name, skill2: s2.name, similarity: similarity}) as skillPairs

        CALL {
            WITH skillPairs
            UNWIND skillPairs as pair
            
            MERGE (sa:SkillNode {name: pair.skill1})
            MERGE (sb:SkillNode {name: pair.skill2})
            MERGE (sa)-[r:RELATED {similarity: pair.similarity}]->(sb)
            
            WITH collect(distinct sa.name) + collect(distinct sb.name) as allSkillNames
            
            CALL {
                WITH allSkillNames
                UNWIND allSkillNames as name
                MERGE (s:SkillNode {name: name})
                RETURN count(s) as nodeCount
            }
            
            CALL gds.graph.project(
                'skillGraph',
                'SkillNode',
                'RELATED',
                {
                    relationshipProperties: 'similarity'
                }
            )
            
            CALL gds.louvain.stream('skillGraph')
            YIELD nodeId as louvainNodeId, communityId
            
            WITH louvainNodeId, communityId
            
            MATCH (s:SkillNode)
            WHERE id(s) = louvainNodeId
            
            RETURN s.name as skillName, communityId as clusterId
        }

        // Clean up temporary graph and nodes
        CALL gds.graph.drop('skillGraph')
        MATCH (s:SkillNode)
        DETACH DELETE s

        // Group skills by cluster
        WITH skillName, clusterId
        ORDER BY clusterId, skillName

        WITH clusterId, collect(skillName) as skills
        WHERE size(skills) > 2  // Only include clusters with at least 3 skills

        // Identify most common skills for cluster naming
        MATCH (s:Skill)
        WHERE s.name IN skills
        OPTIONAL MATCH (p:Profile)-[:HAS_SKILL]->(s)
        WITH clusterId, skills, s, count(p) as popularity
        ORDER BY clusterId, popularity DESC

        WITH clusterId, skills, collect(s.name)[0] as primarySkill

        RETURN {
            clusterId: clusterId,
            clusterName: primarySkill + ' Cluster',
            skills: skills,
            primarySkill: primarySkill,
            skillCount: size(skills)
        } as cluster
        ORDER BY cluster.skillCount DESC
        """

        # Note: This query uses GDS (Graph Data Science) library which needs to be installed
        # If GDS is not available, a simpler clustering can be implemented

        try:
            results = self.db._run_query(query)
            return [r["cluster"] for r in results]
        except Exception as e:
            print(f"Error in skill cluster analysis: {e}")

            # Fallback to simpler clustering if GDS is not available
            fallback_query = """
            MATCH (s1:Skill)<-[:HAS_SKILL]-(p:Profile)-[:HAS_SKILL]->(s2:Skill)
            WHERE s1 <> s2
            WITH s1, s2, count(p) as coOccurrence
            WHERE coOccurrence > 5
            
            WITH s1.name as skill1, s2.name as skill2, coOccurrence
            ORDER BY coOccurrence DESC
            LIMIT 100
            
            WITH collect({skill1: skill1, skill2: skill2, count: coOccurrence}) as pairs
            
            // Manual clustering based on top co-occurrences
            UNWIND pairs as pair
            WITH pair.skill1 as skill, collect(pair.skill2) as relatedSkills
            
            RETURN {
                clusterId: apoc.util.md5([skill] + relatedSkills),
                clusterName: skill + ' Group',
                skills: [skill] + relatedSkills,
                primarySkill: skill,
                skillCount: 1 + size(relatedSkills)
            } as cluster
            ORDER BY cluster.skillCount DESC
            LIMIT 10
            """

            try:
                results = self.db._run_query(fallback_query)
                return [r["cluster"] for r in results]
            except Exception as fallback_error:
                print(f"Error in fallback skill analysis: {fallback_error}")
                return []


## _________________________________________________________________________________________________________________________
## Mock Data Integration Functions
## _________________________________________________________________________________________________________________________


def generate_and_store_mock_data(num_profiles: int = 100):
    """
    Generate mock data and store it in Neo4j.

    Args:
        num_profiles: Number of profiles to generate
    """
    from mock_enhanced import generate_mock_data_for_testing

    print(f"Generating {num_profiles} mock profiles...")
    dataset = generate_mock_data_for_testing(num_profiles=num_profiles)

    # Convert to Pydantic models
    profiles = []
    for profile_data in dataset["profiles"]:
        try:
            profile = LinkedInProfile(**profile_data)
            profiles.append(profile)
        except Exception as e:
            print(f"Error converting profile: {e}")

    companies = []
    for company_data in dataset["companies"]:
        try:
            company = LinkedInCompany(**company_data)
            companies.append(company)
        except Exception as e:
            print(f"Error converting company: {e}")

    # Store in Neo4j
    send_to_neo4j(profiles=profiles, companies=companies)

    # Store transitions
    db = Neo4jDatabase()
    try:
        print(f"Storing {len(dataset['transitions'])} transitions in Neo4j...")
        db.batch_store_chunked(db.batch_store_transitions, dataset["transitions"])
    finally:
        db.close()

    print("Mock data generation and storage complete")
    return len(profiles), len(companies), len(dataset["transitions"])
