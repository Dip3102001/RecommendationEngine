from fastapi.concurrency import run_in_threadpool;
from fastapi.responses import JSONResponse;
from fastapi import FastAPI, UploadFile, File, Form;
from fastapi.middleware.cors import CORSMiddleware;

import os;
import requests;
from dotenv import load_dotenv;
from functools import partial;

from typing import Optional;

from helper import ProductSearchSystem;

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    file: Optional[UploadFile] = File(None),
    q : str = Form(...)
):
    image = {
        
    };

    if file and file.content_type.startswith('image'):
        content = await file.read();
        files = {
            "file": (file.filename, content, file.content_type)
        };

        res = requests.post(image_vectorizer_api, files=files);
        response = res.json();

        image["embedding"] = response["embedding"];
        image["items"] = response["classification"][0];

    
    if "embedding" in image and "items" in image:
        print(image["embedding"], image["items"]);
        results = await run_in_threadpool(partial(search_system.build_fuzzy_type_vector_query, image["items"], image["embedding"]));
    else:
        results = await run_in_threadpool(partial(search_system.search_products, q));
        formatted_results = await run_in_threadpool(partial(search_system.format_results_with_llm, results, q));

    print(formatted_results);

    return JSONResponse(
        content=formatted_results,
    );
