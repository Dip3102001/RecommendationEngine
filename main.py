from fastapi.concurrency import run_in_threadpool;

from fastapi import FastAPI, UploadFile, File, HTTPException, Form;
from fastapi.responses import JSONResponse;
from dotenv import load_dotenv;
import os;

from typing import Optional;

from helper import ProductSearchSystem;

import requests;

from elasticsearch import Elasticsearch

# loading ss
load_dotenv();

elk_url = os.getenv("ELK_URL");
elk_api_key = os.getenv("ELK_API_KEY");
elk_index = os.getenv("ELK_INDEX");

openai_api_key = os.getenv("OPENAI_API_KEY");

image_vectorizer_api = os.getenv("IMAGE_VC_API");

app = FastAPI(
    title="Product Recommendation Engine",
    description="User Prompt -> Product Recommendation"
);

es = Elasticsearch(
    elk_url,
    api_key=elk_api_key
)
    
# Initialize search system
search_system = ProductSearchSystem(
    es_client=es,
    openai_api_key=openai_api_key,
    index_name=elk_index
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze_prompt(
    file: Option[UploadFile] = File(...),
    q : str = Form(...)
):
    image = {
        
    };

    if file.content_type.startswith('image'):
        content = await file.read();
        files = {
            "file": (file.filename, content, file.content_type)
        };

        res = requests.post(image_vectorizer_api, files=files);
        response = res.json();

        image["embedding"] = response["embedding"];
        image["items"] = [];

        for items in response["classification"][:2]:
            item = items[0];
            image["items"].append(item);

    
    results = await run_in_threadpool(search_system.search_products(q));
    formatted_results = await run_in_threadpool(search_system.format_results_with_llm(results, q));

    return {
        "results" : formatted_results
    };