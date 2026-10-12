from apify_client import ApifyClient
import os
from dotenv import load_dotenv
from urllib.parse import quote


load_dotenv()


APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

client = ApifyClient(APIFY_API_TOKEN)



# ======================================
# LinkedIn Jobs
# ======================================

def fetch_linkedin_jobs(keyword, rows=60):

    run_input = {
        "urls": [
            f"https://www.linkedin.com/jobs/search/?keywords={quote(keyword)}"
        ],
        "scrapeCompany": False,
        "count": max(rows, 10),
        "splitByLocation": False,
        "splitCountry": "TN"
    }


    print("LINKEDIN INPUT:")
    print(run_input)


    run = client.actor(
        "hKByXkMQaC5Qt9UMN"
    ).call(
        run_input=run_input
    )


    dataset_id = run.default_dataset_id


    jobs = []


    for item in client.dataset(dataset_id).iterate_items():
        jobs.append(item)


    return jobs




# ======================================
# Naukri Jobs
# ======================================

def fetch_naukri_jobs(keyword, rows=50):

    search_url = (
        "https://www.naukri.com/jobs-in-india?keyword="
        + quote(keyword)
    )


    run_input = {
        "keyword": keyword,
        "searchUrl": search_url,
        "fetchDetails": False,
        "maxJobs": max(rows, 50),
        "freshness": "all",
        "sortBy": "relevance",
        "experience": "all",
        "workMode": [],
        "cities": [],
        "department": [],
        "salaryRange": [],
        "companyType": [],
        "roleCategory": [],
        "stipend": [],
        "duration": [],
        "ugCourse": [],
        "pgCourse": [],
        "postedBy": [],
        "industry": [],
        "topCompanies": [],
        "jobIds": []
    }


    print("NAUKRI INPUT:")
    print(run_input)


    run = client.actor(
        "alpcnRV9YI9lYVPWk"
    ).call(
        run_input=run_input
    )


    # IMPORTANT
    dataset_id = run.default_dataset_id


    jobs = []

    for item in client.dataset(dataset_id).iterate_items():
        jobs.append(item)


    return jobs