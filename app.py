
import re
import os
import streamlit as st

from src.helper import extract_text_from_pdf, ask_openai
from src.job_api import fetch_linkedin_jobs, fetch_naukri_jobs


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI Job Recommender",
    page_icon="💼",
    layout="wide",
)

st.title("💼 AI Job Recommender")

st.markdown(
    """
    Upload your resume to analyze your skills, discover your career path,
    and search for relevant job opportunities.
    """
)


# =========================================================
# SESSION STATE
# =========================================================

DEFAULT_STATES = {
    "summary": "",
    "gaps": "",
    "roadmap": "",
    "resume_text": "",
    "linkedin_jobs": [],
    "naukri_jobs": [],
    "keywords": "",
    "career_title": "Suitable Career Path",
    "analysis_done": False,
    "analysis_errors": [],
    "linkedin_error": "",
    "naukri_error": "",
    "file_signature": "",
}

for key, value in DEFAULT_STATES.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def is_error_response(response):
    """Detect errors returned by the AI helper as text."""

    if not isinstance(response, str) or not response.strip():
        return True

    error_markers = (
        "Ollama Error:",
        "Ollama Cloud Error:",
        "Configuration Error:",
        "Error:",
    )

    return response.strip().startswith(error_markers)


def safe_error_message(error):
    """Avoid displaying API keys if an exception contains one."""

    message = f"{type(error).__name__}: {error}"

    for secret_name in ("APIFY_API_TOKEN", "OLLAMA_API_KEY"):
        secret = os.getenv(secret_name)

        if secret:
            message = message.replace(secret, "[REDACTED]")

    return message[:1000]


def reset_analysis():
    """Reset analysis results when the user wants to try again."""

    st.session_state["summary"] = ""
    st.session_state["gaps"] = ""
    st.session_state["roadmap"] = ""
    st.session_state["resume_text"] = ""
    st.session_state["keywords"] = ""
    st.session_state["career_title"] = "Suitable Career Path"
    st.session_state["analysis_done"] = False
    st.session_state["analysis_errors"] = []
    st.session_state["linkedin_jobs"] = []
    st.session_state["naukri_jobs"] = []
    st.session_state["linkedin_error"] = ""
    st.session_state["naukri_error"] = ""


def get_career_title(summary):
    """Generate a suitable career title from the CV summary."""

    prompt = f"""
You are a professional technical recruiter.

Choose ONE realistic junior-level job title for this candidate.
Use the technologies and experience actually mentioned in the resume.
Do not return generic answers such as Junior or Developer alone.

Return only the job title, without explanations.

Resume summary:
{summary[:6000]}
"""

    result = ask_openai(prompt, max_tokens=100)

    if is_error_response(result):
        return "Junior Full Stack Developer"

    title = re.sub(r"\s+", " ", result).strip().strip("\"'`")
    title = re.sub(r"^(job title|career path)\s*:\s*", "", title, flags=re.I)

    if (
        not title
        or len(title) < 5
        or title.lower() in {"junior", "developer", "software developer"}
    ):
        return "Junior Full Stack Developer"

    return title[:100]


def get_job_keywords(summary):
    """
    Ask the AI for several relevant job titles.
    Use a reliable fallback if the model returns a generic answer.
    """

    prompt = f"""
You are a technical recruitment specialist.

Recommend exactly five realistic job-search titles for this candidate.
Prioritize junior positions and technologies supported by the CV.

The titles may include PHP Laravel Developer, Junior Full Stack Developer,
Junior React Developer, Junior Java Spring Boot Developer, or Junior
Web Developer, but select titles according to the actual resume.

Rules:
- Return five distinct titles.
- Separate titles with commas.
- Never return only the word Junior.
- Do not include explanations or numbering.
- Do not invent skills.

Resume:
{summary[:6000]}
"""

    result = ask_openai(prompt, max_tokens=220)

    if is_error_response(result):
        return build_fallback_keywords(summary)

    result = re.sub(r"[\r\n]+", ",", result)
    result = re.sub(r"^\s*```.*?\n|\n```$", "", result, flags=re.S)
    titles = [
        re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", title).strip().strip("\"'`")
        for title in result.split(",")
    ]

    titles = [
        title for title in titles
        if len(title) >= 5
        and title.lower() not in {
            "junior",
            "developer",
            "software developer",
            "full stack",
        }
    ]

    # Remove duplicate titles while preserving order.
    unique_titles = []
    seen = set()

    for title in titles:
        normalized = title.casefold()

        if normalized not in seen:
            seen.add(normalized)
            unique_titles.append(title)

    # A generic or incomplete AI response should not be used.
    if len(unique_titles) < 3:
        return build_fallback_keywords(summary)

    return ", ".join(unique_titles[:5])


def build_fallback_keywords(summary):
    """Create sensible job titles if AI output is incomplete."""

    text = summary.lower()
    titles = []

    if "laravel" in text or "php" in text:
        titles.append("Junior PHP Laravel Developer")

    if "react" in text:
        titles.append("Junior React Developer")

    if "angular" in text:
        titles.append("Junior Angular Developer")

    if "spring boot" in text or "java" in text:
        titles.append("Junior Java Spring Boot Developer")

    if "mysql" in text or "full stack" in text:
        titles.append("Junior Full Stack Web Developer")

    if not titles:
        titles = [
            "Junior Web Developer",
            "Junior Full Stack Developer",
            "Junior Software Developer",
        ]

    return ", ".join(titles[:5])


def normalize_jobs(result):
    """Normalize Apify results into a list of job dictionaries."""

    if result is None:
        return []

    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]

    if isinstance(result, dict):
        # Some integrations return {"data": [...]} or {"items": [...]}.
        for key in ("data", "items", "jobs", "results"):
            value = result.get(key)

            if isinstance(value, list):
                return [
                    item for item in value
                    if isinstance(item, dict)
                ]

        # A single job object.
        if any(
            key in result
            for key in ("title", "jobTitle", "jobRole", "jobUrl", "url")
        ):
            return [result]

    return []


def display_jobs(jobs, platform):
    """Display job listings returned by the job-search integration."""

    st.subheader(f"💼 {platform}")

    if not jobs:
        st.info(
            f"No jobs are available from {platform}. "
            "Check the search result or the diagnostic message above."
        )
        return

    st.caption(f"{len(jobs)} job listing(s) returned.")

    for index, job in enumerate(jobs, start=1):
        title = (
            job.get("title")
            or job.get("jobTitle")
            or job.get("jobRole")
            or job.get("positionName")
            or "Title unavailable"
        )

        company = (
            job.get("companyName")
            or job.get("company")
            or job.get("hiringFor")
            or job.get("employer")
            or "Company unavailable"
        )

        location = (
            job.get("location")
            or job.get("place")
            or job.get("city")
            or job.get("jobLocation")
            or "Location unavailable"
        )

        link = (
            job.get("link")
            or job.get("url")
            or job.get("jobUrl")
            or job.get("job_url")
            or job.get("jdURL")
            or job.get("job_link")
        )

        with st.container(border=True):
            st.markdown(f"**{index}. {title}**")
            st.write(f"🏢 **Company:** {company}")
            st.write(f"📍 **Location:** {location}")

            if isinstance(link, str) and link.startswith(("https://", "http://")):
                st.link_button("🔗 View Job", link)
            else:
                st.caption("No valid job URL was provided by the source.")


# =========================================================
# CV UPLOAD
# =========================================================

uploaded_file = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"],
    key="resume_upload",
)

if uploaded_file:
    file_signature = f"{uploaded_file.name}_{uploaded_file.size}"

    if st.session_state["file_signature"] != file_signature:
        reset_analysis()
        st.session_state["file_signature"] = file_signature

    if not st.session_state["analysis_done"]:
        if st.button("📄 Analyze Resume", type="primary"):
            st.session_state["analysis_errors"] = []

            try:
                with st.spinner("📖 Extracting text from your CV..."):
                    resume_text = extract_text_from_pdf(uploaded_file)

                if not isinstance(resume_text, str) or not resume_text.strip():
                    st.error(
                        "No readable text was found in this PDF. "
                        "Try a text-based PDF instead of a scanned document."
                    )
                    st.stop()

                st.session_state["resume_text"] = resume_text

                # -----------------------------------------
                # 1. RESUME SUMMARY
                # -----------------------------------------

                with st.spinner("🧠 Generating your resume summary..."):
                    summary = ask_openai(
                        f"""
Analyze this resume and provide a clear, structured report.

Include:
1. Professional profile
2. Education
3. Internships and experience
4. Technical skills
5. Suitable junior-level job roles

Use concise headings and bullet points.
Do not invent information.

Resume:
{resume_text[:12000]}
""",
                        max_tokens=900,
                    )

                if is_error_response(summary):
                    st.error(f"Resume summary failed: {summary}")
                    st.stop()

                st.session_state["summary"] = summary

                # -----------------------------------------
                # 2. SKILL GAPS
                # -----------------------------------------

                with st.spinner("🛠️ Analyzing your skill gaps..."):
                    gaps = ask_openai(
                        f"""
Evaluate this candidate for junior web development positions.

Write a useful, detailed assessment with these sections:

## 1. Existing strengths
Identify the technologies and experience demonstrated by the CV.

## 2. Skills to improve
List specific technical skills worth strengthening.

## 3. Useful additional technologies
Suggest technologies only when relevant to the candidate's target roles.

## 4. Professional skills
Discuss communication, teamwork, Git, documentation and interviews
where relevant. Do not assume a skill is missing without evidence.

## 5. Three priority actions
Give three concrete actions the candidate can complete.

Be realistic. Distinguish between skills not mentioned in the CV
and skills the candidate demonstrably does not have.

Resume:
{resume_text[:10000]}
""",
                        max_tokens=900,
                    )

                if is_error_response(gaps):
                    st.session_state["gaps"] = ""
                    st.session_state["analysis_errors"].append(
                        f"Skill-gap analysis: {gaps}"
                    )
                else:
                    st.session_state["gaps"] = gaps

                # -----------------------------------------
                # 3. SIX-MONTH CAREER ROADMAP
                # -----------------------------------------

                with st.spinner("🚀 Creating your six-month roadmap..."):
                    roadmap = ask_openai(
                        f"""
Create a practical six-month career roadmap for this candidate.

Use the following sections:

## Month 1: Assessment and foundations
Identify the most important skills to assess and strengthen.

## Months 2-3: Learning and projects
Recommend focused learning and one practical project related to
the candidate's existing technologies.

## Months 4-5: Portfolio and interview preparation
Explain how to improve GitHub, portfolio, CV, technical projects
and interview skills.

## Month 6: Job applications
Suggest realistic application, networking and interview goals.

Include measurable objectives for each phase.
Recommend certifications only when relevant and useful.
Prioritize junior-level roles. Do not guarantee employment.

Resume:
{resume_text[:10000]}
""",
                        max_tokens=1000,
                    )

                if is_error_response(roadmap):
                    st.session_state["roadmap"] = ""
                    st.session_state["analysis_errors"].append(
                        f"Career roadmap: {roadmap}"
                    )
                else:
                    st.session_state["roadmap"] = roadmap

                # -----------------------------------------
                # 4. CAREER TITLE
                # -----------------------------------------

                with st.spinner("🎯 Identifying your career path..."):
                    st.session_state["career_title"] = get_career_title(
                        st.session_state["summary"]
                    )

                st.session_state["analysis_done"] = True

                if st.session_state["analysis_errors"]:
                    st.warning(
                        "The resume summary is ready, but some analysis "
                        "sections could not be generated. See the diagnostics "
                        "below."
                    )
                else:
                    st.success("Resume analysis completed successfully!")

                st.rerun()

            except Exception as error:
                st.error(
                    "Resume analysis failed: "
                    + safe_error_message(error)
                )

    else:
        st.success("Your resume has been analyzed.")

        if st.button("🔄 Analyze Again"):
            reset_analysis()
            st.rerun()


# =========================================================
# DISPLAY RESUME ANALYSIS
# =========================================================

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
            "Skill-gap analysis is not available. "
            "Review the diagnostic messages or click Analyze Again."
        )

    st.markdown("---")
    st.header(
        f"🚀 Six-Month Career Roadmap: "
        f"{st.session_state['career_title']}"
    )

    if st.session_state["roadmap"]:
        st.markdown(st.session_state["roadmap"])
    else:
        st.info(
            "The career roadmap could not be generated. "
            "Review the diagnostic messages or click Analyze Again."
        )

    if st.session_state["analysis_errors"]:
        with st.expander("⚠️ Analysis diagnostics"):
            for error in st.session_state["analysis_errors"]:
                st.error(error)


# =========================================================
# JOB RECOMMENDATIONS
# =========================================================

st.markdown("---")
st.header("💼 Job Recommendations")

st.write(
    "Search for jobs based on your CV using the LinkedIn and Naukri "
    "integrations configured in your project."
)

if st.button("🔍 Find Suitable Jobs", type="primary"):
    if not st.session_state["summary"]:
        st.warning("Please upload and analyze your resume first.")

    elif not os.getenv("APIFY_API_TOKEN"):
        st.error(
            "APIFY_API_TOKEN is missing from the application environment. "
            "Configure it in Streamlit Cloud → App settings → Secrets."
        )

    else:
        with st.spinner("🎯 Preparing relevant job-search titles..."):
            keywords = get_job_keywords(st.session_state["summary"])

        st.session_state["keywords"] = keywords
        st.session_state["linkedin_jobs"] = []
        st.session_state["naukri_jobs"] = []
        st.session_state["linkedin_error"] = ""
        st.session_state["naukri_error"] = ""

        st.write(f"**Search titles:** {keywords}")

        # -----------------------------------------
        # LINKEDIN SEARCH
        # -----------------------------------------

        with st.spinner("🔎 Searching LinkedIn through Apify..."):
            try:
                result = fetch_linkedin_jobs(keywords, rows=30)
                st.session_state["linkedin_jobs"] = normalize_jobs(result)

                if not st.session_state["linkedin_jobs"]:
                    st.session_state["linkedin_error"] = (
                        "The integration returned no job records. "
                        "This can mean no results were found, or that "
                        "src/job_api.py is swallowing an Apify error."
                    )

            except Exception as error:
                st.session_state["linkedin_jobs"] = []
                st.session_state["linkedin_error"] = safe_error_message(error)

        # -----------------------------------------
        # NAUKRI SEARCH
        # -----------------------------------------

        with st.spinner("🔎 Searching Naukri through Apify..."):
            try:
                result = fetch_naukri_jobs(keywords, rows=30)
                st.session_state["naukri_jobs"] = normalize_jobs(result)

                if not st.session_state["naukri_jobs"]:
                    st.session_state["naukri_error"] = (
                        "The integration returned no job records. "
                        "This can mean no results were found, or that "
                        "src/job_api.py is swallowing an Apify error."
                    )

            except Exception as error:
                st.session_state["naukri_jobs"] = []
                st.session_state["naukri_error"] = safe_error_message(error)

        st.rerun()


# =========================================================
# DISPLAY JOB SEARCH RESULTS
# =========================================================

if st.session_state["keywords"]:
    st.markdown("---")
    st.subheader("📊 Job Search Results")

    tab_linkedin, tab_naukri = st.tabs(["LinkedIn", "Naukri"])

    with tab_linkedin:
        if st.session_state["linkedin_error"]:
            st.warning(st.session_state["linkedin_error"])

        display_jobs(
            st.session_state["linkedin_jobs"],
            "LinkedIn Jobs",
        )

    with tab_naukri:
        if st.session_state["naukri_error"]:
            st.warning(st.session_state["naukri_error"])

        display_jobs(
            st.session_state["naukri_jobs"],
            "Naukri Jobs",
        )
