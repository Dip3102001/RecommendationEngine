# Product Recommendation Engine

A sophisticated product search and recommendation system that combines natural language processing, image analysis, and Elasticsearch to deliver intelligent product recommendations based on user queries and uploaded images.

## 🚀 Features

- **Intelligent Text Search**: Enhanced query processing using OpenAI GPT-4 for better understanding of user intent
- **Image-Based Search**: Upload product images to find similar items using vector similarity
- **Multi-Modal Search**: Combine text queries with image uploads for more precise results
- **Smart Feature Extraction**: Automatically extracts product attributes, price ranges, categories, and user intent from queries
- **Fuzzy Matching**: Handles typos and variations in product names and categories
- **Relevance Scoring**: Advanced ranking using multiple factors including ratings, popularity, and similarity scores

## 🏗️ Architecture & Design Choices

### Core Components

1. **FastAPI Backend** (`main.py`)
   - RESTful API with CORS support
   - Asynchronous request handling
   - Multi-part form support for image uploads

2. **Product Search System** (`helper.py`)
   - Centralized search logic with multiple fallback strategies
   - LLM-powered query enhancement and feature extraction
   - Flexible Elasticsearch query building

3. **Utility Functions** (`util.py`)
   - S3 URL conversion for image handling

### Key Design Decisions

#### 1. **Hybrid Search Approach**
- **Text-First Strategy**: Enhances user queries using GPT-4 before feature extraction
- **Multi-Field Matching**: Searches across product names, descriptions, categories, brands, and tags
- **Fallback Mechanisms**: Graceful degradation from complex to simple queries when needed

#### 2. **LLM Integration Strategy**
- **Query Enhancement**: Transforms ambiguous queries into detailed, searchable descriptions
- **Feature Extraction**: Uses GPT-4 to extract structured data from natural language
- **Result Formatting**: Presents search results in user-friendly, contextual formats

#### 3. **Vector Search for Images**
- **External Vectorization**: Leverages specialized image vectorization API
- **Classification-First**: Determines product type before vector similarity matching
- **Hybrid Filtering**: Combines fuzzy text matching with vector similarity scoring

#### 4. **Elasticsearch Query Architecture**
- **Layered Scoring**: Combines relevance score, ratings, and view counts
- **Smart Filtering**: Separates MUST filters from SHOULD clauses for optimal performance
- **Limited Results**: Returns top 2 results to maintain response speed and relevance

#### 5. **Error Handling & Resilience**
- **Progressive Fallbacks**: Complex → Simple → Basic query strategies
- **Graceful Degradation**: Continues operation even if LLM services fail
- **Comprehensive Exception Handling**: Maintains service availability

## 📋 Prerequisites

- Python 3.8+
- Elasticsearch cluster with product data
- OpenAI API key
- Image vectorization service (external API)
- Required Python packages (see `requirements.txt`)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd product-recommendation-engine
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file with the following variables:
   ```env
   ELK_URL=your_elasticsearch_url
   ELK_API_KEY=your_elasticsearch_api_key
   ELK_INDEX=your_product_index_name
   OPENAI_API_KEY=your_openai_api_key
   IMAGE_VC_API=your_image_vectorization_api_url
   ```

4. **Run the application**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   
   Or manually:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📡 API Endpoints

### Health Check
```http
GET /health
```
Returns the service status.

### Product Analysis
```http
POST /analyze
```

**Parameters:**
- `q` (form field, required): Search query string
- `file` (form field, optional): Product image file

**Example with cURL:**
```bash
# Text-only search
curl -X POST "http://localhost:8000/analyze" \
  -F "q=best smartphone under 500"

# Image + text search
curl -X POST "http://localhost:8000/analyze" \
  -F "q=find similar products" \
  -F "file=@product_image.jpg"
```

**Response Format:**
```json
{
  "summary": "Brief summary of search results",
  "products": [
    {
      "name": "Product Name",
      "brand": "Brand Name",
      "description": "Detailed product description",
      "image_url": "https://...",
      "price": "$X.XX",
      "rating": "4.5/5"
    }
  ]
}
```

## 🔍 Search Capabilities

### Text Search Features
- **Natural Language Processing**: "Find me a good laptop for programming under $1000"
- **Brand Recognition**: "Samsung 4K TV with HDMI 2.1"
- **Category Inference**: "noise cancelling headphones"
- **Price Range Detection**: "budget smartphones", "premium watches"
- **Intent Recognition**: "compare", "recommend", "find best"

### Image Search Features
- **Product Classification**: Automatically identifies product type from images
- **Visual Similarity**: Finds products with similar visual characteristics
- **Hybrid Matching**: Combines image analysis with text descriptions

### Advanced Query Understanding
The system extracts and processes:
- Product names and model numbers
- Categories and subcategories
- Brand preferences
- Price ranges (explicit and implicit)
- Product attributes (color, size, specifications)
- Rating requirements
- User intent (search, compare, recommend)

## 🏗️ Elasticsearch Index Structure

Expected product document structure:
```json
{
  "name": "Product Name",
  "description": "Product description",
  "category": "electronics",
  "brand": "Brand Name",
  "price": 299.99,
  "rating": 4.5,
  "tags": ["tag1", "tag2"],
  "image_url": "s3://bucket/image.jpg",
  "image_vector": [0.1, 0.2, ...],
  "attributes": [
    {"name": "color", "value": "black"},
    {"name": "storage", "value": "256GB"}
  ],
  "view_count": 1500
}
```

## 🔧 Configuration

### Search Behavior
- **Result Limit**: Returns top 2 most relevant products
- **Fuzzy Matching**: Handles typos with AUTO fuzziness
- **Boost Values**: Name (3x), Description (2x), Brand (2x)
- **Sorting**: Score → Rating → Popularity

### LLM Configuration
- **Model**: GPT-4 for query processing and formatting
- **Temperature**: 0.1 for feature extraction, 0.7 for formatting
- **Fallback**: Basic regex-based extraction if LLM fails

## 🚀 Performance Considerations

1. **Response Time**: Optimized for <2s response times
2. **Result Limiting**: Top 2 results prevent information overload
3. **Async Processing**: Non-blocking I/O for external API calls
4. **Caching Strategy**: Consider implementing Redis for frequent queries
5. **Connection Pooling**: Elasticsearch client handles connection reuse

## 🛡️ Error Handling

The system implements multiple layers of error handling:
- LLM service failures → Basic feature extraction
- Complex query failures → Simple query fallback
- Image processing errors → Text-only search
- Elasticsearch errors → Graceful error messages

## 📝 Logging

Enable detailed logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## 🧪 Testing

Run health check:
```bash
curl http://localhost:8000/health
```

Test search functionality:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "q=wireless earbuds"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Troubleshooting

### Common Issues

1. **Elasticsearch Connection Failed**
   - Verify `ELK_URL` and `ELK_API_KEY` in `.env`
   - Check network connectivity to Elasticsearch cluster

2. **OpenAI API Errors**
   - Verify `OPENAI_API_KEY` is valid and has credits
   - Check API rate limits

3. **Image Processing Failures**
   - Ensure `IMAGE_VC_API` endpoint is accessible
   - Verify image file formats are supported

4. **No Search Results**
   - Check if Elasticsearch index contains data
   - Verify index name in `ELK_INDEX` environment variable

### Performance Tuning

- Adjust `size` parameter in queries for more/fewer results
- Modify boost values for different field priorities
- Implement caching for frequent queries
- Consider index optimization for your specific use case

---

**Built with ❤️ using FastAPI, Elasticsearch, and OpenAI**
