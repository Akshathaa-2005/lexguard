# LexGuard Legal Analysis Platform - Technical Architecture Report

## 🎯 Executive Summary

LexGuard is an AI-powered legal feasibility analysis platform designed for startup founders to evaluate their product ideas against regulatory frameworks. The system combines Retrieval-Augmented Generation (RAG) with Large Language Models (LLMs) to provide comprehensive legal compliance assessments.

---

## 🏗️ Current Technology Stack

### **Frontend Architecture**
- **Framework**: Next.js 14 (React-based)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **State Management**: React Hooks (useState, useEffect, useRef)
- **Responsive Design**: Custom dynamic sizing based on screen dimensions

### **Backend Architecture**
- **Framework**: Flask (Python)
- **Language**: Python 3.11+
- **LLM Integration**: Groq API (Llama 3.1 models)
- **Vector Database**: MongoDB with Atlas Search
- **Document Processing**: PyPDF2, python-docx
- **Text Embeddings**: OpenAI embeddings
- **Data Retrieval**: Custom RAG pipeline

### **Infrastructure & Deployment**
- **Version Control**: Git with GitHub
- **Environment**: Windows development environment
- **Package Management**: pip (Python), npm (Node.js)
- **Virtual Environment**: Python venv

---

## 🔧 Implementation Details

### **Frontend Components**

#### **Core Dashboard Layout**
```typescript
// Main dashboard sections
- Upload Project: Product description, file upload, country/domain selection
- Explore Policy: Policy browsing with filters
- Policy Preview: Retrieved legal documents display
- Compliance Report: Dynamic scoring visualization
- Risk Analysis: Text-based risk assessment
- Legal Recommendations: Actionable compliance steps
- Relevant Policies: Card-based policy display
- Executive Summary: Comprehensive legal overview
```

#### **Responsive Design System**
```typescript
const getResponsiveClasses = () => {
  const { width } = screenSize
  
  if (width < 640) {
    // Mobile: text-2xl, p-4, grid-cols-1
  } else if (width < 1024) {
    // Tablet: text-3xl, p-6, grid-cols-1 lg:grid-cols-2
  } else if (width < 1440) {
    // Desktop: text-4xl, p-6, grid-cols-1 lg:grid-cols-3
  } else {
    // Large Desktop: text-5xl, p-8, grid-cols-1 lg:grid-cols-3 xl:grid-cols-4
  }
}
```

#### **State Management**
```typescript
// Core state hooks
const [productDescription, setProductDescription] = useState('')
const [selectedCountry, setSelectedCountry] = useState('')
const [selectedDomain, setSelectedDomain] = useState('')
const [legalReport, setLegalReport] = useState<any>(null)
const [isAnalyzing, setIsAnalyzing] = useState(false)
```

### **Backend Architecture**

#### **Core Classes & Modules**

**LLMJudge (judge.py)**
```python
class LLMJudge:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_JUDGE_MODEL", "llama-3.1-8b-instant")
    
    def filter_and_summarize(self, chunks, product, country, domain):
        # Dynamic relevance scoring based on product context
        # LLM-infers document names from section titles
        # Calculates relevance scores (0.0-1.0) dynamically
```

**ReportGenerator (report_generator.py)**
```python
class ReportGenerator:
    def generate(self, product_description, country, domain, contexts):
        # Dynamic scoring system
        # LLM calculates:
        # - validity_score (0-100)
        # - risk_level (Low/Medium/High)
        # - compliance_scores per category
        # - policy_relevance_chart percentages
```

**Retrieval Pipeline (retriever.py)**
```python
class VectorRetriever:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.embed_model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def retrieve(self, query, country, domain, top_k=10):
        # Hybrid search: vector + metadata filtering
        # Returns most relevant legal document chunks
```

#### **Database Schema**
```javascript
// MongoDB Collections
legal_documents: {
  document_id: String,
  country: String,
  domain: String,
  publish_date: String,
  sections: [String],
  chunks: [{
    chunk_text: String,
    section_title: String,
    embedding: [Float] // 1536-dimensional vector
  }]
}
```

---

## 🧠 Methodology

### **RAG (Retrieval-Augmented Generation) Pipeline**

#### **1. Document Ingestion**
```
Legal Documents → PDF/DOCX Parsing → Text Chunking → Embedding Generation → Vector Storage
```

**Process:**
1. **Document Parsing**: PyPDF2/python-docx extract raw text
2. **Chunking**: Split documents into manageable sections
3. **Embedding**: OpenAI creates 1536-dimensional vectors
4. **Storage**: MongoDB Atlas with vector search capability

#### **2. Query Processing**
```
User Query → Embedding → Vector Search → Relevance Filtering → Context Assembly
```

**Process:**
1. **Query Embedding**: Convert user query to vector
2. **Hybrid Search**: Vector similarity + metadata filtering
3. **Relevance Scoring**: LLM evaluates legal relevance (0.0-1.0)
4. **Context Assembly**: Top relevant chunks compiled

#### **3. Analysis Generation**
```
Context + Product Info → LLM Analysis → Dynamic Scoring → Structured Report
```

**Process:**
1. **Context Integration**: Retrieved legal documents + product details
2. **LLM Analysis**: Groq Llama 3.1 generates comprehensive analysis
3. **Dynamic Scoring**: All scores calculated based on specific context
4. **Report Formatting**: JSON structure with actionable insights

### **Dynamic Scoring System**

#### **Relevance Scoring (judge.py)**
```python
# Dynamic calculation based on:
- Product-domain alignment
- Country-specific regulations
- Legal framework applicability
- Minimum 0.7 for fintech/healthcare/AI products
```

#### **Compliance Scoring (report_generator.py)**
```python
# Categories dynamically evaluated:
- data_privacy: 0-100 (GDPR, CCPA, HIPAA relevance)
- financial_regulation: 0-100 (FinCEN, SEC, banking laws)
- ai_regulation: 0-100 (EU AI Act, NIST frameworks)
- consumer_protection: 0-100 (FTC, consumer rights laws)
```

---

## 🔄 API Endpoints

### **Core Endpoints**

#### **POST /analyze**
```python
# Request
{
  "product_description": "Product description",
  "country": "Country",
  "domain": "Domain",
  "file_content": "Optional document text"
}

# Response
{
  "executive_summary": "Legal overview",
  "validity_score": 85,
  "risk_level": "Medium",
  "compliance_scores": {...},
  "policy_relevance_chart": [...],
  "pros": [...],
  "cons": [...],
  "recommendations": [...]
}
```

#### **POST /policies**
```python
# Request
{
  "country": "Country filter",
  "domain": "Domain filter"
}

# Response
{
  "results": [
    {
      "document_id": "doc_id",
      "document_name": "Full Law Name",
      "country": "Country",
      "publish_date": "Date",
      "sections": ["Section1", "Section2"]
    }
  ]
}
```

---

## 📊 Data Flow Architecture

### **Analysis Flow**
```
1. User Input (Frontend)
   ↓
2. API Request (Next.js → Flask)
   ↓
3. Document Retrieval (MongoDB + Vector Search)
   ↓
4. Relevance Filtering (LLM Judge)
   ↓
5. Context Assembly (Top Relevant Chunks)
   ↓
6. Report Generation (LLM Analysis)
   ↓
7. Dynamic Scoring (Context-Based)
   ↓
8. Response (Backend → Frontend)
   ↓
9. UI Display (Dashboard Components)
```

### **Error Handling & Resilience**
```python
# Retry mechanisms
- LLM API: 3 attempts with exponential backoff
- Database: Connection pooling and retry logic
- File parsing: Multiple format support with fallbacks

# Fallback strategies
- Relevance scoring: Minimum 0.7 baseline for relevant domains
- Document naming: Section title fallback if LLM fails
- Report generation: Generic legal advice if context insufficient
```

---

## 🛡️ Security & Performance

### **Security Measures**
- **API Keys**: Environment variables (.env files)
- **Input Validation**: File type restrictions, content sanitization
- **Rate Limiting**: Built-in retry mechanisms
- **Data Privacy**: No persistent storage of user data

### **Performance Optimizations**
- **Vector Search**: MongoDB Atlas for fast similarity matching
- **Caching**: LLM responses cached where appropriate
- **Lazy Loading**: Frontend components load on demand
- **Responsive Design**: Optimized for all screen sizes

---

## 🚀 Current Capabilities

### **Legal Analysis Features**
- ✅ **Multi-Jurisdiction**: US, EU, UK, and other regulatory frameworks
- ✅ **Domain-Specific**: Fintech, Healthcare, AI, Consumer products
- ✅ **Dynamic Scoring**: Context-aware relevance and compliance assessment
- ✅ **Document Intelligence**: LLM-based document naming and summarization
- ✅ **Actionable Insights**: Specific legal recommendations with citations

### **Technical Features**
- ✅ **Responsive UI**: Dynamic sizing for mobile, tablet, desktop
- ✅ **File Processing**: PDF and DOCX document support
- ✅ **Real-time Analysis**: Progress indicators and error handling
- ✅ **Policy Browsing**: Searchable legal document database
- ✅ **Modern Stack**: Next.js, TypeScript, Tailwind CSS

---

## 📈 Scalability & Future Enhancements

### **Current Scalability**
- **Database**: MongoDB Atlas scales horizontally
- **LLM Integration**: Groq API handles concurrent requests
- **Frontend**: Next.js optimized for performance
- **Deployment**: Git-based version control for continuous deployment

### **Potential Enhancements**
- **Real-time Collaboration**: Multi-user analysis sessions
- **Advanced Analytics**: Historical analysis tracking
- **Integration APIs**: Direct government database connections
- **Mobile Application**: Native iOS/Android apps
- **Regulatory Updates**: Automated legal framework monitoring

---

## 🎯 Conclusion

LexGuard represents a sophisticated legal-tech solution combining:
- **Modern Web Technologies**: Next.js, React, TypeScript
- **Advanced AI**: RAG pipeline with LLM analysis
- **Dynamic Intelligence**: Context-aware scoring and recommendations
- **User-Centric Design**: Responsive, intuitive interface

The platform successfully bridges the gap between complex legal frameworks and startup innovation, providing actionable compliance insights through cutting-edge AI technology.

*Generated: April 2026*
*Version: 1.0*
