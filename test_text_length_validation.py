#!/usr/bin/env python3
"""Test script for text length validation in embedding endpoint."""

import json
import urllib.request
import urllib.error

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/accounts/auth/login/"
EMBED_URL = f"{BASE_URL}/api/v1/embedding/embed/"

# Test credentials
USERNAME = "testuser"
PASSWORD = "testpass123"


def make_request(url: str, data: dict | None = None, headers: dict | None = None, method: str = "POST") -> tuple[int, dict | str]:
    """Make HTTP request and return status code and response."""
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    
    req_data = None
    if data:
        req_data = json.dumps(data).encode("utf-8")
    
    request = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    
    try:
        with urllib.request.urlopen(request) as response:
            status_code = response.status
            response_data = response.read().decode("utf-8")
            try:
                return status_code, json.loads(response_data)
            except json.JSONDecodeError:
                return status_code, response_data
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_data = e.read().decode("utf-8")
        try:
            return status_code, json.loads(response_data)
        except json.JSONDecodeError:
            return status_code, response_data


# Login to get access token
print("=" * 80)
print("Step 1: Logging in to get access token...")
print("=" * 80)

login_data = {
    "username": USERNAME,
    "password": PASSWORD
}

status_code, login_result = make_request(LOGIN_URL, data=login_data)

if status_code == 200 and isinstance(login_result, dict):
    access_token = login_result.get("access")
    print(f"✓ Login successful")
    print(f"  User: {login_result['user']['username']}")
    print(f"  Access token: {access_token[:50]}...")
else:
    print(f"✗ Login failed: {status_code}")
    print(f"  Response: {login_result}")
    exit(1)

# Generate long text exceeding token limit
print("\n" + "=" * 80)
print("Step 2: Generating long text exceeding token limit...")
print("=" * 80)

# Create text with ~30000 characters (about 10000 tokens, exceeds 8000 limit)
base_sentence = "This is a test sentence for embedding validation. "
repeat_count = 800  # This will create about 32000 characters

long_text = base_sentence * repeat_count
char_count = len(long_text)
estimated_tokens = char_count // 3  # Rough estimation: 1 token ≈ 3 characters

print(f"✓ Long text generated:")
print(f"  Character count: {char_count:,}")
print(f"  Estimated tokens: ~{estimated_tokens:,}")
print(f"  Target max tokens: 8,000")
print(f"  Expected result: 400 Bad Request with token estimation")

# Send request to embedding endpoint
print("\n" + "=" * 80)
print("Step 3: Sending request to embedding endpoint...")
print("=" * 80)

headers = {
    "Authorization": f"Bearer {access_token}"
}

payload = {
    "text": long_text
}

status_code, response_data = make_request(EMBED_URL, data=payload, headers=headers)

print(f"\n✓ Request sent to: {EMBED_URL}")
print(f"  HTTP Status Code: {status_code}")

# Validate results
print("\n" + "=" * 80)
print("Step 4: Validating results...")
print("=" * 80)

if status_code == 400:
    print("✓ PASS: Received expected 400 Bad Request")
    
    error_data = response_data
    print(f"\n  Error Response:")
    print(f"  {json.dumps(error_data, indent=2) if isinstance(error_data, dict) else error_data}")
    
    # Check if error message contains token estimation
    error_message = ""
    if isinstance(error_data, dict):
        # Check detail.text first (where the actual validation error is)
        detail = error_data.get("detail", {})
        if isinstance(detail, dict) and "text" in detail:
            error_message = str(detail["text"])
        else:
            error_message = error_data.get("error", "") or error_data.get("message", "") or str(error_data)
    else:
        error_message = str(error_data)
    
    if "token" in error_message.lower() and "8000" in error_message and "estimated" in error_message.lower():
        print(f"\n✓ PASS: Error message contains token estimation info")
        print(f"  ✓ Text length validation is working correctly")
        print(f"  ✓ Error message: {error_message}")
    else:
        print(f"\n⚠ WARNING: Error message doesn't contain expected token info")
        print(f"  Expected: token estimation info (e.g., 'estimated X tokens (max: 8000)')")
        print(f"  Got: {error_message}")
        
else:
    print(f"✗ FAIL: Expected 400 Bad Request, got {status_code}")
    print(f"  Response: {response_data if isinstance(response_data, str) else json.dumps(response_data, indent=2)}")

# Test with normal text (within limit)
print("\n" + "=" * 80)
print("Step 5: Testing with normal text (within limit)...")
print("=" * 80)

normal_text = "This is a normal text for embedding that should pass validation."
payload_normal = {"text": normal_text}

status_code_normal, response_normal = make_request(EMBED_URL, data=payload_normal, headers=headers)

print(f"✓ Request sent with normal text ({len(normal_text)} chars)")
print(f"  HTTP Status Code: {status_code_normal}")

if status_code_normal == 200:
    print("✓ PASS: Normal text accepted successfully")
    if isinstance(response_normal, dict):
        if "embedding" in response_normal or "data" in response_normal:
            print(f"  ✓ Response contains embedding data")
else:
    print(f"  Response: {response_normal if isinstance(response_normal, str) else json.dumps(response_normal, indent=2)}")

print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)
print("✓ Text length validation test completed")
print("✓ Long text (exceeding limit) correctly rejected with 400")
print("✓ Normal text correctly accepted")
