import pandas as pd
import streamlit as st

try:
    from st_link_analysis import EdgeStyle, NodeStyle, st_link_analysis
except ImportError:
    EdgeStyle = None
    NodeStyle = None
    st_link_analysis = None


st.set_page_config(page_title="Clinical Concept Knowledge Graph", layout="wide")

st.markdown(
    """
    <style>
      .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1580px;
      }

      h1 {
        color: #18202f;
        font-size: 1.85rem !important;
        letter-spacing: 0;
        margin-bottom: 0.1rem;
      }

      [data-testid="stCaptionContainer"] {
        color: #64748b;
      }

      [data-testid="stSidebar"] {
        background: #fbfcfe;
        border-right: 1px solid #e2e8f0;
      }

      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3 {
        color: #172033;
      }

      [data-testid="stFileUploader"] section {
        border-color: #cbd5e1;
        background: #fbfdff;
      }

      div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


st.header("**:blue[APEX: Automated Phenotype Knowledge Extraction and Representation from EHRs]**")



st.sidebar.header("Controls")

disease_options = [
    "Behcet syndrome",
    "Pulmonary arterial hypertension",
    "Sickle cell anemia"]
data_source = ["Columbia University Irving Medical Center", "Children's hospital of Philadelphia"]

selected_disease = st.sidebar.selectbox("Disease of interest", disease_options)
selected_data_source = st.sidebar.selectbox("Data Source", data_source)
if selected_data_source == "Columbia University Irving Medical Center":
    df = pd.read_excel("CUIMC_rel_display.xlsx", sheet_name=selected_disease)
else:
    df = pd.read_excel("CHOP_rel_display.xlsx", sheet_name=selected_disease)

required_cols = [
    "doi_concept_id",
    "disease_of_interest",
    "candidate_clinical_concept_id",
    "candidate_clinical_concept",
    "relation",
    "entity_category",
]

missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    st.error(f"Missing columns: {missing_cols}")
    st.stop()


relation_options = sorted(df["relation"].dropna().unique())
selected_relations = st.sidebar.multiselect(
    "Filter by relation",
    relation_options,
    default=relation_options,
)

domain_options = sorted(df["entity_category"].dropna().str.lower().unique())
selected_domains = st.sidebar.multiselect(
    "Filter by domain",
    domain_options,
    default=domain_options,
)

search_text = st.sidebar.text_input("Search candidate concept", placeholder="Type to search...")
max_nodes = st.sidebar.slider("Max candidate concepts", 5, 300, 50)
show_relation_labels = st.sidebar.toggle("Show relation labels", value=True)


plot_df = df.copy()
plot_df["entity_category"] = plot_df["entity_category"].astype(str).str.lower()
print(selected_relations)
# plot_df = plot_df[
#     (plot_df["disease_of_interest"] == selected_disease)
#     & (plot_df["relation"].isin(selected_relations))
#     & (plot_df["entity_category"].isin(selected_domains))
# ].copy()
plot_df = plot_df[
    (plot_df["disease_of_interest"] == selected_disease)
    & (plot_df["relation"].isin(selected_relations))
    & (plot_df["entity_category"].isin(selected_domains))
].copy()



if search_text:
    plot_df = plot_df[
        plot_df["candidate_clinical_concept"]
        .astype(str)
        .str.contains(search_text, case=False, na=False)
    ]

plot_df = plot_df.drop_duplicates(
    subset=[
        "disease_of_interest",
        "candidate_clinical_concept_id",
        "candidate_clinical_concept",
        "relation",
        "entity_category",
    ]
).head(max_nodes)

if plot_df.empty:
    st.warning("No rows match the selected filters.")
    st.stop()


def wrap_label(text, width=14):
    text = str(text)
    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return "\n".join(lines)


def display_relation(text):
    return str(text).replace("_", " ")


class CytoscapeStyle:
    def __init__(self, selector, style):
        self.selector = selector
        self.style = style

    def dump(self):
        return {
            "selector": self.selector,
            "style": self.style,
        }


domain_colors = {
    "doi": "#FAC369",
    "condition": "#78B3F2",
    "drug": "#91C58B",
    "procedure": "#E694B0",
    "measurement": "#94A4AC"
}

# relation_colors = {
#     "synonym": "#9CA3AF",
#     "is_a": "#9CA3AF",
#     "subsumes": "#9CA3AF",
#     "has_symptom": "#B8892E",
#     "has_complication": "#DC2626",
#     "is_complication_of": "#DC2626",
#     "is_differential_diagnosis_of": "#F97316",
#     "used_for_treatment_or_prevention": "#078899",
#     "diagnosis": "#1D5B79",
#     "treat": "#6D5BD0",
#     "none": "#CBD5E1",
# }

nodes = []
edges = []
added_nodes = set()

doi_node_id = f"doi::{selected_disease}"

nodes.append({
    "data": {
        "id": doi_node_id,
        "label": "doi",
        "caption": wrap_label(selected_disease, 16),
        # "name": selected_disease,
        # "type": "Disease of interest",
        # "node_type": "doi",
        "entity_category": "doi",
        # "node_color": domain_colors["doi"],
    }
})
added_nodes.add(doi_node_id)

for edge_index, (_, row) in enumerate(plot_df.iterrows(), start=1):
    candidate_name = str(row["candidate_clinical_concept"])
    candidate_id = str(row["candidate_clinical_concept_id"])
    relation = str(row["relation"])
    domain = str(row["entity_category"]).lower()
    rational = row["rationale"]
    target_node_id = f"concept::{candidate_id}"
    node_color = "#0f0f0f"
    edge_color = "#0f0f0f"

    if target_node_id not in added_nodes:
        nodes.append({
            "data": {
                "id": target_node_id,
                "label": domain,
                "caption": wrap_label(candidate_name, 14),
                "description": rational,
                # "name": candidate_name,
                # "entity_category": domain,
            }
        })
        added_nodes.add(target_node_id)

    edges.append({
        "data": {
            "id": f"edge::{edge_index}",
            "source": doi_node_id,
            "target": target_node_id,
            "label": relation,
            "caption": display_relation(relation),
            "relation": relation,
            "edge_color": edge_color,
        }
    })

elements = {
    "nodes": nodes,
    "edges": edges,
}

if st_link_analysis is None:
    st.error(
        "This version uses st-link-analysis. Install it with "
        "`pip install st-link-analysis`, then rerun the app."
    )
    st.stop()


summary_cols = st.columns(3)

with summary_cols[0]:
    st.markdown("**Selected DOI**")
    st.markdown(
        f"""
        <div style="
            font-size: 2.0rem;
            font-weight: 600;
            line-height: 1.2;
            word-wrap: break-word;
        ">
            {selected_disease}
        </div>
        """,
        unsafe_allow_html=True
    )

summary_cols[1].metric("Relations", len(df))
summary_cols[2].metric(
    "Entity category",
    df["entity_category"].nunique()
)

legend_items = [
    (domain, color)
    for domain, color in domain_colors.items()
    if  domain in selected_domains
]

legend_html = "".join(
    f"""
    <div class="graph-legend-item">
      <span class="graph-legend-swatch" style="background:{color};"></span>
      <span class="graph-legend-label">{domain}</span>
    </div>
    """
    for domain, color in legend_items
)

st.markdown(
    """
    <style>
      .graph-legend-panel {
        height: 820px;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background: #ffffff;
        padding: 16px 14px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
      }

      .graph-legend-title {
        color: #18202f;
        font-size: 0.9rem;
        font-weight: 750;
        margin-bottom: 12px;
      }

      .graph-legend-item {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 8px 0;
        border-bottom: 1px solid #f1f5f9;
      }

      .graph-legend-item:last-child {
        border-bottom: 0;
      }

      .graph-legend-swatch {
        width: 16px;
        height: 16px;
        border: 2px solid #ffffff;
        border-radius: 999px;
        box-shadow: 0 0 0 1px #cbd5e1;
        flex: 0 0 auto;
      }

      .graph-legend-label {
        color: #334155;
        font-size: 0.86rem;
        font-weight: 650;
        text-transform: capitalize;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

node_styles = [
    NodeStyle("doi", domain_colors["doi"], "caption"),
]

for domain, color in domain_colors.items():
    if domain != "doi":
        node_styles.append(NodeStyle(domain, color, "caption"))

node_styles.extend(
    [
        CytoscapeStyle(
            "node",
            {
                "text-valign": "center",
                "text-halign": "center",
                "text-wrap": "wrap",
                "text-max-width": "112px",
                "font-size": "20px",
                "font-family": "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
                "font-weight": "700",
                "color": "#0f0f0f",
                "text-outline-width": 0,
                "text-outline-color": "data(node_color)",
                "width": "120px",
                "height": "120px",
                "border-width": "2px",
                "border-color": "#0a0a0a",
                "shadow-blur": 12,
                "shadow-color": "rgba(15, 23, 42, 0.22)",
                "shadow-offset-x": 0,
                "shadow-offset-y": 4,
                "shadow-opacity": 0.7,
            },
        ),
        CytoscapeStyle(
            'node[label = "doi"]',
            {
                "width": "180px",
                "height": "180px",
                "font-size": "35px",
                "border-width": "4px",
                 "color": "#0f0f0f",
                "border-color": "#010101",
                "shadow-blur": 18,
                "shadow-color": "rgba(15, 58, 109, 0.34)",
                "shadow-opacity": 0.9,
            },
        ),
        CytoscapeStyle(
            "node:selected",
            {
                "border-color": "#0C0C0C",
                "border-width": "4px",
                "shadow-blur": 14,
                "shadow-color": "rgba(0, 184, 217, 0.45)",
                "shadow-opacity": 1,
            },
        ),
    ]
)

edge_styles = [
    EdgeStyle(
        relation,
        "#0f0f0f",
        caption="caption" if show_relation_labels else None,
        directed=True,
        curve_style="bezier",
    )
    for relation in relation_options
]

edge_styles.append(
    CytoscapeStyle(
        "edge",
        {
            "width": 3,
            "opacity": 0.72,
            "target-arrow-shape": "triangle",
            "target-arrow-scale": 0.7,
            "font-size": "30px",
            "font-family": "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            "font-weight": "700",
            "color": "#080808",
            "text-wrap": "wrap",
            "text-max-width": "320px",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.94,
            "text-background-shape": "roundrectangle",
            "text-background-padding": "8px",
            "text-border-color": "#e2e8f0",
            "text-border-width": 1,
            "text-border-opacity": 1,
            "text-margin-y": -12,
        },
    )
)

edge_styles.append(
    CytoscapeStyle(
        "edge:selected",
        {
            "line-color": "#00B8D9",
            "target-arrow-color": "#00B8D9",
            "width": 3,
            "opacity": 1,
        },
    )
)

layout = {
    "name": "cose",
    "fit": True,
    "padding": 70,
    "animate": False,
    "nodeRepulsion": 360000,
    "nodeOverlap": 16,
    "idealEdgeLength": 135,
    "edgeElasticity": 100,
    "gravity": 0.55,
    "numIter": 1200,
    "nodeDimensionsIncludeLabels": False,
}

legend_col, graph_col = st.columns([0.16, 0.84], gap="small")

with legend_col:
    st.markdown(
        f"""
        <div class="graph-legend-panel">
          <div class="graph-legend-title">Entity category</div>
          {legend_html}
        """,
        unsafe_allow_html=True,
    )

with graph_col:
    st_link_analysis(
        elements,
        layout,
        node_styles,
        edge_styles,
        height=820,
        key = f"clinical-kg-{selected_data_source}-{selected_disease}-{len(nodes)}-{len(edges)}-{show_relation_labels}"
    )

with st.expander("Show filtered data"):
    st.dataframe(plot_df, use_container_width=True)
