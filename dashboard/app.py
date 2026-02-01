import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from categorize import add_rule_pattern, categorize, load_rules, resolve_rules_path


st.set_page_config(page_title="money-backward dashboard", layout="wide")

st.title("money-backward dashboard")
st.caption("Normalized transactions -> quick personal finance view (Streamlit)")

DEFAULT_CSV = os.environ.get("MONEY_BACKWARD_CSV", "./out/merged.csv")

with st.sidebar:
    st.header("Data")
    csv_path = st.text_input("CSV path", value=DEFAULT_CSV)

    st.header("Categories")
    rules_path = resolve_rules_path()
    st.caption("Rules YAML (edit directly, or use the UI below to append patterns)")
    st.code(rules_path, language="text")

    reload_btn = st.button("Reload")


@st.cache_data(show_spinner=False)
def load_csv(p: str) -> pd.DataFrame:
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    for c in ["currency", "description", "merchant", "category", "account"]:
        if c in df.columns:
            df[c] = df[c].fillna("")
    return df


@st.cache_data(show_spinner=False)
def load_category_rules():
    return load_rules()


if reload_btn:
    load_csv.clear()  # type: ignore[attr-defined]
    load_category_rules.clear()  # type: ignore[attr-defined]

try:
    df = load_csv(csv_path)
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

if df.empty:
    st.warning("No rows.")
    st.stop()

rules, default_cat = load_category_rules()

# Fill merchant fallback
if "merchant" in df.columns:
    df.loc[df["merchant"].eq(""), "merchant"] = df["description"]

# Ensure a category exists (use provided, else infer)
if "category" not in df.columns:
    df["category"] = ""

need = df["category"].eq("")
df.loc[need, "category"] = df.loc[need, "description"].map(lambda s: categorize(s, rules, default_cat))

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
md = d.assign(month=d["date"].dt.to_period("M").astype(str))
monthly = (
    md.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "net"})
)
monthly_income = md.loc[md["amount"] > 0].groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "income"})
monthly_expense = (
    md.loc[md["amount"] < 0]
    .assign(expense=lambda x: -x["amount"])
    .groupby("month", as_index=False)["expense"]
    .sum()
)
monthly = monthly.merge(monthly_income, on="month", how="left").merge(monthly_expense, on="month", how="left")
monthly[["income", "expense"]] = monthly[["income", "expense"]].fillna(0)

st.line_chart(monthly, x="month", y=["income", "expense", "net"])

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
    st.dataframe(by_merch, width="stretch", hide_index=True)

st.subheader("Categorize (learn rules)")
st.caption("Pick a transaction and append a regex pattern to the YAML rules.")

# Work on a recent slice to keep UI snappy
work = d.sort_values("date", ascending=False).copy().reset_index(drop=True)
max_rows = st.slider("Rows shown", min_value=50, max_value=1000, value=200, step=50)
work = work.head(max_rows)

idx = st.selectbox(
    "Select row",
    options=list(range(len(work))),
    format_func=lambda i: f"{work.loc[i, 'date'].date()}  {work.loc[i, 'amount']:,.0f}  {work.loc[i, 'description']}",
)
row = work.loc[int(idx)]

existing_categories = sorted([c for c in df["category"].unique().tolist() if c])
cat_mode = st.radio("Category", options=["existing", "new"], horizontal=True)
if cat_mode == "new":
    cat = st.text_input("New category name", value="")
else:
    cat = st.selectbox("Assign category", options=existing_categories, index=0 if existing_categories else 0)

suggest = row.get("merchant", "") or row.get("description", "")
mode = st.radio("Pattern mode", options=["contains", "exact"], horizontal=True)
if mode == "exact":
    pattern_default = f"^{re.escape(str(suggest))}$"
else:
    pattern_default = re.escape(str(suggest))

pattern = st.text_input("Regex pattern (case-insensitive)", value=pattern_default)

c_apply, c_note = st.columns([1, 2])
with c_apply:
    if st.button("Add rule"):
        try:
            if rules_path.endswith("categories.example.yaml"):
                st.error(
                    "You're using categories.example.yaml. Copy it first: cp dashboard/categories.example.yaml dashboard/categories.yaml"
                )
            elif not str(cat).strip():
                st.error("Category name is empty")
            else:
                add_rule_pattern(path=rules_path, category=str(cat).strip(), pattern=pattern)
                st.success(f"Added pattern to {str(cat).strip()}: {pattern}")
                load_category_rules.clear()  # type: ignore[attr-defined]
                st.rerun()
        except Exception as e:
            st.error(str(e))
with c_note:
    st.write(
        "Tip: Use **exact** for noisy merchants you want to pin precisely. Use **contains** for broad matches."
    )

st.subheader("Transactions")
st.dataframe(work, width="stretch", hide_index=True)
