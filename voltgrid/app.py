"""
VoltGrid — EV Infrastructure Intelligence for India
Main Streamlit Application
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import time
import numpy as np
import textwrap
import os

import src.city_resolver
import src.charger_loader
import src.data_manager
import src.scoring
import src.feature_engine
import src.ai_demand
import src.ai_analyst
import importlib

importlib.reload(src.charger_loader)
importlib.reload(src.feature_engine)
importlib.reload(src.scoring)
importlib.reload(src.data_manager)

from src.city_resolver import (
    load_city_index, find_city_in_index, is_city_cached,
    get_all_cached_cities, load_city_metadata, slugify
)
from src.charger_loader import load_chargers_for_city
from src.data_manager import analyze_city, generate_city_live
from src.scoring import get_scoring_formulas
from src.ai_demand import get_ai_demand_outlook
from src.ai_analyst import generate_site_appraisal

# Import our new UI components and styles
from styles import get_enterprise_css
import ui_components
import importlib
importlib.reload(ui_components)
from ui_components import (
    render_top_bar, render_status_strip, render_empty_state, 
    render_ai_card, render_candidate_comparison, render_deployment_readiness
)

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG 
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="VoltGrid | EV Infrastructure Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Enterprise CSS
st.markdown(get_enterprise_css(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'overview'
if 'selected_city' not in st.session_state:
    st.session_state.selected_city = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'selected_candidate_idx' not in st.session_state:
    st.session_state.selected_candidate_idx = 0

# ══════════════════════════════════════════════════════════════
# APP SHELL: SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sidebar-brand">⚡ VoltGrid</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">EV Infrastructure Intelligence — India</div>', unsafe_allow_html=True)
    
    st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#6B7280; margin-bottom:8px; text-transform:uppercase;'>Platform</div>", unsafe_allow_html=True)
    
    if st.button("🇮🇳 Overview", key="nav_overview", use_container_width=True, type="secondary" if st.session_state.current_page != 'overview' else "primary"):
        st.session_state.current_page = 'overview'
        st.session_state.selected_city = None
        st.session_state.analysis_result = None
        st.rerun()
        
    if st.button("🔬 City Intelligence", key="nav_analysis", use_container_width=True, type="secondary" if st.session_state.current_page != 'analysis' else "primary"):
        st.session_state.current_page = 'analysis' if st.session_state.selected_city else 'overview'
        st.rerun()
        
    st.markdown("<div style='margin-top:20px; font-size:0.75rem; font-weight:700; color:#6B7280; margin-bottom:8px; text-transform:uppercase;'>Knowledge</div>", unsafe_allow_html=True)
    
    if st.button("💼 Business Case", key="nav_business", use_container_width=True, type="secondary" if st.session_state.current_page != 'business' else "primary"):
        st.session_state.current_page = 'business'
        st.rerun()
        
    if st.button("📐 Methodology", key="nav_method", use_container_width=True, type="secondary" if st.session_state.current_page != 'methodology' else "primary"):
        st.session_state.current_page = 'methodology'
        st.rerun()
        
    st.markdown("<div style='margin-top:auto; padding-top:40px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin-bottom:12px;">
        <div style="font-size:0.7rem; font-weight:600; color:#9CA3AF; margin-bottom:4px; text-transform:uppercase;">System Status</div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; margin-bottom:4px;">
            <span>Data API</span><span style="color:#10B981; font-weight:700;">● ONLINE</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem;">
            <span>AI Engine</span><span style="color:#06B6D4; font-weight:700;">● READY</span>
        </div>
    </div>
    <div style="font-size:0.7rem; color:#6B7280; text-align:center;">VoltGrid v2.1.0 • Enterprise</div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════

if st.session_state.current_page == 'overview':
    render_top_bar("Overview", "VoltGrid")
    
    st.markdown(textwrap.dedent("""
    <div style="text-align: center; margin-bottom: 40px; padding: 20px 0;">
        <div style="font-size: 2.2rem; font-weight: 900; color: #111827; letter-spacing: -0.02em;">
            Find where charging infrastructure should go next.
        </div>
        <div style="font-size: 1.1rem; color: #6B7280; margin-top: 8px; max-width: 600px; margin-left: auto; margin-right: auto;">
            Screen the city first. Survey the best zones second. Search any Indian city to analyse EV charging demand potential, coverage gaps, and site feasibility.
        </div>
    </div>
    """), unsafe_allow_html=True)
    
    # ── KPI Cards ──
    cities = load_city_index()
    cached = get_all_cached_cities()
    
    total_chargers_known = 0
    for c in cached:
        meta = load_city_metadata(c['slug'])
        if meta:
            total_chargers_known += meta.get('charger_count', 0)
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Cities Analysed", f"{len(cached)}", help="Markets with offline-ready spatial grids")
    with k2: st.metric("Known Chargers", f"{total_chargers_known:,}", help="Verified stations in analyzed markets")
    with k3: st.metric("Supported Markets", f"{len(cities)}", help="Indian cities mapped in standard index")
    with k4: st.metric("AI Engine", "Online", help="Demand & Site screening active")
    
    st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)
    
    # ── Search Bar ──
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input(
            "Search a city",
            placeholder="Search any Indian city — Chandigarh, Amloh, Khanna, Bengaluru...",
            label_visibility="collapsed",
            key="city_search"
        )
    with search_col2:
        search_clicked = st.button("🔍 Search Market", key="btn_search", use_container_width=True)

    if search_clicked and search_query:
        city_match = find_city_in_index(search_query)
        if city_match:
            slug = city_match['slug']
        else:
            slug = slugify(search_query)
            st.session_state._pending_city_name = search_query
            
        st.session_state.selected_city = slug
        st.session_state.current_page = 'analysis'
        st.session_state.analysis_result = None
        st.rerun()

    # ── Main Overview Content (Map & Table) ──
    col_map, col_table = st.columns([1.3, 1], gap="large")

    with col_map:
        st.markdown("<div class='section-header'>🗺️ Network Coverage Map</div>", unsafe_allow_html=True)
        m_india = folium.Map(location=[22.5, 78.5], zoom_start=5, tiles='OpenStreetMap')
        cached_slugs = {c['slug'] for c in cached}
        for city in cities:
            is_cached = city['slug'] in cached_slugs
            color = '#DC2626' if is_cached else '#9CA3AF'
            status = "Analysed" if is_cached else "Available"
            folium.CircleMarker(
                location=[city['lat'], city['lon']],
                radius=6 if is_cached else 4,
                color=color, fill=True, fill_color=color, fill_opacity=0.8,
                tooltip=f"<b>{city['name']}</b><br>{status}",
            ).add_to(m_india)
        map_data = st_folium(m_india, use_container_width=True, height=500, returned_objects=["last_clicked"], key="india_map")
        
        # MAP CLICK REVERSE GEOCODING
        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lon = map_data["last_clicked"]["lng"]
            click_key = f"{lat:.4f}_{lon:.4f}"
            if st.session_state.get('last_map_click') != click_key:
                st.session_state['last_map_click'] = click_key
                with st.spinner("Locating clicked area..."):
                    import requests
                    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=en"
                    try:
                        resp = requests.get(url, headers={'User-Agent': 'VoltGrid/2.0'}, timeout=5)
                        if resp.status_code == 200:
                            data = resp.json()
                            address = data.get('address', {})
                            city_name = address.get('city') or address.get('town') or address.get('county') or address.get('state_district')
                            if city_name:
                                st.session_state.selected_city = slugify(city_name)
                                st.session_state['_pending_city_name'] = city_name
                                st.session_state.current_page = 'analysis'
                                st.session_state.analysis_result = None
                                st.rerun()
                            else:
                                st.toast("Could not identify a city at this location.", icon="⚠️")
                    except Exception as e:
                        st.toast(f"Geocoding failed: {e}", icon="⚠️")

    with col_table:
        st.markdown("<div class='section-header'>📊 Recent Analyses</div>", unsafe_allow_html=True)
        
        if not cached:
            render_empty_state("No Analyses Found", "Search a city to generate your first analysis.")
        else:
            for city_info in cached[:5]:
                meta = load_city_metadata(city_info['slug'])
                charger_count = meta.get('charger_count', 0) if meta else 0
                area = meta.get('study_area_km2', '—') if meta else '—'
                
                st.markdown(f"""
<div class="vg-card" style="margin-bottom: 12px; padding: 16px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<div style="font-weight: 700; font-size: 1rem; color: #111827;">{city_info['name']}</div>
<span class="vg-badge badge-success">READY</span>
</div>
<div style="font-size: 0.8rem; color: #6B7280; display: flex; justify-content: space-between;">
<span>Chargers: <b>{charger_count}</b></span>
<span>Area: <b>{area} km²</b></span>
</div>
</div>
""", unsafe_allow_html=True)
                
                if st.button(f"Open {city_info['name']}", key=f"btn_open_{city_info['slug']}", use_container_width=True):
                    st.session_state.selected_city = city_info['slug']
                    st.session_state.current_page = 'analysis'
                    st.session_state.analysis_result = None
                    st.rerun()


elif st.session_state.current_page == 'analysis':
    city_slug = st.session_state.selected_city
    if not city_slug:
        st.warning("Please select a city from the Overview page.")
        st.stop()

    # Determine Name
    pending_name = st.session_state.get('_pending_city_name', None)
    city_display = pending_name if pending_name else city_slug.replace('_', ' ').title()
    city_info = find_city_in_index(city_slug)
    if city_info:
        osm_query = city_info.get('osm_query', city_info['name'] + ', India')
        city_display = city_info['name']
    else:
        osm_query = city_display

    render_top_bar(city_display, "City Intelligence")
    
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
    if st.button("← Back to Search", key="btn_back_top"):
        st.session_state.current_page = 'overview'
        st.session_state.analysis_result = None
        st.rerun()

    # Force recompute button for developers/debugging
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Force Recompute Scores", key="btn_recompute", use_container_width=True):
            st.session_state.analysis_result = None
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Wipe City Cache", key="btn_wipe_cache", type="primary", use_container_width=True):
            import shutil
            from src.city_resolver import get_city_data_dir
            city_dir = get_city_data_dir(city_slug)
            if os.path.exists(city_dir):
                shutil.rmtree(city_dir)
            st.session_state.analysis_result = None
            st.rerun()

    # If Not Cached -> Live Generate
    if not is_city_cached(city_slug):
        render_empty_state(
            "ANALYSIS REQUIRED", 
            f"The spatial grid for <b>{city_display}</b> is not yet computed. VoltGrid will pull live OpenStreetMap data to generate the analysis.",
            "📡"
        )
        if st.button("🚀 GENERATE LIVE ANALYSIS", key="btn_generate_live", use_container_width=True):
            progress_box = st.status("Preparing City Intelligence", expanded=True)
            try:
                def progress_cb(step, msg):
                    progress_box.write(f"• {msg}")
                import sys, os
                from contextlib import redirect_stdout, redirect_stderr
                with open('fetch_error.log', 'w') as flog:
                    with redirect_stdout(flog), redirect_stderr(flog):
                        result = generate_city_live(city_slug=city_slug, display_name=city_display, osm_query=osm_query, progress_callback=progress_cb)
                st.session_state.analysis_result = result
                if '_pending_city_name' in st.session_state:
                    del st.session_state['_pending_city_name']
                progress_box.update(label="Analysis complete!", state="complete", expanded=False)
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                progress_box.update(label="Analysis failed.", state="error")
                st.error(f"Error details: {e}")
                st.info("Live generation requires an internet connection.")
        st.stop()

    # Load Analysis
    meta = load_city_metadata(city_slug)
    city_name = meta.get('city', city_slug.replace('_', ' ').title()) if meta else city_slug.replace('_', ' ').title()

    if st.session_state.analysis_result is None or st.session_state.analysis_result.get('city_name', '') != city_name:
        with st.status(f"Loading intelligence for {city_name}...", expanded=False) as status:
            try:
                status.write("• Loading spatial grid")
                status.write("• Calculating scores")
                result = analyze_city(city_slug)
                st.session_state.analysis_result = result
                st.session_state.selected_candidate_idx = 0
                status.update(label="Intelligence loaded", state="complete")
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                status.update(label="Load failed", state="error")
                
            if 'error_trace' in locals():
                st.error(f"Analysis error occurred!")
                st.code(error_trace, language='python')
                st.stop()

    result = st.session_state.analysis_result
    scored_gdf = result['scored_gdf']
    candidates = result['candidates']
    chargers = result['chargers']
    charger_available = result['charger_data_available']

    # ── KPIs & Status Strip ──
    render_status_strip(meta)
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Cells Analysed", f"{len(scored_gdf):,}")
    with k2: st.metric("Known Chargers", f"{len(chargers)}" if charger_available else "N/A")
    with k3: st.metric("Candidate Zones", f"{len(candidates)}")
    with k4: 
        top_score = candidates[0]['Recommendation_Score'] if candidates else 0
        st.metric("Top Recommendation", f"{top_score:.1f}/100")

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    # ── 70/30 Layout: Map & Details ──
    col_map, col_details = st.columns([7, 3], gap="medium")

    with col_map:
        # Floating-style controls
        layer_option = st.radio(
            "LAYERS",
            ["Recommendation Score", "Demand Potential", "Coverage Gap", "Preliminary Feasibility"],
            horizontal=True
        )
        layer_mapping = {
            "Recommendation Score": ("Recommendation_Score", "YlOrRd"),
            "Demand Potential": ("Demand", "YlOrRd"),
            "Coverage Gap": ("Coverage", "YlOrRd"),
            "Preliminary Feasibility": ("Feasibility", "Reds")
        }
        target_field, colormap = layer_mapping[layer_option]

        center_lat = float(scored_gdf['centroid_lat'].mean())
        center_lon = float(scored_gdf['centroid_lon'].mean())

        m_main = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='OpenStreetMap')

        geojson_data = scored_gdf[['h3_index', target_field, 'geometry']].to_json()
        folium.Choropleth(
            geo_data=json.loads(geojson_data),
            data=scored_gdf,
            columns=['h3_index', target_field],
            key_on='feature.properties.h3_index',
            fill_color=colormap,
            fill_opacity=0.6,
            line_opacity=0.1,
            line_weight=0.5,
            legend_name=f"{layer_option} (0–100)"
        ).add_to(m_main)

        # Tooltips
        tooltip = folium.features.GeoJsonTooltip(fields=[target_field], aliases=[f"{layer_option}:"], localize=True)
        folium.GeoJson(
            geojson_data,
            style_function=lambda x: {'fillColor': '#ffffff', 'color': '#111827', 'fillOpacity': 0.0, 'weight': 0.1},
            highlight_function=lambda x: {'fillOpacity': 0.3, 'weight': 2, 'color': '#DC2626'},
            tooltip=tooltip
        ).add_to(m_main)

        # Known chargers
        for c in chargers:
            popup_html = f"<b>⚡ {c['name']}</b><br>{c['operator']}"
            folium.CircleMarker(
                location=[c['lat'], c['lon']], radius=4,
                color='#DC2626', fill=True, fill_color='#DC2626', fill_opacity=0.9,
                tooltip=f"⚡ {c['name']}",
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(m_main)

        # Candidates
        selected_idx = min(st.session_state.selected_candidate_idx, max(len(candidates) - 1, 0))
        for i, cand in enumerate(candidates):
            rank = cand['rank']
            color = "blue" if i == selected_idx else "lightblue"
            icon = folium.Icon(color=color, icon="info-sign")
            
            # Using DivIcon for number markers
            folium.map.Marker(
                [cand['centroid_lat'], cand['centroid_lon']],
                icon=folium.DivIcon(html=f"""
                    <div style="display: flex; align-items: center; gap: 6px; transform: translate(-12px, -12px);">
                        <div style="background-color: {'#0891B2' if i == selected_idx else '#9CA3AF'}; 
                                    color: white; border-radius: 50%; min-width: 24px; height: 24px; 
                                    display: flex; align-items: center; justify-content: center; 
                                    font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); flex-shrink: 0;">
                            {rank}
                        </div>
                        <div style="background-color: rgba(255,255,255,0.95); padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 0.8rem; color: #111827; box-shadow: 0 1px 3px rgba(0,0,0,0.2); white-space: nowrap; border: 1px solid #E5E7EB;">
                            Score: {cand['Recommendation_Score']:.1f}
                        </div>
                    </div>
                """),
                tooltip=f"Candidate #{rank}: {cand['Recommendation_Score']:.1f}/100"
            ).add_to(m_main)

        st_folium(m_main, use_container_width=True, height=700, returned_objects=[], key=f"map_{layer_option}_{selected_idx}")

    with col_details:
        if not candidates:
            render_empty_state("NO CANDIDATE ZONES PASSED SCREENING", "VoltGrid analysed the selected study area but no zones passed the current screening criteria.")
            st.stop()

        cand_labels = [f"#{c['rank']} ({c['Recommendation_Score']:.0f})" for c in candidates]
        chosen_tab = st.selectbox("Select Candidate", cand_labels, index=selected_idx, label_visibility="collapsed")
        new_idx = cand_labels.index(chosen_tab)
        if new_idx != selected_idx:
            st.session_state.selected_candidate_idx = new_idx
            st.rerun()

        active = candidates[selected_idx]

        st.markdown(f"""
<div class="candidate-panel">
<div style="font-size: 0.75rem; font-weight: 700; color: #DC2626; text-transform: uppercase;">
CANDIDATE #{active['rank']}
</div>
<div style="font-size: 1.25rem; font-weight: 800; color: #111827; margin-bottom: 16px;">
{active.get('locality_name', 'Zone')}
</div>
<div style="margin-bottom: 16px;">
<div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:600;">
<span>Recommendation Score</span><span>{active['Recommendation_Score']:.1f} / 100</span>
</div>
<div class="score-bar-container"><div class="score-bar-fill" style="width: {active['Recommendation_Score']}%;"></div></div>
</div>
<div style="margin-bottom: 12px;">
<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#4B5563; margin-bottom:4px;">
<span>Demand Potential</span><span>{active['Demand']:.1f}</span>
</div>
<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#4B5563; margin-bottom:4px;">
<span>Coverage Gap</span><span>{active['Coverage']:.1f}</span>
</div>
<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#4B5563; margin-bottom:4px;">
<span>Preliminary Feasibility</span><span>{active['Feasibility']:.1f}</span>
</div>
<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#4B5563; margin-top:8px; padding-top:8px; border-top:1px solid #E5E7EB;">
<span>Nearest Known Charger</span><span style="font-weight:600; color:#111827;">{active['nearest_charger_km']:.1f} km</span>
</div>
</div>
<div style="display: flex; gap: 8px; margin-top: 16px;">
<span class="vg-badge badge-neutral">🛒 {active.get('commercial_poi_count', 0)} Commercial</span>
<span class="vg-badge badge-neutral">🏠 {active.get('dwell_poi_count', 0)} Dwell</span>
<span class="vg-badge badge-neutral">🅿️ {active.get('parking_poi_count', 0)} Parking</span>
</div>
</div>
""".replace('\n', ''), unsafe_allow_html=True)

        # AI Demand Outlook
        with st.spinner("AI Outlook..."):
            ai_outlook = get_ai_demand_outlook(active, city_name)
        render_ai_card(ai_outlook)

    # ── Comparison & Readiness ──
    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        render_candidate_comparison(candidates)
    with c2:
        render_deployment_readiness()


elif st.session_state.current_page == 'business':
    render_top_bar("Business Case", "Knowledge")
    
    st.markdown(textwrap.dedent("""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px;">
        <div class="vg-card">
            <div style="font-size: 0.85rem; font-weight: 800; color: #2563EB; text-transform: uppercase; margin-bottom: 8px;">WHO USES VOLTGRID</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 16px;">Charging Network Operators</div>
            <div style="font-size: 0.9rem; color: #4B5563; margin-bottom: 12px;"><b>The Job:</b> "We are planning new charging stations. Which areas should our field teams investigate first?"</div>
            <div style="font-size: 0.9rem; color: #4B5563;"><b>Value Proposition:</b> Screen the city first. Survey the best zones second. Prioritize expensive field surveys to save capital.</div>
        </div>
        <div class="vg-card">
            <div style="font-size: 0.85rem; font-weight: 800; color: #059669; text-transform: uppercase; margin-bottom: 8px;">REVENUE MODEL</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 16px;">Enterprise SaaS</div>
            <div style="font-size: 0.9rem; color: #4B5563; margin-bottom: 12px;"><b>Model:</b> Annual platform licensing for CPO planning teams + tiered pricing per city analysis generated.</div>
            <div style="font-size: 0.9rem; color: #4B5563;"><b>Scalability:</b> Deterministic spatial engine scales effortlessly across all municipalities without manual geospatial engineering.</div>
        </div>
    </div>
    
    <div class="vg-card">
        <div style="font-size: 1.1rem; font-weight: 800; color: #111827; margin-bottom: 16px;">Deployment Workflow</div>
        <div style="display: flex; justify-content: space-between; align-items: center; background: #F9FAFB; border-radius: 8px; padding: 20px;">
            <div style="text-align: center; flex: 1;"><div style="font-size: 24px; margin-bottom: 8px;">🖥️</div><div style="font-size: 0.75rem; font-weight: 700; color: #DC2626;">1. CITY SCREENING</div><div style="font-size: 0.7rem; color: #6B7280;">(VoltGrid)</div></div>
            <div style="color: #D1D5DB;">➔</div>
            <div style="text-align: center; flex: 1;"><div style="font-size: 24px; margin-bottom: 8px;">📍</div><div style="font-size: 0.75rem; font-weight: 700; color: #DC2626;">2. TOP ZONES</div><div style="font-size: 0.7rem; color: #6B7280;">(VoltGrid)</div></div>
            <div style="color: #D1D5DB;">➔</div>
            <div style="text-align: center; flex: 1;"><div style="font-size: 24px; margin-bottom: 8px;">👷</div><div style="font-size: 0.75rem; font-weight: 700; color: #111827;">3. FIELD SURVEY</div><div style="font-size: 0.7rem; color: #6B7280;">(Engineering Team)</div></div>
            <div style="color: #D1D5DB;">➔</div>
            <div style="text-align: center; flex: 1;"><div style="font-size: 24px; margin-bottom: 8px;">⚡</div><div style="font-size: 0.75rem; font-weight: 700; color: #111827;">4. GRID CHECK</div><div style="font-size: 0.7rem; color: #6B7280;">(DISCOM)</div></div>
            <div style="color: #D1D5DB;">➔</div>
            <div style="text-align: center; flex: 1;"><div style="font-size: 24px; margin-bottom: 8px;">✅</div><div style="font-size: 0.75rem; font-weight: 700; color: #111827;">5. DEPLOYMENT</div><div style="font-size: 0.7rem; color: #6B7280;">(Final Decision)</div></div>
        </div>
    </div>
    """), unsafe_allow_html=True)


elif st.session_state.current_page == 'methodology':
    render_top_bar("Methodology", "Knowledge")
    
    st.markdown(textwrap.dedent("""
    <div class="vg-card" style="margin-bottom: 32px;">
        <div style="font-size: 1.1rem; font-weight: 800; color: #111827; margin-bottom: 16px;">How Every Score Is Calculated</div>
        <div style="font-size:0.85rem; color:#6B7280; margin-bottom:20px;">
            VoltGrid uses transparent, reproducible scoring based on established facility location models.<br>
            <i>These are prototype policy weights, not learned probabilities.</i>
        </div>
    </div>
    """), unsafe_allow_html=True)

    formulas = get_scoring_formulas()
    
    cols = st.columns(3)
    idx = 0
    for key in ['demand', 'coverage', 'feasibility']:
        f = formulas[key]
        with cols[idx]:
            comp_html = "".join([f"<li><b>{w}</b> {n}</li>" for n, w, d in f['components']])
            st.markdown(textwrap.dedent(f"""
            <div class="vg-card" style="height: 100%;">
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 12px; color: #111827;">{f['name']}</div>
                <ul style="font-size: 0.85rem; color: #4B5563; padding-left: 18px; margin-bottom: 16px;">{comp_html}</ul>
                <div style="background: #F9FAFB; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 0.75rem; color: #DC2626;">
                    {f['formula']}
                </div>
            </div>
            """), unsafe_allow_html=True)
        idx += 1
        
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
    
    f_rec = formulas['recommendation']
    comp_html = "".join([f"<li><b>{w}</b> {n}</li>" for n, w, d in f_rec['components']])
    st.markdown(textwrap.dedent(f"""
    <div class="vg-card" style="border-top: 4px solid #DC2626;">
        <div style="font-weight: 800; font-size: 1.1rem; margin-bottom: 12px; color: #111827;">FINAL RECOMMENDATION</div>
        <ul style="font-size: 0.9rem; color: #4B5563; padding-left: 20px; margin-bottom: 16px;">{comp_html}</ul>
        <div style="background: #F9FAFB; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 0.85rem; color: #DC2626;">
            {f_rec['formula']}
        </div>
    </div>
    """), unsafe_allow_html=True)
