from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import pdfplumber
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Set the UPLOAD_FOLDER
UPLOAD_FOLDER = os.path.join(current_dir, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load environment variables from the .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(current_dir), '.env')
load_dotenv(dotenv_path)

# Initialize Anthropic client with API key from environment variable
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

client = Anthropic(api_key=anthropic_api_key)

app = Flask(__name__, static_folder='../frontend/build')
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

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
            "description": """
            Extracts financial entities from text.
            Entity names may not exactly match the schema - use best judgment for mapping.
            IMPORTANT: Documents may have varying layouts and tables with multiple date columns.
            Always extract data from the MOST RECENT date column available.
            If multiple tables exist for the same type of financial statement, use the most recent one.
            Adjust values based on scale modifiers (e.g., 'In Millions', 'In Thousands').
            Use 0.0 as default for missing values.
            """,
            "input_schema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "assets": {
                        "type": "object",
                        "properties": {
                            "current_assets": {
                                "type": "object",
                                "properties": {
                                    "cash_and_cash_equivalents": {"type": "number"},
                                    "accounts_receivable": {"type": "number"},
                                    "prepaid_expenses": {"type": "number"},
                                    "total_current_assets": {"type": "number"}
                                }
                            },
                            "non_current_assets": {
                                "type": "object",
                                "properties": {
                                    "property_plant_and_equipment": {"type": "number"},
                                    "accumulated_depreciation": {"type": "number"},
                                    "total_property_plant_and_equipment": {"type": "number"},
                                    "investments": {"type": "number"},
                                    "total_non_current_assets": {"type": "number"}
                                }
                            },
                            "total_assets": {"type": "number"}
                        }
                    },
                    "liabilities_and_equity": {
                        "type": "object",
                        "properties": {
                            "current_liabilities": {
                                "type": "object",
                                "properties": {
                                    "accounts_payable": {"type": "number"},
                                    "short_term_debt": {"type": "number"},
                                    "accrued_expenses": {"type": "number"},
                                    "total_current_liabilities": {"type": "number"}
                                }
                            },
                            "non_current_liabilities": {
                                "type": "object",
                                "properties": {
                                    "long_term_debt": {"type": "number"},
                                    "total_non_current_liabilities": {"type": "number"}
                                }
                            },
                            "total_liabilities": {"type": "number"},
                            "equity": {
                                "type": "object",
                                "properties": {
                                    "common_stock": {"type": "number"},
                                    "retained_earnings": {"type": "number"},
                                    "total_equity": {"type": "number"}
                                }
                            },
                            "total_liabilities_and_equity": {"type": "number"}
                        }
                    },
                    "income_statement": {
                        "type": "object",
                        "properties": {
                            "revenue": {
                                "type": "object",
                                "properties": {
                                    "sales_revenue": {"type": "number"},
                                    "rental_income": {"type": "number"},
                                    "total_revenue": {"type": "number"}
                                }
                            },
                            "expenses": {
                                "type": "object",
                                "properties": {
                                    "cost_of_goods_sold": {"type": "number"},
                                    "operating_expenses": {"type": "number"},
                                    "depreciation": {"type": "number"},
                                    "interest_expense": {"type": "number"},
                                    "total_expenses": {"type": "number"}
                                }
                            },
                            "net_income": {"type": "number"}
                        }
                    }
                },
                "required": ["company_name", "assets", "liabilities_and_equity", "income_statement"]
            }
        }
    ]

    query = f"""
    <document>
    <content>   
    {text}
    </content>
    </document>

    Use the extract_financial_entities tool to extract financial entities from the text.
    """

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=8192,
            system="You are an expert financial analyst specializing in spreading financials for credit underwriting and loan originations. Your task is to accurately extract and interpret financial data from various document formats.",
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
                "assets": {
                    "current_assets": {
                        "cash_and_cash_equivalents": 0.0,
                        "accounts_receivable": 0.0,
                        "prepaid_expenses": 0.0,
                        "total_current_assets": 0.0
                    },
                    "non_current_assets": {
                        "property_plant_and_equipment": 0.0,
                        "accumulated_depreciation": 0.0,
                        "total_property_plant_and_equipment": 0.0,
                        "investments": 0.0,
                        "total_non_current_assets": 0.0
                    },
                    "total_assets": 0.0
                },
                "liabilities_and_equity": {
                    "current_liabilities": {
                        "accounts_payable": 0.0,
                        "short_term_debt": 0.0,
                        "accrued_expenses": 0.0,
                        "total_current_liabilities": 0.0
                    },
                    "non_current_liabilities": {
                        "long_term_debt": 0.0,
                        "total_non_current_liabilities": 0.0
                    },
                    "total_liabilities": 0.0,
                    "equity": {
                        "common_stock": 0.0,
                        "retained_earnings": 0.0,
                        "total_equity": 0.0
                    },
                    "total_liabilities_and_equity": 0.0
                },
                "income_statement": {
                    "revenue": {
                        "sales_revenue": 0.0,
                        "rental_income": 0.0,
                        "total_revenue": 0.0
                    },
                    "expenses": {
                        "cost_of_goods_sold": 0.0,
                        "operating_expenses": 0.0,
                        "depreciation": 0.0,
                        "interest_expense": 0.0,
                        "total_expenses": 0.0
                    },
                    "net_income": 0.0
                }
            }
    except Exception as e:
        print(f"Error calling Anthropic API: {str(e)}")
        return None

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/test')
def test_route():
    return "Backend is working!"

@app.route('/test-pdf')
def test_pdf():
    files = os.listdir(UPLOAD_FOLDER)
    logging.debug(f"Files in upload folder: {files}")
    if files:
        test_file = files[0]
        return send_from_directory(UPLOAD_FOLDER, test_file, mimetype='application/pdf')
    else:
        return "No PDF files found in the upload folder", 404

@app.route('/list-uploads')
def list_uploads():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify(files)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/<filename>')
def serve_uploaded_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='application/pdf')

@app.route('/upload', methods=['POST'])
def upload_files():
    global results  # Move this line to the beginning of the function
    app.logger.info("Received upload request")
    app.logger.debug(f"Request files: {request.files}")
    app.logger.debug(f"Request form: {request.form}")
    
    if 'files' not in request.files:
        app.logger.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        app.logger.error("No selected files")
        return jsonify({'error': 'No selected files'}), 400
    
    results = []  # Initialize the results list
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            app.logger.info(f"File saved: {filepath}")
            
            # Extract text from PDF
            extracted_text = extract_text_from_pdf(filepath)
            
            # Extract entities using Claude API
            entities = extract_key_fields(extracted_text)
            
            result = {
                'filename': filename,
                'extracted_text': extracted_text,
                'entities': entities,
                'pdfUrl': f'/uploads/{filename}'
            }
            results.append(result)  # Store the result in the global list
            print(results)  # Add this line to print the results list
        else:
            app.logger.error(f"File type not allowed: {file.filename}")
            return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
    
    app.logger.info(f"upload_files is returning: {type(results)}")
    return jsonify(results), 200  # Return the results list directly

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.after_request
def add_csp_header(response):
    response.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; worker-src blob:;"
    return response

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    app.logger.info(f"Attempting to serve PDF: {file_path}")
    if os.path.exists(file_path):
        app.logger.info(f"File found, serving: {file_path}")
        file_size = os.path.getsize(file_path)
        app.logger.info(f"File size: {file_size} bytes")
        return send_file(file_path, mimetype='application/pdf')
    else:
        app.logger.error(f"File not found: {file_path}")
        return "PDF not found", 404

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/extracted_data', methods=['GET'])
def get_extracted_data():
    # This should return the previously extracted data
    # You might need to store this data somewhere (e.g., in-memory, database)
    if not results:  # Assuming 'results' is a global variable storing extracted data
        return jsonify([]), 200
    return jsonify(results), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Flask server on port {port}")
    app.run(debug=True, port=port)