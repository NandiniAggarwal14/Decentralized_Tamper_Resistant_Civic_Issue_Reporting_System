import logging
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File

from backend.app.database import get_connection
from backend.app.auth import RoleChecker, UserResponse
from backend.app.models import ProfileUpdateRequest, PriorityRequest, RedirectRequest
from backend.app.helpers import anchor_ward_profile, _save_media_file, _serialize_issue, _assign_dynamic_priorities
import backend.app.ipfs_service as ipfs_service
import backend.app.blockchain_service as blockchain_service

router = APIRouter(prefix="/api/ward", tags=["ward"])

@router.get("/profile")
async def get_ward_profile(
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT w.name as ward_name, w.ipfs_cid, w.blockchain_hash, w.id as ward_id,
                           u.full_name, u.contact, u.username
                    FROM users u
                    JOIN wards w ON u.id = w.ward_member_id
                    WHERE u.id = %s
                    """,
                    (current_user.id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Ward profile not found")
        
        onchain_hash = blockchain_service.get_personnel_hash(current_user.id)
        db_hash = row["blockchain_hash"]
        is_verified = bool(db_hash and onchain_hash and db_hash.lower() == onchain_hash.lower())

        return {
            "success": True,
            "data": {
                "username": row["username"],
                "full_name": row["full_name"],
                "contact": row["contact"],
                "ward_id": row["ward_id"],
                "ward_name": row["ward_name"],
                "ipfs_cid": row["ipfs_cid"],
                "blockchain_hash": row["blockchain_hash"],
                "onchain_hash": onchain_hash,
                "is_verified": is_verified
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to fetch ward profile")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/profile")
async def update_ward_profile(
    req: ProfileUpdateRequest,
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET full_name = %s, contact = %s WHERE id = %s",
                    (req.full_name, req.contact, current_user.id)
                )
                cursor.execute("SELECT id FROM wards WHERE ward_member_id = %s", (current_user.id,))
                ward_row = cursor.fetchone()
                if not ward_row:
                    raise HTTPException(status_code=404, detail="Ward not found for this user")
                ward_id = ward_row["id"]
            conn.commit()

        await anchor_ward_profile(current_user.id, current_user.username, req.full_name, req.contact or "", ward_id)
        return {"success": True, "message": "Profile updated and anchored to blockchain successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to update ward profile")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats")
async def get_ward_stats(
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM wards WHERE ward_member_id = %s", (current_user.id,))
                ward_row = cursor.fetchone()
                if not ward_row:
                    raise HTTPException(status_code=404, detail="Ward not found for this member")
                ward_id = ward_row["id"]

                cursor.execute("SELECT COUNT(*) as count FROM issues WHERE ward_id = %s", (ward_id,))
                total_issues = cursor.fetchone()["count"]

                cursor.execute(
                    "SELECT status, COUNT(*) as count FROM issues WHERE ward_id = %s GROUP BY status",
                    (ward_id,)
                )
                status_rows = cursor.fetchall()
                status_breakdown = {r["status"]: r["count"] for r in status_rows}

                cursor.execute(
                    "SELECT priority, COUNT(*) as count FROM issues WHERE ward_id = %s GROUP BY priority",
                    (ward_id,)
                )
                priority_rows = cursor.fetchall()
                priority_breakdown = {r["priority"]: r["count"] for r in priority_rows}

                cursor.execute(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (h.created_at - i.created_at))) / 3600.0 as avg_time
                    FROM issues i
                    JOIN issue_status_history h ON i.id = h.issue_id
                    WHERE i.ward_id = %s AND h.new_status = 'resolved'
                    """,
                    (ward_id,)
                )
                avg_time_row = cursor.fetchone()
                avg_res_time = round(avg_time_row["avg_time"], 1) if avg_time_row and avg_time_row["avg_time"] is not None else 0.0

                cursor.execute(
                    """
                    SELECT category, COUNT(*) as count 
                    FROM issues 
                    WHERE ward_id = %s 
                    GROUP BY category 
                    ORDER BY count DESC 
                    LIMIT 5
                    """,
                    (ward_id,)
                )
                cat_rows = cursor.fetchall()
                top_categories = {r["category"]: r["count"] for r in cat_rows}

        return {
            "success": True,
            "data": {
                "total_issues": total_issues,
                "status_breakdown": status_breakdown,
                "priority_breakdown": priority_breakdown,
                "avg_res_time_hours": avg_res_time,
                "top_categories": top_categories
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to fetch ward statistics")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/issues")
async def get_ward_issues(current_user: UserResponse = Depends(RoleChecker(["ward_member"]))) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT i.id, i.title, i.description, i.category, i.area, i.address,
                           i.latitude, i.longitude, i.reporter_name, i.contact,
                           i.image_url, i.status, i.created_at, i.hash,
                           i.priority, i.ward_id, w.name as ward_name,
                           i.department_id, d.name as department_name,
                           i.ipfs_cid, i.media_urls, i.completion_proof_ipfs_cid, i.completion_hash,
                           i.completion_proof_url,
                           i.rejection_reason, i.rejection_proof_url, i.rejection_proof_ipfs_cid,
                           i.rejected_by, rej.full_name as rejected_by_name, rej.contact as rejected_by_contact,
                           i.upvote_count, i.downvote_count
                    FROM issues i
                    JOIN wards w ON i.ward_id = w.id
                    LEFT JOIN departments d ON i.department_id = d.id
                    LEFT JOIN users rej ON i.rejected_by = rej.id
                    WHERE w.ward_member_id = %s
                    ORDER BY i.upvote_count DESC, i.created_at DESC
                    """,
                    (current_user.id,)
                )
                rows = cursor.fetchall()

        items = [_serialize_issue(row) for row in rows]
        items = _assign_dynamic_priorities(items)
        return {"success": True, "count": len(items), "data": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ward issues: {exc}")

@router.patch("/issues/{issue_id}/priority")
async def update_issue_priority(
    issue_id: str,
    req: PriorityRequest,
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    raise HTTPException(status_code=403, detail="Priority updates are handled automatically by user votes.")

@router.post("/issues/{issue_id}/redirect")
async def redirect_issue(
    issue_id: str,
    req: RedirectRequest,
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT i.id FROM issues i
                    JOIN wards w ON i.ward_id = w.id
                    WHERE i.id = %s AND w.ward_member_id = %s
                    """,
                    (issue_id, current_user.id)
                )
                if not cursor.fetchone():
                    raise HTTPException(status_code=403, detail="Not authorized to route issues in another ward")

                cursor.execute("SELECT id FROM departments WHERE id = %s", (req.department_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Department not found")

                cursor.execute(
                    "UPDATE issues SET department_id = %s WHERE id = %s",
                    (req.department_id, issue_id)
                )

                # Get department name
                cursor.execute("SELECT name FROM departments WHERE id = %s", (req.department_id,))
                dept_name = cursor.fetchone()["name"]

                # Log redirection event to status history
                cursor.execute(
                    """
                    INSERT INTO issue_status_history (id, issue_id, old_status, new_status, changed_by, comments)
                    VALUES (%s, %s, 'pending', 'pending', %s, %s)
                    """,
                    (str(uuid.uuid4()), issue_id, current_user.id, f"Routed to {dept_name}")
                )
            conn.commit()
        return {"success": True, "message": "Issue redirected to new department"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to redirect issue: {exc}")

@router.post("/issues/{issue_id}/reject")
async def reject_issue(
    issue_id: str,
    reason: str = Form(...),
    evidence: UploadFile = File(...),
    current_user: UserResponse = Depends(RoleChecker(["ward_member"]))
) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Fetch issue details to verify access
                cursor.execute(
                    """
                    SELECT i.id, i.status, i.ward_id, w.ward_member_id
                    FROM issues i
                    JOIN wards w ON i.ward_id = w.id
                    WHERE i.id = %s
                    """,
                    (issue_id,)
                )
                issue = cursor.fetchone()
                if not issue:
                    raise HTTPException(status_code=404, detail="Issue not found")
                
                if issue["ward_member_id"] != current_user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to reject issues in another ward")
                
                if issue["status"] != "pending":
                    raise HTTPException(status_code=400, detail="Only pending issues can be rejected")
                
                old_status = issue["status"]

        # 2. Save evidence file to local uploads and IPFS
        evidence_info = await _save_media_file(evidence, expected_type="proof")
        if not evidence_info:
            raise HTTPException(status_code=400, detail="Failed to save rejection evidence file")
            
        evidence_cid = evidence_info["cid"]
        evidence_url = evidence_info["url"]

        # 3. Compile rejection metadata and save to IPFS
        rejection_data = {
            "issue_id": issue_id,
            "rejected_by": str(current_user.id),
            "rejected_by_name": current_user.full_name,
            "rejected_by_contact": current_user.contact or "",
            "reason": reason,
            "evidence": evidence_info,
            "rejected_at": datetime.now(timezone.utc).isoformat()
        }
        rejection_ipfs_cid = ipfs_service.store_json(rejection_data, type_label="rejection_proof")
        rejection_hash = hashlib.sha256(
            json.dumps(rejection_data, sort_keys=True).encode()
        ).hexdigest()

        # 4. Compile status history payload
        history_id = str(uuid.uuid4())
        status_payload = {
            "history_id": history_id,
            "issue_id": issue_id,
            "old_status": old_status,
            "new_status": "rejected",
            "changed_by": str(current_user.id),
            "changed_by_name": current_user.full_name,
            "comments": reason,
            "proof_url": evidence_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        status_ipfs_cid = ipfs_service.store_json(status_payload, type_label="status_history")
        status_payload_str = json.dumps(status_payload, sort_keys=True)
        status_blockchain_hash = hashlib.sha256(status_payload_str.encode()).hexdigest()

        # 5. Anchor history to Sepolia blockchain
        status_tx_hash = blockchain_service.store_issue_hash(history_id, status_blockchain_hash)

        # 6. Update Database
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 6a. Delete existing votes for this issue
                cursor.execute(
                    "DELETE FROM issue_votes WHERE issue_id = %s",
                    (issue_id,)
                )

                # 6b. Update issue columns
                cursor.execute(
                    """
                    UPDATE issues
                    SET status = 'rejected',
                        rejection_reason = %s,
                        rejection_proof_url = %s,
                        rejection_proof_ipfs_cid = %s,
                        rejected_by = %s,
                        upvote_count = 0,
                        downvote_count = 0
                    WHERE id = %s
                    """,
                    (reason, evidence_url, evidence_cid, current_user.id, issue_id)
                )

                # 6c. Insert history record
                cursor.execute(
                    """
                    INSERT INTO issue_status_history (id, issue_id, old_status, new_status, changed_by, comments, proof_url, ipfs_cid, blockchain_hash)
                    VALUES (%s, %s, %s, 'rejected', %s, %s, %s, %s, %s)
                    """,
                    (history_id, issue_id, old_status, current_user.id, reason, evidence_url, status_ipfs_cid, status_blockchain_hash)
                )
            conn.commit()

        return {
            "success": True,
            "message": "Issue rejected successfully and anchored on blockchain",
            "tx_hash": status_tx_hash,
            "ipfs_cid": status_ipfs_cid,
            "blockchain_hash": status_blockchain_hash
        }
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Failed to reject issue")
        raise HTTPException(status_code=500, detail=f"Failed to reject issue: {exc}")

