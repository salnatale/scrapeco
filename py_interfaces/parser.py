# parsers/profile_extract.py
import io, json, pdfplumber, pytesseract, pdf2image
from PIL import Image
from typing import Dict, Any
from openai import OpenAI
from models import LinkedInProfile, LinkedInCompany, Company, TransitionEvent
from typing import Optional
from uuid import uuid4
from pydantic import ValidationError
from neo4j_database import Neo4jDatabase  # your existing wrapper


client = OpenAI()  # relies on OPENAI_API_KEY env var


def _image_ocr(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)


def _pdf_to_text(fp: bytes) -> str:
    """Return text for native or scanned PDFs."""
    with pdfplumber.open(io.BytesIO(fp)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    if len(text.strip()) > 100:  # native PDF – done
        return text
    # probably a scanned résumé ⇒ OCR page images
    images = pdf2image.convert_from_bytes(fp, dpi=300)
    return "\n".join(_image_ocr(img) for img in images)


def _image_file_to_text(fp: bytes) -> str:
    img = Image.open(io.BytesIO(fp))
    return _image_ocr(img)


def raw_text_from_upload(filename: str, fp: bytes) -> str:
    ext = filename.lower().split(".")[-1]
    if ext in {"pdf"}:
        return _pdf_to_text(fp)
    if ext in {"png", "jpg", "jpeg"}:
        return _image_file_to_text(fp)
    if ext in {"txt"}:
        return fp.decode("utf-8", errors="replace")  # replaces invalid bytes with �

    raise ValueError("Unsupported file type")


def text_to_profile(text: str) -> LinkedInProfile:
    """
    Convert raw resume text into a structured LinkedInProfile object using AI.
    
    This function uses OpenAI's models to parse resume text into structured data,
    with fallback mechanisms and validation to ensure high-quality extraction.
    
    Args:
        text: Raw text from a resume or LinkedIn profile
        
    Returns:
        LinkedInProfile: Structured profile data
        
    Raises:
        ValueError: If the profile data cannot be parsed or validated
    """
    # Prepare a detailed system prompt to guide the model
    system = """
    You are an expert resume parser specialized in extracting structured information from resumes and LinkedIn profiles.
    Your task is to accurately extract profile information including:
    
    1. Personal details (name, contact information)
    2. Work experience with accurate company names, job titles, dates, and descriptions
    3. Education history with institutions, degrees, and dates
    4. Skills categorized by type (technical, soft skills, etc.)
    5. Certifications and other professional qualifications
    
    For dates, extract as much detail as available (year, month, day).
    For companies, ensure consistent naming and provide industry information when possible.
    For job titles, standardize to common industry terms while preserving specialization.
    
    The output must conform exactly to the LinkedInProfile schema provided.
    Be conservative - if information is unclear or ambiguous, it's better to omit it than guess incorrectly.
    """

    # Add schema information to the prompt
    schema = LinkedInProfile.model_json_schema()
    
    # Try with the most capable model first
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text[:32_000]},  # Allow more context
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "extract_profile",
                        "description": "Extract structured profile information from resume text",
                        "parameters": schema,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "extract_profile"}},
            temperature=0.2,  # Lower temperature for more deterministic extraction
        )
        
        # Extract the profile data from the response
        tool_call = response.choices[0].message.tool_calls[0]
        json_profile = json.loads(tool_call.function.arguments)
        
    except Exception as e:
        # Log the error
        print(f"Error with primary model, falling back to alternative: {e}")
        
        # Fall back to a smaller, more reliable model
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text[:20_000]},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "extract_profile",
                            "description": "Extract structured profile information from resume text",
                            "parameters": schema,
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": "extract_profile"}},
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            json_profile = json.loads(tool_call.function.arguments)
            
        except Exception as fallback_error:
            raise ValueError(f"Failed to parse profile with fallback model: {fallback_error}") from fallback_error
    
    # Validate and fix common issues before creating the model
    try:
        # Ensure profile_urn exists
        if 'profile_urn' not in json_profile or not json_profile['profile_urn']:
            json_profile['profile_urn'] = f"urn:li:profile:{uuid4().hex}"
        
        # Normalize dates in experience
        if 'experience' in json_profile:
            for i, exp in enumerate(json_profile['experience']):
                if 'time_period' in exp:
                    # Ensure start_date has at least year
                    if 'start_date' in exp['time_period'] and exp['time_period']['start_date']:
                        if 'year' not in exp['time_period']['start_date'] or not exp['time_period']['start_date']['year']:
                            # Try to infer year from other experiences or set to current year
                            exp['time_period']['start_date']['year'] = datetime.now().year
        
        # Ensure company URNs are set
        if 'experience' in json_profile:
            for i, exp in enumerate(json_profile['experience']):
                if 'company' in exp and ('urn' not in exp['company'] or not exp['company']['urn']):
                    exp['company']['urn'] = f"urn:li:company:{uuid4().hex[:12]}"
        
        # Create the validated profile object
        profile = LinkedInProfile(**json_profile)
        
        # Additional validation for essential fields
        if not profile.first_name or not profile.last_name:
            if profile.full_name:
                # Try to split full name
                parts = profile.full_name.split(maxsplit=1)
                if len(parts) >= 2:
                    profile.first_name = parts[0]
                    profile.last_name = parts[1]
                else:
                    profile.first_name = profile.full_name
                    profile.last_name = "."
        
        return profile
        
    except ValidationError as e:
        # Try to fix common validation errors
        error_msg = str(e)
        print(f"Validation error: {error_msg}")
        
        # Make one more attempt with explicit error information
        try:
            # Send the validation error back to the model to get a fixed version
            fix_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text[:10_000]},
                    {"role": "assistant", "content": f"I tried to parse this resume but encountered validation errors: {error_msg}. Let me fix these issues and try again."}
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "extract_profile",
                            "description": "Extract structured profile information from resume text",
                            "parameters": schema,
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": "extract_profile"}},
            )
            
            fixed_tool_call = fix_response.choices[0].message.tool_calls[0]
            fixed_json_profile = json.loads(fixed_tool_call.function.arguments)
            
            return LinkedInProfile(**fixed_json_profile)
            
        except Exception as repair_error:
            raise ValueError(f"Failed to repair invalid profile data: {error_msg}") from repair_error


# parsers/profile_extract.py   (add below text_to_profile)

from models import (
    LinkedInProfile,
    TransitionEvent,
)  # ← TransitionEvent is declared in api.py
from datetime import datetime, date
from dateutil.relativedelta import relativedelta  # pip install python-dateutil


from datetime import datetime
from typing import List
from models import LinkedInProfile, TransitionEvent


def transitions_from_profile(profile: LinkedInProfile) -> List[TransitionEvent]:

    print("Starting transitions_from_profile function.")
    print("input profile:", profile)

    events: List[TransitionEvent] = []
    exp = profile.experience  # newest‑>oldest (per your generator)
    print(f"Extracted experience list with {len(exp)} entries.")

    if len(exp) < 2:
        print(
            "Not enough experience entries to calculate transitions. Returning empty list."
        )
        return events
    print("experiences: \n", exp)

    for i in range(len(exp) - 1):
        new, old = exp[i], exp[i + 1]
        print(
            f"Processing transition between experience entries {i} (new) and {i + 1} (old)."
        )

        company_change = new.company.urn != old.company.urn
        title_change = new.title != old.title
        print(f"Company change: {company_change}, Title change: {title_change}.")

        if not (company_change or title_change):
            print("No significant transition detected. Skipping to the next entry.")
            continue  # no transition here
        if not (new.company.urn and old.company.urn):
            continue  # not full transitions

        nsd = new.time_period.start_date or {}
        osd = old.time_period.start_date or {}

        if not (
            nsd.get("year")
            and nsd.get("month")
            and osd.get("year")
            and osd.get("month")
        ):
            print("Skipping due to missing year/month.")
            tenure_days = 0
            if not nsd.get("year") or not nsd.get("month"):
                t_date = datetime(
                    nsd.get("year", datetime.now().year), nsd.get("month", 1), 1
                )
                print(
                    f"Transition date set to {t_date} due to missing date information."
                )
        else:
            print(f"New start date: {nsd}, Old start date: {osd}.")
            t_date = datetime(nsd["year"], nsd["month"], 1)
            old_date = datetime(osd["year"], osd["month"], 1)
            tenure_days = abs((t_date - old_date).days)
            print(f"Transition date calculated as {t_date}.")

            tenure_days = abs(t_date - old_date).days
            print(f"Tenure days calculated as {tenure_days}.")

        transition_event = TransitionEvent(
            transition_date=t_date,
            profile_urn=profile.profile_urn,
            from_company_urn=old.company.urn,
            to_company_urn=new.company.urn,
            transition_type="company_change" if company_change else "promotion",
            old_title=old.title,
            new_title=new.title,
            location_change=(
                (old.location and old.location.name)
                != (new.location and new.location.name)
            ),
            tenure_days=tenure_days,
        )
        print(f"Created TransitionEvent: {transition_event}.")

        events.append(transition_event)

    print(f"Finished processing transitions. Total events created: {len(events)}.")
    return events


# --- check company code ---


def _generate_unique_company_urn(db: Neo4jDatabase) -> str:
    """
    Create a URN that is guaranteed not to collide with anything already
    in Neo4j.  We use a 12‑char hex shard of a UUID, but any strategy works
    as long as you test for existence.
    """
    while True:
        urn = f"urn:li:company:{uuid4().hex[:12]}"
        hit = db._run_query("MATCH (c:Company {urn:$u}) RETURN c LIMIT 1", {"u": urn})
        if not hit:
            return urn


def _ensure_urn_in_db(db: Neo4jDatabase, comp: Company) -> None:
    """
    Make sure there's a Company node for `comp`.
    Uses the minimal dict shape that `Neo4jDatabase.store_company` accepts.
    """
    # does this URN already exist in Neo4j?
    exists = db._run_query(
        "MATCH (c:Company {urn:$u}) RETURN c LIMIT 1", {"u": comp.urn}
    )
    if exists:
        return

    # stub object → only `name` + `entity_urn` are required by store_company
    db.store_company({"entity_urn": comp.urn, "name": comp.name})


def _check_company_exists_in_db(db: Neo4jDatabase, comp: Company) -> Optional[Company]:
    """
    Check if a company with the given name exists in the Neo4j database.

    Args:
        db: The Neo4jDatabase instance
        comp: The Company object to check for

    Returns:
        Optional[Company]: The existing Company object if found, otherwise None
    """
    # Sanitize company name to avoid Cypher injection
    company_name = comp.name.replace("'", "\\'")

    # Query to find companies with the exact name
    query = """
    MATCH (c:Company)
    WHERE c.name = $company_name
    RETURN c.urn as urn, c.name as name
    LIMIT 1
    """

    # Execute the query
    result = db._run_query(query, {"company_name": comp.name})

    # Check if a company was found
    if result and len(result) > 0:
        company_data = result[0]
        print(
            f"Found existing company in database: {company_data['name']} with URN: {company_data['urn']}"
        )

        # Update the original company object's URN
        comp.urn = company_data["urn"]

        return comp


def check_companies(
    profile: LinkedInProfile, db: Optional[Neo4jDatabase] = None
) -> LinkedInProfile:
    """
    ▸ Walk through `profile.experience`
    ▸ If a company's `urn` is missing, mint a unique one
    ▸ Guarantee that every referenced Company is present in Neo4j
    ▸ Return the (mutated) profile so callers can continue to use it
    """
    print("Starting check_companies function.")
    print(
        f"Input profile: {profile.profile_urn}, Experience count: {len(profile.experience)}"
    )

    owns_db = False
    if db is None:
        print("No database instance provided. Creating a new Neo4jDatabase instance.")
        db = Neo4jDatabase()
        owns_db = True  # so we can close it at the end

    try:
        for i, exp in enumerate(profile.experience):
            comp = exp.company  # ← `Company` Pydantic model
            print(
                f"Processing experience entry {i + 1}/{len(profile.experience)}: {comp.name}"
            )
            # ----------------------------------------------------------
            # 1.  Check if the company exists by name in the DB
            # ----------------------------------------------------------
            exists = _check_company_exists_in_db(db, comp) # returns found company if found, and mutates original company's urn, so will merge.
            if exists:
                print(f"Company '{comp.name}' found in DB with URN: {comp.urn}")
                ## If the company exists, we can use the existing URN and skip the rest of the checks.
            else:
                print(f"Company '{comp.name}' not found in DB by name.")
                    
                # ----------------------------------------------------------
                # 2.  Make sure we *have* a URN
                # ----------------------------------------------------------
                
                if not comp.urn:
                    print(
                        f"Company '{comp.name}' is missing a URN, and not in DB by name, generating a new one."
                    )
                    
                    comp.urn = _generate_unique_company_urn(db)
                    print(f"Generated URN for company '{comp.name}': {comp.urn}")

                # ----------------------------------------------------------
                # 3.  Add company urn to neo4j, assuming it doesn't exist
                # ----------------------------------------------------------
                print(
                    f"Ensuring company '{comp.name}' with URN '{comp.urn}' exists in Neo4j."
                )
                _ensure_urn_in_db(db, comp)
                print(f"Company '{comp.name}' is now ensured in Neo4j.")

        print("Finished processing all experience entries.")
        print(f"Returning profile with expriences: {profile.experience}")
        return profile

    finally:
        if owns_db:
            print("Closing the Neo4jDatabase instance.")
            db.close()
