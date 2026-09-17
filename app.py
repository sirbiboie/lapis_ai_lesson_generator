import io
import re
import streamlit as st
from google import genai
from google.genai import types
from docx import Document
from docx.shared import Inches

# ---------------------------------------------------------
# 1. PAGE SETUP & CUSTOM STYLING (CSS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="ILAW AI Lesson Plan Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, clean UI components
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    
    .ilaw-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .ilaw-header h1 {
        color: white !important;
        margin-bottom: 0.2rem;
        font-weight: 700;
    }
    .ilaw-header p {
        color: #e0e7ff;
        font-size: 1.1rem;
    }

    div[data-testid="stForm"] {
        background-color: white;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }

    .output-card {
        background-color: white;
        padding: 2rem;
        border-radius: 12px;
        border-left: 6px solid #2563eb;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-top: 1.5rem;
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Render Header Banner
st.markdown("""
    <div class="ilaw-header">
        <h1>🎓 ILAW AI Lesson Plan Generator</h1>
        <p>Philippine Elementary Instructional Design Assistant • DepEd MATATAG Aligned Framework (3-Term Format)</p>
    </div>
""", unsafe_allow_html=True)

# Retrieve API Key directly from secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")

# Initialize Session State Variables
if "history" not in st.session_state:
    st.session_state["history"] = []
if "current_plan" not in st.session_state:
    st.session_state["current_plan"] = None

# ---------------------------------------------------------
# 2. SIDEBAR CONFIGURATION & LESSON HISTORY
# ---------------------------------------------------------
st.sidebar.header("📚 Saved Session History")

if st.session_state["history"]:
    for idx, item in enumerate(st.session_state["history"]):
        button_label = f"📌 {item['grade']} ({item['term']}) - {item['topic']}"
        if st.sidebar.button(button_label, key=f"hist_{idx}"):
            st.session_state["current_plan"] = item["content"]
            st.session_state["file_prefix"] = item["prefix"]
            
    if st.sidebar.button("🗑️ Clear History", type="secondary"):
        st.session_state["history"] = []
        st.session_state["current_plan"] = None
        st.rerun()
else:
    st.sidebar.info("No generated plans in this session yet.")

# ---------------------------------------------------------
# 3. FORM INPUTS (CLEAN UI)
# ---------------------------------------------------------
ELEMENTARY_GRADES = [
    "Kindergarten",
    "Grade 1",
    "Grade 2",
    "Grade 3",
    "Grade 4",
    "Grade 5",
    "Grade 6"
]

ELEMENTARY_SUBJECTS = [
    "Makabansa",
    "GMRC / Values Education",
    "Language",
    "Reading & Literacy",
    "Mathematics",
    "Science",
    "English",
    "Filipino",
    "Araling Panlipunan",
    "MAPEH (Music, Arts, PE, Health)",
    "EPP / TLE",
    "Kindergarten Learning Areas"
]

st.subheader("📋 Lesson Details")

with st.form("ilaw_form"):
    col1, col2 = st.columns(2)

    with col1:
        competency = st.text_area(
            "Learning Competency (Required)*",
            value="",
            placeholder="e.g., Identify living and non-living things found in a local ecosystem."
        )
        activity_count = st.selectbox("Activity Count (Required)*", [1, 3, 5], index=1)
        grade_level = st.selectbox("Grade Level", ELEMENTARY_GRADES)
        learning_area = st.selectbox("Learning Area / Subject", ELEMENTARY_SUBJECTS)

    with col2:
        topic = st.text_input("Topic", value="", placeholder="e.g., Ecosystems and Environment")
        academic_term = st.selectbox("Academic Term", ["Term 1", "Term 2", "Term 3"])
        time_allotment = st.text_input("Time Allotment", value="60 minutes")
        available_resources = st.text_input(
            "Available Resources",
            value="",
            placeholder="e.g., Whiteboard, chart papers, plant picture cards"
        )

    submitted = st.form_submit_button("✨ Generate ILAW Lesson Plan", use_container_width=True)

# ---------------------------------------------------------
# 4. MASTER SYSTEM PROMPT & DOCX HELPER
# ---------------------------------------------------------
MASTER_SYSTEM_PROMPT = """
You are an expert Philippine elementary instructional designer, curriculum-alignment assistant, and ILAW lesson-planning specialist.
Your task is to transform teacher-provided curriculum competencies and lesson requirements into a complete, practical, developmentally appropriate, and teacher-editable ILAW lesson plan tailored to the Philippine 3-Term Academic Calendar and DepEd MATATAG Standards.

CORE INSTRUCTIONAL MODEL:
COMPETENCY -> INTENTIONS -> LEARNING EXPERIENCES -> ASSESSING LEARNING -> WAYS FORWARD

EXACT KSA OBJECTIVE RULE:
Every generated lesson MUST contain exactly THREE objectives:
- K (Knowledge): Exactly 1 objective.
- S (Skills): Exactly 1 objective.
- A (Attitude): Exactly 1 objective.

ACTIVITY COUNT RULE:
Generate EXACTLY the requested activity_count of main activities (1, 3, or 5).

ACADEMIC TERM CONTEXT:
The lesson plan must explicitly reflect the 3-Term Academic Format (Term 1, Term 2, or Term 3) in its metadata section.

OUTPUT FORMAT:
Generate the lesson adhering strictly to the ILAW LESSON PLAN structure:
1. Lesson Information (Include Grade Level, Subject, Topic, Academic Term, Time Allotment)
2. I — INTENTIONS
3. L — LEARNING EXPERIENCES
4. A — ASSESSING LEARNING
5. W — WAYS FORWARD
6. Resources
7. Teacher Notes
"""

def create_clean_docx(text_content):
    doc = Document()
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    lines = text_content.split("\n")
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
            
        if clean_line.startswith("#"):
            header_level = min(clean_line.count("#"), 3)
            heading_text = re.sub(r"^#+\s*", "", clean_line).replace("**", "").replace("*", "")
            doc.add_heading(heading_text, level=header_level)
        elif clean_line.startswith("* ") or clean_line.startswith("- "):
            bullet_text = re.sub(r"^[\*\-]\s*", "", clean_line).replace("**", "").replace("*", "")
            doc.add_paragraph(bullet_text, style='List Bullet')
        else:
            body_text = clean_line.replace("**", "").replace("*", "")
            doc.add_paragraph(body_text)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# ---------------------------------------------------------
# 5. GENERATION LOGIC & RESULT RENDERING
# ---------------------------------------------------------
if submitted:
    if not api_key:
        st.error("API Key not found. Please set `GEMINI_API_KEY` in your `.streamlit/secrets.toml` file.")
    elif not competency.strip():
        st.error("Please enter a Learning Competency before generating.")
    else:
        try:
            client = genai.Client(api_key=api_key)

            user_payload = f"""
            competency: {competency}
            activity_count: {activity_count}
            grade_level: {grade_level}
            learning_area: {learning_area}
            topic: {topic}
            academic_term: {academic_term}
            time_allotment: {time_allotment}
            available_resources: {available_resources}
            """

            with st.spinner("Generating DepEd MATATAG-aligned ILAW lesson plan..."):
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=user_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=MASTER_SYSTEM_PROMPT,
                        temperature=0.3,
                        tools=[]
                    )
                )

            plan_prefix = f"ILAW_{grade_level}_{academic_term}_{topic if topic else 'Lesson'}".replace(" ", "_")
            st.session_state["current_plan"] = response.text
            st.session_state["file_prefix"] = plan_prefix
            
            st.session_state["history"].append({
                "grade": grade_level,
                "term": academic_term,
                "topic": topic if topic else "Lesson",
                "content": response.text,
                "prefix": plan_prefix
            })

        except Exception as e:
            st.error(f"An error occurred: {e}")

# Render Active Generated Plan
if st.session_state["current_plan"]:
    st.divider()
    st.markdown('<div class="output-card">', unsafe_allow_html=True)
    st.success("✅ ILAW Lesson Plan Ready!")
    st.markdown(st.session_state["current_plan"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📥 Export Lesson Plan")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.download_button(
            label="📄 Download Clean Word Document (.docx)",
            data=create_clean_docx(st.session_state["current_plan"]),
            file_name=f"{st.session_state['file_prefix']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
        
    with col_dl2:
        st.download_button(
            label="📝 Download Text File (.txt)",
            data=st.session_state["current_plan"],
            file_name=f"{st.session_state['file_prefix']}.txt",
            mime="text/plain",
            use_container_width=True
        )