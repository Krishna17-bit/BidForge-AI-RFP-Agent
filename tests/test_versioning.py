from __future__ import annotations

import os
from src.database import init_db, execute_query, execute_read

def test_proposal_version_history():
    init_db()
    
    opp_id = "OPP_VER_TEST"
    sec_id = "SEC_VER_TEST"
    
    # Clean up
    execute_query("DELETE FROM opportunities WHERE id = ?", (opp_id,))
    execute_query("DELETE FROM proposal_sections WHERE id = ?", (sec_id,))
    execute_query("DELETE FROM proposal_versions WHERE opportunity_id = ?", (opp_id,))
    
    # 1. Insert Opportunity
    execute_query("INSERT INTO opportunities (id, title, buyer, status) VALUES (?, ?, ?, ?)", (opp_id, "Version Test Bid", "Verifier", "Draft"))
    
    # 2. Insert Proposal Section
    execute_query("""
    INSERT INTO proposal_sections (id, opportunity_id, section_name, draft_content, completion_status, version)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (sec_id, opp_id, "Executive Summary", "This is the initial draft version.", "Draft", 1))
    
    # 3. Create historical versions
    execute_query("""
    INSERT INTO proposal_versions (id, opportunity_id, section_id, version_number, draft_content, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, ("V1", opp_id, sec_id, 1, "This is the initial draft version.", "2026-06-16T12:00:00"))
    
    execute_query("""
    INSERT INTO proposal_versions (id, opportunity_id, section_id, version_number, draft_content, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, ("V2", opp_id, sec_id, 2, "This is the updated draft version.", "2026-06-16T12:30:00"))
    
    # 4. Verify we retrieve both versions
    vers = execute_read("SELECT * FROM proposal_versions WHERE section_id = ? ORDER BY version_number ASC", (sec_id,))
    assert len(vers) == 2
    assert vers[0]["draft_content"] == "This is the initial draft version."
    assert vers[1]["draft_content"] == "This is the updated draft version."
    
    # 5. Restore version 1
    execute_query("UPDATE proposal_sections SET draft_content = ?, version = 3 WHERE id = ?", (vers[0]["draft_content"], sec_id))
    
    active_sec = execute_read("SELECT * FROM proposal_sections WHERE id = ?", (sec_id,))[0]
    assert active_sec["draft_content"] == "This is the initial draft version."
    assert active_sec["version"] == 3
    
    # Cleanup
    execute_query("DELETE FROM opportunities WHERE id = ?", (opp_id,))
    execute_query("DELETE FROM proposal_sections WHERE id = ?", (sec_id,))
    execute_query("DELETE FROM proposal_versions WHERE opportunity_id = ?", (opp_id,))
