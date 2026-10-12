import re
import streamlit as st

from src.helper import extract_text_from_pdf, ask_openai
from src.job_api import fetch_linkedin_jobs, fetch_naukri_jobs


st.set_page_config(
    page_title="AI Job Recommender",
    page_icon="💼",
    layout="wide"
)

st.title("AI Job Recommender")

st.markdown(
    "Upload your resume to analyze your skills, discover career opportunities, "
    "and find jobs from LinkedIn and Naukri."
)


# ==========================
# SESSION STATE
# ==========================

default_states = {
    "summary": "",
    "gaps": "",
    "roadmap": "",
    "resume_text": "",
    "linkedin_jobs": [],
    "naukri_jobs": [],
    "keywords": "",
    "career_title": "Suitable Career Path",
    "analysis_done": False,
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================
# HELPER FUNCTIONS
# ==========================

def is_error_response(response):
    """Detect errors returned as text by ask_openai()."""
    if not isinstance(response, str) or not response.strip():
        return True

    error_markers = (
        "Ollama Error:",
        "Ollama Cloud Error:",
        "Configuration Error:",
        "Error:",
    )

    return response.strip().startswith(error_markers)


def get_career_title(summary):
    """Ask the AI to identify a suitable job title."""
    prompt = f"""
Based on the resume summary below, identify the single most suitable
junior-level professional job title.

Return ONLY the job title, without explanation or Markdown.
Do not invent qualifications.

Resume summary:
{summary}
"""

    result = ask_openai(prompt, max_tokens=60)

    if is_error_response(result):
        return "Suitable Career Path"

    title = result.strip().strip('"').strip("'")
    title = title.replace("\n", " ")

    if not title:
        return "Suitable Career Path"

    return title[:100]


# ==========================
# UPLOAD CV
# ==========================

uploaded_file = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"],
    key="resume_upload"
)

if uploaded_file:
    file_signature = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state.get("file_signature") != file_signature:
        st.session_state["file_signature"] = file_signature
        st.session_state["summary"] = ""
        st.session_state["gaps"] = ""
        st.session_state["roadmap"] = ""
        st.session_state["resume_text"] = ""
        st.session_state["linkedin_jobs"] = []
        st.session_state["naukri_jobs"] = []
        st.session_state["keywords"] = ""
        st.session_state["career_title"] = "Suitable Career Path"
        st.session_state["analysis_done"] = False

    if not st.session_state["analysis_done"]:
        if st.button("📄 Analyze Resume", type="primary"):
            try:
                with st.spinner("Extracting resume text..."):
                    resume_text = extract_text_from_pdf(uploaded_file)
                    st.session_state["resume_text"] = resume_text

                if not resume_text.strip():
                    st.error(
                        "No readable text was found in this PDF. "
                        "Try a text-based PDF instead of a scanned image."
                    )
                    st.stop()

                with st.spinner("Generating resume summary..."):
                    summary = ask_openai(
                        f"""
Analyze the following resume and provide a clear, structured report.

Include:
1. Professional profile
2. Education
3. Professional experience and internships
4. Technical skills
5. Suitable junior-level job roles

Use concise headings and bullet points.
Do not invent information not present in the resume.

Resume:
{resume_text}
""",
                        max_tokens=700
                    )

                if is_error_response(summary):
                    st.error(summary)
                    st.stop()

                st.session_state["summary"] = summary

                with st.spinner("Analyzing skill gaps..."):
                    gaps = ask_openai(
                        f"""
Analyze the resume and identify skills the candidate should develop
to improve their chances of getting a junior-level job.

Organize the answer into:
1. Existing strengths
2. Technical skills to improve
3. Missing or useful technologies
4. Communication and professional skills
5. Three priority actions

Be realistic. Do not claim a skill is missing unless the resume
provides insufficient evidence that the candidate has it.

Resume:
{resume_text}
""",
                        max_tokens=600
                    )

                if is_error_response(gaps):
                    st.warning(
                        "The resume summary was generated, but skill-gap "
                        "analysis failed."
                    )
                    st.error(gaps)
                    st.session_state["gaps"] = ""
                else:
                    st.session_state["gaps"] = gaps

                with st.spinner("Creating career roadmap..."):
                    roadmap = ask_openai(
                        f"""
Create a practical 6-month career roadmap for this candidate.

Include:
- Month 1: foundations and skills assessment
- Months 2-3: technical learning and one practical project
- Months 4-5: portfolio, CV, GitHub and interview preparation
- Month 6: applications, networking and interview practice
- Relevant certifications, only where useful
- Measurable goals for each phase

Adapt the roadmap to the candidate's actual experience.
Prioritize junior-level opportunities.
Do not invent qualifications or guarantee employment.

Resume:
{resume_text}
""",
                        max_tokens=700
                    )

                if is_error_response(roadmap):
                    st.warning(
                        "The summary was generated, but career-roadmap "
                        "generation failed."
                    )
                    st.error(roadmap)
                    st.session_state["roadmap"] = ""
                else:
                    st.session_state["roadmap"] = roadmap

                with st.spinner("Identifying the best career path..."):
                    st.session_state["career_title"] = get_career_title(
                        st.session_state["summary"]
                    )

                st.session_state["analysis_done"] = True
                st.success("Resume analysis completed!")

            except Exception as e:
                st.error(
                    f"Resume analysis failed: {e}"
                )

    else:
        st.success("Resume analysis completed.")

        if st.button("🔄 Analyze Again"):
            st.session_state["summary"] = ""
            st.session_state["gaps"] = ""
            st.session_state["roadmap"] = ""
            st.session_state["analysis_done"] = False
            st.rerun()


# ==========================
# DISPLAY ANALYSIS
# ==========================

if st.session_state["summary"]:
    st.markdown("---")
    st.header("📄 Resume Summary")
    st.markdown(st.session_state["summary"])

    st.markdown("---")
    st.header("🛠️ Skill Gaps")

    if st.session_state["gaps"]:
        st.markdown(st.session_state["gaps"])
    else:
        st.info(
            "Skill-gap analysis is not available yet. "
            "Click Analyze Again to retry."
        )

    st.markdown("---")
    st.header(
        f"🚀 Career Roadmap for {st.session_state['career_title']}"
    )

    if st.session_state["roadmap"]:
        st.markdown(st.session_state["roadmap"])
    else:
        st.info(
            "The career roadmap is not available yet. "
            "Click Analyze Again to retry."
        )


# ==========================
# GET JOB RECOMMENDATIONS
# ==========================

st.markdown("---")
st.header("💼 Job Recommendations")

if st.button("🔍 Get Job Recommendations"):
    if not st.session_state["summary"]:
        st.warning("Please upload and analyze a resume first.")
    else:
        with st.spinner("Identifying suitable job titles..."):
            keywords = ask_openai(
                f"""
Based on this resume, return up to five suitable junior-level job titles.
Use comma-separated titles only.
Avoid senior roles and unrelated jobs.

Resume summary:
{st.session_state['summary']}
""",
                max_tokens=150
            )

        if is_error_response(keywords):
            st.error(keywords)
        else:
            keywords = re.sub(r"\s+", " ", keywords).strip()
            st.session_state["keywords"] = keywords

            st.write(f"Searching jobs for: **{keywords}**")

            with st.spinner("Searching LinkedIn jobs..."):
                try:
                    st.session_state["linkedin_jobs"] = (
                        fetch_linkedin_jobs(keywords, rows=30) or []
                    )
                except Exception:
                    st.session_state["linkedin_jobs"] = []
                    st.warning(
                        "LinkedIn job search failed. Check your Apify "
                        "API token, actor configuration and usage limits."
                    )

            with st.spinner("Searching Naukri jobs..."):
                try:
                    st.session_state["naukri_jobs"] = (
                        fetch_naukri_jobs(keywords, rows=30) or []
                    )
                except Exception:
                    st.session_state["naukri_jobs"] = []
                    st.warning(
                        "Naukri job search failed. Check your Apify "
                        "API token, actor configuration and usage limits."
                    )


# ==========================
# DISPLAY JOBS
# ==========================

def display_jobs(jobs, platform):
    st.subheader(f"💼 {platform}")

    if not jobs:
        st.info(
            f"No jobs to display from {platform}. "
            "The search may have returned no results or failed."
        )
        return

    for job in jobs:
        title = (
            job.get("title")
            or job.get("jobTitle")
            or job.get("jobRole")
            or "No title"
        )

        company = (
            job.get("companyName")
            or job.get("company")
            or job.get("hiringFor")
            or "Unknown company"
        )

        location = (
            job.get("location")
            or job.get("place")
            or job.get("city")
            or "Unknown location"
        )

        link = (
            job.get("link")
            or job.get("url")
            or job.get("jobUrl")
            or job.get("job_url")
            or job.get("jdURL")
        )

        st.markdown(f"### {title}")
        st.write(f"🏢 **Company:** {company}")
        st.write(f"📍 **Location:** {location}")

        if isinstance(link, str) and link.startswith(("https://", "http://")):
            st.link_button("🔗 View Job", link)
        else:
            st.caption("Job link unavailable")

        st.markdown("---")


if st.session_state["keywords"]:
    display_jobs(st.session_state["linkedin_jobs"], "LinkedIn Jobs")
    display_jobs(st.session_state["naukri_jobs"], "Naukri Jobs")
