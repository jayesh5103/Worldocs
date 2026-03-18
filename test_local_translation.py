import os
import sys

# Patch boto3 to avoid S3 upload during local test
import boto3
class DummyS3:
    def upload_file(self, *args, **kwargs):
        print("Mock S3 Upload:", args)
    def generate_presigned_url(self, *args, **kwargs):
        return "http://mock-url"

import app
app.s3 = DummyS3()

# Patch database to avoid issues
class DummyTask:
    status = "processing"
    download_url = ""

class DummyQuery:
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        return DummyTask()

class DummySession:
    def query(self, *args, **kwargs):
        return DummyQuery()
    def commit(self):
        pass
    def close(self):
        pass

import database
database.SessionLocal = lambda: DummySession()

print("Testing app.process_translation...")
test_pdf = "sample.pdf"
if not os.path.exists(test_pdf):
    print("sample.pdf missing, generating mock pdf to test")
    # Generate mock PDF
    import fitz
    d = fitz.open()
    p = d.new_page()
    p.insert_text((50, 50), "Name : John Doe", fontsize=15)
    d.save(test_pdf)

# Prevent deletion of sample.pdf
_original_remove = os.remove
def mock_remove(path):
    if path != test_pdf:
        _original_remove(path)
os.remove = mock_remove

# Test Marathi translation
app.process_translation(input_path=test_pdf, language="mr", task_id="test1234", file_key="test1234.pdf")

if os.path.exists("translated_test1234.pdf"):
    print("SUCCESS: translated_test1234.pdf was generated!")
else:
    print("FAILED: Output PDF not generated")
