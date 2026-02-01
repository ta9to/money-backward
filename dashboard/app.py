import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st


st.set_page_config(page_title="money-backward dashboard", layout="wide")

st.title("money-backward dashboard")
st.caption("Normalized transactions -> quick personal finance view (Streamlit)")

DEFAULT_CSV = os.environ.get("MONEY_BACKWARD_CSV", "./out/merged.csv")

with st.sidebar:
    st.header("Data")
    csv_path = st.text_input("CSV path", value=DEFAULT_CSV)
    reload_btn = st.button("Reload")


@st.cache_data(show_spinner=False)
def load_csv(p: str) -> pd.DataFrame:
    df = pd.read_csv(p)
    # Normalize types
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    for c in ["currency", "description", "merchant", "category", "account"]:
        if c in df.columns:
            df[c] = df[c].fillna("")
    return df


def infer_category(desc: str) -> str:
    # Very small rule-based categorizer. Edit freely.
    rules = [
        (r"(UNEXT|ユーネクスト|NETFLIX|Spotify|Apple\.com/bill|Google)" , "Subscriptions"),
        (r"(Amazon|AMZN|楽天|Rakuten)" , "Shopping"),
        (r"(コンビニ|セブン|ローソン|ファミマ|FamilyMart)" , "Convenience"),
        (r"(Suica|PASMO|JR|東京メトロ|バス|タクシー)" , "Transport"),
        (r"(電気|ガス|水道|Utilities)" , "Utilities"),
        (r"(病院|薬局|クリニック|Dent|歯科)" , "Health"),
        (r"(居酒屋|レストラン|カフェ|スタバ|Starbucks)" , "Food"),
    ]
    for pat, cat in rules:
        if re.search(pat, desc, flags=re.IGNORECASE):
            return cat
    return "Uncategorized"


if reload_btn:
    load_csv.clear()  # type: ignore[attr-defined]

try:
    df = load_csv(csv_path)
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

if df.empty:
    st.warning("No rows.")
    st.stop()

# Fill merchant fallback
if "merchant" in df.columns:
    df.loc[df["merchant"].eq(""), "merchant"] = df["description"]

# Ensure a category exists (use provided, else infer)
if "category" not in df.columns:
    df["category"] = ""

df.loc[df["category"].eq(""), "category"] = df.loc[df["category"].eq(""), "description"].map(infer_category)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    min_date = df["date"].min()
    max_date = df["date"].max()
    date_range = st.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )

    accounts = sorted([a for a in df.get("account", pd.Series(dtype=str)).unique().tolist() if a])
    account_sel = st.multiselect("Account", options=accounts, default=accounts)

    categories = sorted([c for c in df["category"].unique().tolist() if c])
    category_sel = st.multiselect("Category", options=categories, default=categories)

# Apply filters
start, end = date_range
mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
if account_sel:
    mask &= df.get("account", "").isin(account_sel)
if category_sel:
    mask &= df["category"].isin(category_sel)

d = df.loc[mask].copy()

# KPIs
income = d.loc[d["amount"] > 0, "amount"].sum()
expense = -d.loc[d["amount"] < 0, "amount"].sum()
net = d["amount"].sum()

k1, k2, k3 = st.columns(3)
k1.metric("Income", f"{income:,.0f}")
k2.metric("Expense", f"{expense:,.0f}")
k3.metric("Net", f"{net:,.0f}")

# Monthly time series
st.subheader("Monthly")
monthly = (
    d.assign(month=d["date"].dt.to_period("M").astype(str))
    .groupby("month", as_index=False)["amount"]
    .sum()
)
st.line_chart(monthly, x="month", y="amount")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Expense by Category")
    by_cat = (
        d.loc[d["amount"] < 0]
        .assign(expense=lambda x: -x["amount"])
        .groupby("category", as_index=False)["expense"]
        .sum()
        .sort_values("expense", ascending=False)
    )
    st.bar_chart(by_cat, x="category", y="expense")

with c2:
    st.subheader("Top Merchants (Expense)")
    by_merch = (
        d.loc[d["amount"] < 0]
        .assign(expense=lambda x: -x["amount"])
        .groupby("merchant", as_index=False)["expense"]
        .sum()
        .sort_values("expense", ascending=False)
        .head(20)
    )
    st.dataframe(by_merch, use_container_width=True, hide_index=True)

st.subheader("Transactions")
st.dataframe(
    d.sort_values("date", ascending=False),
    use_container_width=True,
    hide_index=True,
)
