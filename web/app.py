import streamlit as st
from langchain_openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
import redis
import pandas as pd
import pickle

from langchain_community.utilities.sql_database import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_openai import ChatOpenAI
import os
import sqlite3

from redisvl.extensions.llmcache import SemanticCache
from redisvl.utils.vectorize import OpenAITextVectorizer

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SQLLITE_URI = "sqlite:///cars_database.db"
SQLLITE_DB = "cars_database.db"
SEMANTIC_CACHE_FRESHNESS = 15

db = SQLDatabase.from_uri(SQLLITE_URI)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
redis_url = "redis://localhost:6379"
vectorizer = OpenAITextVectorizer(
    model="text-embedding-ada-002",
    api_config={"api_key": OPENAI_API_KEY},
)
llmcache = SemanticCache(
    name="llmcache",  # underlying search index name
    prefix="llmcache",  # redis key prefix for hash entries
    redis_url=redis_url,  # redis connection url string
    distance_threshold=0.1,  # semantic cache distance threshold
    vectorizer=vectorizer,
    ttl=SEMANTIC_CACHE_FRESHNESS,
)

# Load environment variables
load_dotenv()

# Initialize redis
r = redis.Redis(decode_responses=True)
r_no_decode = redis.Redis()
p = r.pipeline()

STAGE_KEY = "stage"

st.set_page_config(initial_sidebar_state="collapsed")
with open("web/static/custom.css") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)


def get_stages():
    if not r.exists("stage"):
        r.sadd("stage", "init")
    return r.smembers("stage")


def add_stage(stage_name):
    r.sadd("stage", stage_name)


async def generate_sql_query(prompt, cache):
    r.set("input_prompt", prompt)

    if cache:
        if response := llmcache.check(
            prompt=prompt, return_fields=["prompt", "response", "metadata"]
        ):
            source = "Semantic Cache"
            sqlquery = response[0]["response"]
            print(response)
        else:
            generate_query = create_sql_query_chain(llm, db)
            sqlquery = generate_query.invoke({"question": prompt})
            source = "LLM"
    else:
        generate_query = create_sql_query_chain(llm, db)
        sqlquery = generate_query.invoke({"question": prompt})
        source = "LLM"

    r.set("sqlquery", sqlquery)
    r.set("source", source)

    return source


async def exec_query(sqlquery, cache):
    r.set("sqlquery", sqlquery)
    
    
    if cache:
        if response := llmcache.check(
            prompt=r.get("input_prompt"), return_fields=["metadata"]
        ):
           results_source = "Semantic Cache" 
           metadata = response[0]["metadata"]
           sqlresponse = metadata['sqlresponse']
           print(sqlresponse)
        else:
            results_source = "Database"
            conn = sqlite3.connect(SQLLITE_DB)
            cursor = conn.cursor()
            cursor.execute(sqlquery)
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            sqlresponse = [column_names] + rows
            
    else:
        results_source = "Database"
        conn = sqlite3.connect(SQLLITE_DB)
        cursor = conn.cursor()
        cursor.execute(sqlquery)
        column_names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        sqlresponse = [column_names] + rows

    r.set("sqlresponse", pickle.dumps(sqlresponse))
    r.set('results_source', results_source)

    return sqlresponse


async def main():
    col1, col2, col3 = st.columns([5, 0.1,1])
    col1.title("Natural Language to SQL Bot")
    col1.subheader("Using Semantic Caching effectively")
    col3.image("web/static/mark.svg",width=100)
    # col3.image("web/static/blu.png",width=100)
    
    st.sidebar.image("web/static/logo.png", caption="See how fast feels")

    if "init" in get_stages():
        print(f"Stages - {get_stages()}")
        with st.form("sql_form1"):
            input_prompt = st.text_area(
                "Prompt:", placeholder="Write your question here"
            )
            cache = st.toggle(label="Semantic Cache ( Query Results )")
            init_stage = st.form_submit_button("Submit")
            if init_stage:
                await generate_sql_query(prompt=input_prompt, cache=cache)
                add_stage("verify")

    if "verify" in get_stages():
        print(f"Stages - {get_stages()}")
        with st.form("sql_form2"):
            st.info(f"This query is served from {r.get('source')}")
            sqlquery = st.text_area("SQL Generated", value=r.get("sqlquery"))
            verify_stage = st.form_submit_button("Execute")
            if verify_stage:
                await exec_query(sqlquery=sqlquery, cache=cache)
                add_stage("visualize")

    if "visualize" in get_stages():
        print(f"Stages - {get_stages()}")
        with st.form("sql_form3"):
            st.info(f"This query is served from {r.get('results_source')}")
            sqlresponse = pickle.loads(r_no_decode.get("sqlresponse"))
            st.dataframe(
                pd.DataFrame(data=sqlresponse[1:], columns=sqlresponse[0]),
                hide_index=True,
                use_container_width=True
            )
            save_toggle = st.toggle(label="Save Results")
            proceed = st.form_submit_button("Proceed")

            if save_toggle:
                llmcache.store(
                    prompt=input_prompt,
                    response=sqlquery,
                    metadata={
                        "sqlresponse": pickle.loads(r_no_decode.get("sqlresponse"))
                    },
                )

            if proceed:
                r.srem("stage", "init", "verify", "visualize")
                r.delete(*["input_prompt", "sqlquery", "sqlresponse", "source","results_source"])
                st.rerun()


if __name__ == "__main__":
    asyncio.run(main())
