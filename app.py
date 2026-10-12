import streamlit as st
from src.helper import extract_text_from_pdf, ask_openai
from src.job_api import fetch_linkedin_jobs, fetch_naukri_jobs


st.set_page_config(
    page_title="Job Recommender",
    layout="wide"
)


st.title("AI Job Recommender")

st.markdown(
    "Upload your resume and get job recommendations based on your skills and experience from LinkedIn and Naukri."
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
    "keywords": ""

}


for key, value in default_states.items():

    if key not in st.session_state:
        st.session_state[key] = value




# ==========================
# UPLOAD CV
# ==========================


uploaded_file = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"]
)



if uploaded_file:


    if st.session_state["summary"] == "":


        with st.spinner("Extracting resume text..."):


            resume_text = extract_text_from_pdf(uploaded_file)

            st.session_state["resume_text"] = resume_text




        with st.spinner("Analyzing resume..."):


            summary = ask_openai(
                f"""

Analyze this resume.

Extract:
- education
- experience
- technical skills
- professional profile
- possible job roles


Resume:

{resume_text}

""",
                max_tokens=600
            )


            st.session_state["summary"] = summary





        with st.spinner("Finding skill gaps..."):


            gaps = ask_openai(

                f"""

Analyze this resume and identify missing skills
to improve career opportunities.

Resume:

{resume_text}

""",

                max_tokens=400
            )


            st.session_state["gaps"] = gaps





        with st.spinner("Creating roadmap..."):


            roadmap = ask_openai(

                f"""

Create a career roadmap based on this resume.

Include:
- skills to learn
- certifications
- possible career evolution


Resume:

{resume_text}

""",

                max_tokens=400

            )


            st.session_state["roadmap"] = roadmap



        st.success(
            "✅ Resume analysis completed"
        )




# ==========================
# DISPLAY ANALYSIS
# ==========================


if st.session_state["summary"]:


    st.markdown("---")

    st.header("📄 Resume Summary")


    st.markdown(
        f"""
<div style="
background-color:#000000;
padding:15px;
border-radius:10px;
color:white;
">

{st.session_state["summary"]}

</div>
""",
        unsafe_allow_html=True
    )



    st.markdown("---")

    st.header("🛠️ Skill Gaps")


    st.markdown(
        f"""
<div style="
background-color:#000000;
padding:15px;
border-radius:10px;
color:white;
">

{st.session_state["gaps"]}

</div>
""",
        unsafe_allow_html=True
    )



    st.markdown("---")

    st.header("🚀 Career Roadmap")


    st.markdown(
        f"""
<div style="
background-color:#000000;
padding:15px;
border-radius:10px;
color:white;
">

{st.session_state["roadmap"]}

</div>
""",
        unsafe_allow_html=True
    )





# ==========================
# GET JOBS
# ==========================


st.markdown("---")


if st.button("🔍 Get Job Recommendations"):


    if not st.session_state["summary"]:


        st.warning(
            "Please upload a resume first."
        )


    else:


        with st.spinner("Finding suitable job titles..."):


            keywords = ask_openai(

                f"""

Based on this resume summary, identify the MOST suitable job positions.

Rules:
- Match the person's real skills.
- Do not invent unrelated jobs.
- Avoid senior positions for junior profiles.
- Return maximum 5 job titles.
- Only return comma separated job titles.


Resume:

{st.session_state["summary"]}

""",

                max_tokens=150

            )


            st.session_state["keywords"] = (
                keywords.replace("\n","").strip()
            )



        st.success(
            f"Searching jobs for: {st.session_state['keywords']}"
        )



        with st.spinner("Fetching jobs..."):


            st.session_state["linkedin_jobs"] = fetch_linkedin_jobs(
                st.session_state["keywords"],
                rows=30
            )



            st.session_state["naukri_jobs"] = fetch_naukri_jobs(
                st.session_state["keywords"],
                rows=30
            )







# ==========================
# LINKEDIN DISPLAY
# ==========================


if st.session_state["linkedin_jobs"]:


    st.markdown("---")

    st.header("💼 LinkedIn Jobs")


    for job in st.session_state["linkedin_jobs"]:


        title = job.get("title","No title")

        company = job.get(
            "companyName",
            "Unknown company"
        )


        location = job.get(
            "location",
            "Unknown location"
        )


        link = job.get("link")



        st.markdown(
            f"""
### {title}

🏢 **Company:** {company}

📍 **Location:** {location}

"""
        )


        if link:

            st.link_button(
                "🔗 View Job",
                link
            )

        else:

            st.warning(
                "Job link unavailable"
            )


        st.markdown("---")




# ==========================
# NAUKRI DISPLAY
# ==========================


if st.session_state["naukri_jobs"]:


    st.markdown("---")

    st.header("💼 Naukri Jobs")



    for job in st.session_state["naukri_jobs"]:


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



        # Plusieurs noms possibles selon le scraper Naukri

        link = (

            job.get("jdURL")
            or job.get("url")
            or job.get("jobUrl")
            or job.get("link")
            or job.get("job_url")

        )



        st.markdown(
            f"""
### {title}

🏢 **Company:** {company}

📍 **Location:** {location}

"""
        )



        if link:


            st.link_button(
                "🔗 View Job",
                link
            )


        else:


            st.warning(
                "Job link unavailable"
            )



        st.markdown("---")