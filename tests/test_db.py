from __future__ import annotations

import os
from pathlib import Path
from src.database import init_db, seed_demo_data, execute_read, execute_query, DB_PATH

def test_db_lifecycle():
    # Verify we can initialize and read from DB
    init_db()
    assert DB_PATH.exists()
    
    # Test inserting temporary opportunity
    test_id = "OPP_TEST_DB"
    execute_query("DELETE FROM opportunities WHERE id = ?", (test_id,))
    
    execute_query("""
    INSERT INTO opportunities (id, title, buyer, status, fit_score)
    VALUES (?, ?, ?, ?, ?)
    """, (test_id, "Test Integration Opportunity", "Acme Test Corp", "New", 80))
    
    rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (test_id,))
    assert len(rows) == 1
    assert rows[0]["title"] == "Test Integration Opportunity"
    assert rows[0]["fit_score"] == 80
    
    # Cleanup
    execute_query("DELETE FROM opportunities WHERE id = ?", (test_id,))
    rows_after = execute_read("SELECT * FROM opportunities WHERE id = ?", (test_id,))
    assert len(rows_after) == 0

def test_db_seeding():
    init_db()
    seed_demo_data()
    
    opps = execute_read("SELECT count(*) as count FROM opportunities")
    assert opps[0]["count"] >= 5
    
    kb = execute_read("SELECT count(*) as count FROM knowledge_items")
    assert kb[0]["count"] >= 5
