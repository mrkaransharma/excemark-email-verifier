from flask import Flask, render_template, request, send_file
import csv
import io
import re
import dns.resolver
import smtplib
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

def is_valid_email(email):
    return re.match(EMAIL_REGEX, email)

def check_mx(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return True
    except:
        return False

def smtp_check(email):
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(mx_records[0].exchange)
        server = smtplib.SMTP(timeout=3)
        server.connect(mx_record)
        server.helo("example.com")
        server.mail("test@example.com")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except:
        return False

def verify_email(email):
    if not is_valid_email(email):
        return 'invalid', 'Invalid syntax'
    domain = email.split('@')[1]
    if not check_mx(domain):
        return 'invalid', 'No MX record'
    if not smtp_check(email):
        return 'risky', 'SMTP check failed'
    return 'valid', 'Valid email'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return "No file uploaded.", 400
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        output = io.StringIO()
        csv_output = csv.writer(output)
        header = next(csv_input)
        header += ['Status', 'Reason']
        csv_output.writerow(header)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(lambda row: row + list(verify_email(row[0])), csv_input)
            for row in results:
                csv_output.writerow(row)

        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='verified_emails.csv')
    return render_template('index.html')
