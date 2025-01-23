from flask import Flask, request, render_template, jsonify
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import tempfile
import httpx

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY environment variable.")

# Configure httpx client with timeout
timeout = httpx.Timeout(30.0, connect=30.0)
http_client = httpx.Client(timeout=timeout)
client = OpenAI(
    api_key=api_key,
    http_client=http_client,
    max_retries=3
)

# Set the correct template folder path
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def compare_texts(text1, text2):
    """Compare two texts using OpenAI API."""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Vergelijk de verschillen tussen de protocollen van Den Haag en Zoetermeer. opmaak is onbelangrijk. het gaat om de inhoud"},
                {"role": "user", "content": f"Hier volgen de protocollen:\n\nProtocollen Den Haag:\n{text1}\n\nProtocollen Zoetermeer:\n{text2}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error in compare_texts: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({'error': 'Both files are required'})
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': 'Both files must be selected'})
    
    if not (file1.filename.lower().endswith('.pdf') and file2.filename.lower().endswith('.pdf')):
        return jsonify({'error': 'Both files must be PDFs'})
    
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as temp1, tempfile.NamedTemporaryFile(delete=False) as temp2:
            file1.save(temp1.name)
            file2.save(temp2.name)
            
            # Extract text from both PDFs
            text1 = extract_text_from_pdf(temp1.name)
            text2 = extract_text_from_pdf(temp2.name)
            
            # Clean up temporary files
            os.unlink(temp1.name)
            os.unlink(temp2.name)
            
            # Generate comparison
            comparison = compare_texts(text1, text2)
            
            return jsonify({
                'comparison': comparison
            })
            
    except Exception as e:
        return jsonify({'error': str(e)})

# Cleanup when the application exits
@app.teardown_appcontext
def cleanup(error):
    if http_client:
        http_client.close()

# For local development
if __name__ == '__main__':
    print("Starting Flask application...")
    app.run(debug=True, port=5000) 