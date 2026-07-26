import pytest
from unittest.mock import MagicMock, patch
from backend.app.auth import create_access_token

def test_reject_issue_success(client, mock_db):
    token = create_access_token({"sub": "ward_member_id", "role": "ward_member"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Custom side effect for fetchone:
    # 1. First fetch is get_current_user/RoleChecker: return ward member user profile
    # 2. Second fetch is issue details check inside reject_issue: return pending issue belonging to ward_member_id
    mock_db.fetchone.side_effect = [
        # User Profile fetch (Auth)
        {
            "id": "ward_member_id",
            "username": "ward_member_test",
            "role": "ward_member",
            "full_name": "Ward Member User",
            "contact": "9876543210",
            "is_approved": True,
            "department_id": None,
            "department_name": None,
            "ward_id": 1,
            "ward_name": "Ward 1"
        },
        # Issue Verification fetch (reject_issue)
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "status": "pending",
            "ward_id": 1,
            "ward_member_id": "ward_member_id"
        }
    ]
    
    payload = {
        "reason": "Not a civic issue, belongs to private property."
    }
    
    # Use real image magic bytes to bypass magic bytes checks
    dummy_image = ("evidence.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"dummy pixels")
    
    response = client.post(
        "/api/ward/issues/11111111-2222-3333-4444-555555555555/reject",
        data=payload,
        files={"evidence": dummy_image},
        headers=headers
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "Issue rejected" in res_data["message"]
    assert "tx_hash" in res_data
    assert "ipfs_cid" in res_data
    assert "blockchain_hash" in res_data

def test_reject_issue_not_authorized(client, mock_db):
    # Try with another ward member who doesn't own the issue
    token = create_access_token({"sub": "another_ward_member_id", "role": "ward_member"})
    headers = {"Authorization": f"Bearer {token}"}
    
    mock_db.fetchone.side_effect = [
        # User Profile
        {
            "id": "another_ward_member_id",
            "username": "another_ward_test",
            "role": "ward_member",
            "full_name": "Another Ward Member",
            "contact": "123",
            "is_approved": True,
            "department_id": None,
            "department_name": None,
            "ward_id": 2,
            "ward_name": "Ward 2"
        },
        # Issue Verification: belongs to ward_member_id, not another_ward_member_id
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "status": "pending",
            "ward_id": 1,
            "ward_member_id": "ward_member_id"
        }
    ]
    
    payload = {"reason": "Out of jurisdiction"}
    dummy_image = ("evidence.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"dummy pixels")
    
    response = client.post(
        "/api/ward/issues/11111111-2222-3333-4444-555555555555/reject",
        data=payload,
        files={"evidence": dummy_image},
        headers=headers
    )
    
    assert response.status_code == 403
    assert "Not authorized to reject" in response.json()["detail"]

def test_reject_issue_already_processed(client, mock_db):
    token = create_access_token({"sub": "ward_member_id", "role": "ward_member"})
    headers = {"Authorization": f"Bearer {token}"}
    
    mock_db.fetchone.side_effect = [
        # User Profile
        {
            "id": "ward_member_id",
            "username": "ward_member_test",
            "role": "ward_member",
            "full_name": "Ward Member User",
            "contact": "9876543210",
            "is_approved": True,
            "department_id": None,
            "department_name": None,
            "ward_id": 1,
            "ward_name": "Ward 1"
        },
        # Issue Verification: already 'resolved'
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "status": "resolved",
            "ward_id": 1,
            "ward_member_id": "ward_member_id"
        }
    ]
    
    payload = {"reason": "Already resolved, cannot reject."}
    dummy_image = ("evidence.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"dummy pixels")
    
    response = client.post(
        "/api/ward/issues/11111111-2222-3333-4444-555555555555/reject",
        data=payload,
        files={"evidence": dummy_image},
        headers=headers
    )
    
    assert response.status_code == 400
    assert "Only pending issues can be rejected" in response.json()["detail"]
