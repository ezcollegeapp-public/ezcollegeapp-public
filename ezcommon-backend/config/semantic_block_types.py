"""
Semantic Block Types for College Application Documents

These 11 core block types are designed to work with ANY college application,
regardless of which specific documents or schools are involved.
"""

SEMANTIC_BLOCK_TYPES = {
    "PERSONAL_PROFILE": {
        "description": "Student's identity, contact information, and biographical data",
        "includes": [
            "Name (full, preferred, legal)",
            "Birthdate and age",
            "Contact information (email, phone, address)",
            "Citizenship status and birthplace",
            "Gender identity, pronouns, military status",
            "Language spoken at home",
            "Personal statement header/summary"
        ],
        "from_documents": ["Common App profile page", "Images with name", "Cover letters"],
        "use_case": "Answer: 'Tell us about the student'"
    },
    
    "ACADEMIC_PERFORMANCE": {
        "description": "Complete academic standing and performance metrics",
        "includes": [
            "High school/college attended",
            "Graduation date",
            "GPA (weighted, unweighted, unspecified)",
            "Class rank",
            "Current year courses",
            "Grades breakdown by grade level",
            "Academic progression notes"
        ],
        "from_documents": ["Transcripts", "Progress reports", "Academic pages"],
        "use_case": "Answer: 'What is the student's academic standing?'"
    },
    
    "STANDARDIZED_TESTING": {
        "description": "All standardized test scores and exam results",
        "includes": [
            "SAT scores (all components: Reading, Writing, Math)",
            "ACT scores (all components)",
            "Test dates taken",
            "Planned/future test dates",
            "AP exam results (all exams, scores, dates)",
            "IB exam scores if applicable",
            "Other standardized tests (TOEFL, IELTS, etc.)"
        ],
        "from_documents": ["AP/SAT/ACT score reports", "Testing section of applications", "Score cards"],
        "use_case": "Answer: 'What are the student's test scores?'"
    },
    
    "RESEARCH_EXPERIENCE": {
        "description": "Complete research projects with context and outcomes",
        "includes": [
            "Research project title",
            "Institution/lab name",
            "Duration and time commitment",
            "Mentor/advisor names and department",
            "Research methods and approach",
            "Outcomes and results",
            "Publications or presentations",
            "Skills developed"
        ],
        "from_documents": ["Activities section", "Resumes", "Research summaries", "Publication lists"],
        "use_case": "Answer: 'What research has the student conducted?'"
    },
    
    "AWARD_HONOR_RECOGNITION": {
        "description": "Individual awards, honors, and recognitions",
        "includes": [
            "Award/honor name",
            "Issuing organization or school",
            "Award date",
            "Award criteria or reason",
            "Award significance (regional, national, school-level)",
            "Certificate or image of award"
        ],
        "from_documents": ["Honors sections", "Award certificates", "Progress reports", "Images"],
        "use_case": "Answer: 'What awards has the student won?'"
    },
    
    "EXTRACURRICULAR_ACTIVITY": {
        "description": "Student's clubs, activities, and organizational involvement",
        "includes": [
            "Activity name and organization",
            "Role or position (member, leader, captain, founder)",
            "Years of involvement",
            "Time commitment (hours per week, weeks per year)",
            "Description of responsibilities",
            "Impact or achievements in activity",
            "Leadership development",
            "Related awards or recognitions"
        ],
        "from_documents": ["Activities section", "Resumes", "Event photos"],
        "use_case": "Answer: 'What clubs and activities is the student involved in?'"
    },
    
    "WORK_EXPERIENCE": {
        "description": "Employment history and job-related experiences",
        "includes": [
            "Job title",
            "Employer/organization name",
            "Duration of employment",
            "Hours per week and weeks per year",
            "Job responsibilities",
            "Skills developed or applied",
            "Achievements or outcomes",
            "Income or financial impact if applicable"
        ],
        "from_documents": ["Activities section", "Resumes", "Common App work section"],
        "use_case": "Answer: 'Has the student worked? What job experience do they have?'"
    },
    
    "FAMILY_BACKGROUND": {
        "description": "Family composition, parents' background, and household context",
        "includes": [
            "Parents' names and occupations",
            "Parents' education level",
            "Household composition (both parents, single parent, etc.)",
            "Number of siblings and their ages",
            "Household income bracket (if reported)",
            "Home language(s)",
            "First-generation college student status",
            "Special family circumstances"
        ],
        "from_documents": ["Family section", "Common App profile", "Demographic pages"],
        "use_case": "Answer: 'Tell us about the student's family background'"
    },
    
    "ESSAYS_WRITING": {
        "description": "Essays, personal statements, and supplemental writing",
        "includes": [
            "Essay title or prompt",
            "Full essay text/content",
            "Essay type (personal statement, why us, supplemental, etc.)",
            "Word count",
            "Theme or central message",
            "Writing quality and voice"
        ],
        "from_documents": ["Essays section", "Separate essay documents", "Writing samples"],
        "use_case": "Answer: 'Read the student's essays' or 'What are the student's writing strengths?'"
    },
    
    "INSTITUTIONAL_PREFERENCES": {
        "description": "College preferences and application-specific information",
        "includes": [
            "College/university name",
            "Intended major or program of study",
            "Preferred start term (Fall, Spring, etc.)",
            "Admission plan (Early Decision, Early Action, Regular Decision)",
            "Special program interests (honors college, scholarship, etc.)",
            "School-specific application responses",
            "Campus visit notes if provided"
        ],
        "from_documents": ["School-specific questions section", "College preference forms"],
        "use_case": "Answer: 'What schools is the student applying to?' or 'What are their academic interests?'"
    },
    
    "APPLICATION_METADATA": {
        "description": "Administrative and process information for the application",
        "includes": [
            "Application submission status and date",
            "Fee waiver status",
            "Contact preferences and consent",
            "FERPA waiver status",
            "Legal agreements and affirmations",
            "GPA/score reporting preferences",
            "Application portal access information"
        ],
        "from_documents": ["Application metadata sections", "Affirmations page"],
        "use_case": "Answer: 'What is the application processing status?'"
    }
}

# Summary of block types
BLOCK_TYPE_NAMES = list(SEMANTIC_BLOCK_TYPES.keys())

def get_block_type_description(block_type: str) -> str:
    """Get the description for a block type"""
    if block_type in SEMANTIC_BLOCK_TYPES:
        return SEMANTIC_BLOCK_TYPES[block_type]["description"]
    return "Unknown block type"

def get_all_block_types() -> list:
    """Get list of all available block types"""
    return BLOCK_TYPE_NAMES

def validate_block_type(block_type: str) -> bool:
    """Check if a block type is valid"""
    return block_type in SEMANTIC_BLOCK_TYPES
