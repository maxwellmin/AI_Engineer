# Phase 4: Document Parser Module - Curl Testing Plan

## Overview

详细的 curl 测试步骤计划，针对 documents_parser 模块的手动测试，覆盖认证流程、文档上传、存储模块测试等所有功能点。

## Prerequisites

### Environment Setup

```bash
# Set environment variables
export BASE_URL="http://localhost:8000/api/v1"
export ACCESS_TOKEN=""  # Will be set after login
export REFRESH_TOKEN=""  # Will be set after login
export DOCUMENT_ID=""  # Will be set after upload
```

### Pre-test Requirements

1. Django server running: `poetry run python manage.py runserver`
2. Database migrated: `poetry run python manage.py migrate`
3. PostgreSQL running
4. MinIO running (optional, for S3 mode testing)
5. Test files prepared (create sample PDF, DOCX, TXT files in test_files/ directory)

---

## Submodule 1: Authentication & Authorization Testing

### Task 1.1: User Registration

**Test Purpose**: Verify new user registration functionality

**Curl Command**:
```bash
curl -X POST "$BASE_URL/accounts/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "TestPass123!",
    "password_confirm": "TestPass123!",
    "phone": "13812345678"
  }'
```

**Expected Result**: `201 Created`
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "testuser@example.com",
    "phone": "13812345678",
    "avatar": "",
    "bio": "",
    "is_verified": false,
    "created_at": "2026-02-25T10:00:00Z",
    "updated_at": "2026-02-25T10:00:00Z"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Status**: [ ] Not tested

---

### Task 1.2: User Login

**Test Purpose**: Verify user login and token generation

**Curl Command**:
```bash
curl -X POST "$BASE_URL/accounts/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!"
  }'
```

**Expected Result**: `200 OK`
```json
{
  "user": { ... },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "knox_token": "abc123def456..."
}
```

**Post-action**: Set tokens in environment
```bash
export ACCESS_TOKEN="<access_token_from_response>"
export REFRESH_TOKEN="<refresh_token_from_response>"
```

**Status**: [ ] Not tested

---

### Task 1.3: Get User Profile

**Test Purpose**: Verify authentication token works

**Curl Command**:
```bash
curl -X GET "$BASE_URL/accounts/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK`
```json
{
  "id": 1,
  "username": "testuser",
  "email": "testuser@example.com",
  "phone": "13812345678",
  "avatar": "",
  "bio": "",
  "is_verified": false,
  "created_at": "2026-02-25T10:00:00Z",
  "updated_at": "2026-02-25T10:00:00Z"
}
```

**Status**: [ ] Not tested

---

### Task 1.4: Update User Profile

**Test Purpose**: Verify authenticated user can update profile

**Curl Command**:
```bash
curl -X PATCH "$BASE_URL/accounts/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Test user for document parser testing",
    "phone": "13999999999"
  }'
```

**Expected Result**: `200 OK`
```json
{
  "id": 1,
  "username": "testuser",
  "bio": "Test user for document parser testing",
  "phone": "13999999999",
  ...
}
```

**Status**: [ ] Not tested

---

## Submodule 2: Document Upload Testing

### Task 2.1: Upload PDF Document

**Test Purpose**: Verify PDF document upload works correctly

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.pdf" \
  -F "title=Test PDF Document" \
  -F "description=This is a test PDF document"
```

**Expected Result**: `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "sample_abc12345.pdf",
  "original_name": "sample.pdf",
  "file_type": "pdf",
  "file_size": 102400,
  "status": "uploaded",
  "title": "Test PDF Document",
  "description": "This is a test PDF document",
  "storage_backend": "s3",
  "created_at": "2026-02-25T10:00:00Z"
}
```

**Post-action**: Set document ID
```bash
export DOCUMENT_ID="<id_from_response>"
```

**Status**: [ ] Not tested

---

### Task 2.2: Upload DOCX Document

**Test Purpose**: Verify DOCX document upload works correctly

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.docx" \
  -F "title=Test DOCX Document"
```

**Expected Result**: `201 Created`
```json
{
  "id": "uuid-string",
  "name": "sample_def67890.docx",
  "original_name": "sample.docx",
  "file_type": "docx",
  "file_size": 204800,
  "status": "uploaded",
  "title": "Test DOCX Document",
  ...
}
```

**Status**: [ ] Not tested

---

### Task 2.3: Upload TXT Document

**Test Purpose**: Verify TXT document upload with encoding detection

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.txt" \
  -F "title=Test TXT Document"
```

**Expected Result**: `201 Created`
```json
{
  "id": "uuid-string",
  "name": "sample_ghi12345.txt",
  "original_name": "sample.txt",
  "file_type": "txt",
  "file_size": 5120,
  "status": "uploaded",
  "title": "Test TXT Document",
  ...
}
```

**Status**: [ ] Not tested

---

### Task 2.4: Upload Duplicate Document

**Test Purpose**: Verify document deduplication works (same file hash)

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.pdf"
```

**Expected Result**: `200 OK` (not 201 Created)
```json
{
  "id": "existing-document-uuid",
  "name": "sample_abc12345.pdf",
  "original_name": "sample.pdf",
  "file_type": "pdf",
  "file_size": 102400,
  "status": "uploaded",
  "message": "Document already exists",
  "created_at": "2026-02-25T10:00:00Z"
}
```

**Status**: [ ] Not tested

---

### Task 2.5: Upload Unsupported File Type

**Test Purpose**: Verify file type validation works

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.jpg"
```

**Expected Result**: `400 Bad Request`
```json
{
  "file": [
    "Unsupported file type '.jpg'. Supported types: pdf, docx, doc, txt, md"
  ]
}
```

**Status**: [ ] Not tested

---

### Task 2.6: Upload Large File (>100MB)

**Test Purpose**: Verify file size limit validation

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/large_file.pdf"
```

**Expected Result**: `400 Bad Request`
```json
{
  "file": [
    "File size exceeds the maximum allowed size (100 MB)"
  ]
}
```

**Status**: [ ] Not tested

---

## Submodule 3: Document Management Testing

### Task 3.1: List All Documents

**Test Purpose**: Verify document list API returns user's documents

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "name": "sample_abc12345.pdf",
      "original_name": "sample.pdf",
      "file_type": "pdf",
      "file_size": 102400,
      "status": "uploaded",
      "title": "Test PDF Document",
      "storage_backend": "s3",
      "created_at": "2026-02-25T10:00:00Z"
    }
  ],
  "pagination": {
    "count": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

**Status**: [ ] Not tested

---

### Task 3.2: List Documents with Status Filter

**Test Purpose**: Verify status filter works correctly

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/?status=uploaded" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK` - Only documents with status "uploaded"
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "status": "uploaded",
      ...
    }
  ],
  "pagination": { ... }
}
```

**Status**: [ ] Not tested

---

### Task 3.3: List Documents with Pagination

**Test Purpose**: Verify pagination parameters work

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/?page=1&page_size=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK` with pagination metadata
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "count": 15,
    "page": 1,
    "page_size": 10,
    "total_pages": 2,
    "has_next": true,
    "has_previous": false
  }
}
```

**Status**: [ ] Not tested

---

### Task 3.4: Get Document Detail

**Test Purpose**: Verify document detail API returns complete information

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/$DOCUMENT_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK`
```json
{
  "id": "uuid-string",
  "name": "sample_abc12345.pdf",
  "original_name": "sample.pdf",
  "file_size": 102400,
  "file_type": "pdf",
  "status": "uploaded",
  "title": "Test PDF Document",
  "description": "This is a test PDF document",
  "author": "",
  "storage_backend": "s3",
  "chunks_count": 0,
  "chunks": [],
  "error_message": "",
  "created_at": "2026-02-25T10:00:00Z",
  "updated_at": "2026-02-25T10:00:00Z"
}
```

**Status**: [ ] Not tested

---

### Task 3.5: Get Non-existent Document

**Test Purpose**: Verify 404 response for non-existent document

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/00000000-0000-0000-0000-000000000000/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `404 Not Found`
```json
{
  "detail": "Not found."
}
```

**Status**: [ ] Not tested

---

## Submodule 4: Document Download Testing

### Task 4.1: Get Presigned Download URL (S3 Mode)

**Test Purpose**: Verify presigned URL generation for S3 storage

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/$DOCUMENT_ID/presigned-url/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result (S3 Mode)**: `200 OK`
```json
{
  "url": "https://s3.amazonaws.com/bucket/documents/2026/02/25/sample_abc12345.pdf?X-Amz-Algorithm=...&X-Amz-Credential=...",
  "expires_in": 3600,
  "method": "GET",
  "backend_type": "s3",
  "is_presigned": true
}
```

**Expected Result (Local Mode)**: `200 OK`
```json
{
  "url": "/media/documents/2026/02/25/sample_abc12345.pdf",
  "expires_in": 0,
  "method": "GET",
  "backend_type": "local",
  "is_presigned": false
}
```

**Status**: [ ] Not tested

---

### Task 4.2: Download Using Presigned URL (S3 Mode)

**Test Purpose**: Verify presigned URL is valid for download

**Curl Command**:
```bash
# First get presigned URL
PRESIGNED_URL=$(curl -s -X GET "$BASE_URL/documents/$DOCUMENT_ID/presigned-url/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.url')

# Then download using the URL (S3 mode only)
curl -X GET "$PRESIGNED_URL" -o downloaded_document.pdf
```

**Expected Result**: File downloaded successfully

**Status**: [ ] Not tested

---

### Task 4.3: Direct Download (Local Mode)

**Test Purpose**: Verify direct download API for local storage

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/$DOCUMENT_ID/download/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -O -J
```

**Expected Result**: `200 OK` - File downloaded with correct filename

**Status**: [ ] Not tested

---

## Submodule 5: Presigned URL Upload Flow Testing

### Task 5.1: Get Presigned Upload URL

**Test Purpose**: Verify presigned upload URL generation

**Curl Command**:
```bash
curl -X POST "$BASE_URL/storage/presigned-upload/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test-document.pdf",
    "file_type": "application/pdf",
    "file_size": 102400
  }'
```

**Expected Result**: `200 OK`
```json
{
  "upload_url": "https://s3.amazonaws.com/bucket/documents/2026/02/25/abc12345-test-document.pdf?X-Amz-Algorithm=...",
  "file_path": "documents/2026/02/25/abc12345-test-document.pdf",
  "expires_in": 3600
}
```

**Post-action**: Save file_path for next test
```bash
export FILE_PATH="<file_path_from_response>"
export UPLOAD_URL="<upload_url_from_response>"
```

**Status**: [ ] Not tested

---

### Task 5.2: Upload File to S3 Using Presigned URL

**Test Purpose**: Verify presigned URL is valid for upload

**Curl Command**:
```bash
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @test_files/sample.pdf
```

**Expected Result**: `200 OK` (S3 returns no body on success)

**Status**: [ ] Not tested

---

### Task 5.3: Confirm Upload and Create Document

**Test Purpose**: Verify upload confirmation creates document record

**Curl Command**:
```bash
curl -X POST "$BASE_URL/storage/confirm-upload/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "'"$FILE_PATH"'",
    "file_name": "test-document.pdf",
    "file_size": 102400,
    "file_type": "pdf",
    "title": "Document via Presigned URL",
    "description": "Uploaded using presigned URL flow"
  }'
```

**Expected Result**: `201 Created`
```json
{
  "id": "new-uuid-string",
  "name": "test-document.pdf",
  "file_path": "documents/2026/02/25/abc12345-test-document.pdf",
  "file_size": 102400,
  "file_type": "pdf",
  "status": "uploaded",
  "title": "Document via Presigned URL",
  "description": "Uploaded using presigned URL flow",
  "message": "Document uploaded successfully"
}
```

**Status**: [ ] Not tested

---

### Task 5.4: Get Presigned Download URL from Storage API

**Test Purpose**: Verify storage presigned download URL generation

**Curl Command**:
```bash
curl -X GET "$BASE_URL/storage/presigned-download/?file_path=$FILE_PATH&expires_in=3600" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `200 OK`
```json
{
  "download_url": "https://s3.amazonaws.com/bucket/documents/2026/02/25/abc12345-test-document.pdf?X-Amz-Algorithm=...",
  "expires_in": 3600
}
```

**Status**: [ ] Not tested

---

## Submodule 6: Document Deletion Testing

### Task 6.1: Delete Document

**Test Purpose**: Verify document deletion works correctly

**Curl Command**:
```bash
curl -X DELETE "$BASE_URL/documents/$DOCUMENT_ID/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `204 No Content` (no response body)

**Status**: [ ] Not tested

---

### Task 6.2: Access Deleted Document

**Test Purpose**: Verify deleted document returns 404

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/$DOCUMENT_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `404 Not Found`
```json
{
  "detail": "Not found."
}
```

**Status**: [ ] Not tested

---

### Task 6.3: Delete Non-existent Document

**Test Purpose**: Verify deleting non-existent document returns 404

**Curl Command**:
```bash
curl -X DELETE "$BASE_URL/documents/00000000-0000-0000-0000-000000000000/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `404 Not Found`
```json
{
  "detail": "Not found."
}
```

**Status**: [ ] Not tested

---

## Submodule 7: Authorization & Security Testing

### Task 7.1: Access API Without Token

**Test Purpose**: Verify 401 response when no token provided

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/"
```

**Expected Result**: `401 Unauthorized`
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status**: [ ] Not tested

---

### Task 7.2: Access API with Invalid Token

**Test Purpose**: Verify 401 response when token is invalid

**Curl Command**:
```bash
curl -X GET "$BASE_URL/documents/" \
  -H "Authorization: Bearer invalid_token_12345"
```

**Expected Result**: `401 Unauthorized`
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is invalid or expired"
    }
  ]
}
```

**Status**: [ ] Not tested

---

### Task 7.3: Access Other User's Document

**Test Purpose**: Verify user cannot access documents owned by others

**Prerequisite**: Create a second user and upload a document

**Curl Command**:
```bash
# Create second user
curl -X POST "$BASE_URL/accounts/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "otheruser",
    "email": "other@example.com",
    "password": "TestPass123!",
    "password_confirm": "TestPass123!"
  }'

# Login as second user and get their document ID
# Then try to access it with first user's token
curl -X GET "$BASE_URL/documents/$OTHER_USER_DOCUMENT_ID/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Result**: `404 Not Found`
```json
{
  "detail": "Not found."
}
```

**Status**: [ ] Not tested

---

### Task 7.4: Rate Limit Testing (Auth Endpoints)

**Test Purpose**: Verify rate limiting works on auth endpoints (5 req/min)

**Curl Command**:
```bash
# Send 6 login requests rapidly
for i in {1..6}; do
  curl -X POST "$BASE_URL/accounts/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"wrongpass"}'
  echo ""
done
```

**Expected Result**: Last request returns `429 Too Many Requests`
```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

**Status**: [ ] Not tested

---

## Submodule 8: Edge Case Testing

### Task 8.1: Upload File Without Required Fields

**Test Purpose**: Verify validation for missing file field

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=No File Upload"
```

**Expected Result**: `400 Bad Request`
```json
{
  "file": [
    "No file was submitted."
  ]
}
```

**Status**: [ ] Not tested

---

### Task 8.2: Upload Empty File

**Test Purpose**: Verify validation for empty file

**Curl Command**:
```bash
# Create empty file
touch test_files/empty.pdf

curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/empty.pdf"
```

**Expected Result**: `400 Bad Request`
```json
{
  "file": [
    "The submitted file is empty."
  ]
}
```

**Status**: [ ] Not tested

---

### Task 8.3: Upload File with Special Characters in Name

**Test Purpose**: Verify handling of special characters in filename

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/test 文件 (1).pdf"
```

**Expected Result**: `201 Created` - Filename should be sanitized
```json
{
  "id": "uuid-string",
  "original_name": "test 文件 (1).pdf",
  "name": "test____1_abc12345.pdf",
  ...
}
```

**Status**: [ ] Not tested

---

### Task 8.4: Upload Corrupted PDF File

**Test Purpose**: Verify handling of corrupted file

**Curl Command**:
```bash
# Create corrupted file
echo "This is not a PDF" > test_files/corrupted.pdf

curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/corrupted.pdf"
```

**Expected Result**: File uploads but may fail during processing (status will be "failed" if processing is triggered)

**Status**: [ ] Not tested

---

## Submodule 9: Token Management Testing

### Task 9.1: Refresh Access Token

**Test Purpose**: Verify token refresh works correctly

**Curl Command**:
```bash
curl -X POST "$BASE_URL/accounts/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "'"$REFRESH_TOKEN"'"}'
```

**Expected Result**: `200 OK`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Status**: [ ] Not tested

---

### Task 9.2: Logout User

**Test Purpose**: Verify logout works and token is blacklisted

**Curl Command**:
```bash
curl -X POST "$BASE_URL/accounts/auth/logout/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "'"$REFRESH_TOKEN"'"}'
```

**Expected Result**: `200 OK`
```json
{
  "message": "Successfully logged out"
}
```

**Status**: [ ] Not tested

---

### Task 9.3: Use Blacklisted Refresh Token

**Test Purpose**: Verify blacklisted token cannot be used

**Curl Command**:
```bash
curl -X POST "$BASE_URL/accounts/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "'"$REFRESH_TOKEN"'"}'
```

**Expected Result**: `401 Unauthorized`
```json
{
  "detail": "Token is blacklisted",
  "code": "token_is_blacklisted"
}
```

**Status**: [ ] Not tested

---

## Submodule 10: Multi-format Testing

### Task 10.1: Upload Markdown File

**Test Purpose**: Verify MD file format support

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.md" \
  -F "title=Markdown Document"
```

**Expected Result**: `201 Created`
```json
{
  "id": "uuid-string",
  "file_type": "md",
  "original_name": "sample.md",
  ...
}
```

**Status**: [ ] Not tested

---

### Task 10.2: Upload Old DOC Format

**Test Purpose**: Verify legacy DOC format support

**Curl Command**:
```bash
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_files/sample.doc" \
  -F "title=Legacy DOC Document"
```

**Expected Result**: `201 Created`
```json
{
  "id": "uuid-string",
  "file_type": "doc",
  "original_name": "sample.doc",
  ...
}
```

**Status**: [ ] Not tested

---

## Testing Checklist Summary

### Pre-requisites Checklist

- [ ] Django server running on port 8000
- [ ] PostgreSQL database running
- [ ] Database migrations applied
- [ ] MinIO running (for S3 mode testing)
- [ ] Test files prepared in test_files/ directory
- [ ] Environment variables set

### Test Files Required

Create the following test files:

```bash
mkdir -p test_files
# Create sample files for testing
touch test_files/sample.pdf
touch test_files/sample.docx
touch test_files/sample.txt
touch test_files/sample.md
touch test_files/sample.doc
touch test_files/sample.jpg  # For unsupported type testing
touch test_files/large_file.pdf  # >100MB for size limit testing
touch test_files/empty.pdf  # Empty file testing
touch test_files/corrupted.pdf  # Corrupted file testing
```

### Test Execution Order

**Recommended execution sequence**:

1. **Submodule 1**: Authentication (Tasks 1.1-1.4) - Setup user and tokens
2. **Submodule 2**: Upload Testing (Tasks 2.1-2.6) - Test document upload
3. **Submodule 3**: Management Testing (Tasks 3.1-3.5) - Test list/detail APIs
4. **Submodule 4**: Download Testing (Tasks 4.1-4.3) - Test download functionality
5. **Submodule 5**: Presigned Flow (Tasks 5.1-5.4) - Test S3 direct upload
6. **Submodule 6**: Deletion Testing (Tasks 6.1-6.3) - Test delete functionality
7. **Submodule 7**: Authorization (Tasks 7.1-7.4) - Security testing
8. **Submodule 8**: Edge Cases (Tasks 8.1-8.4) - Boundary condition testing
9. **Submodule 9**: Token Management (Tasks 9.1-9.3) - Token lifecycle testing
10. **Submodule 10**: Multi-format (Tasks 10.1-10.2) - Format support testing

---

## Success Criteria

- [ ] All authentication flows work correctly
- [ ] Document upload works for all supported formats (PDF, DOCX, TXT, MD, DOC)
- [ ] Document deduplication prevents duplicate uploads
- [ ] File type validation rejects unsupported formats
- [ ] File size limit validation works
- [ ] Document list returns correct results with filters and pagination
- [ ] Document detail API returns complete information
- [ ] Presigned URL upload flow works end-to-end
- [ ] Document download works in both S3 and Local modes
- [ ] Document deletion removes file and database record
- [ ] Authorization prevents unauthorized access
- [ ] Rate limiting works on auth endpoints
- [ ] Edge cases handled gracefully
- [ ] Token refresh and blacklisting work correctly

---

## Troubleshooting Guide

| Problem | Solution |
|---------|----------|
| Connection refused | Ensure Django server is running: `poetry run python manage.py runserver` |
| 401 Unauthorized | Check token format: `Bearer <token>`, verify token not expired |
| 400 Bad Request (file type) | Confirm file extension is supported: pdf, docx, doc, txt, md |
| 400 Bad Request (file size) | Confirm file size does not exceed 100MB |
| 404 Not Found | Confirm document UUID is correct and belongs to current user |
| Token expired | Use refresh token to get new access token: Task 9.1 |
| Presigned URL not working | Check `USE_S3_STORAGE` setting, verify MinIO/S3 is running |
| Upload confirmation fails | Ensure file was uploaded to S3 before calling confirm endpoint |
| CORS error | Use Swagger UI or ensure `CORS_ALLOW_ALL_ORIGINS=True` in local settings |

---

## Database Verification

### Check uploaded documents

```bash
poetry run python manage.py dbshell
```

```sql
-- View all documents
SELECT id, original_name, file_type, status, storage_backend, created_at
FROM documents_parser_document
ORDER BY created_at DESC;

-- View documents for specific user
SELECT id, original_name, status
FROM documents_parser_document
WHERE user_id = 'user-uuid';

-- Count documents by status
SELECT status, COUNT(*)
FROM documents_parser_document
GROUP BY status;

-- View document chunks
SELECT d.original_name, c.chunk_index, LENGTH(c.content) as content_length
FROM documents_parser_document d
JOIN documents_parser_documentchunk c ON d.id = c.document_id
ORDER BY d.created_at DESC, c.chunk_index;
```

---

## Test Report Template

After completing all tests, use this template to report results:

```markdown
# Test Execution Report

**Date**: YYYY-MM-DD
**Tester**: Name
**Environment**: Local/Development/Staging

## Summary

- Total Tests: 40
- Passed: X
- Failed: Y
- Skipped: Z

## Detailed Results

### Submodule 1: Authentication
- [x] Task 1.1: User Registration - PASSED
- [x] Task 1.2: User Login - PASSED
- [ ] Task 1.3: Get User Profile - FAILED (reason)
- [ ] Task 1.4: Update User Profile - SKIPPED (dependency)

### Submodule 2: Document Upload
...

## Issues Found
1. Issue description...
2. Issue description...

## Recommendations
1. Recommendation...
2. Recommendation...
```

---

## Notes

- This plan assumes Phase 4 implementation is complete
- All curl commands use environment variables for flexibility
- Tests should be executed in sequential order as some depend on previous results
- For S3 mode testing, ensure MinIO or AWS S3 is properly configured
- For Local mode testing, ensure `USE_S3_STORAGE=false` in environment
- Test files should be created before starting test execution
- Save tokens and document IDs after each step for subsequent tests
