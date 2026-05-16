import requests
import io
import json

API = "http://127.0.0.1:8000/api"

session = requests.Session()

print('Creating job...')
job_payload = {
    'title': 'Senior Python/Django Engineer',
    'company_name': 'TestCorp',
    'location': 'Remote',
    'employment_type': 'full_time',
    'description': 'We need a Senior Python developer with Django and Docker experience.',
    'required_skills': ['python', 'django', 'docker'],
    'minimum_experience': 3,
}
resp = session.post(f'{API}/jobs/', json=job_payload)
print('job status', resp.status_code)
print(resp.text)
if resp.status_code != 201:
    raise SystemExit('Job creation failed')
job = resp.json()

print('Creating candidate with small CV file...')
cv_bytes = b"John Doe\nExperienced Python developer. Skills: Python, Django, Docker. 5 years experience."
files = {'cv_file': ('cv.pdf', cv_bytes)}
data = {
    'full_name': 'John Doe',
    'email': 'john@example.com',
    'phone_number': '1234567890',
    'years_of_experience': '5.0',
    'skills': json.dumps(['python','django','docker']),
}
# Note: skills must be JSON list; candidate serializer expects list, but multipart form needs string.
resp = session.post(f'{API}/candidates/', data=data, files=files)
print('candidate status', resp.status_code)
print(resp.text)
if resp.status_code not in (200,201):
    raise SystemExit('Candidate creation failed')
candidate = resp.json()

print('Triggering match...')
match_payload = {'candidate_id': candidate['id'], 'job_id': job['id']}
resp = session.post(f'{API}/match/', json=match_payload)
print('match status', resp.status_code)
print(resp.text)
if resp.status_code != 200:
    raise SystemExit('Match failed')

print('Requesting match explanation via AI endpoint...')
resp = session.post(f'{API}/ai/match-explanation/', json=match_payload)
print('explain status', resp.status_code)
print(resp.text)

print('Requesting interview questions via AI endpoint...')
resp = session.post(f'{API}/ai/interview-questions/', json=match_payload)
print('interview status', resp.status_code)
print(resp.text)

print('Job parse test...')
resp = session.post(f'{API}/ai/parse-job/', json={'job_description': job['description']})
print('parse status', resp.status_code)
print(resp.text)

print('Done')
