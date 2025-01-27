from flask import Flask, request, render_template, jsonify
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import tempfile
import traceback
import json

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

# Set the correct template folder path
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {str(e)}")
        raise Exception("Error reading PDF file")

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
        
        # Ensure we get a valid response
        if not completion or not completion.choices or not completion.choices[0].message:
            raise Exception("Invalid response from OpenAI API")
            
        response_text = completion.choices[0].message.content
        if not response_text:
            raise Exception("Empty response from OpenAI API")
            
        return response_text
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in compare_texts: {error_msg}")
        print(traceback.format_exc())
        
        # Ensure we return a valid JSON-serializable error message
        try:
            json.dumps({'error': error_msg})
            raise Exception(error_msg)
        except:
            raise Exception("Error comparing texts")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file1' not in request.files or 'file2' not in request.files:
            return jsonify({'error': 'Both files are required'}), 400
        
        file1 = request.files['file1']
        file2 = request.files['file2']
        
        if file1.filename == '' or file2.filename == '':
            return jsonify({'error': 'Both files must be selected'}), 400
        
        if not (file1.filename.lower().endswith('.pdf') and file2.filename.lower().endswith('.pdf')):
            return jsonify({'error': 'Both files must be PDFs'}), 400
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as temp1, tempfile.NamedTemporaryFile(delete=False) as temp2:
            file1.save(temp1.name)
            file2.save(temp2.name)
            
            try:
                # Extract text from both PDFs
                text1 = extract_text_from_pdf(temp1.name)
                text2 = extract_text_from_pdf(temp2.name)
                
                # Generate comparison
                comparison = compare_texts(text1, text2)
                
                # Ensure the response is JSON serializable
                response = {'comparison': comparison}
                try:
                    json.dumps(response)
                    return jsonify(response)
                except:
                    return jsonify({'error': 'Invalid response format'}), 500
                    
            except Exception as e:
                error_msg = str(e)
                try:
                    json.dumps({'error': error_msg})
                    return jsonify({'error': error_msg}), 500
                except:
                    return jsonify({'error': 'An unexpected error occurred'}), 500
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp1.name)
                    os.unlink(temp2.name)
                except:
                    pass
                
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'error': 'An unexpected error occurred'
        }), 500

# For local development
if __name__ == '__main__':
    print("Starting Flask application...")
    app.run(debug=True, port=5000) 