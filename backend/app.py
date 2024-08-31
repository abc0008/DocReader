from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import pdfplumber
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory
parent_dir = os.path.dirname(current_dir)
# Construct the path to the .env file in the parent directory
dotenv_path = os.path.join(parent_dir, '.env')

# Load environment variables from the .env file in the parent directory
load_dotenv(dotenv_path)

# Initialize Anthropic client with API key from environment variable
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

client = Anthropic(api_key=anthropic_api_key)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def extract_key_fields(text):
    MODEL_NAME = "claude-3-5-sonnet-20240620"

    tools = [
        {
            "name": "extract_financial_entities",
            "description": "Extracts financial entities from the text.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "revenue": {"type": "number"},
                    "net_income": {"type": "number"},
                    "total_assets": {"type": "number"},
                    "accounts_receivable": {"type": "number"},
                    "inventory": {"type": "number"},
                    "prepaid_expenses": {"type": "number"},
                    "accounts_payable": {"type": "number"},
                    "short_term_debt": {"type": "number"},
                    "accrued_expenses": {"type": "number"},
                    "long_term_debt": {"type": "number"},
                    "common_stock": {"type": "number"},
                    "retained_earnings": {"type": "number"}
                },
                "required": ["company_name", "revenue", "net_income", "total_assets", "accounts_receivable", 
                             "inventory", "prepaid_expenses", "accounts_payable", "short_term_debt", 
                             "accrued_expenses", "long_term_debt", "common_stock", "retained_earnings"]
            }
        }
    ]

    query = f"""
    <document>
    {text}
    </document>

    Use the extract_financial_entities tool to extract financial entities from the text. 
    If you can't find a specific value, use 0.0 as the default.
    """

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            tools=tools,
            messages=[{"role": "user", "content": query}]
        )

        extracted_entities = None
        for content in response.content:
            if content.type == "tool_use" and content.name == "extract_financial_entities":
                extracted_entities = content.input
                break

        if extracted_entities:
            return extracted_entities
        else:
            return {
                "company_name": "Unknown",
                "revenue": 0.0,
                "net_income": 0.0,
                "total_assets": 0.0,
                "accounts_receivable": 0.0,
                "inventory": 0.0,
                "prepaid_expenses": 0.0,
                "accounts_payable": 0.0,
                "short_term_debt": 0.0,
                "accrued_expenses": 0.0,
                "long_term_debt": 0.0,
                "common_stock": 0.0,
                "retained_earnings": 0.0
            }
    except Exception as e:
        print(f"Error calling Anthropic API: {str(e)}")
        return None

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400
    
    results = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF
            extracted_text = extract_text_from_pdf(filepath)
            
            # Extract entities using Claude API
            entities = extract_key_fields(extracted_text)
            
            results.append({
                'filename': filename,
                'extracted_text': extracted_text,
                'entities': entities
            })
        else:
            return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
    
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(debug=True, port=8000)