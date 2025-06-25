import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super-secret-key-for-session-management'
app.config['UPLOAD_FOLDER'] = 'patient_audio'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('patient_pdfs', exist_ok=True)


# --- Mock Data and Placeholder Functions ---

# In-memory data stores (for demonstration purposes)
# In a real app, use a database (e.g., SQLite, PostgreSQL)
users = {
    'nurse': {'password': 'password', 'role': 'nurse'},
    'doctor': {'password': 'password', 'role': 'doctor'}
}
patient_queue = []
consultation_data = {} # To hold data during a consultation session

# Mock medicine inventory
medicine_inventory = [
    "Paracetamol 500mg", "Amoxicillin 250mg", "Ibuprofen 200mg",
    "Lisinopril 10mg", "Metformin 500mg", "Aspirin 81mg", "Salbutamol Inhaler"
]

# Placeholder for AI-based transcription
def transcribe_audio(audio_file_path):
    print(f"Transcribing {audio_file_path}...")
    # In a real app, integrate a speech-to-text API or model here
    return "Patient complained of persistent cough and shortness of breath for the last three days. Also mentioned feeling feverish. No history of similar symptoms."

# Placeholder for AI-based summarization
def summarize_text(text):
    print("Summarizing text...")
    # In a real app, use a summarization model (e.g., from Hugging Face)
    return "Persistent cough, shortness of breath, and fever for 3 days."

# Placeholder for AI-based suggestion generation
def get_examination_suggestions(summary):
    suggestions = []
    if "cough" in summary.lower() or "breath" in summary.lower():
        suggestions.append("Auscultate chest for wheezing or crackles")
        suggestions.append("Check oxygen saturation (SpO2)")
    if "fever" in summary.lower():
        suggestions.append("Measure body temperature")
    return suggestions

def get_prescription_suggestions(summary):
    suggestions = []
    if "cough" in summary.lower():
        suggestions.append("Salbutamol Inhaler")
    if "fever" in summary.lower():
        suggestions.append("Paracetamol 500mg")
    return suggestions

def get_lab_test_suggestions(summary):
    suggestions = []
    if "fever" in summary.lower():
        suggestions.append("Complete Blood Count (CBC)")
    if "breath" in summary.lower():
        suggestions.append("Chest X-Ray (CXR)")
    return suggestions


# --- Routes ---

@app.route('/')
def index():
    if 'username' in session:
        role = session.get('role')
        if role == 'nurse':
            return redirect(url_for('nurse_dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/nurse/dashboard', methods=['GET', 'POST'])
def nurse_dashboard():
    if session.get('role') != 'nurse':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Collect all form fields, including new ones
        patient = {
            'id': str(len(patient_queue) + 1),
            'name': request.form.get('name'),
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'mobile': request.form.get('mobile'),
            'height': request.form.get('height'),
            'weight': request.form.get('weight'),
            'heart_rate': request.form.get('heart_rate'),
            'temperature': request.form.get('temperature'),
            'vitals': request.form.get('vitals'),
            'status': 'Waiting'
        }
        patient_queue.append(patient)
        return redirect(url_for('nurse_dashboard'))
    
    return render_template('nurse_dashboard.html', queue=patient_queue)

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))
    return render_template('doctor_dashboard.html', queue=patient_queue)

@app.route('/consultation/<patient_id>')
def consultation(patient_id):
    if session.get('role') != 'doctor':
        return redirect(url_for('login'))

    patient = next((p for p in patient_queue if p['id'] == patient_id), None)
    if not patient:
        return "Patient not found", 404
        
    consultation_data[patient_id] = {'patient': patient}
    return render_template('consultation.html', patient=patient)

@app.route('/process_audio/<patient_id>', methods=['POST'])
def process_audio(patient_id):
    if session.get('role') != 'doctor':
        return {"error": "Unauthorized"}, 403

    if 'audio_data' not in request.files:
        return {"error": "No audio file"}, 400
    
    file = request.files['audio_data']
    filename = secure_filename(f"{patient_id}.wav")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # AI Processing
    transcription = transcribe_audio(filepath)
    summary = summarize_text(transcription)
    
    # Store results
    consultation_data[patient_id]['transcription'] = transcription
    consultation_data[patient_id]['summary'] = summary
    
    return redirect(url_for('examination', patient_id=patient_id))
    
@app.route('/examination/<patient_id>', methods=['GET', 'POST'])
def examination(patient_id):
    if session.get('role') != 'doctor' or patient_id not in consultation_data:
        return redirect(url_for('login'))
        
    data = consultation_data[patient_id]

    if request.method == 'POST':
        selected_exams = request.form.getlist('exams')
        custom_exam = request.form.get('custom_exam')
        if custom_exam:
            selected_exams.append(custom_exam)
        data['exams'] = selected_exams
        return redirect(url_for('prescription', patient_id=patient_id))

    summary = data.get('summary', '')
    suggestions = get_examination_suggestions(summary)
    return render_template('examination.html', patient=data['patient'], summary=summary, suggestions=suggestions)


@app.route('/prescription/<patient_id>', methods=['GET', 'POST'])
def prescription(patient_id):
    if session.get('role') != 'doctor' or patient_id not in consultation_data:
        return redirect(url_for('login'))
        
    data = consultation_data[patient_id]
    
    if request.method == 'POST':
        selected_meds = request.form.getlist('prescriptions')
        data['prescriptions'] = selected_meds
        return redirect(url_for('lab_tests', patient_id=patient_id))

    summary = data.get('summary', '')
    suggestions = get_prescription_suggestions(summary)
    return render_template('prescription.html', patient=data['patient'], summary=summary, suggestions=suggestions, inventory=medicine_inventory)

@app.route('/lab_tests/<patient_id>', methods=['GET', 'POST'])
def lab_tests(patient_id):
    if session.get('role') != 'doctor' or patient_id not in consultation_data:
        return redirect(url_for('login'))
        
    data = consultation_data[patient_id]
    
    if request.method == 'POST':
        selected_tests = request.form.getlist('tests')
        custom_test = request.form.get('custom_test')
        if custom_test:
            selected_tests.append(custom_test)
        data['lab_tests'] = selected_tests
        return redirect(url_for('summary', patient_id=patient_id))

    summary = data.get('summary', '')
    suggestions = get_lab_test_suggestions(summary)
    return render_template('lab_tests.html', patient=data['patient'], summary=summary, suggestions=suggestions)

@app.route('/summary/<patient_id>')
def summary(patient_id):
    if session.get('role') != 'doctor' or patient_id not in consultation_data:
        return redirect(url_for('login'))
        
    data = consultation_data[patient_id]
    return render_template('summary.html', data=data)

@app.route('/download_pdf/<patient_id>')
def download_pdf(patient_id):
    if session.get('role') != 'doctor' or patient_id not in consultation_data:
        return redirect(url_for('login'))

    data = consultation_data[patient_id]
    patient = data['patient']
    
    pdf_dir = 'patient_pdfs'
    pdf_path = os.path.join(pdf_dir, f"{patient['name'].replace(' ', '_')}_prescription.pdf")
    
    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("E-Prescription", styles['h1']))
    story.append(Spacer(1, 12))
    
    summary_data = {
        "Patient Name": patient.get('name', ''),
        "Age": patient.get('age', ''),
        "Gender": patient.get('gender', ''),
        "Vitals": patient.get('vitals', ''),
        "Chief Complaint Summary": data.get('summary', 'N/A'),
        "Physical Examination": ", ".join(data.get('exams', ['N/A'])),
        "Prescription": "<br/>".join(data.get('prescriptions', ['N/A'])),
        "Lab Tests": "<br/>".join(data.get('lab_tests', ['N/A']))
    }
    
    for key, value in summary_data.items():
        story.append(Paragraph(f"<b>{key}:</b> {value}", styles['BodyText']))
        story.append(Spacer(1, 6))

    doc.build(story)
    
    # After generating PDF, remove patient from queue and clear consultation data
    global patient_queue
    patient_queue = [p for p in patient_queue if p['id'] != patient_id]
    del consultation_data[patient_id]
    
    return send_from_directory(directory=pdf_dir, path=os.path.basename(pdf_path), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)