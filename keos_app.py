"""
Keos sales dashboard
====================

This Streamlit application visualises the sales and revenue data for
Keos by reading two Excel files provided by the user.  It allows
interactive exploration of revenue, orders, discounts and profits over
time and across sales channels.  The layout and styling are inspired
by modern business dashboards with a clean sidebar for filters and
colourful charts rendered via Altair and Plotly.  The app is
internationalised for Vietnamese labels and uses the official Keos
logo at the top of the page.

How to run
----------

From your terminal run:

```
streamlit run keos_app.py
```

Make sure that `Kenhbanhang.xlsx`, `Doanhthu.xlsx` and
`logo.png` are in the same directory as this script.  The app will
load these files automatically and cache the results for faster
interaction.  If you update the underlying data, simply restart the
app.
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
from datetime import datetime, date
from functools import lru_cache
from pathlib import Path


def load_data():
    """Load sales and revenue data from Excel files.

    The function looks for the expected files in the current
    working directory.  If they are not present it also looks in
    the `/home/oai/share` folder which is used when running the app
    in this assignment environment.  This makes the script more
    robust when deployed elsewhere, because the user may run it
    from a directory different to the data location.

    Returns
    -------
    sales_df : pandas.DataFrame
        Aggregated sales metrics by sales channel (Kênh bán hàng).
    revenue_df : pandas.DataFrame
        Daily revenue metrics for the business.
    """
    import os
    from pathlib import Path

    # Define possible locations for the data files
    possible_dirs = [Path('.'), Path('/home/oai/share')]
    sales_filename = 'Kenhbanhang.xlsx'
    revenue_filename = 'Doanhthu.xlsx'

    # Find the first directory that contains both files
    sales_path = None
    revenue_path = None
    for d in possible_dirs:
        if (d / sales_filename).exists() and (d / revenue_filename).exists():
            sales_path = d / sales_filename
            revenue_path = d / revenue_filename
            break
    if sales_path is None or revenue_path is None:
        raise FileNotFoundError(
            f"Không tìm thấy các file dữ liệu {sales_filename} và {revenue_filename}. "
            "Hãy chắc chắn rằng các file nằm cùng thư mục với script hoặc trong /home/oai/share."
        )
    # Read the Excel files
    sales_df = pd.read_excel(sales_path)
    revenue_df = pd.read_excel(revenue_path)
    # Parse the date column in the revenue data
    revenue_df['Ngày'] = pd.to_datetime(revenue_df['Ngày'], dayfirst=True)
    return sales_df, revenue_df


@st.cache_data
def get_data():
    """Cache the loaded data for improved performance."""
    return load_data()


def preprocess_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare the revenue dataframe for analysis.

    Adds additional computed columns such as profit margin (%) and
    converts numeric fields to floats for plotting.

    Parameters
    ----------
    df : pandas.DataFrame
        Raw revenue dataframe.

    Returns
    -------
    pandas.DataFrame
        Processed dataframe.
    """
    processed = df.copy()
    # Compute profit margin as (total profit / net revenue)
    processed['Profit margin (%)'] = processed.apply(
        lambda row: (row['Tổng lợi nhuận'] / row['Doanh thu thuần'] * 100) if row['Doanh thu thuần'] != 0 else 0,
        axis=1
    )
    # Convert columns to numeric if not already
    numeric_cols = [
        'Đơn hàng', 'Doanh thu', 'Giảm giá', 'Doanh thu thuần',
        'Vận chuyển', 'Giảm giá vận chuyển', 'Tổng hoá đơn', 'Đã thu',
        'Hoàn trả', 'Tổng giá vốn', 'Tổng lợi nhuận', '% lợi nhuận'
    ]
    for col in numeric_cols:
        processed[col] = pd.to_numeric(processed[col], errors='coerce')
    return processed


def main():
    # Basic page configuration
    st.set_page_config(
        page_title="Keos Business Dashboard",
        page_icon="🛍️",
        layout="wide",
    )

    # Load data
    sales_df, revenue_df_raw = get_data()
    revenue_df = preprocess_revenue(revenue_df_raw)

    # Sidebar — filters and options
    with st.sidebar:
        st.header("Bộ lọc")
        # Date range filter
        min_date = revenue_df['Ngày'].min().date()
        max_date = revenue_df['Ngày'].max().date()
        default_start = min_date
        default_end = max_date
        date_range = st.date_input(
            "Chọn khoảng thời gian",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date
        )
        # Metric selection for time series plot
        metric_options = {
            'Doanh thu': 'Doanh thu',
            'Doanh thu thuần': 'Doanh thu thuần',
            'Tổng lợi nhuận': 'Tổng lợi nhuận',
            'Đơn hàng': 'Đơn hàng'
        }
        selected_metric_label = st.selectbox(
            "Chọn chỉ số biểu diễn theo ngày",
            options=list(metric_options.keys()),
            index=0
        )
        selected_metric = metric_options[selected_metric_label]
        # Chart type selection for the time series
        chart_type = st.radio(
            "Kiểu biểu đồ thời gian",
            options=["Đường", "Cột"]
        )
        st.markdown("---")
        st.caption("Chọn các chỉ số và khoảng thời gian để hiển thị các biểu đồ phù hợp.")

    # Main content
    # Display logo at the top of the page
    # Try to locate the logo in the current directory or fallback to /home/oai/share
    possible_logo_paths = [Path('logo.png'), Path('/home/oai/share/logo.png')]
    logo_path = None
    for p in possible_logo_paths:
        if p.exists():
            logo_path = str(p)
            break
    if logo_path:
        st.image(logo_path, width=200)
    else:
        st.write("**Logo không tìm thấy.**")
    st.title("Bảng điều khiển Kinh doanh Keos")
    st.write(
        "Ứng dụng này trực quan hóa dữ liệu bán hàng và doanh thu của Keos, "
        "giúp bạn hiểu rõ hơn về hiệu quả kinh doanh theo thời gian và theo kênh bán hàng."
    )

    # Filter revenue data by selected date range
    start_date, end_date = date_range
    mask = (revenue_df['Ngày'].dt.date >= start_date) & (revenue_df['Ngày'].dt.date <= end_date)
    filtered_revenue = revenue_df.loc[mask]

    # Summarise key metrics for the selected range
    total_orders = int(filtered_revenue['Đơn hàng'].sum())
    total_revenue = float(filtered_revenue['Doanh thu'].sum())
    total_net_revenue = float(filtered_revenue['Doanh thu thuần'].sum())
    total_profit = float(filtered_revenue['Tổng lợi nhuận'].sum())
    average_profit_margin = (
        filtered_revenue['Tổng lợi nhuận'].sum() / filtered_revenue['Doanh thu thuần'].sum() * 100
        if filtered_revenue['Doanh thu thuần'].sum() > 0 else 0
    )

    # Display KPI summary cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Tổng đơn hàng", f"{total_orders:,}")
    kpi2.metric("Tổng doanh thu", f"{total_revenue:,.0f} ₫")
    kpi3.metric("Doanh thu thuần", f"{total_net_revenue:,.0f} ₫")
    kpi4.metric("Tổng lợi nhuận", f"{total_profit:,.0f} ₫", f"{average_profit_margin:.1f}%")

    st.markdown("## Tổng quan theo kênh bán hàng")
    # Bar chart for aggregated sales by channel
    channel_chart = alt.Chart(sales_df).transform_fold(
        ['Đơn hàng', 'Doanh thu', 'Doanh thu thuần', 'Tổng lợi nhuận'],
        as_=['Chỉ số', 'Giá trị']
    ).encode(
        x=alt.X('Kênh bán hàng:N', title='Kênh bán hàng'),
        y=alt.Y('Giá trị:Q', title='Giá trị (₫)', stack=None),
        color='Chỉ số:N',
        column=alt.Column('Chỉ số:N', title='')
    ).mark_bar().properties(
        width=120,
        height=300
    )
    st.altair_chart(channel_chart, use_container_width=True)

    st.markdown("## Xu hướng theo thời gian")
    # Create time series chart for the selected metric
    chart_data = filtered_revenue[['Ngày', selected_metric]].rename(columns={selected_metric: 'Giá trị'})
    chart_data = chart_data.sort_values('Ngày')
    if chart_type == "Đường":
        # Line chart using altair
        line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X('Ngày:T', title='Ngày'),
            y=alt.Y('Giá trị:Q', title=selected_metric_label),
            tooltip=['Ngày:T', 'Giá trị:Q']
        ).interactive().properties(height=400)
        st.altair_chart(line_chart, use_container_width=True)
    else:
        # Column/bar chart using altair
        bar_chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Ngày:T', title='Ngày'),
            y=alt.Y('Giá trị:Q', title=selected_metric_label),
            tooltip=['Ngày:T', 'Giá trị:Q']
        ).interactive().properties(height=400)
        st.altair_chart(bar_chart, use_container_width=True)

    st.markdown("## Phân tích sâu hơn")
    # Correlation scatter plot: Orders vs Revenue
    scatter_fig = px.scatter(
        filtered_revenue,
        x='Đơn hàng',
        y='Doanh thu thuần',
        size='Tổng lợi nhuận',
        color='Profit margin (%)',
        hover_data=['Ngày'],
        title='Mối quan hệ giữa số đơn hàng và doanh thu thuần',
        labels={'Đơn hàng': 'Số đơn hàng', 'Doanh thu thuần': 'Doanh thu thuần (₫)', 'Profit margin (%)': 'Biên lợi nhuận (%)'}
    )
    st.plotly_chart(scatter_fig, use_container_width=True)

    st.markdown("### Dữ liệu chi tiết")
    # Show the filtered data in a table with some styling
    styled_df = filtered_revenue[['Ngày', 'Đơn hàng', 'Doanh thu', 'Giảm giá', 'Doanh thu thuần', 'Tổng lợi nhuận', 'Profit margin (%)']].copy()
    styled_df['Ngày'] = styled_df['Ngày'].dt.strftime('%d/%m/%Y')
    st.dataframe(styled_df.style.format({
        'Đơn hàng': '{:,.0f}',
        'Doanh thu': '{:,.0f} ₫',
        'Giảm giá': '{:,.0f} ₫',
        'Doanh thu thuần': '{:,.0f} ₫',
        'Tổng lợi nhuận': '{:,.0f} ₫',
        'Profit margin (%)': '{:.1f}%'
    }))

    st.markdown("#### Tải xuống dữ liệu")
    # Provide a download button for the filtered data
    csv_data = filtered_revenue.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="Tải dữ liệu CSV",
        data=csv_data,
        file_name=f"Keos_Doanhthu_{start_date}_den_{end_date}.csv",
        mime="text/csv"
    )

    # ------------------------------------------------------------------
    # Monthly analysis section
    # Aggregate data by month and year to allow comparison across months
    st.markdown("## Doanh thu theo tháng")
    # Create month and year columns
    monthly_df = revenue_df.copy()
    monthly_df['Year'] = monthly_df['Ngày'].dt.year
    monthly_df['Month'] = monthly_df['Ngày'].dt.month
    # Aggregate metrics per month/year
    monthly_summary = monthly_df.groupby(['Year', 'Month']).agg({
        'Đơn hàng': 'sum',
        'Doanh thu': 'sum',
        'Doanh thu thuần': 'sum',
        'Tổng lợi nhuận': 'sum'
    }).reset_index()
    # Map month numbers to names in Vietnamese
    month_names = {
        1: 'Tháng 1', 2: 'Tháng 2', 3: 'Tháng 3', 4: 'Tháng 4',
        5: 'Tháng 5', 6: 'Tháng 6', 7: 'Tháng 7', 8: 'Tháng 8',
        9: 'Tháng 9', 10: 'Tháng 10', 11: 'Tháng 11', 12: 'Tháng 12'
    }
    monthly_summary['MonthName'] = monthly_summary['Month'].map(month_names)
    # Sort by Year and Month for consistent ordering
    monthly_summary = monthly_summary.sort_values(['Year', 'Month'])
    # Allow users to select which months to display
    available_months = monthly_summary['MonthName'].unique().tolist()
    selected_months = st.multiselect(
        "Chọn tháng để so sánh",
        options=available_months,
        default=available_months
    )
    # Filter data based on selected months
    comparison_df = monthly_summary[monthly_summary['MonthName'].isin(selected_months)].copy()
    # Build the comparison bar chart (grouped by year, colored by month)
    monthly_chart = alt.Chart(comparison_df).mark_bar().encode(
        x=alt.X('Year:N', title='Năm'),
        y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
        color=alt.Color('MonthName:N', title='Tháng'),
        tooltip=['Year:N', 'MonthName:N', 'Doanh thu thuần:Q']
    ).properties(height=400)
    st.altair_chart(monthly_chart, use_container_width=True)
    # Story telling / narrative insight
    # Identify the month with the highest and lowest revenue
    if not monthly_summary.empty:
        highest = monthly_summary.loc[monthly_summary['Doanh thu thuần'].idxmax()]
        lowest = monthly_summary.loc[monthly_summary['Doanh thu thuần'].idxmin()]
        st.markdown("### Đánh giá xu hướng")
        st.write(
            f"Trong toàn bộ dữ liệu, **{month_names[int(highest['Month'])]} {int(highest['Year'])}** "
            f"đạt doanh thu thuần cao nhất với khoảng **{highest['Doanh thu thuần']:,.0f} ₫**. "
            f"Ngược lại, **{month_names[int(lowest['Month'])]} {int(lowest['Year'])}** "
            f"có doanh thu thuần thấp nhất với **{lowest['Doanh thu thuần']:,.0f} ₫**."
        )
        # Compute month-on-month change for each year
        monthly_summary['Prev_Revenue'] = monthly_summary.groupby('Year')['Doanh thu thuần'].shift(1)
        monthly_summary['MoM_Change'] = (monthly_summary['Doanh thu thuần'] - monthly_summary['Prev_Revenue']) / monthly_summary['Prev_Revenue'] * 100
        # Remove rows where previous revenue is NaN
        changes = monthly_summary.dropna(subset=['MoM_Change'])
        if not changes.empty:
            increase_month = changes.loc[changes['MoM_Change'].idxmax()]
            decrease_month = changes.loc[changes['MoM_Change'].idxmin()]
            inc_mom = increase_month['MoM_Change']
            dec_mom = decrease_month['MoM_Change']
            st.write(
                f"Tăng trưởng doanh thu thuần mạnh nhất diễn ra từ **{month_names[int(increase_month['Month']-1)] if increase_month['Month']>1 else month_names[12]}"
                f" đến {month_names[int(increase_month['Month'])]} {int(increase_month['Year'])}**, tăng khoảng **{inc_mom:.1f}%** so với tháng trước. "
                f"Ngược lại, mức sụt giảm lớn nhất là từ **{month_names[int(decrease_month['Month']-1)] if decrease_month['Month']>1 else month_names[12]}"
                f" đến {month_names[int(decrease_month['Month'])]} {int(decrease_month['Year'])}**, giảm **{abs(dec_mom):.1f}%** so với tháng trước."
            )
    st.markdown("---")


if __name__ == "__main__":
    main()