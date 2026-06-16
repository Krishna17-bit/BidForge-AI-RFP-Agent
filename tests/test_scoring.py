from __future__ import annotations

import numpy as np

def test_fit_score_calculation():
    # Simulate slider fit variables
    domain = 90
    tech = 80
    budget = 70
    timeline = 80
    compliance = 95
    resource = 80
    strategic = 85
    comp_risk = 30 # Risk is inverted
    
    score = int(np.mean([domain, tech, budget, timeline, compliance, resource, strategic, (100 - comp_risk)]))
    assert score == 81
    
    # Check decision outcomes
    if score >= 75:
        decision = "Strong Bid"
    elif score >= 50:
        decision = "Bid with caution"
    else:
        decision = "No-Bid"
        
    assert decision == "Strong Bid"
