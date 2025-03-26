import requests
import pandas as pd
from urllib.parse import urljoin
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def fetch_debt_data(start="1990-01-01", end="2025-12-31"):
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
    params = {"filter": f"record_date:gte:{start},record_date:lte:{end}", "format": "json", "page[size]": 10000}
    data = []
    next_url = url
    while next_url:
        r = requests.get(next_url, params=params if next_url == url else None)
        r.raise_for_status()
        j = r.json()
        data.extend(j["data"])
        params = None
        next_link = j.get("links", {}).get("next")
        next_url = url + next_link if next_link and next_link.startswith("?") else next_link
    df = pd.DataFrame(data)
    df["record_date"] = pd.to_datetime(df["record_date"])
    df["debt"] = pd.to_numeric(df["tot_pub_debt_out_amt"])
    df["year"] = df["record_date"].dt.year
    return df.sort_values("record_date").groupby("year").tail(1)

def calculate_debt_metrics(df):
    administrations = [
        {"president": "Clinton (1st Term)", "start_year": 1993, "end_year": 1996, "party": "Democrat"},
        {"president": "Clinton (2nd Term)", "start_year": 1997, "end_year": 2000, "party": "Democrat"},
        {"president": "Bush (1st Term)", "start_year": 2001, "end_year": 2004, "party": "Republican"},
        {"president": "Bush (2nd Term)", "start_year": 2005, "end_year": 2008, "party": "Republican"},
        {"president": "Obama (1st Term)", "start_year": 2009, "end_year": 2012, "party": "Democrat"},
        {"president": "Obama (2nd Term)", "start_year": 2013, "end_year": 2016, "party": "Democrat"},
        {"president": "Trump (1st Term)", "start_year": 2017, "end_year": 2020, "party": "Republican"},
        {"president": "Biden", "start_year": 2021, "end_year": 2024, "party": "Democrat"},
        {"president": "Trump (2nd Term)", "start_year": 2025, "end_year": 2028, "party": "Republican"}
    ]

    def assign_admin(year):
        for a in administrations:
            if a["start_year"] <= year <= a["end_year"]:
                return pd.Series([a["president"], a["party"]])
        return pd.Series(["Unknown", "Unknown"])

    df[["administration", "party"]] = df["year"].apply(assign_admin)
    df["slope"] = df["debt"].diff() / df["year"].diff()
    df["percent_change"] = df["debt"].pct_change() * 100

    summary = df.groupby(["administration", "party"]).agg(
        avg_slope=("slope", "mean"),
        avg_percent_change=("percent_change", "mean"),
        avg_debt=("debt", "mean")
    ).reset_index()

    start_year_map = {a["president"]: a["start_year"] for a in administrations}
    summary["start_year"] = summary["administration"].map(start_year_map)
    summary = summary.sort_values("start_year").reset_index(drop=True)

    color_list, pattern_list = [], []
    for _, row in summary.iterrows():
        if row["administration"] == "Trump (2nd Term)":
            color_list.append("red")
            pattern_list.append("/")
        elif row["party"] == "Republican":
            color_list.append("red")
            pattern_list.append("")
        elif row["party"] == "Democrat":
            color_list.append("blue")
            pattern_list.append("")
        else:
            color_list.append("gray")
            pattern_list.append("")
    return df, summary, color_list, pattern_list

def plot_debt_dashboard(df, summary, color_list, pattern_list):
    events = [
        {"year": 2001, "event": "Dot-com Bust"},
        {"year": 2008, "event": "Great Recession"},
        {"year": 2011, "event": "Debt Ceiling Crisis"},
        {"year": 2020, "event": "COVID-19"},
    ]

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Average Debt (USD)", "Average Slope (Δ Debt)", 
                                        "Average Percent Change (%)", "National Debt by Year"))

    fig.add_trace(go.Bar(x=summary["administration"], y=summary["avg_debt"],
                         marker=dict(color=color_list, pattern=dict(shape=pattern_list)),
                         name="Average Debt (USD)"), row=1, col=1)

    fig.add_trace(go.Scatter(x=summary["administration"], y=summary["avg_slope"],
                             mode="lines+markers", name="Average Slope (Δ Debt)"), row=2, col=1)

    fig.add_trace(go.Scatter(x=summary["administration"], y=summary["avg_percent_change"],
                             mode="lines+markers", name="Average Percent Change (%)"), row=3, col=1)

    fig.add_trace(go.Scatter(x=df["year"], y=df["debt"], mode="lines+markers",
                             name="National Debt by Year"), row=4, col=1)

    for e in events:
        fig.add_vline(x=e["year"], line_dash="dot", line_color="gray", row=4, col=1)
        fig.add_annotation(x=e["year"], y=df["debt"].max() * 1.05, text=e["event"], 
                           showarrow=False, textangle=-90, font=dict(size=10, color="gray"), 
                           xanchor="left", row=4, col=1)

    fig.update_layout(title_text="",
                      height=1000, width=1000, showlegend=True,
                      xaxis4=dict(title="Year", tickangle=45, tickfont=dict(size=10)),
                      hovermode="x unified")
    fig.show()
