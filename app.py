
import os
import math
import pandas as pd
import streamlit as st
import altair as alt

# -------------------- Page Config (mobile friendly) --------------------
st.set_page_config(
    page_title="Payments Explorer",
    page_icon="💳",
    layout="centered",  # better for phones
    initial_sidebar_state="collapsed",
)

# Small CSS tweaks for mobile spacing and card look
st.markdown(
    """
    <style>
    .small-text { font-size: 0.9rem; }
    .card {
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 14px 14px 6px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        background: white;
    }
    .muted { color: #6b7280; }
    .chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid #e5e7eb;
        font-size: 0.8rem;
        margin-right: 6px;
        background: #f9fafb;
    }
    .nowrap { white-space: nowrap; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------- Data Loading --------------------
@st.cache_data
def load_data(file_like=None):
    if file_like is not None:
        df = pd.read_csv(file_like)
    else:
        # Fallback to a local CSV if present
        default_path = "fake_data.csv"
        if os.path.exists(default_path):
            df = pd.read_csv(default_path)
        else:
            st.stop()  # no data, app cannot proceed
    # Normalize column names to expected schema
    expected = ["city", "year", "receiver", "value", "type", "payes"]
    lower_cols = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=lower_cols)
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {missing}. Expected columns: {expected}")
        st.stop()
    # Coerce dtypes
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["city"] = df["city"].astype(str)
    df["receiver"] = df["receiver"].astype(str)
    df["type"] = df["type"].astype(str)
    df["payes"] = df["payes"].astype(str).str.strip().str.lower().replace({"now": "no"})  # handle "yes/now" typo -> "no"
    return df.dropna(subset=["year", "value"])

# Header
st.markdown("### 💳 Payments Explorer")
st.caption("Filter, explore and visualize your CSV. Optimized for phones.")

# Data source: upload or bundled file
with st.expander("📁 Data source", expanded=False):
    uploaded = st.file_uploader("Upload a CSV with columns: city, year, receiver, value, type, payes", type=["csv"])
df = load_data(uploaded)


# -------------------- Filters (compact for mobile) --------------------
with st.expander("🔎 Filters", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        # City multiselect
        city_sel = st.multiselect("City", sorted(df["city"].dropna().unique()), placeholder="All")
        
        # Receiver dropdown depends on selected city(ies)
        if city_sel:
            receiver_pool = sorted(df[df["city"].isin(city_sel)]["receiver"].dropna().unique().tolist())
        else:
            receiver_pool = sorted(df["receiver"].dropna().unique().tolist())
        receiver_options = ["All"] + receiver_pool
        receiver_sel = st.selectbox("Receiver", receiver_options, index=0)

        type_sel = st.multiselect("Type", sorted(df["type"].dropna().unique()), placeholder="All")
        payes_sel = st.multiselect("Paid?", ["yes", "no"], placeholder="All")
    with c2:
        year_min, year_max = int(df["year"].min()), int(df["year"].max())
        year_range = st.slider("Year range", min_value=year_min, max_value=year_max, value=(year_min, year_max))
        value_min, value_max = float(df["value"].min()), float(df["value"].max())
        value_range = st.slider("Value range", min_value=float(round(value_min, 2)), max_value=float(round(value_max, 2)),
                                value=(float(round(value_min, 2)), float(round(value_max, 2))))
    search = st.text_input("Search receiver (case-insensitive)", "")

# Apply filters
mask = (
    df["year"].between(year_range[0], year_range[1]) &
    df["value"].between(value_range[0], value_range[1])
)
if city_sel:
    mask &= df["city"].isin(city_sel)
# Apply receiver dropdown filter
if receiver_sel != "All":
    mask &= df["receiver"] == receiver_sel
if type_sel:
    mask &= df["type"].isin(type_sel)
if payes_sel:
    mask &= df["payes"].isin([p.lower() for p in payes_sel])
if search:
    mask &= df["receiver"].str.contains(search, case=False, na=False)

fdf = df[mask].copy()
# Apply filters

mask = (
    df["year"].between(year_range[0], year_range[1]) &
    df["value"].between(value_range[0], value_range[1])
)
if city_sel:
    mask &= df["city"].isin(city_sel)
# NEW: apply receiver dropdown filter
if "receiver_sel" in locals() and receiver_sel != "All":
    mask &= df["receiver"] == receiver_sel
if type_sel:
    mask &= df["type"].isin(type_sel)
if payes_sel:
    mask &= df["payes"].isin([p.lower() for p in payes_sel])
if search:
    mask &= df["receiver"].str.contains(search, case=False, na=False)

fdf = df[mask].copy()

# -------------------- KPIs --------------------
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Rows", len(fdf))
with k2:
    st.metric("Total Value", f"${fdf['value'].sum():,.2f}")
with k3:
    st.metric("Avg. Value", f"${(fdf['value'].mean() if len(fdf) else 0):,.2f}")

# -------------------- Quick Charts --------------------
with st.expander("📊 Quick charts", expanded=False):
    # Values by city
    by_city = fdf.groupby("city", as_index=False)["value"].sum().sort_values("value", ascending=False).head(10)
    chart_city = alt.Chart(by_city).mark_bar().encode(
        x=alt.X("value:Q", title="Total value"),
        y=alt.Y("city:N", sort="-x", title="City"),
        tooltip=["city", alt.Tooltip("value:Q", format=",.2f")]
    ).properties(height=220)
    st.altair_chart(chart_city, use_container_width=True)

    # Count by type
    by_type = fdf["type"].value_counts().reset_index()
    by_type.columns = ["type", "count"]
    chart_type = alt.Chart(by_type).mark_bar().encode(
        x=alt.X("count:Q", title="Count"),
        y=alt.Y("type:N", sort="-x", title="Type"),
        tooltip=["type", "count"]
    ).properties(height=220)
    st.altair_chart(chart_type, use_container_width=True)


# -------------------- Data Table (paginated) --------------------
page_size = st.selectbox("Rows per page", [5, 10, 20, 50], index=1)
total_pages = max(1, math.ceil(len(fdf) / page_size))
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
start, end = (page - 1) * page_size, (page - 1) * page_size + page_size

st.dataframe(
    fdf.iloc[start:end].reset_index(drop=True),
    use_container_width=True,
    hide_index=True
)
st.caption(f"Page {page} of {total_pages}")

# -------------------- Download filtered data --------------------

csv = fdf.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download filtered CSV", data=csv, file_name="filtered_data.csv", mime="text/csv")

st.caption("Tip: Put **app.py** and **fake_data.csv** in the same folder, then run: `streamlit run app.py`.")
