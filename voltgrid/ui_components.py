import streamlit as st
import textwrap

def render_top_bar(title, breadcrumb):
    st.markdown(f"""
    <div class="top-bar">
        <div class="top-bar-breadcrumb">{breadcrumb} / {title}</div>
        <div class="top-bar-badges">
            <span class="vg-badge badge-success">Data: LIVE</span>
            <span class="vg-badge badge-ai">AI: ONLINE</span>
    <span style="font-size: 1.2rem;">👤</span>
    </div>
    </div>
    """.replace('\n', ''), unsafe_allow_html=True)

def render_status_strip(meta):
    dc = meta.get('data_completeness', {}) if meta else {}
    charger_source = meta.get('charger_source', 'N/A') if meta else 'N/A'
    
    roads_status = "REAL" if dc.get('roads') else "MISSING"
    pois_status = "REAL" if dc.get('pois') else "MISSING"
    chargers_status = "CURATED / PUBLIC" if dc.get('chargers') else "UNAVAILABLE"
    
    st.markdown(f"""
    <div class="status-strip">
        <div class="status-item">
            <span class="status-label">Roads</span>
            <span class="status-value {'badge-success' if roads_status=='REAL' else 'badge-danger'}" style="padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">{roads_status}</span>
        </div>
        <div class="status-item">
            <span class="status-label">POIs</span>
            <span class="status-value {'badge-success' if pois_status=='REAL' else 'badge-danger'}" style="padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">{pois_status}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Chargers</span>
            <span class="status-value {'badge-info' if chargers_status!='UNAVAILABLE' else 'badge-danger'}" style="padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">{chargers_status}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Traffic</span>
            <span class="status-value badge-warning" style="padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">PROXY</span>
        </div>
        <div class="status-item">
            <span class="status-label">AI</span>
    <span class="status-value badge-ai" style="padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">ONLINE</span>
    </div>
    </div>
    """.replace('\n', ''), unsafe_allow_html=True)

def render_empty_state(title, description, icon="⚠️"):
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-title">{title}</div>
    <div class="empty-state-desc">{description}</div>
    </div>
    """.replace('\n', ''), unsafe_allow_html=True)

def render_ai_card(ai_outlook):
    outlook_colors = {"VERY HIGH": "#059669", "HIGH": "#DC2626", "MODERATE": "#D97706", "LOW": "#6B7280"}
    badge_bg = outlook_colors.get(ai_outlook['demand_outlook'], "#DC2626")
    drivers_html = "".join([f"<li style='margin-bottom:6px;'>{d}</li>" for d in ai_outlook.get('drivers', [])])
    
    st.markdown(f"""
<div class="ai-card">
<div class="ai-header">
<div class="ai-title">⚡ VoltGrid AI: Demand Outlook</div>
<span style="background:{badge_bg}; color:#FFF; font-size:0.75rem; font-weight:800; padding:4px 12px; border-radius:6px;">
{ai_outlook['demand_outlook']}
</span>
</div>
<div style="font-size:0.85rem; color:#374151; margin-bottom: 16px;">
<div style="font-weight:700; color:#111827; margin-bottom:8px;">Why this zone stands out</div>
<ul style="margin:0; padding-left:20px; color:#4B5563;">{drivers_html}</ul>
</div>
<div style="font-size:0.75rem; color:#6B7280; border-top:1px solid #E5E7EB; padding-top:12px;">
<b>Limitations:</b> {ai_outlook.get('limitation_note', '')}<br/>
<i>Engine: {ai_outlook.get('mode', '')} | Data Strength: {ai_outlook.get('evidence_strength', '')}</i>
</div>
</div>
""".replace('\n', ''), unsafe_allow_html=True)

def render_candidate_comparison(candidates):
    if not candidates:
        return
    
    # We take top 3 candidates for comparison
    top_cands = candidates[:3]
    
    html = """
    <div style="margin-top: 32px;">
        <div class="section-header">Candidate Comparison</div>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Metric</th>
    """
    for i, c in enumerate(top_cands):
        badge = "⭐ #1" if c['rank'] == 1 else f"#{c['rank']}"
        html += f"<th>Candidate {badge}</th>"
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    metrics = [
        ("Recommendation Score", lambda c: f"{c['Recommendation_Score']:.1f} / 100"),
        ("Demand Potential", lambda c: f"{c['Demand']:.1f}"),
        ("Coverage Gap", lambda c: f"{c['Coverage']:.1f}"),
        ("Preliminary Feasibility", lambda c: f"{c['Feasibility']:.1f}"),
        ("Nearest Charger", lambda c: f"{c.get('nearest_charger_km', 0):.1f} km"),
        ("Commercial POIs", lambda c: f"{c.get('commercial_poi_count', 0)}"),
        ("Dwell POIs", lambda c: f"{c.get('dwell_poi_count', 0)}"),
        ("Parking Opportunities", lambda c: f"{c.get('parking_poi_count', 0)}")
    ]
    
    for label, formatter in metrics:
        html += f"<tr><td>{label}</td>"
        for c in top_cands:
            val = formatter(c)
            # Make the best value bold for scores (this is purely visual logic, not modifying backend data)
            html += f"<td>{val}</td>"
        html += "</tr>"
        
    html += """
            </tbody>
        </table>
    </div>
    """
    
    st.markdown(html.replace('\n', ''), unsafe_allow_html=True)

def render_deployment_readiness():
    st.markdown("""
    <div class="vg-card" style="margin-top: 20px;">
        <div style="font-weight: 800; font-size: 1rem; color: #111827; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            📋 Deployment Readiness
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: #059669; text-transform: uppercase; margin-bottom: 8px;">Completed (Spatial)</div>
                <div style="font-size: 0.85rem; color: #374151; line-height: 1.6;">
                    ✓ Demand screening<br/>
                    ✓ Coverage screening<br/>
                    ✓ Road accessibility screening
                </div>
            </div>
            <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: #D97706; text-transform: uppercase; margin-bottom: 8px;">Requires Field Verification</div>
                <div style="font-size: 0.85rem; color: #374151; line-height: 1.6;">
                    <span style="color:#D97706;">!</span> Grid capacity<br/>
                    <span style="color:#D97706;">!</span> Land availability<br/>
                    <span style="color:#D97706;">!</span> Parking ownership<br/>
                    <span style="color:#D97706;">!</span> Electrical connection<br/>
    <span style="color:#D97706;">!</span> Zoning / approvals
    </div>
    </div>
    </div>
    </div>
    """.replace('\n', ''), unsafe_allow_html=True)
