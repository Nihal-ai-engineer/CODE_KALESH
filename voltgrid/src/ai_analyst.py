"""
VoltGrid — AI Site Analyst
Generates structured executive site appraisals for candidate zones.
Uses local Gemma via LM Studio when available, deterministic fallback otherwise.

The AI receives ONLY structured spatial evidence and is PROHIBITED from inventing:
- Grid capacity
- Land prices / revenue
- Charger utilization
- Future traffic predictions
- Transformer capacity
- Zoning status
"""
import json
import requests
import hashlib
import os

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 9.0

# Health cache
_lm_studio_available = None

def check_lm_studio_health():
    global _lm_studio_available
    if _lm_studio_available is not None:
        return _lm_studio_available
    try:
        resp = requests.get("http://localhost:1234/v1/models", timeout=2.0)
        _lm_studio_available = (resp.status_code == 200)
    except Exception:
        _lm_studio_available = False
    return _lm_studio_available


def generate_offline_appraisal(candidate_data, city_name="City"):
    """
    Deterministic appraisal when LM Studio is offline.
    Follows the exact 5-point structure using only available data.
    """
    loc_name = candidate_data.get('locality_name', 'Candidate Zone')
    score = candidate_data.get('Recommendation_Score', 0)
    demand = candidate_data.get('Demand', 0)
    gap = candidate_data.get('Coverage', 0)
    feas = candidate_data.get('Feasibility', 0)
    dist = candidate_data.get('nearest_charger_km', 2.0)
    comp = candidate_data.get('nearest_charger_name', 'Known Station')
    comm_pois = candidate_data.get('commercial_poi_count', 0)
    dwell_pois = candidate_data.get('dwell_poi_count', 0)
    parking = candidate_data.get('parking_poi_count', 0)
    
    summary = (
        f"**1. Why this zone ranked highly:** {loc_name} in {city_name} scored {score:.1f}/100 "
        f"based on convergence of road hierarchy activity, local commercial density, and charging coverage gap.\n\n"
        f"**2. Primary strengths:** Demand index of {demand:.1f}/100 with {comm_pois} commercial POIs, "
        f"{dwell_pois} dwell venues. Coverage gap of {gap:.1f}/100 with nearest station {dist:.1f} km away ({comp}).\n\n"
        f"**3. Key limitation:** {'Parking availability is limited (' + str(parking) + ' known parking nodes)' if parking < 3 else 'Moderate parking availability (' + str(parking) + ' parking nodes)'}. "
        f"Physical site acquisition must be confirmed through field survey.\n\n"
        f"**4. Unknown factors:** Real-time electrical grid headroom, transformer capacity, "
        f"land lease rates, live peak traffic flow, and historical charger utilization data.\n\n"
        f"**5. Next verification step:** Conduct on-ground utility assessment with the local "
        f"electricity distribution company to verify transformer connection capacity and survey physical property boundaries."
    )
    return {
        "text": summary,
        "mode": "Deterministic Site Summary (Offline)",
        "model": "Rules Engine"
    }


def generate_site_appraisal(candidate_data, city_name="City"):
    """
    Generate structured executive site appraisal.
    Tries LM Studio first (if healthy), falls back to deterministic engine.
    Uses file-based caching to prevent demo delays.
    """
    # 1. Generate cache key based on evidence
    evidence = {
        "city": city_name,
        "h3_index": candidate_data.get('h3_index', 'Unknown'),
        "locality_name": candidate_data.get('locality_name', 'Candidate Zone'),
        "recommendation_score": round(float(candidate_data.get('Recommendation_Score', 0)), 1),
        "demand_potential": round(float(candidate_data.get('Demand', 0)), 1),
        "coverage_gap": round(float(candidate_data.get('Coverage', 0)), 1),
        "preliminary_feasibility": round(float(candidate_data.get('Feasibility', 0)), 1),
        "road_activity_score": round(float(candidate_data.get('norm_road_activity', 0)), 1),
        "commercial_poi_count": int(candidate_data.get('commercial_poi_count', 0)),
        "dwell_poi_count": int(candidate_data.get('dwell_poi_count', 0)),
        "parking_poi_count": int(candidate_data.get('parking_poi_count', 0)),
        "nearest_charger_km": round(float(candidate_data.get('nearest_charger_km', 0)), 2),
        "nearest_charger_name": candidate_data.get('nearest_charger_name', 'Reference Station'),
        "nearby_charger_count": int(candidate_data.get('nearby_charger_count', 0)),
        "known_limitations": [
            "No live traffic volume telemetry",
            "No electrical grid capacity data",
            "No land-cost or leasehold data",
            "No charger-utilization data"
        ]
    }
    
    evidence_str = json.dumps(evidence, sort_keys=True)
    cache_hash = hashlib.md5(evidence_str.encode()).hexdigest()
    
    from src.city_resolver import slugify
    city_slug = slugify(city_name)
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', city_slug, '.ai_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"appraisal_{cache_hash}.json")
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass

    if not check_lm_studio_health():
        result = generate_offline_appraisal(candidate_data, city_name)
        with open(cache_file, 'w') as f:
            json.dump(result, f)
        return result
    evidence = {
        "city": city_name,
        "h3_index": candidate_data.get('h3_index', 'Unknown'),
        "locality_name": candidate_data.get('locality_name', 'Candidate Zone'),
        "recommendation_score": round(float(candidate_data.get('Recommendation_Score', 0)), 1),
        "demand_potential": round(float(candidate_data.get('Demand', 0)), 1),
        "coverage_gap": round(float(candidate_data.get('Coverage', 0)), 1),
        "preliminary_feasibility": round(float(candidate_data.get('Feasibility', 0)), 1),
        "road_activity_score": round(float(candidate_data.get('norm_road_activity', 0)), 1),
        "commercial_poi_count": int(candidate_data.get('commercial_poi_count', 0)),
        "dwell_poi_count": int(candidate_data.get('dwell_poi_count', 0)),
        "parking_poi_count": int(candidate_data.get('parking_poi_count', 0)),
        "nearest_charger_km": round(float(candidate_data.get('nearest_charger_km', 0)), 2),
        "nearest_charger_name": candidate_data.get('nearest_charger_name', 'Reference Station'),
        "nearby_charger_count": int(candidate_data.get('nearby_charger_count', 0)),
        "known_limitations": [
            "No live traffic volume telemetry",
            "No electrical grid capacity data",
            "No land-cost or leasehold data",
            "No charger-utilization data"
        ]
    }
    
    system_prompt = (
        "You are an EV infrastructure site-planning analyst.\n\n"
        "Use ONLY the supplied structured evidence.\n"
        "Do not invent any information.\n\n"
        "Explain in concise, professional business English:\n"
        "1. Why the zone ranked highly.\n"
        "2. Its strongest demand/coverage signals.\n"
        "3. Its most important limitation.\n"
        "4. What information remains unknown.\n"
        "5. The next real-world verification step.\n\n"
        "CRITICAL RULE: Never invent transformer capacity, land price, land availability, "
        "traffic counts, charging utilization, revenue, ROI, electrical approval, "
        "or zoning approval.\n\n"
        "Maximum 130 words."
    )
    
    user_prompt = (
        f"Conduct an executive due-diligence appraisal for this candidate zone in {city_name}:\n\n"
        f"{json.dumps(evidence, indent=2)}"
    )
    
    try:
        payload = {
            "model": "google/gemma-3-12b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 280,
            "stream": False
        }
        resp = requests.post(
            LM_STUDIO_URL, json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            result = {
                "text": content,
                "mode": "AI Site Analyst — Gemma-3 (Local)",
                "model": "google/gemma-3-12b"
            }
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            return result
    except Exception:
        pass
    
    result = generate_offline_appraisal(candidate_data, city_name)
    with open(cache_file, 'w') as f:
        json.dump(result, f)
    return result
