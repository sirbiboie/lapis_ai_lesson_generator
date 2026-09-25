import io
import json
import re
import time
import streamlit as st
from google import genai
from google.genai import types
from docxtpl import DocxTemplate

# ---------------------------------------------------------
# 1. PAGE SETUP & LAPIS BRANDING
# ---------------------------------------------------------
st.set_page_config(
    page_title="LAPIS AI | DepEd Revised K to 10 Lesson Plan Generator",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern LAPIS Interface + Soft Blue Mesh Background
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f7ff;
        background-image: 
            radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.12) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(245, 158, 11, 0.10) 0px, transparent 50%),
            radial-gradient(at 50% 100%, rgba(30, 58, 138, 0.12) 0px, transparent 50%);
        background-attachment: fixed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.08);
    }

    .lapis-card {
        background-color: #ffffff !important;
        padding: 1.75rem;
        border-radius: 12px;
        border: 1px solid #cbd5e1 !important;
        border-left: 6px solid #2563eb !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.25rem;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: none;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }

    .metric-card {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
""", unsafe_allow_html=True)

# Display Top Banner Image
try:
    st.image("banner.png", use_container_width=True)
except Exception:
    st.title("✏️ LAPIS AI Assistant")
    st.caption("DepEd Revised K to 10 Curriculum Aligned")

# Retrieve API Key directly from secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")

# Initialize Session State
if "history" not in st.session_state:
    st.session_state["history"] = []
if "current_plan" not in st.session_state:
    st.session_state["current_plan"] = None

# ---------------------------------------------------------
# 2. SIDEBAR CONFIGURATION & HISTORY
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## ✏️ LAPIS AI Controls")
    st.caption("AI Assistant for DepEd Revised K to 10 Framework")
    
    st.divider()
    
    st.subheader("👤 Teacher Profile")
    saved_teacher = st.text_input("Default Teacher Name", value="Juan Dela Cruz")
    saved_position = st.text_input("Default Position / Title", value="Teacher I")
    
    st.divider()
    
    st.subheader("📚 Saved Sessions")
    if st.session_state["history"]:
        st.caption(f"{len(st.session_state['history'])} plan(s) generated in this session")
        for idx, item in enumerate(reversed(st.session_state["history"])):
            button_label = f"📌 {item['grade']} - {item['topic']}"
            if st.button(button_label, key=f"hist_{idx}", use_container_width=True):
                st.session_state["current_plan"] = item["json_data"]
                st.session_state["file_prefix"] = item["prefix"]
        
        st.write("")
        if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
            st.session_state["history"] = []
            st.session_state["current_plan"] = None
            st.rerun()
    else:
        st.info("No generated plans stored in session.")

# ---------------------------------------------------------
# 3. FORM INPUTS (REVISED K TO 10 CURRICULUM ALIGNED)
# ---------------------------------------------------------
GRADE_LEVELS = [
    "Kindergarten", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10"
]

REVISED_K10_SUBJECTS = [
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

st.subheader("📋 Step 1: Input Curriculum Details")

with st.form("lapis_form"):
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("##### 📌 Basic Information")
        teacher_name = st.text_input("Teacher Name*", value=saved_teacher)
        position = st.text_input("Position / Title", value=saved_position)
        grade_level = st.selectbox("Grade Level", GRADE_LEVELS)
        section_class = st.text_input("Section / Class", placeholder="e.g., Section Sampaguita")
        subject = st.selectbox("Revised K to 10 Learning Area", REVISED_K10_SUBJECTS)
        lesson_name = st.text_input("Lesson Title / Topic*", placeholder="e.g., Ecosystems and Interdependence")

    with col2:
        st.markdown("##### 🎯 Revised K to 10 Alignment & Depth")
        competency = st.text_area(
            "Learning Competency (Required)*",
            placeholder="Paste standard competency from the Revised K to 10 Curriculum Guide (e.g., Identify living and non-living components of an ecosystem).",
            height=100
        )
        
        detail_mode = st.radio(
            "⚡ Detail Level & Instruction Depth",
            options=["Comprehensive / Ultra-Detailed (Scripted Steps)", "Standard (Concise Structure)"],
            index=0,
            help="Ultra-detailed mode includes verbatim teacher scripts, expected student responses, explicit activity procedures, and time allocations."
        )

        duration = st.text_input("Duration / Period", value="1 Session (45-60 minutes)")
        activity_count = st.select_slider(
            "Activity Structure Rule", 
            options=[1, 3, 5], 
            value=3,
            help="1 = Minimal/Focused, 3 = Standard Balanced, 5 = Comprehensive Multi-Activity Flow"
        )
        learner_context = st.text_input(
            "Learner Context (Optional)",
            placeholder="e.g., Kinesthetic learners, differentiated support for struggling readers."
        )
        references = st.text_input(
            "References (Optional)",
            placeholder="e.g., DepEd Revised K to 10 Curriculum Guide, LRMDS Portal"
        )

    st.write("")
    submitted = st.form_submit_button("✨ Generate LAPIS Lesson Plan", type="primary", use_container_width=True)

# ---------------------------------------------------------
# 4. SYSTEM PROMPT
# ---------------------------------------------------------
MASTER_SYSTEM_PROMPT = """
You are LAPIS (Learner-Centered & AI-Powered Instructional System), an expert master instructional designer for the Department of Education (DepEd) Philippines, adhering strictly to the DepEd Revised K to 10 Curriculum framework.

Your task is to generate an EXTREMELY DETAILED, highly actionable lesson plan formatted STRICTLY as a raw JSON object matching the exact key structure provided below. Do NOT output markdown code blocks (e.g., ```json), plain text explanations, or extra commentary. Output ONLY valid JSON.

JSON STRUCTURE TO FOLLOW STRICTLY:
{
  "ai_declaration": "Generated using LAPIS AI Assistant aligned with the DepEd Revised K to 10 Curriculum Framework.",
  "intentions_objectives": [
    "Knowledge (K): Exactly 1 highly specific knowledge objective aligned with the Revised K to 10 competency.",
    "Skills (S): Exactly 1 skill/performance objective focusing on concrete learner output.",
    "Attitude (A): Exactly 1 attitude or values integration objective (GMRC/Makabansa)."
  ],
  "pre_lesson": "Comprehensive warm-up or prior knowledge review activity including exact teacher script/questions and anticipated student responses.",
  "learning_steps": [
    {
      "phase": "Introduction & Motivation",
      "details": "Thorough breakdown of phase goals, time management, and teacher setup.",
      "activities": [
        {
          "activity_name": "Activity 1 Title",
          "description": "Exhaustive, step-by-step instructions. Include explicit teacher directives ('Teacher says:...'), expected learner behavior ('Students will:...'), grouping details, exact activity rules, and discussion prompts."
        }
      ]
    },
    {
      "phase": "Main Guided Practice",
      "details": "Thorough instructional breakdown of core learning tasks.",
      "activities": [
        {
          "activity_name": "Activity Title",
          "description": "Step-by-step execution procedure with fully articulated instructions, worksheet/task card directions, scaffolded teacher assistance steps, and check-for-understanding questions."
        }
      ]
    },
    {
      "phase": "Wrap-Up & Reflection",
      "details": "Synthesis and meta-cognitive reflection overview.",
      "activities": [
        {
          "activity_name": "Synthesis Activity",
          "description": "Complete consolidation protocol including guided reflection questions, student recap procedures, and values connection."
        }
      ]
    }
  ],
  "learning_resources": "Exhaustive list of physical, printed, and digital materials, task cards, visual aids, and manipulatives required.",
  "opportunities_for_integration": "Concrete, actionable integration of values (GMRC), literacy, numeracy, cross-disciplinary links, and patriotic/community context (Makabansa).",
  "assessment_tasks": [
    {
      "task": "Fully detailed formative or summative assessment task with complete test items, prompt instructions, or rubric criteria.",
      "accommodation": "Detailed differentiated support strategies for struggling learners, fast finishers, and diverse learning styles."
    }
  ],
  "extended_learning": "Detailed enrichment or remediation activity to be performed outside regular classroom hours.",
  "reflections": "Specific post-lesson evaluation questions for teacher self-reflection on learner engagement, mastery rate, and instructional effectiveness."
}

EXACT OBJECTIVE RULE:
`intentions_objectives` MUST contain exactly THREE items (1 Knowledge, 1 Skills, 1 Attitude).

MAXIMUM DETAIL RULE:
When detailed instructions are requested, DO NOT write brief summaries or placeholders. Write full sentences, step-by-step numbered steps within descriptions, explicit teacher prompts, and thorough activity mechanics.
"""

def generate_docx_from_template(context):
    doc = DocxTemplate("ilaw_template.docx")
    doc.render(context)
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# ---------------------------------------------------------
# 5. GENERATION LOGIC WITH AUTO-FALLBACK & RETRIES
# ---------------------------------------------------------
if submitted:
    if not api_key:
        st.error("🔑 API Key not found. Please configure `GEMINI_API_KEY` in `.streamlit/secrets.toml`.")
    elif not competency.strip() or not lesson_name.strip():
        st.warning("⚠️ Please fill in all required fields: Lesson Title and Learning Competency.")
    else:
        candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        
        user_payload = f"""
        lesson_name: {lesson_name}
        subject: {subject}
        teacher_name: {teacher_name if teacher_name else 'DepEd Teacher'}
        position: {position}
        grade_level: {grade_level}
        section_class: {section_class if section_class else 'All Sections'}
        duration: {duration}
        detail_level: {detail_mode}
        references: {references if references else 'DepEd Revised K to 10 Curriculum Guide'}
        competency: {competency}
        activity_count: {activity_count}
        learner_context: {learner_context if learner_context else 'General elementary learners'}
        
        SPECIAL INSTRUCTION: Please provide maximal instructional detail, complete teacher scripting, step-by-step procedures, and explicit student tasks according to the detail level selected: {detail_mode}.
        """

        response = None
        success = False
        last_error_msg = ""

        with st.spinner("✏️ LAPIS is crafting your detailed Revised K to 10 lesson plan..."):
            try:
                client = genai.Client(api_key=api_key)
                
                for model_name in candidate_models:
                    for attempt in range(2):
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=user_payload,
                                config=types.GenerateContentConfig(
                                    system_instruction=MASTER_SYSTEM_PROMPT,
                                    temperature=0.2,
                                    response_mime_type="application/json",
                                    tools=[]
                                )
                            )
                            success = True
                            break
                        except Exception as err:
                            last_error_msg = str(err)
                            if "503" in last_error_msg or "UNAVAILABLE" in last_error_msg:
                                time.sleep(2)
                                continue
                            else:
                                break
                    if success:
                        break
            except Exception as e:
                last_error_msg = str(e)

        if not success or not response:
            st.error(f"❌ Failed to generate lesson plan. API Error Details: {last_error_msg}")
        else:
            clean_text = response.text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r'''^```(?:json)?\n?''', '', clean_text)
                clean_text = re.sub(r'''\n?```$''', '', clean_text)

            try:
                ai_data = json.loads(clean_text)
            except json.JSONDecodeError:
                st.error("❌ Failed to parse AI response into structured JSON. Please click 'Generate' again.")
                st.stop()

            full_context = {
                "lesson_name": lesson_name,
                "subject": subject,
                "teacher_name": teacher_name if teacher_name else "DepEd Teacher",
                "position": position,
                "grade_level": grade_level,
                "section_class": section_class if section_class else "All Sections",
                "duration": duration,
                "references": references if references else "DepEd Revised K to 10 Curriculum Guide",
                "competency": competency,
                "learner_context": learner_context if learner_context else "General elementary learners",
                **ai_data
            }

            plan_prefix = f"LAPIS_{grade_level}_{lesson_name}".replace(" ", "_")
            st.session_state["current_plan"] = full_context
            st.session_state["file_prefix"] = plan_prefix

            st.session_state["history"].append({
                "grade": grade_level,
                "topic": lesson_name,
                "json_data": full_context,
                "prefix": plan_prefix
            })

            st.toast("Detailed LAPIS Lesson Plan Generated Successfully!", icon="✏️")

# ---------------------------------------------------------
# 6. OUTPUT PRESENTATION
# ---------------------------------------------------------
if st.session_state["current_plan"]:
    data = st.session_state["current_plan"]

    st.divider()
    st.subheader("📄 Step 2: Review & Export")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["grade_level"]}</div><div class="metric-label">Grade Level</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["subject"]}</div><div class="metric-label">Learning Area</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["duration"]}</div><div class="metric-label">Duration</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(data.get("intentions_objectives", []))}</div><div class="metric-label">Target Objectives</div></div>', unsafe_allow_html=True)

    st.write("")

    tab_preview, tab_download, tab_json = st.tabs(["👁️ Plan Preview", "📥 Export Panel", "🔍 JSON Data"])

    with tab_preview:
        st.markdown(f"""
        <div class="lapis-card">
            <h3 style="margin-top:0; color:#1e3a8a;">{data['lesson_name']}</h3>
            <p style="color:#64748b; font-size:0.95rem;"><b>Teacher:</b> {data['teacher_name']} ({data['position']}) | <b>Section:</b> {data['section_class']}</p>
            <hr style="border:none; border-top:1px solid #e2e8f0; margin: 1rem 0;">
            <p><b>Revised K to 10 Learning Competency:</b> {data['competency']}</p>
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("#### 🎯 Intentions (K-S-A Objectives)")
            for obj in data.get("intentions_objectives", []):
                st.markdown(f"- {obj}")

            st.markdown("#### 🛠️ Learning Resources")
            st.info(data.get("learning_resources", "Standard instructional materials."))

            st.markdown("#### 🌐 Values & Subject Integration")
            st.caption(data.get("opportunities_for_integration", "N/A"))

        with col_right:
            st.markdown("#### 📝 Assessment Tasks & Accommodations")
            for task in data.get("assessment_tasks", []):
                st.markdown(f"- **Task:** {task.get('task', '')}")
                st.markdown(f"  *Accommodation Strategy:* `{task.get('accommodation', '')}`")

            st.markdown("#### 🚀 Extended Learning")
            st.write(data.get("extended_learning", "N/A"))

        st.markdown("---")
        st.markdown("#### 🗺️ Instructional Flow & Detailed Activities")
        st.markdown(f"**Pre-Lesson Warmup:** {data.get('pre_lesson', '')}")

        for step in data.get("learning_steps", []):
            with st.expander(f"📍 Phase: {step.get('phase', 'Lesson Phase')}", expanded=True):
                st.caption(step.get("details", ""))
                for act in step.get("activities", []):
                    st.markdown(f"**• {act.get('activity_name', '')}**")
                    st.write(act.get("description", ""))

    with tab_download:
        st.markdown("#### Download Formatted Official Document")
        st.write("Your document is ready to be exported into your official DepEd `.docx` template.")
        
        d_col1, d_col2 = st.columns([1, 1])
        
        with d_col1:
            try:
                docx_bytes = generate_docx_from_template(data)
                st.download_button(
                    label="📄 Download Formatted Word Document (.docx)",
                    data=docx_bytes,
                    file_name=f"{st.session_state['file_prefix']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True
                )
            except FileNotFoundError:
                st.error("`ilaw_template.docx` not found. Ensure your `.docx` template file is in the root project folder.")
            except Exception as e:
                st.error(f"Error rendering Word document: {e}")

        with d_col2:
            st.info("💡 **LAPIS Tip:** Downloaded `.docx` files preserve all table formatting, headers, and footers from your original template file.")

    with tab_json:
        st.markdown("#### Raw Template Context")
        st.json(data)import io
import json
import re
import streamlit as st
from google import genai
from google.genai import types
from docxtpl import DocxTemplate

# ---------------------------------------------------------
# 1. PAGE SETUP & LAPIS BRANDING
# ---------------------------------------------------------
st.set_page_config(
    page_title="LAPIS AI | DepEd Revised K to 10 Lesson Plan Generator",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern LAPIS Interface + Soft Blue Mesh Background
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f7ff;
        background-image: 
            radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.12) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(245, 158, 11, 0.10) 0px, transparent 50%),
            radial-gradient(at 50% 100%, rgba(30, 58, 138, 0.12) 0px, transparent 50%);
        background-attachment: fixed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.08);
    }

    .lapis-card {
        background-color: #ffffff !important;
        padding: 1.75rem;
        border-radius: 12px;
        border: 1px solid #cbd5e1 !important;
        border-left: 6px solid #2563eb !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.25rem;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: none;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }

    .metric-card {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
""", unsafe_allow_html=True)

# Display Top Banner Image
try:
    st.image("banner.png", use_container_width=True)
except Exception:
    st.title("✏️ LAPIS AI Assistant")
    st.caption("DepEd Revised K to 10 Curriculum Aligned")

# Retrieve API Key directly from secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")

# Initialize Session State
if "history" not in st.session_state:
    st.session_state["history"] = []
if "current_plan" not in st.session_state:
    st.session_state["current_plan"] = None

# ---------------------------------------------------------
# 2. SIDEBAR CONFIGURATION & HISTORY
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## ✏️ LAPIS AI Controls")
    st.caption("AI Assistant for DepEd Revised K to 10 Framework")
    
    st.divider()
    
    st.subheader("👤 Teacher Profile")
    saved_teacher = st.text_input("Default Teacher Name", value="Juan Dela Cruz")
    saved_position = st.text_input("Default Position / Title", value="Teacher I")
    
    st.divider()
    
    st.subheader("📚 Saved Sessions")
    if st.session_state["history"]:
        st.caption(f"{len(st.session_state['history'])} plan(s) generated in this session")
        for idx, item in enumerate(reversed(st.session_state["history"])):
            button_label = f"📌 {item['grade']} - {item['topic']}"
            if st.button(button_label, key=f"hist_{idx}", use_container_width=True):
                st.session_state["current_plan"] = item["json_data"]
                st.session_state["file_prefix"] = item["prefix"]
        
        st.write("")
        if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
            st.session_state["history"] = []
            st.session_state["current_plan"] = None
            st.rerun()
    else:
        st.info("No generated plans stored in session.")

# ---------------------------------------------------------
# 3. FORM INPUTS (REVISED K TO 10 CURRICULUM ALIGNED)
# ---------------------------------------------------------
GRADE_LEVELS = [
    "Kindergarten", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10"
]

REVISED_K10_SUBJECTS = [
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

st.subheader("📋 Step 1: Input Curriculum Details")

with st.form("lapis_form"):
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("##### 📌 Basic Information")
        teacher_name = st.text_input("Teacher Name*", value=saved_teacher)
        position = st.text_input("Position / Title", value=saved_position)
        grade_level = st.selectbox("Grade Level", GRADE_LEVELS)
        section_class = st.text_input("Section / Class", placeholder="e.g., Section Sampaguita")
        subject = st.selectbox("Revised K to 10 Learning Area", REVISED_K10_SUBJECTS)
        lesson_name = st.text_input("Lesson Title / Topic*", placeholder="e.g., Ecosystems and Interdependence")

    with col2:
        st.markdown("##### 🎯 Revised K to 10 Alignment & Depth")
        competency = st.text_area(
            "Learning Competency (Required)*",
            placeholder="Paste standard competency from the Revised K to 10 Curriculum Guide (e.g., Identify living and non-living components of an ecosystem).",
            height=100
        )
        
        # New Detail Mode Selection Feature
        detail_mode = st.radio(
            "⚡ Detail Level & Instruction Depth",
            options=["Comprehensive / Ultra-Detailed (Scripted Steps)", "Standard (Concise Structure)"],
            index=0,
            help="Ultra-detailed mode includes verbatim teacher scripts, expected student responses, explicit activity procedures, and time allocations."
        )

        duration = st.text_input("Duration / Period", value="1 Session (45-60 minutes)")
        activity_count = st.select_slider(
            "Activity Structure Rule", 
            options=[1, 3, 5], 
            value=3,
            help="1 = Minimal/Focused, 3 = Standard Balanced, 5 = Comprehensive Multi-Activity Flow"
        )
        learner_context = st.text_input(
            "Learner Context (Optional)",
            placeholder="e.g., Kinesthetic learners, differentiated support for struggling readers."
        )
        references = st.text_input(
            "References (Optional)",
            placeholder="e.g., DepEd Revised K to 10 Curriculum Guide, LRMDS Portal"
        )

    st.write("")
    submitted = st.form_submit_button("✨ Generate LAPIS Lesson Plan", type="primary", use_container_width=True)

# ---------------------------------------------------------
# 4. SYSTEM PROMPT
# ---------------------------------------------------------
MASTER_SYSTEM_PROMPT = """
You are LAPIS (Learner-Centered & AI-Powered Instructional System), an expert master instructional designer for the Department of Education (DepEd) Philippines, adhering strictly to the DepEd Revised K to 10 Curriculum framework.

Your task is to generate an EXTREMELY DETAILED, highly actionable lesson plan formatted STRICTLY as a raw JSON object matching the exact key structure provided below. Do NOT output markdown code blocks (e.g., ```json), plain text explanations, or extra commentary. Output ONLY valid JSON.

JSON STRUCTURE TO FOLLOW STRICTLY:
{
  "ai_declaration": "Generated using LAPIS AI Assistant aligned with the DepEd Revised K to 10 Curriculum Framework.",
  "intentions_objectives": [
    "Knowledge (K): Exactly 1 highly specific knowledge objective aligned with the Revised K to 10 competency.",
    "Skills (S): Exactly 1 skill/performance objective focusing on concrete learner output.",
    "Attitude (A): Exactly 1 attitude or values integration objective (GMRC/Makabansa)."
  ],
  "pre_lesson": "Comprehensive warm-up or prior knowledge review activity including exact teacher script/questions and anticipated student responses.",
  "learning_steps": [
    {
      "phase": "Introduction & Motivation",
      "details": "Thorough breakdown of phase goals, time management, and teacher setup.",
      "activities": [
        {
          "activity_name": "Activity 1 Title",
          "description": "Exhaustive, step-by-step instructions. Include explicit teacher directives ('Teacher says:...'), expected learner behavior ('Students will:...'), grouping details, exact activity rules, and discussion prompts."
        }
      ]
    },
    {
      "phase": "Main Guided Practice",
      "details": "Thorough instructional breakdown of core learning tasks.",
      "activities": [
        {
          "activity_name": "Activity Title",
          "description": "Step-by-step execution procedure with fully articulated instructions, worksheet/task card directions, scaffolded teacher assistance steps, and check-for-understanding questions."
        }
      ]
    },
    {
      "phase": "Wrap-Up & Reflection",
      "details": "Synthesis and meta-cognitive reflection overview.",
      "activities": [
        {
          "activity_name": "Synthesis Activity",
          "description": "Complete consolidation protocol including guided reflection questions, student recap procedures, and values connection."
        }
      ]
    }
  ],
  "learning_resources": "Exhaustive list of physical, printed, and digital materials, task cards, visual aids, and manipulatives required.",
  "opportunities_for_integration": "Concrete, actionable integration of values (GMRC), literacy, numeracy, cross-disciplinary links, and patriotic/community context (Makabansa).",
  "assessment_tasks": [
    {
      "task": "Fully detailed formative or summative assessment task with complete test items, prompt instructions, or rubric criteria.",
      "accommodation": "Detailed differentiated support strategies for struggling learners, fast finishers, and diverse learning styles."
    }
  ],
  "extended_learning": "Detailed enrichment or remediation activity to be performed outside regular classroom hours.",
  "reflections": "Specific post-lesson evaluation questions for teacher self-reflection on learner engagement, mastery rate, and instructional effectiveness."
}

EXACT OBJECTIVE RULE:
`intentions_objectives` MUST contain exactly THREE items (1 Knowledge, 1 Skills, 1 Attitude).

MAXIMUM DETAIL RULE:
When detailed instructions are requested, DO NOT write brief summaries or placeholders. Write full sentences, step-by-step numbered steps within descriptions, explicit teacher prompts, and thorough activity mechanics.
"""

def generate_docx_from_template(context):
    doc = DocxTemplate("ilaw_template.docx")
    doc.render(context)
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

import time

# ---------------------------------------------------------
# 5. GENERATION LOGIC WITH AUTO-FALLBACK & RETRIES
# ---------------------------------------------------------
if submitted:
    if not api_key:
        st.error("🔑 API Key not found. Please configure `GEMINI_API_KEY` in `.streamlit/secrets.toml`.")
    elif not competency.strip() or not lesson_name.strip():
        st.warning("⚠️ Please fill in all required fields: Lesson Title and Learning Competency.")
    else:
        # List of models to try sequentially if one is experiencing high demand (503)
        candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        
        user_payload = f"""
        lesson_name: {lesson_name}
        subject: {subject}
        teacher_name: {teacher_name if teacher_name else 'DepEd Teacher'}
        position: {position}
        grade_level: {grade_level}
        section_class: {section_class if section_class else 'All Sections'}
        duration: {duration}
        detail_level: {detail_mode}
        references: {references if references else 'DepEd Revised K to 10 Curriculum Guide'}
        competency: {competency}
        activity_count: {activity_count}
        learner_context: {learner_context if learner_context else 'General elementary learners'}
        
        SPECIAL INSTRUCTION: Please provide maximal instructional detail, complete teacher scripting, step-by-step procedures, and explicit student tasks according to the detail level selected: {detail_mode}.
        """

        response = None
        success = False

        with st.spinner("✏️ LAPIS is crafting your detailed Revised K to 10 lesson plan..."):
            client = genai.Client(api_key=api_key)
            
            for model_name in candidate_models:
                # Attempt up to 2 retries per model if 503 occurs
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=user_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=MASTER_SYSTEM_PROMPT,
                                temperature=0.2,
                                response_mime_type="application/json",
                                tools=[]
                            )
                        )
                        success = True
                        break
                    except Exception as err:
                        err_msg = str(err)
                        if "503" in err_msg or "UNAVAILABLE" in err_msg:
                            time.sleep(2)  # Short pause before retry
                            continue
                        else:
                            raise err
                if success:
                    break

        if not success or not response:
            st.error("⚠️ Google AI servers are experiencing extremely high global demand right now. Please wait 10 seconds and click Generate again.")
        else:
            clean_text = response.text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r'''^```(?:json)?\n?''', '', clean_text)
                clean_text = re.sub(r'''\n?```$''', '', clean_text)

            try:
                ai_data = json.loads(clean_text)
            except json.JSONDecodeError:
                st.error("❌ Failed to parse AI response into structured JSON. Please click 'Generate' again.")
                st.stop()

            full_context = {
                "lesson_name": lesson_name,
                "subject": subject,
                "teacher_name": teacher_name if teacher_name else "DepEd Teacher",
                "position": position,
                "grade_level": grade_level,
                "section_class": section_class if section_class else "All Sections",
                "duration": duration,
                "references": references if references else "DepEd Revised K to 10 Curriculum Guide",
                "competency": competency,
                "learner_context": learner_context if learner_context else "General elementary learners",
                **ai_data
            }

            plan_prefix = f"LAPIS_{grade_level}_{lesson_name}".replace(" ", "_")
            st.session_state["current_plan"] = full_context
            st.session_state["file_prefix"] = plan_prefix

            st.session_state["history"].append({
                "grade": grade_level,
                "topic": lesson_name,
                "json_data": full_context,
                "prefix": plan_prefix
            })

            st.toast("Detailed LAPIS Lesson Plan Generated Successfully!", icon="✏️")
# ---------------------------------------------------------
# 6. OUTPUT PRESENTATION
# ---------------------------------------------------------
if st.session_state["current_plan"]:
    data = st.session_state["current_plan"]

    st.divider()
    st.subheader("📄 Step 2: Review & Export")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["grade_level"]}</div><div class="metric-label">Grade Level</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["subject"]}</div><div class="metric-label">Learning Area</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{data["duration"]}</div><div class="metric-label">Duration</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(data.get("intentions_objectives", []))}</div><div class="metric-label">Target Objectives</div></div>', unsafe_allow_html=True)

    st.write("")

    tab_preview, tab_download, tab_json = st.tabs(["👁️ Plan Preview", "📥 Export Panel", "🔍 JSON Data"])

    with tab_preview:
        st.markdown(f"""
        <div class="lapis-card">
            <h3 style="margin-top:0; color:#1e3a8a;">{data['lesson_name']}</h3>
            <p style="color:#64748b; font-size:0.95rem;"><b>Teacher:</b> {data['teacher_name']} ({data['position']}) | <b>Section:</b> {data['section_class']}</p>
            <hr style="border:none; border-top:1px solid #e2e8f0; margin: 1rem 0;">
            <p><b>Revised K to 10 Learning Competency:</b> {data['competency']}</p>
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("#### 🎯 Intentions (K-S-A Objectives)")
            for obj in data.get("intentions_objectives", []):
                st.markdown(f"- {obj}")

            st.markdown("#### 🛠️ Learning Resources")
            st.info(data.get("learning_resources", "Standard instructional materials."))

            st.markdown("#### 🌐 Values & Subject Integration")
            st.caption(data.get("opportunities_for_integration", "N/A"))

        with col_right:
            st.markdown("#### 📝 Assessment Tasks & Accommodations")
            for task in data.get("assessment_tasks", []):
                st.markdown(f"- **Task:** {task.get('task', '')}")
                st.markdown(f"  *Accommodation Strategy:* `{task.get('accommodation', '')}`")

            st.markdown("#### 🚀 Extended Learning")
            st.write(data.get("extended_learning", "N/A"))

        st.markdown("---")
        st.markdown("#### 🗺️ Instructional Flow & Detailed Activities")
        st.markdown(f"**Pre-Lesson Warmup:** {data.get('pre_lesson', '')}")

        for step in data.get("learning_steps", []):
            with st.expander(f"📍 Phase: {step.get('phase', 'Lesson Phase')}", expanded=True):
                st.caption(step.get("details", ""))
                for act in step.get("activities", []):
                    st.markdown(f"**• {act.get('activity_name', '')}**")
                    st.write(act.get("description", ""))

    with tab_download:
        st.markdown("#### Download Formatted Official Document")
        st.write("Your document is ready to be exported into your official DepEd `.docx` template.")
        
        d_col1, d_col2 = st.columns([1, 1])
        
        with d_col1:
            try:
                docx_bytes = generate_docx_from_template(data)
                st.download_button(
                    label="📄 Download Formatted Word Document (.docx)",
                    data=docx_bytes,
                    file_name=f"{st.session_state['file_prefix']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True
                )
            except FileNotFoundError:
                st.error("`ilaw_template.docx` not found. Ensure your `.docx` template file is in the root project folder.")
            except Exception as e:
                st.error(f"Error rendering Word document: {e}")

        with d_col2:
            st.info("💡 **LAPIS Tip:** Downloaded `.docx` files preserve all table formatting, headers, and footers from your original template file.")

    with tab_json:
        st.markdown("#### Raw Template Context")
        st.json(data)
