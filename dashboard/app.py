import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

from categorize import add_rule_pattern, categorize, load_rules, resolve_rules_path


st.set_page_config(page_title="money-backward dashboard", layout="wide")

st.title("money-backward dashboard")
st.caption("Normalized transactions -> quick personal finance view (Streamlit)")

DEFAULT_CSV = os.environ.get("MONEY_BACKWARD_CSV", "./out/merged.csv")

with st.sidebar:
    st.header("Data")
    csv_path = st.text_input("CSV path", value=DEFAULT_CSV, key="csv_path")

    st.header("Categories")
    rules_path = resolve_rules_path()
    st.caption("Rules YAML (edit directly, or use the UI below to append patterns)")
    st.code(rules_path, language="text")

    c1, c2 = st.columns(2)
    with c1:
        reload_btn = st.button("Reload")
    with c2:
        reset_btn = st.button("Reset")


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

if 'reset_btn' in locals() and reset_btn:
    # Clear widget state back to defaults
    for k in ["date_range", "account_filter", "category_filter"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

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
        key="date_range",
    )

    accounts = sorted([a for a in df.get("account", pd.Series(dtype=str)).unique().tolist() if a])
    account_sel = st.multiselect("Account", options=accounts, default=accounts, key="account_filter")

    categories = sorted([c for c in df["category"].unique().tolist() if c])
    category_sel = st.multiselect("Category", options=categories, default=categories, key="category_filter")

# Apply filters
start, end = date_range
mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
if account_sel:
    mask &= df.get("account", "").isin(account_sel)
if category_sel:
    mask &= df["category"].isin(category_sel)

d = df.loc[mask].copy()

tabs = st.tabs(["Overview", "Monthly"])

# ---------- Overview tab ----------
with tabs[0]:
    # KPIs (current filters)
    income = d.loc[d["amount"] > 0, "amount"].sum()
    expense = -d.loc[d["amount"] < 0, "amount"].sum()
    net = d["amount"].sum()

    k1, k2, k3 = st.columns(3)
    k1.metric("Income", f"{income:,.0f}")
    k2.metric("Expense", f"{expense:,.0f}")
    k3.metric("Net", f"{net:,.0f}")

    st.subheader("Monthly trend")
    md = d.assign(month=d["date"].dt.to_period("M").astype(str))
    monthly = md.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "net"})
    monthly_income = (
        md.loc[md["amount"] > 0]
        .groupby("month", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "income"})
    )
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

    work = d.sort_values("date", ascending=False).copy().reset_index(drop=True)
    max_rows = st.slider("Rows shown", min_value=50, max_value=1000, value=200, step=50, key="rows_shown")
    work = work.head(max_rows)

    idx = st.selectbox(
        "Select row",
        options=list(range(len(work))),
        format_func=lambda i: f"{work.loc[i, 'date'].date()}  {work.loc[i, 'amount']:,.0f}  {work.loc[i, 'description']}",
        key="row_select",
    )
    row = work.loc[int(idx)]

    existing_categories = sorted([c for c in df["category"].unique().tolist() if c])
    cat_mode = st.radio("Category", options=["existing", "new"], horizontal=True, key="cat_mode")
    if cat_mode == "new":
        cat = st.text_input("New category name", value="", key="new_cat")
    else:
        cat = st.selectbox("Assign category", options=existing_categories, index=0 if existing_categories else 0, key="assign_cat")

    suggest = row.get("merchant", "") or row.get("description", "")
    mode = st.radio("Pattern mode", options=["contains", "exact"], horizontal=True, key="pattern_mode")
    if mode == "exact":
        pattern_default = f"^{re.escape(str(suggest))}$"
    else:
        pattern_default = re.escape(str(suggest))

    pattern = st.text_input("Regex pattern (case-insensitive)", value=pattern_default, key="pattern")

    c_apply, c_note = st.columns([1, 2])
    with c_apply:
        if st.button("Add rule", key="add_rule"):
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

# ---------- Monthly tab (MoneyForward-like) ----------
with tabs[1]:
    st.subheader("Monthly summary")

    md_all = d.assign(month=d["date"].dt.to_period("M").astype(str))
    months = sorted([m for m in md_all["month"].dropna().unique().tolist()])
    if not months:
        st.info("No data in the selected filter range.")
    else:
        default_month = months[-1]
        month = st.selectbox("Month", options=months, index=months.index(default_month), key="month_select")

        mdf = md_all.loc[md_all["month"] == month].copy()
        m_income = mdf.loc[mdf["amount"] > 0, "amount"].sum()
        m_expense = -mdf.loc[mdf["amount"] < 0, "amount"].sum()
        m_net = mdf["amount"].sum()

        # prev month comparison (if exists)
        prev_idx = months.index(month) - 1
        if prev_idx >= 0:
            prev_month = months[prev_idx]
            pdf = md_all.loc[md_all["month"] == prev_month]
            p_income = pdf.loc[pdf["amount"] > 0, "amount"].sum()
            p_expense = -pdf.loc[pdf["amount"] < 0, "amount"].sum()
            p_net = pdf["amount"].sum()
            d_income = m_income - p_income
            d_expense = m_expense - p_expense
            d_net = m_net - p_net
        else:
            prev_month = None
            d_income = d_expense = d_net = None

        c1, c2, c3 = st.columns(3)
        c1.metric("Income", f"{m_income:,.0f}", delta=(f"{d_income:+,.0f}" if d_income is not None else None))
        c2.metric("Expense", f"{m_expense:,.0f}", delta=(f"{d_expense:+,.0f}" if d_expense is not None else None))
        c3.metric("Net", f"{m_net:,.0f}", delta=(f"{d_net:+,.0f}" if d_net is not None else None))

        st.divider()
        mode = st.radio("View", options=["Expense", "Income"], horizontal=True, key="monthly_view")

        if mode == "Expense":
            base = mdf.loc[mdf["amount"] < 0].assign(value=lambda x: -x["amount"])
            value_label = "expense"
        else:
            base = mdf.loc[mdf["amount"] > 0].assign(value=lambda x: x["amount"])
            value_label = "income"

        if base.empty:
            st.info(f"No {mode.lower()} rows for this month.")
        else:
            by_cat = (
                base.groupby("category", as_index=False)["value"]
                .sum()
                .rename(columns={"value": value_label})
                .sort_values(value_label, ascending=False)
            )

            total = float(by_cat[value_label].sum())
            top_n = st.slider("Top categories", 5, 20, 10, 1, key="top_n")

            top = by_cat.head(top_n).copy()
            other_sum = by_cat.iloc[top_n:][value_label].sum()
            if other_sum > 0:
                top = pd.concat(
                    [top, pd.DataFrame([{"category": "Other", value_label: other_sum}])],
                    ignore_index=True,
                )

            top["pct"] = (top[value_label] / total * 100.0).round(2)

            c4, c5 = st.columns(2)
            with c4:
                st.subheader(f"By category ({mode.lower()})")
                fig = px.pie(
                    top,
                    names="category",
                    values=value_label,
                    hole=0.55,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
                st.plotly_chart(fig, use_container_width=True)

            with c5:
                st.subheader("Categories")
                cat_table = top[["category", value_label, "pct"]].copy()
                cat_table["pct"] = cat_table["pct"].map(lambda x: f"{x:.2f}%")
                st.dataframe(cat_table, width="stretch", hide_index=True)

                categories = by_cat["category"].tolist()
                selected_cat = st.selectbox(
                    "Drill down category",
                    options=["(all)"] + categories,
                    index=0,
                    key="drill_category",
                )

            # Merchants + transactions, filtered by selected category
            if selected_cat != "(all)":
                base2 = base.loc[base["category"] == selected_cat]
            else:
                base2 = base

            st.subheader(f"Top merchants ({mode.lower()})")
            by_merch = (
                base2.groupby("merchant", as_index=False)["value"]
                .sum()
                .rename(columns={"value": value_label})
                .sort_values(value_label, ascending=False)
                .head(25)
            )
            st.dataframe(by_merch, width="stretch", hide_index=True)

            st.subheader("Transactions (this month)")
            show = mdf.copy()
            if selected_cat != "(all)":
                show = show.loc[show["category"] == selected_cat]
            st.dataframe(show.sort_values("date", ascending=False), width="stretch", hide_index=True)
