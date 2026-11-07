"""
VoltGrid — AI Demand Outlook
Qualitative demand assessment using structured spatial evidence.
Uses local Gemma via LM Studio when available, deterministic fallback otherwise.

═══════════════════════════════════════════════════════════
HOW AI DEMAND OUTLOOK WORKS
═══════════════════════════════════════════════════════════

1. Collect structured spatial evidence for the candidate zone:
   - road_activity_score, commercial_poi_count, dwell_poi_count
   - coverage_gap, nearest_charger_km, nearby_charger_count

2. If LM Studio is running:
   → Send evidence as JSON to local Gemma-3 model
   → Model classifies demand outlook: LOW / MODERATE / HIGH / VERY HIGH
   → Model provides 2-3 spatial driver bullet points
   → System prompt PROHIBITS invention of data

3. If LM Studio is offline:
   → Deterministic rules engine classifies based on demand_potential score
   → Transparent thresholds: ≥75 = VERY HIGH, ≥55 = HIGH, ≥35 = MODERATE, else LOW

4. Evidence Strength is computed from data completeness:
   → Strong: road data + ≥5 POIs + charger distance available
   → Moderate: road data + charger distance available
   → Limited: missing one or more key inputs
═══════════════════════════════════════════════════════════
"""
import json
import requests
import hashlib
import os

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 8.0
from src.ai_analyst import check_lm_studio_health


def evaluate_evidence_strength(evidence):
    """
    Evaluates evidence strength based on data completeness.
    Returns: 'Strong', 'Moderate', or 'Limited'
    """
    has_road = evidence.get('road_activity_score', 0) > 0
    poi_count = evidence.get('commercial_poi_count', 0) + evidence.get('dwell_poi_count', 0)
    has_charger_dist = evidence.get('nearest_charger_km') is not None and evidence.get('nearest_charger_km', 99) < 90
    
    if has_road and poi_count >= 5 and has_charger_dist:
        return "Strong"
    elif has_road and has_charger_dist:
        return "Moderate"
    else:
        return "Limited"


def get_deterministic_demand_outlook(evidence):
    """
    Transparent deterministic fallback when LM Studio is unavailable.
    Thresholds based on demand_potential score.
    """
    demand_pot = evidence.get('demand_potential', 50.0)
    cov_gap = evidence.get('coverage_gap', 50.0)
    comm_pois = evidence.get('commercial_poi_count', 0)
    dwell_pois = evidence.get('dwell_poi_count', 0)
    road_act = evidence.get('road_activity_score', 0)
    near_km = evidence.get('nearest_charger_km', 2.0)
    
    if demand_pot >= 75:
        outlook = "VERY HIGH"
    elif demand_pot >= 55:
        outlook = "HIGH"
    elif demand_pot >= 35:
        outlook = "MODERATE"
    else:
        outlook = "LOW"
    
    drivers = []
    if road_act > 60:
        drivers.append(f"Significant arterial road hierarchy ({road_act:.0f}/100 activity proxy)")
    if comm_pois > 0 or dwell_pois > 0:
        drivers.append(f"{comm_pois} commercial POIs and {dwell_pois} dwell venues within cell")
    if cov_gap >= 70:
        drivers.append(f"Severe charging deficit — nearest station {near_km:.1f} km away")
    elif cov_gap >= 50:
        drivers.append(f"Moderate distance ({near_km:.1f} km) to nearest reference station")
    
    if not drivers:
        drivers.append("Baseline urban road hierarchy in residential corridor")
    
    return {
        "demand_outlook": outlook,
        "evidence_strength": evaluate_evidence_strength(evidence),
        "mode": "Deterministic Rules Engine (Offline)",
        "drivers": drivers,
        "limitation_note": "Based on spatial proxies. Live traffic and historical charger utilization are not available."
    }


def get_ai_demand_outlook(candidate_dict, city_name="City"):
    """
    AI Demand Outlook: qualitative assessment via local Gemma or deterministic fallback.
    Sends ONLY structured JSON evidence — never invents data.
    """
    evidence = {
        "city": city_name,
        "locality": candidate_dict.get('locality_name', 'Candidate Zone'),
        "h3_index": candidate_dict.get('h3_index', ''),
        "recommendation_score": round(float(candidate_dict.get('Recommendation_Score', 0)), 1),
        "demand_potential": round(float(candidate_dict.get('Demand', 0)), 1),
        "coverage_gap": round(float(candidate_dict.get('Coverage', 0)), 1),
        "preliminary_feasibility": round(float(candidate_dict.get('Feasibility', 0)), 1),
        "road_activity_score": round(float(candidate_dict.get('norm_road_activity', 0)), 1),
        "commercial_poi_count": int(candidate_dict.get('commercial_poi_count', 0)),
        "dwell_poi_count": int(candidate_dict.get('dwell_poi_count', 0)),
        "parking_poi_count": int(candidate_dict.get('parking_poi_count', 0)),
        "nearest_charger_km": round(float(candidate_dict.get('nearest_charger_km', 0)), 2),
        "nearby_charger_count": int(candidate_dict.get('nearby_charger_count', 0)),
        "known_limitations": [
            "No live traffic telemetry",
            "No electrical grid capacity data",
            "No land lease cost data",
            "No charger session utilization logs"
        ]
    }
    
    strength = evaluate_evidence_strength(evidence)
    
    # 1. Generate cache key based on evidence
    evidence = {
        "city": city_name,
        "locality": candidate_dict.get('locality_name', 'Candidate Zone'),
        "h3_index": candidate_dict.get('h3_index', ''),
        "recommendation_score": round(float(candidate_dict.get('Recommendation_Score', 0)), 1),
        "demand_potential": round(float(candidate_dict.get('Demand', 0)), 1),
        "coverage_gap": round(float(candidate_dict.get('Coverage', 0)), 1),
        "preliminary_feasibility": round(float(candidate_dict.get('Feasibility', 0)), 1),
        "road_activity_score": round(float(candidate_dict.get('norm_road_activity', 0)), 1),
        "commercial_poi_count": int(candidate_dict.get('commercial_poi_count', 0)),
        "dwell_poi_count": int(candidate_dict.get('dwell_poi_count', 0)),
        "parking_poi_count": int(candidate_dict.get('parking_poi_count', 0)),
        "nearest_charger_km": round(float(candidate_dict.get('nearest_charger_km', 0)), 2),
        "nearby_charger_count": int(candidate_dict.get('nearby_charger_count', 0)),
        "known_limitations": [
            "No live traffic telemetry",
            "No electrical grid capacity data",
            "No land lease cost data",
            "No charger session utilization logs"
        ]
    }
    
    evidence_str = json.dumps(evidence, sort_keys=True)
    cache_hash = hashlib.md5(evidence_str.encode()).hexdigest()
    
    from src.city_resolver import slugify
    city_slug = slugify(city_name)
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', city_slug, '.ai_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"demand_{cache_hash}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
            
    if not check_lm_studio_health():
        result = get_deterministic_demand_outlook(evidence)
        with open(cache_file, 'w') as f:
            json.dump(result, f)
        return result
    
    system_prompt = (
        f"You are an expert EV Infrastructure Demand Analyst evaluating spatial evidence for {city_name}, India.\n"
        "Use ONLY the supplied JSON evidence. Do NOT invent data, percentages, or financial claims.\n"
        "Classify the DEMAND OUTLOOK into exactly one of: LOW, MODERATE, HIGH, VERY HIGH.\n"
        "Provide 2-3 concise bullet points identifying the primary spatial drivers.\n"
        "Format strictly as:\n"
        "DEMAND OUTLOOK: [LOW/MODERATE/HIGH/VERY HIGH]\n"
        "• Driver 1\n"
        "• Driver 2\n"
        "• Driver 3"
    )
    
    user_prompt = f"Evaluate this spatial evidence:\n{json.dumps(evidence, indent=2)}"
    
    try:
        payload = {
            "model": "google/gemma-3-12b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 160,
            "stream": False
        }
        resp = requests.post(LM_STUDIO_URL, json=payload,
                           headers={"Content-Type": "application/json"},
                           timeout=REQUEST_TIMEOUT_SECONDS)
        
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            outlook = "HIGH"
            for candidate in ["VERY HIGH", "HIGH", "MODERATE", "LOW"]:
                if candidate in content.upper():
                    outlook = candidate
                    break
            
            lines = [line.strip() for line in content.split('\n')
                    if line.strip().startswith('•') or line.strip().startswith('-')]
            if not lines:
                lines = [content[:200]]
            
            result = {
                "demand_outlook": outlook,
                "evidence_strength": strength,
                "mode": "Gemma-3 AI (Local LM Studio)",
                "drivers": [l.lstrip('•- ').strip() for l in lines[:3]],
                "limitation_note": "AI qualitative assessment based on spatial evidence. Live traffic and grid telemetry are not available."
            }
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            return result
    except Exception:
        pass
    
    result = get_deterministic_demand_outlook(evidence)
    with open(cache_file, 'w') as f:
        json.dump(result, f)
    return result
