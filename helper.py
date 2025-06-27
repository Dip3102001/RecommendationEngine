import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from elasticsearch import Elasticsearch
import openai
from datetime import datetime

from util import s3_to_url;

@dataclass
class SearchFeatures:
    """Extracted features from user query"""
    product_name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price_range: Optional[Dict[str, float]] = None
    attributes: List[Dict[str, str]] = None
    tags: List[str] = None
    rating_min: Optional[float] = None
    description_keywords: List[str] = None
    intent: str = "search"  # search, compare, recommend, etc.
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = []
        if self.tags is None:
            self.tags = []
        if self.description_keywords is None:
            self.description_keywords = []

class ProductSearchSystem:
    def __init__(self, es_client: Elasticsearch, openai_api_key: str, index_name: str = "products"):
        self.es = es_client
        self.index_name = index_name
        openai.api_key = openai_api_key
        
    def enhance_query(self, user_query: str) -> str:
        """Enhance user query using LLM"""

        prompt = f"""
                    You are an intelligent assistant that reformulates user product queries to make them clearer and more descriptive.

                    Given a user's short or ambiguous query, expand it by:
                    - Making implicit details explicit
                    - Guessing likely product category, brand, and attributes based on common knowledge
                    - Highlighting price range, rating preference, or comparison intent if mentioned or implied
                    - Including keywords useful for searching product descriptions

                    Output should be a natural-sounding sentence or paragraph that keeps the original intent but adds clarity.

                    Examples:
                    ---

                    Input: "nike shoes"
                    Output: "I am looking for Nike brand shoes, likely in the clothing or sportswear category, suitable for running or casual use."

                    Input: "best phone under 500"
                    Output: "I want to find a top-rated smartphone under $500, ideally with good camera quality and performance."

                    Input: "compare dell laptops"
                    Output: "I want to compare different Dell laptops in the electronics category, focusing on specs like RAM, storage, and screen size."

                    Input: "4k tv with hdmi 2.1"
                    Output: "I am searching for a 4K resolution television with HDMI 2.1 support, preferably from a popular brand like Samsung or LG."

                    ---

                    Now enhance the following query:
                    {user_query}
                """;

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You enhance user product queries for better understanding."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            user_query = response.choices[0].message.content;

        except Exception as e:
            print(f"Error extracting features: {e}");

        return user_query;


    def extract_features_with_llm(self, user_query: str) -> SearchFeatures:
        """Extract search features from user query using LLM"""
        

        
        prompt = f"""
            You are an intelligent assistant that reformulates user product queries to make them clearer and more descriptive. 

            Given a user's short or ambiguous query, expand it by:
            - Making implicit details explicit
            - Guessing likely product category, brand, and attributes based on common knowledge
            - Highlighting price range, rating preference, or comparison intent if mentioned or implied
            - Including keywords useful for searching product descriptions

            Output should be a natural-sounding sentence or paragraph that keeps the original intent but adds clarity.

            Examples:
            ---

            Input: "nike shoes"
            Output: "I am looking for Nike brand shoes, likely in the clothing or sportswear category, suitable for running or casual use."

            Input: "best phone under 500"
            Output: "I want to find a top-rated smartphone under $500, ideally with good camera quality and performance."

            Input: "compare dell laptops"
            Output: "I want to compare different Dell laptops in the electronics category, focusing on specs like RAM, storage, and screen size."

            Input: "4k tv with hdmi 2.1"
            Output: "I am searching for a 4K resolution television with HDMI 2.1 support, preferably from a popular brand like Samsung or LG."

            ---

            Now enhance the following query:
            {user_query}
        """;

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You enhance user product queries for better understanding."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            user_query = response.choices[0].message.content;

        except Exception as e:
            print(f"Error extracting features: {e}")


        prompt = f"""
        You are an expert at extracting comprehensive product search features from natural language queries.
        
        User Query: "{user_query}"
        
        Extract the following information and return as JSON:
        {{
            "product_name": "specific product name if mentioned",
            "category": "product category (electronics, clothing, books, toys, home, food, beauty, sports, accessories, etc.)",
            "brand": "brand name if mentioned",
            "price_range": {{"min": number, "max": number}} or null,
            "attributes": [{{"name": "attribute_name", "value": "attribute_value"}}],
            "tags": ["relevant", "tags", "from", "query"],
            "rating_min": minimum_rating_if_mentioned or null,
            "description_keywords": ["important", "keywords", "for", "description"],
            "intent": "search|compare|recommend|browse"
        }}
        
        RELAXED EXTRACTION RULES - Be Liberal and Comprehensive:
        
        1. PRODUCT NAMES: Include partial names, model numbers, product types (e.g., "laptop", "smartphone", "camera")
        
        2. CATEGORIES: Infer categories from context:
           - "phone/mobile/smartphone" → Electronics
           - "book/guide/manual" → Books  
           - "toy car/RC car" → Toys
           - "fridge/refrigerator" → Home & Kitchen
           - "lipstick/makeup" → Beauty
           - "watch/clock" → Accessories or Electronics
        
        3. BRANDS: Include any brand names mentioned or implied
        
        4. PRICE TERMS: Interpret price indicators broadly:
           - "cheap/budget/affordable" → max: 50
           - "expensive/premium/high-end" → min: 500
           - "mid-range/moderate" → min: 100, max: 500
           - Numbers like "under 1000", "between 50-200", "$100"
        
        5. ATTRIBUTES: Extract ALL descriptive features:
           - Colors, sizes, materials, capacities, speeds, features
           - Technical specs (RAM, storage, resolution, battery)
           - Physical properties (weight, dimensions, finish)
           - Special features (wireless, smart, waterproof, fast-charging)
        
        6. DESCRIPTION KEYWORDS: Include ALL relevant words that could match product descriptions:
           - Technical terms (AMOLED, SSD, Wi-Fi, Bluetooth, USB-C)
           - Descriptive adjectives (portable, lightweight, durable, premium)
           - Use cases (business, gaming, photography, outdoor, kitchen)
           - Feature keywords (fast-charging, noise-cancellation, water-resistant)
           - Material types (stainless steel, leather, ceramic, metal)
           - Size descriptors (compact, large-capacity, ultra-thin)
        
        7. TAGS: Be very inclusive with contextual tags:
           - Functional tags (photography, gaming, cooking, fitness)
           - Style tags (vintage, modern, classic, sleek)
           - Usage tags (professional, casual, travel, home)
           - Quality indicators (premium, budget, high-performance)
        
        8. RATING: Look for quality indicators:
           - "best rated/top rated/highly rated" → rating_min: 4.5
           - "good reviews/well reviewed" → rating_min: 4.0
           - "popular/bestseller" → rating_min: 4.0
        
        9. INTENT DETECTION:
           - "best/top/recommend" → recommend
           - "compare/vs/versus" → compare  
           - "show me/find/looking for" → search
           - "browse/explore" → browse
        
        IMPORTANT: Be generous with extraction - it's better to include too many relevant keywords than to miss important ones that could match product descriptions. Think about synonyms and related terms that might appear in product descriptions.
        
        Return valid JSON only.
        """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a product search feature extractor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            
            print(f"Extracted features: {extracted_data}")

            return SearchFeatures(
                product_name=extracted_data.get("product_name"),
                category=extracted_data.get("category"),
                brand=extracted_data.get("brand"),
                price_range=extracted_data.get("price_range"),
                attributes=extracted_data.get("attributes", []),
                tags=extracted_data.get("tags", []),
                rating_min=extracted_data.get("rating_min"),
                description_keywords=extracted_data.get("description_keywords", []),
                intent=extracted_data.get("intent", "search")
            )
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            # Fallback to basic extraction
            return self._basic_feature_extraction(user_query)
    
    def _basic_feature_extraction(self, query: str) -> SearchFeatures:
        """Fallback method for basic feature extraction"""
        features = SearchFeatures()
        
        # Basic price extraction
        price_patterns = [
            r'under \$?(\d+)',
            r'below \$?(\d+)',
            r'less than \$?(\d+)',
            r'\$?(\d+)-\$?(\d+)',
            r'between \$?(\d+) and \$?(\d+)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, query.lower())
            if match:
                if len(match.groups()) == 1:
                    features.price_range = {"max": float(match.group(1))}
                else:
                    features.price_range = {
                        "min": float(match.group(1)),
                        "max": float(match.group(2))
                    }
                break
        
        # Extract potential keywords
        features.description_keywords = [word for word in query.split() if len(word) > 3]
        
        return features
    
    def build_elasticsearch_query(self, features: SearchFeatures, user_query: str) -> Dict[str, Any]:
        """Build Elasticsearch query from extracted features - LIMITED TO TOP 2 RESULTS"""
        
        query = {
            "query": {
                "bool": {
                    "must": [],
                    "should": [],
                    "filter": [],
                    "minimum_should_match": 1  # Ensure at least one should clause must match
                }
            },
            "size": 2,
            "sort": [
                {"_score": {"order": "desc"}},
                {"rating": {"order": "desc", "missing": "_last"}},
                {"view_count": {"order": "desc", "missing": "_last"}}
            ],
            "track_total_hits": True
        }

        # 1. Main text search
        if features.product_name or features.description_keywords:
            search_text = features.product_name or " ".join(features.description_keywords)
            query["query"]["bool"]["should"].extend([
                {
                    "multi_match": {
                        "query": search_text,
                        "fields": ["name^3", "description^2", "category.text"],
                        "type": "best_fields",
                        "boost": 2.0
                    }
                },
                {
                    "match": {
                        "name.keyword": {
                            "query": search_text,
                            "boost": 3.0
                        }
                    }
                }
            ])

        # 2. Fallback with original user query
        query["query"]["bool"]["should"].append({
            "multi_match": {
                "query": user_query,
                "fields": ["name^2", "description", "category.text", "tags"],
                "type": "cross_fields",
                "operator": "or"
            }
        })

        # 3. Category
        if features.category:
            query["query"]["bool"]["should"].extend([
                {"term": {"category": features.category.lower()}},
                {"match": {"category.text": features.category}}
            ])

        # 4. Brands (as list)
        if features.brand:
            for brand in features.brand:
                query["query"]["bool"]["should"].extend([
                    {"term": {"brand": {"value": brand.lower(), "boost": 2.0}}},
                    {"match": {"name": {"query": brand, "boost": 1.5}}}
                ])

        # 5. Price filter
        if features.price_range:
            price_filter = {"range": {"price": {}}}
            if "min" in features.price_range:
                price_filter["range"]["price"]["gte"] = features.price_range["min"]
            if "max" in features.price_range:
                price_filter["range"]["price"]["lte"] = features.price_range["max"]
            query["query"]["bool"]["filter"].append(price_filter)

        # 6. Rating filter
        if features.rating_min:
            query["query"]["bool"]["filter"].append({
                "range": {"rating": {"gte": features.rating_min}}
            })

        # 7. Tags (use `match` not `term`)
        if features.tags:
            for tag in features.tags:
                query["query"]["bool"]["should"].extend([
                    {"match": {"tags": {"query": tag, "boost": 1.5}}},
                    {"match": {"description": {"query": tag, "boost": 1.2}}}
                ])

        # 8. Attributes (nested + fallback)
        if features.attributes:
            for attr in features.attributes:
                name = attr.get("name")
                value = attr.get("value")
                if name and value:
                    # Nested query for attributes
                    query["query"]["bool"]["should"].append({
                        "nested": {
                            "path": "attributes",
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {"attributes.name": name}},
                                        {"match": {"attributes.value": value}}
                                    ]
                                }
                            },
                            "boost": 2.0,
                            "ignore_unmapped": True
                        }
                    })

                    # Fallback: include attribute in general text search
                    query["query"]["bool"]["should"].append({
                        "multi_match": {
                            "query": f"{name} {value}",
                            "fields": ["description", "name", "tags"],
                            "boost": 1.0
                        }
                    })

        # 9. Fallback if nothing else matched
        if not query["query"]["bool"]["should"]:
            query["query"]["bool"]["should"].append({
                "match_all": {}
            })

        return query

    
    def build_simple_query(self, user_query: str, features: SearchFeatures = None) -> Dict[str, Any]:
        """Build a simpler, more robust Elasticsearch query - LIMITED TO TOP 2 RESULTS"""
        
        query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": user_query,
                                "fields": [
                                    "name^3",
                                    "description^2", 
                                    "category^1.5",
                                    "brand^2",
                                    "tags^1.5"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "match_phrase": {
                                "name": {
                                    "query": user_query,
                                    "boost": 2.0
                                }
                            }
                        }
                    ],
                    "filter": [],
                    "minimum_should_match": 1
                }
            },
            "size": 2,  # CHANGED: Only return top 2 results
            "sort": [
                {"_score": {"order": "desc"}},
                {"rating": {"order": "desc", "missing": "_last"}},
                {"view_count": {"order": "desc", "missing": "_last"}}
            ]
        }
        
        # Add simple filters if features are provided
        if features:
            # Price filter
            if features.price_range:
                price_filter = {"range": {"price": {}}}
                if features.price_range.get("min"):
                    price_filter["range"]["price"]["gte"] = features.price_range["min"]
                if features.price_range.get("max"):
                    price_filter["range"]["price"]["lte"] = features.price_range["max"]
                query["query"]["bool"]["filter"].append(price_filter)
            
            # Rating filter
            if features.rating_min:
                query["query"]["bool"]["filter"].append({
                    "range": {"rating": {"gte": features.rating_min}}
                })
        
        return query
    
    def search_products(self, user_query: str) -> Dict[str, Any]:
        """Main search function with fallback strategies - LIMITED TO TOP 2 RESULTS"""
        
        try:
            user_query = self.enhance_query(user_query);
        except Exception as e:
            print(e.with_traceback());

        print(user_query);

        basic_query = {
            "query": {"match": {"name": user_query}},
            "size": 2  # CHANGED: Only return top 2 results
        }
        response = self.es.search(index=self.index_name, body=basic_query)
        return {
            "extracted_features": None,
            "elasticsearch_query": basic_query,
            "results": response["hits"]["hits"],
            "total_results": response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"],
            "max_score": response["hits"]["max_score"]
        }    
    
    def format_results_with_llm(self, search_results: Dict[str, Any], user_query: str) -> str:
        """Format search results using LLM for better presentation - FOCUSED ON TOP 2 RESULTS"""
        
        if "error" in search_results:
            return f"Sorry, there was an error processing your search: {search_results['error']}"
        
        if not search_results["results"]:
            return "No products found matching your criteria. Try adjusting your search terms."
        
        # Prepare data for LLM formatting - limit to top 2 results
        products_data = []
        for hit in search_results["results"][:2]:  # CHANGED: Only top 2 results
            source = hit["_source"]
            products_data.append({
                "name": source.get("name", ""),
                "description": source.get("description", "")[:200] + "...",
                "category": source.get("category", ""),
                "image_url": s3_to_url(source.get("image_url", "")),
                "brand": source.get("brand", ""),
                "price": source.get("price", 0),
                "rating": source.get("rating", 0),
                "tags": source.get("tags", []),
                "score": hit["_score"]
            })
        
        prompt = f"""
                    Format the TOP 2 product search results in a user-friendly JSON response for the query: "{user_query}"

                    Input Data: {products_data}

                    Requirements:
                    1. Return data in clean JSON format with this exact structure:
                    {{
                        "summary": "Brief summary mentioning these are the TOP 2 best matches for the search query",
                        "products": [
                        {{
                            "name": "Product name",
                            "brand": "Brand name",
                            "description": "Detailed product description highlighting key features and benefits",
                            "image_url": "Product image URL",
                            "price": "Price with currency",
                            "rating": "Rating score or text"
                        }}
                        ]
                    }}

                    2. Product descriptions should be:
                    - Rich and informative
                    - Focus on key features and benefits
                    - Quality over quantity approach
                    - Professional tone without emojis

                    3. Include a comparison or recommendation in the summary explaining why these are the top matches

                    Please process the provided product data and return the formatted JSON response.
                """
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful shopping assistant. Format the TOP 2 product search results in an engaging, detailed way."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback formatting
            return self._basic_format_results(search_results, user_query)
    
    def _basic_format_results(self, search_results: Dict[str, Any], user_query: str) -> str:
        """Fallback method for formatting results - TOP 2 FOCUS"""
        results_text = f"🔍 Top 2 best matches for '{user_query}' (from {search_results['total_results']} total results)\n\n"
        
        for i, hit in enumerate(search_results["results"][:2], 1):  # CHANGED: Only top 2
            source = hit["_source"]
            results_text += f"🏆 **#{i} - {source.get('name', 'Unknown')}**\n"
            results_text += f"   💰 ${source.get('price', 0):.2f}\n"
            results_text += f"   ⭐ {source.get('rating', 0)}/5\n"
            results_text += f"   🏷️ {source.get('category', 'N/A')}\n"
            if source.get('brand'):
                results_text += f"   🏢 {source['brand']}\n"
            if source.get('description'):
                results_text += f"   📝 {source['description'][:150]}...\n"
            results_text += f"   📊 Relevance Score: {hit['_score']:.2f}\n"
            results_text += "\n"
        
        results_text += "💡 These are the 2 most relevant products based on your search criteria!"
        
        return results_text