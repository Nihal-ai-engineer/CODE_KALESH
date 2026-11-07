import textwrap

def get_enterprise_css():
    return textwrap.dedent("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #F7F8FA !important;
            color: #111827;
        }
        
        .stApp {
            background-color: #F7F8FA;
            color: #111827;
        }
        
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }

        /* ── Sidebar Styles ── */
        [data-testid="stSidebar"] {
            background-color: #1F2937 !important; /* Deep Navy / Charcoal */
            color: #F9FAFB !important;
        }
        [data-testid="stSidebar"] * {
            color: #F9FAFB !important;
        }
        
        /* Sidebar Logo */
        .sidebar-brand {
            font-size: 1.5rem;
            font-weight: 900;
            color: #FFFFFF;
            padding-bottom: 5px;
            letter-spacing: -0.02em;
        }
        .sidebar-subtitle {
            font-size: 0.75rem;
            font-weight: 500;
            color: #9CA3AF;
            margin-bottom: 30px;
        }

        /* ── Top Bar ── */
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #FFFFFF;
            padding: 12px 24px;
            border-bottom: 1px solid #E5E7EB;
            margin-bottom: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .top-bar-breadcrumb {
            font-weight: 700;
            font-size: 1.1rem;
            color: #111827;
        }
        .top-bar-badges {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        /* ── Generic Cards ── */
        .vg-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
            transition: all 0.2s ease;
        }
        
        /* ── KPI Cards ── */
        [data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            border-top: 4px solid #DC2626 !important; /* VoltGrid brand accent */
            border-radius: 12px !important;
            padding: 16px 20px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
        }
        [data-testid="stMetricLabel"] {
            color: #6B7280 !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }
        [data-testid="stMetricValue"] {
            color: #111827 !important;
            font-size: 1.75rem !important;
            font-weight: 800 !important;
        }
        
        /* Fix radio button labels (prevent white-on-white in dark mode) */
        div[data-testid="stRadio"] *, div[role="radiogroup"] *, [data-baseweb="radio"] *, .stRadio * {
            color: #111827 !important;
            font-weight: 700 !important;
        }

        /* ── Buttons ── */
        .stButton>button {
            background: #DC2626 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1.2rem !important;
            box-shadow: 0 2px 4px rgba(220,38,38,0.2) !important;
            transition: all 0.2s ease !important;
        }
        .stButton>button:hover {
            background: #B91C1C !important;
            box-shadow: 0 4px 12px rgba(185,28,28,0.3) !important;
        }
        
        /* ── Secondary Buttons (e.g. Export) ── */
        .btn-secondary>button {
            background: #FFFFFF !important;
            color: #374151 !important;
            border: 1px solid #D1D5DB !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
        .btn-secondary>button:hover {
            background: #F3F4F6 !important;
            color: #111827 !important;
        }

        /* ── Badges ── */
        .vg-badge {
            font-size: 0.7rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 20px;
            text-transform: uppercase;
        }
        .badge-success { background: #D1FAE5; color: #065F46; }
        .badge-warning { background: #FEF3C7; color: #92400E; }
        .badge-danger { background: #FEE2E2; color: #991B1B; }
        .badge-info { background: #E0F2FE; color: #075985; }
        .badge-neutral { background: #F3F4F6; color: #4B5563; }
        .badge-ai { background: #CFFAFE; color: #164E63; border: 1px solid #A5F3FC; }

        /* ── Section Headers ── */
        .section-header {
            font-weight: 800;
            font-size: 1.25rem;
            color: #111827;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #E5E7EB;
        }

        /* ── Map iframe ── */
        iframe[title*="folium"], iframe[title*="streamlit_folium"], div[data-testid="stCustomComponentV1"] {
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
        }

        /* ── AI Card ── */
        .ai-card {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-top: 4px solid #0891B2; /* Cyan/Teal */
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        }
        .ai-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .ai-title {
            font-weight: 800;
            font-size: 1rem;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* ── Empty State ── */
        .empty-state {
            background: #FFFFFF;
            border: 1px dashed #D1D5DB;
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            margin: 20px 0;
        }
        .empty-state-icon {
            font-size: 2.5rem;
            color: #9CA3AF;
            margin-bottom: 12px;
        }
        .empty-state-title {
            font-weight: 700;
            font-size: 1.1rem;
            color: #111827;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .empty-state-desc {
            font-size: 0.9rem;
            color: #6B7280;
            max-width: 600px;
            margin: 0 auto 16px;
        }

        /* ── Status Strip ── */
        .status-strip {
            display: flex;
            gap: 20px;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            padding: 12px 20px;
            border-radius: 10px;
            margin-bottom: 24px;
            overflow-x: auto;
        }
        .status-item {
            display: flex;
            flex-direction: column;
        }
        .status-label {
            font-size: 0.65rem;
            font-weight: 700;
            color: #6B7280;
            text-transform: uppercase;
        }
        .status-value {
            font-size: 0.8rem;
            font-weight: 600;
            color: #111827;
        }

        /* ── Candidate Comparison Table ── */
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 0.85rem;
            background: #FFFFFF;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #E5E7EB;
        }
        .comparison-table th, .comparison-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #E5E7EB;
        }
        .comparison-table th {
            background: #F9FAFB;
            font-weight: 700;
            color: #374151;
            text-transform: uppercase;
            font-size: 0.75rem;
        }
        .comparison-table td:first-child {
            font-weight: 600;
            color: #111827;
            background: #F9FAFB;
        }
        
        /* ── Progress Bar custom ── */
        .score-bar-container {
            width: 100%;
            background-color: #E5E7EB;
            border-radius: 999px;
            height: 6px;
            margin-top: 6px;
        }
        .score-bar-fill {
            background-color: #DC2626;
            height: 6px;
            border-radius: 999px;
        }
        
        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] { gap: 0px; border-bottom: 1px solid #E5E7EB; }
        .stTabs [data-baseweb="tab"] { 
            font-weight: 600 !important; 
            font-size: 0.9rem !important;
            padding: 12px 16px !important;
            color: #6B7280 !important;
        }
        .stTabs [aria-selected="true"] { 
            border-bottom-color: #DC2626 !important; 
            color: #DC2626 !important; 
        }
        
        /* Candidate detail panel wrapper */
        .candidate-panel {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-top: 4px solid #DC2626;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        
    </style>
    """)
