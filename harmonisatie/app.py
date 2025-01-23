from flask import Flask, request, render_template, jsonify
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def compare_texts(text1, text2):
    """Compare two texts using OpenAI API."""
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Vergelijk de verschillen tussen de protocollen van Den Haag en Zoetermeer. opmaak is onbelangrijk. het gaat om de inhoud"},
            {"role": "user", "content": f"Hier volgen de protocollen:\n\nProtocollen Den Haag:\n{text1}\n\nProtocollen Zoetermeer:\n{text2}"}
        ]
    )
    
    return completion.choices[0].message.content

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
        # Save both files
        filename1 = secure_filename(file1.filename)
        filename2 = secure_filename(file2.filename)
        filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
        filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
        
        file1.save(filepath1)
        file2.save(filepath2)
        
        # Extract text from both PDFs
        text1 = extract_text_from_pdf(filepath1)
        text2 = extract_text_from_pdf(filepath2)
        
        # Generate comparison only
        comparison = compare_texts(text1, text2)
        
        # Clean up - delete the uploaded files
        os.remove(filepath1)
        os.remove(filepath2)
        
        return jsonify({
            'comparison': comparison
        })
        
    except Exception as e:
        # Clean up in case of error
        if os.path.exists(filepath1):
            os.remove(filepath1)
        if os.path.exists(filepath2):
            os.remove(filepath2)
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 