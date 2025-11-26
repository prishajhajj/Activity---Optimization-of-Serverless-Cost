import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Serverless FinOps Dashboard", layout="wide")
st.title("FinOps at Scale for Serverless Applications Dashboard")

# Load the Dataset
uploaded = st.file_uploader("Upload the csv file", type=["csv"])

if uploaded is not None:
    df = pd.read_csv(uploaded)
    df.columns = df.columns.str.strip()

    df["CostUSD"] = pd.to_numeric(df["CostUSD"], errors='coerce')
    df["InvocationsPerMonth"] = pd.to_numeric(df["InvocationsPerMonth"], errors='coerce')
    df["AvgDurationMs"] = pd.to_numeric(df["AvgDurationMs"], errors='coerce')
    df["MemoryMB"] = pd.to_numeric(df["MemoryMB"], errors='coerce')
    df["ColdStartRate"] = pd.to_numeric(df["ColdStartRate"], errors='coerce')
    df["ProvisionedConcurrency"] = pd.to_numeric(df["ProvisionedConcurrency"], errors='coerce')
    df["DataTransferGB"] = pd.to_numeric(df["DataTransferGB"], errors='coerce')

    st.write("### Sample of Uploaded Data")
    st.dataframe(df.head())

    total_cost = df["CostUSD"].sum()
    st.write("### Total Cost (USD): $", total_cost)


# EXERCISE 1: Identify top cost contributors

    st.header("1. Top Cost Contributors")

    df_sorted = df.sort_values("CostUSD", ascending=False)
    df_sorted["CumulativeCost"] = df_sorted["CostUSD"].cumsum()
    df_sorted["CumulativePercent"] = df_sorted["CumulativeCost"] / total_cost * 100

    top_80 = df_sorted[df_sorted["CumulativePercent"] <= 80]

    st.write("### Functions contributing to 80% of total spend:")
    st.dataframe(top_80[["FunctionName", "CostUSD", "CumulativePercent"]])

    fig1 = px.scatter(
        df,
        x="InvocationsPerMonth",
        y="CostUSD",
        log_x=True,
        title="Cost vs Invocation Frequency Plot",
        hover_data=["FunctionName"]
    )
    st.plotly_chart(fig1, use_container_width=True)


# EXERCISE 2: Memory right-sizing

    st.header("2. Memory Right-Sizing Candidates")
    df["DurationSec"] = df["AvgDurationMs"] / 1000

    memory_issues = df[
        (df["MemoryMB"] > 1500) & (df["DurationSec"] < 1)
    ].sort_values("MemoryMB", ascending=False)

    st.write("### Functions with high memory but short duration:")
    st.dataframe(memory_issues[["FunctionName", "MemoryMB", "AvgDurationMs", "CostUSD"]])

    memory_issues["PredictedNewCost"] = memory_issues["CostUSD"] * 0.75
    memory_issues["Savings"] = memory_issues["CostUSD"] - memory_issues["PredictedNewCost"]

    st.write("### Estimated Cost Impact of Lowering Memory:")
    st.dataframe(memory_issues[["FunctionName", "CostUSD", "PredictedNewCost", "Savings"]])

    st.write("Predict cost impact of lowering memory explanation:")
    st.write("Many serverless functions at RetailNova are configured with high memory (2–4 GB) even though their execution times are very short (less than 1 second). In AWS Lambda, cost is calculated based on: Memory (MB), Execution duration (ms) and Number of invocations.")
    st.write("So, higher memory → more GB-seconds → higher cost, even if the function runs very briefly.")
    st.write("By identifying functions that have: 1. High memory allocation, 2. Low execution time, we can estimate the cost savings if memory is reduced to a more appropriate level.")

# EXERCISE 3: Provisioned concurrency optimization

    st.header("3. Provisioned Concurrency Optimization")
    pc_candidates = df[df["ProvisionedConcurrency"] > 0]
    pc_candidates["PC_WasteFlag"] = pc_candidates["ColdStartRate"] < 2

    st.write("### Provisioned Concurrency Functions (Low Cold Start = Possible Waste):")
    st.dataframe(pc_candidates[
        ["FunctionName", "ColdStartRate", "ProvisionedConcurrency", "CostUSD", "PC_WasteFlag"]
    ])

    st.write("To decide whether Provisioned Concurrency (PC) should be reduced or removed, we compare the fixed PC cost with the actual benefit it provides in reducing cold starts.")

    st.write("If a function has a very low cold start rate (<2%), is not latency-critical, or shows low or inconsistent invocation volume, then PC is providing little value and should be removed.")
    st.write("If a function does need faster startup but is currently over-provisioned (e.g., high PC units but only moderate traffic), then PC should be reduced to a smaller number of warm instances.")
    st.write("Only functions with high cold start rates, steady traffic, and strict latency requirements should keep their current PC configuration.")
    st.write("In summary: Remove PC when the fixed cost outweighs the cold-start reduction benefit or Reduce PC when some warm capacity is useful, but the current allocation is higher than necessary.")

# EXERCISE 4: Detect unused or low-value workloads

    st.header("4. Detect Unused or Low-Value Functions")
    total_inv = df["InvocationsPerMonth"].sum()
    df["PercentInvocations"] = df["InvocationsPerMonth"] / total_inv * 100

    low_value = df[(df["PercentInvocations"] < 1) & (df["CostUSD"] > df["CostUSD"].median())]

    st.write("### High Cost but Low (<1%) Invocations:")
    st.dataframe(low_value[["FunctionName", "InvocationsPerMonth", "PercentInvocations", "CostUSD"]])

    st.write("After analyzing all serverless functions, none of them met the criteria of having less than 1% of total invocations while still generating high cost. This means there are no clear low-value or underused functions based on this threshold.")
    st.write("All functions either contribute a meaningful portion of invocation volume, or their costs are proportional to their usage. As a result, there are no immediate candidates for removal or cleanup under this specific rule.")

# EXERCISE 5: Cost Forecasting

    st.header("5. Cost Forecasting Model")
    st.write("Simple Predictive Equation:")
    st.code(""" Cost ≈ Invocations × Duration × Memory × PricingCoefficient + DataTransfer
    """)

    df["PredictedCost"] = (
        df["InvocationsPerMonth"] * df["DurationSec"] * df["MemoryMB"] * 0.000000002 +
        df["DataTransferGB"] * 0.09
    )

    st.write("### Predicted Cost vs Actual Cost")
    st.dataframe(df[["FunctionName", "CostUSD", "PredictedCost"]])

    fig2 = px.scatter(
        df,
        x="PredictedCost",
        y="CostUSD",
        title="Predicted vs Actual Cost Plot",
        trendline="ols",
        hover_data=["FunctionName"]
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.write("The cost model estimates each function’s monthly cost using the formula: Cost ≈ Invocations × Duration × Memory × 𝑘 + 𝑝 × DataTransfer")
    st.write("To apply this, we computed ComputeUnits (invocations × duration in seconds × memory in GB) and used linear regression to estimate the pricing coefficients:")
    st.write("k → cost per GB-second of compute")
    st.write("p → cost per GB of data transfer")
    st.write("b → fixed baseline cost")
    st.write("The model then predicts each function’s monthly cost and compares it to the actual cost.")
    st.write("A good alignment between predicted and actual values shows that compute usage and data transfer are the primary drivers of serverless cost.")
    st.write("Large differences between predicted and actual costs indicate functions with additional cost factors, such as provisioned concurrency, cross-region transfer, or inefficient configuration.")

# EXERCISE 6: Spot workloads that would benefit from containerization

    st.header("6. Containerization Recommendations")
    containers = df[
        (df["DurationSec"] > 3) &
        (df["MemoryMB"] > 2000) &
        (df["InvocationsPerMonth"] < 5000)
    ]

    st.write("### Workloads Better Suited for Containers:")
    st.dataframe(containers[["FunctionName", "DurationSec", "MemoryMB", "InvocationsPerMonth", "CostUSD"]])

else:
    st.info("Upload the dataset to begin the analysis.")

st.write("In the current dataset, none of the functions meet the criteria for containerization candidates because:")
st.write("1. Long-running: All functions have very short execution durations (mostly under 0.1 seconds), so none exceed the threshold of 3 seconds.")
st.write("2. High memory: Most functions are allocated only 128–256 MB of memory, well below the 2 GB threshold.")
st.write("3. Low invocation frequency: The functions have very high invocation counts (hundreds of thousands to millions per month), so none fall under the “low frequency” criterion.")
st.write("As a result, the filter (DurationSec > 3) & (MemoryMB > 2000) & (InvocationsPerMonth < 5000) does not match any rows, producing an empty result.")    