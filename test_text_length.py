#!/usr/bin/env python3
"""Test script for text length validation (Test 22)."""

import json
import urllib.request
import os

# Disable proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

# Access token from login
access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyNTA2ODk0LCJpYXQiOjE3NzI1MDU5OTQsImp0aSI6IjJjZWNmNzBiYzliNTQ5YWE5YzQ4MDg2Zjg4NTRhZGJjIiwidXNlcl9pZCI6IjEifQ.5R7lkELwwcBr7GnxHL09jVRGj7mxGGlgX8CpYW4r_9Y'

# Create a very long text (35000 characters)
long_text = 'A' * 35000

print(f"Testing with text length: {len(long_text)} characters")
print(f"Expected: 400 Bad Request with token estimation error")
print("-" * 80)

# Prepare request
data = json.dumps({'text': long_text}).encode('utf-8')

# Create a handler that doesn't use proxy
proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)

req = urllib.request.Request(
    'http://localhost:8000/api/v1/embedding/embed/',
    data=data,
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    },
    method='POST'
)

# Execute request
try:
    with opener.open(req, timeout=30) as response:
        print(f"Status Code: {response.status}")
        print(f"Response Body:\n{response.read().decode()}")
        print("\nTest FAILED: Expected 400 Bad Request, got success response")
except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    response_body = e.read().decode()
    print(f"Response Body:\n{response_body}")
    
    # Validate response
    if e.code == 400:
        print("\nTest PASSED: Got 400 Bad Request as expected")
        
        # Check if error message contains token estimation
        if 'token' in response_body.lower() or 'length' in response_body.lower():
            print("Validation message present: YES")
        else:
            print("Warning: Expected token/length validation message in response")
    else:
        print(f"\nTest FAILED: Expected 400, got {e.code}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    print("\nTest FAILED: Request failed with exception")
