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
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    # Filter out data beyond October 2025 (exclude month 11 and later)
    revenue_df = revenue_df[revenue_df['Ngày'] < pd.Timestamp(2025, 11, 1)]
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


# ----------------------------------------------------------------------
# Utility functions
def format_currency(value: float) -> str:
    """Format a number into a more readable Vietnamese currency string.

    If the absolute value is greater than one million, it will be
    expressed in "triệu" with one decimal place.  Otherwise the
    number is formatted with thousand separators.  A trailing '₫'
    symbol is appended in both cases.

    Parameters
    ----------
    value : float
        The monetary value to format.

    Returns
    -------
    str
        A formatted string representing the currency.
    """
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        formatted = f"{val / 1_000_000:.1f} triệu ₫"
    elif abs_val >= 1_000:
        formatted = f"{val/1_000:.1f} nghìn ₫"
    else:
        formatted = f"{val:.0f} ₫"
    return formatted


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
        # Determine overall date range from the data
        min_date = revenue_df['Ngày'].min().date()
        max_date = revenue_df['Ngày'].max().date()
        # Date range filter with robust handling of single date selection
        st.write("Chọn khoảng thời gian:")
        date_range = st.date_input(
            label="",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Chọn ngày bắt đầu và ngày kết thúc. Nếu chỉ chọn một ngày, app sẽ tự động dùng ngày đó cho cả hai."
        )
        # Normalise the date selection to always have two dates
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            if end_date is None:
                end_date = start_date
        else:
            # If a single date is returned (old streamlit versions)
            start_date = date_range
            end_date = date_range
        # Quick month selection: build list of year-month strings
        month_options = sorted(revenue_df['Ngày'].dt.strftime('%Y-%m').unique())
        quick_month = st.selectbox(
            "Hoặc chọn nhanh theo tháng",
            options=["--"] + month_options,
            index=0
        )
        if quick_month != "--":
            try:
                year, month = map(int, quick_month.split('-'))
                start_date = date(year, month, 1)
                # Compute end date as last day of month
                if month == 12:
                    end_date = date(year, 12, 31)
                else:
                    end_date = date(year, month + 1, 1) - pd.Timedelta(days=1)
            except Exception:
                pass
        # Divider
        st.markdown("---")
        st.caption("Lọc dữ liệu theo ngày hoặc theo tháng.")

    # Main content
    # Display logo at the top of the page
    # Try to locate the logo in the current directory or fallback to /home/oai/share
    possible_logo_paths = [Path('logo.png'), Path('/home/oai/share/logo.png')]
    logo_path = None
    for p in possible_logo_paths:
        if p.exists():
            logo_path = str(p)
            break
    # Display logo centred using columns
    logo_cols = st.columns([1, 2, 1])
    with logo_cols[1]:
        if logo_path:
            st.image(logo_path, width=180)
        else:
            st.write("**Logo không tìm thấy.**")
    # Title and description
    st.title("Bảng điều khiển Kinh doanh Keos")
    st.write(
        "Ứng dụng này trực quan hóa dữ liệu bán hàng và doanh thu của Keos, "
        "giúp bạn hiểu rõ hơn về hiệu quả kinh doanh theo thời gian, theo tháng và theo kênh bán hàng."
    )

    # Filter revenue data by selected date range
    # Use start_date and end_date from the sidebar filter; they are defined there
    # Ensure both dates are of type datetime.date
    mask = (revenue_df['Ngày'].dt.date >= start_date) & (revenue_df['Ngày'].dt.date <= end_date)
    filtered_revenue = revenue_df.loc[mask]

    # Summarise key metrics for the selected range
    total_orders = int(filtered_revenue['Đơn hàng'].sum())
    total_revenue = float(filtered_revenue['Doanh thu'].sum())
    total_net_revenue = float(filtered_revenue['Doanh thu thuần'].sum())
    total_profit = float(filtered_revenue['Tổng lợi nhuận'].sum())
    total_invoices = float(filtered_revenue['Tổng hoá đơn'].sum())
    total_collected = float(filtered_revenue['Đã thu'].sum())
    aov_overall = (total_net_revenue / total_orders) if total_orders > 0 else 0
    percent_collected = (total_collected / total_invoices * 100) if total_invoices > 0 else 0
    # Display KPI summary cards: net revenue, orders, AOV, percentage collected
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Doanh thu thuần", format_currency(total_net_revenue))
    kpi2.metric("Tổng đơn hàng", f"{total_orders:,}")
    kpi3.metric("AOV", format_currency(aov_overall))
    kpi4.metric("% Đã thu", f"{percent_collected:.1f}%")

    # ------------------------------------------------------------------
    # Tabs for detailed analysis
    tab_ngay, tab_thang, tab_kenh, tab_phanphoi = st.tabs([
        "Theo ngày", "Theo tháng", "Theo kênh", "Phân phối"
    ])

    # ---------- Tab 1: Theo ngày ----------
    with tab_ngay:
        st.subheader("Biểu đồ theo ngày")
        # Prepare daily data sorted by date
        daily_df = filtered_revenue.sort_values('Ngày')
        # Line chart – Doanh thu thuần theo ngày
        line_revenue = alt.Chart(daily_df).mark_line(color='#1f77b4').encode(
            x=alt.X('Ngày:T', title='Ngày'),
            y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
            tooltip=['Ngày:T', 'Doanh thu thuần:Q']
        ).properties(height=300)
        st.altair_chart(line_revenue, use_container_width=True)
        # Line chart – Đơn hàng theo ngày
        line_orders = alt.Chart(daily_df).mark_line(color='#ff7f0e').encode(
            x=alt.X('Ngày:T', title='Ngày'),
            y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
            tooltip=['Ngày:T', 'Đơn hàng:Q']
        ).properties(height=300)
        st.altair_chart(line_orders, use_container_width=True)
        # Dual-axis line chart: Đơn hàng & Doanh thu thuần
        if not daily_df.empty:
            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            fig_dual.add_trace(
                go.Scatter(
                    x=daily_df['Ngày'],
                    y=daily_df['Đơn hàng'],
                    name='Đơn hàng',
                    mode='lines',
                    line=dict(color='#ff7f0e')
                ),
                secondary_y=False
            )
            fig_dual.add_trace(
                go.Scatter(
                    x=daily_df['Ngày'],
                    y=daily_df['Doanh thu thuần'],
                    name='Doanh thu thuần',
                    mode='lines',
                    line=dict(color='#1f77b4')
                ),
                secondary_y=True
            )
            fig_dual.update_layout(
                title_text='Đơn hàng & Doanh thu thuần theo ngày',
                legend=dict(orientation='h', x=0.1, y=1.15)
            )
            fig_dual.update_xaxes(title_text='Ngày')
            fig_dual.update_yaxes(title_text='Đơn hàng', secondary_y=False)
            fig_dual.update_yaxes(title_text='Doanh thu thuần (₫)', secondary_y=True)
            st.plotly_chart(fig_dual, use_container_width=True)
        # Line chart – Tổng hoá đơn vs Đã thu
        invoice_long = daily_df[['Ngày', 'Tổng hoá đơn', 'Đã thu']].melt('Ngày', var_name='Loại', value_name='Giá trị')
        line_invoices = alt.Chart(invoice_long).mark_line().encode(
            x=alt.X('Ngày:T', title='Ngày'),
            y=alt.Y('Giá trị:Q', title='Giá trị (₫)'),
            color=alt.Color('Loại:N', title='Loại'),
            tooltip=['Ngày:T', 'Loại:N', 'Giá trị:Q']
        ).properties(height=300)
        st.altair_chart(line_invoices, use_container_width=True)

        # Top 10 days with highest net revenue
        if not daily_df.empty:
            top10 = daily_df.nlargest(10, 'Doanh thu thuần')
            bar_top = alt.Chart(top10).mark_bar(color='#17becf').encode(
                x=alt.X('Ngày:T', title='Ngày', sort=None),
                y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
                tooltip=['Ngày:T', 'Doanh thu thuần:Q', 'Đơn hàng:Q']
            ).properties(height=300, title='Top 10 ngày có doanh thu thuần cao nhất')
            st.altair_chart(bar_top, use_container_width=True)
            # Commentary on notable days
            top_rev_day = top10.iloc[0]
            st.write(
                f"Ngày **{top_rev_day['Ngày'].strftime('%d/%m/%Y')}** có doanh thu thuần cao nhất: "
                f"**{top_rev_day['Doanh thu thuần']:,.0f} ₫** với **{int(top_rev_day['Đơn hàng'])}** đơn hàng."
            )
            # Compute day with highest AOV (for days with non-zero orders)
            daily_df['AOV'] = daily_df.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
            top_aov_day = daily_df.loc[daily_df['AOV'].idxmax()]
            st.write(
                f"Ngày **{top_aov_day['Ngày'].strftime('%d/%m/%Y')}** có giá trị trung bình đơn hàng (AOV) cao nhất: "
                f"**{top_aov_day['AOV']:,.0f} ₫** với {int(top_aov_day['Đơn hàng'])} đơn hàng."
            )

    # ---------- Tab 2: Theo tháng ----------
    with tab_thang:
        st.subheader("Biểu đồ tổng hợp theo tháng")
        # Compute monthly summary within the filtered date range
        month_df = filtered_revenue.copy()
        month_df['Year'] = month_df['Ngày'].dt.year
        month_df['Month'] = month_df['Ngày'].dt.month
        month_summary = month_df.groupby(['Year', 'Month']).agg({
            'Đơn hàng': 'sum',
            'Doanh thu': 'sum',
            'Doanh thu thuần': 'sum',
            'Giảm giá': 'sum',
            'Hoàn trả': 'sum'
        }).reset_index()
        # Map month numbers to names
        month_names_local = {1:'Tháng 1',2:'Tháng 2',3:'Tháng 3',4:'Tháng 4',5:'Tháng 5',6:'Tháng 6',7:'Tháng 7',8:'Tháng 8',9:'Tháng 9',10:'Tháng 10',11:'Tháng 11',12:'Tháng 12'}
        month_summary['Tháng'] = month_summary['Month'].map(month_names_local)
        # Calculate AOV and discount ratio
        month_summary['AOV'] = month_summary.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
        month_summary['Tỷ lệ giảm giá'] = month_summary.apply(lambda row: abs(row['Giảm giá'])/row['Doanh thu']*100 if row['Doanh thu']>0 else 0, axis=1)
        # Charts side by side
        col1, col2, col3 = st.columns(3)
        with col1:
            chart1 = alt.Chart(month_summary).mark_bar().encode(
                x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
                y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
                tooltip=['Tháng:N', 'Doanh thu thuần:Q']
            ).properties(height=300, title='Doanh thu thuần theo tháng')
            st.altair_chart(chart1, use_container_width=True)
        with col2:
            chart2 = alt.Chart(month_summary).mark_bar(color='#ff7f0e').encode(
                x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
                y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
                tooltip=['Tháng:N', 'Đơn hàng:Q']
            ).properties(height=300, title='Đơn hàng theo tháng')
            st.altair_chart(chart2, use_container_width=True)
        with col3:
            chart3 = alt.Chart(month_summary).mark_bar(color='#2ca02c').encode(
                x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
                y=alt.Y('AOV:Q', title='AOV (₫)'),
                tooltip=['Tháng:N', 'AOV:Q']
            ).properties(height=300, title='AOV theo tháng')
            st.altair_chart(chart3, use_container_width=True)
        # Stacked column: Doanh thu & Giảm giá theo tháng
        stacked_df = month_summary[['Tháng', 'Doanh thu', 'Giảm giá']].melt('Tháng', var_name='Loại', value_name='Giá trị')
        stacked_chart = alt.Chart(stacked_df).mark_bar().encode(
            x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
            y=alt.Y('Giá trị:Q', title='Giá trị (₫)'),
            color=alt.Color('Loại:N', scale=alt.Scale(domain=['Doanh thu','Giảm giá'], range=['#1f77b4','#d62728']), title='Loại'),
            tooltip=['Tháng:N', 'Loại:N', 'Giá trị:Q']
        ).properties(height=300, title='Doanh thu & Giảm giá theo tháng')
        st.altair_chart(stacked_chart, use_container_width=True)
        # Line chart for Hoàn trả và Tỷ lệ giảm giá
        line_returns = alt.Chart(month_summary).mark_line(color='#9467bd').encode(
            x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
            y=alt.Y('Hoàn trả:Q', title='Hoàn trả (₫)', axis=alt.Axis(titleColor='#9467bd')),
            tooltip=['Tháng:N', 'Hoàn trả:Q']
        )
        line_discount_ratio = alt.Chart(month_summary).mark_line(color='#8c564b').encode(
            x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
            y=alt.Y('Tỷ lệ giảm giá:Q', title='Tỷ lệ giảm giá (%)', axis=alt.Axis(titleColor='#8c564b')),
            tooltip=['Tháng:N', 'Tỷ lệ giảm giá:Q']
        )
        layered = alt.layer(line_returns, line_discount_ratio).resolve_scale(y='independent').properties(height=300, title='Hoàn trả & Tỷ lệ giảm giá theo tháng')
        st.altair_chart(layered, use_container_width=True)

        # Commentary on monthly trends
        if not month_summary.empty:
            # Highest and lowest revenue months
            max_row = month_summary.loc[month_summary['Doanh thu thuần'].idxmax()]
            min_row = month_summary.loc[month_summary['Doanh thu thuần'].idxmin()]
            st.write(
                f"Tháng có doanh thu thuần cao nhất là **{max_row['Tháng']} {int(max_row['Year'])}** với "
                f"**{max_row['Doanh thu thuần']:,.0f} ₫**. "
                f"Tháng thấp nhất là **{min_row['Tháng']} {int(min_row['Year'])}** ("
                f"**{min_row['Doanh thu thuần']:,.0f} ₫**)."
            )
            # Highest AOV month
            max_aov_row = month_summary.loc[month_summary['AOV'].idxmax()]
            st.write(
                f"AOV cao nhất rơi vào **{max_aov_row['Tháng']} {int(max_aov_row['Year'])}**: "
                f"**{max_aov_row['AOV']:,.0f} ₫**/đơn hàng."
            )
            # Highest discount ratio month
            max_disc_row = month_summary.loc[month_summary['Tỷ lệ giảm giá'].idxmax()]
            st.write(
                f"Tỷ lệ giảm giá lớn nhất xuất hiện ở **{max_disc_row['Tháng']} {int(max_disc_row['Year'])}**: "
                f"**{max_disc_row['Tỷ lệ giảm giá']:.1f}%** doanh thu."
            )

    # ---------- Tab 3: Theo kênh ----------
    with tab_kenh:
        st.subheader("Biểu đồ theo kênh bán hàng")
        # Prepare channel data
        channel_df = sales_df.copy()
        channel_df['AOV'] = channel_df.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
        # Pie/Donut chart – Tỷ trọng Doanh thu thuần theo kênh
        pie_fig = px.pie(
            channel_df,
            names='Kênh bán hàng',
            values='Doanh thu thuần',
            hole=0.4,
            title='Tỷ trọng Doanh thu thuần theo kênh'
        )
        st.plotly_chart(pie_fig, use_container_width=True)
        # Bar charts: Doanh thu thuần, Đơn hàng, AOV, Giảm giá theo kênh
        bar1, bar2, bar3, bar4 = st.columns(4)
        with bar1:
            chart_rev = alt.Chart(channel_df).mark_bar().encode(
                x=alt.X('Kênh bán hàng:N', title='Kênh'),
                y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
                color=alt.Color('Kênh bán hàng:N', legend=None),
                tooltip=['Kênh bán hàng:N', 'Doanh thu thuần:Q']
            ).properties(height=250, title='Doanh thu thuần')
            st.altair_chart(chart_rev, use_container_width=True)
        with bar2:
            chart_orders = alt.Chart(channel_df).mark_bar(color='#ff7f0e').encode(
                x=alt.X('Kênh bán hàng:N', title='Kênh'),
                y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
                tooltip=['Kênh bán hàng:N', 'Đơn hàng:Q']
            ).properties(height=250, title='Đơn hàng')
            st.altair_chart(chart_orders, use_container_width=True)
        with bar3:
            chart_aov = alt.Chart(channel_df).mark_bar(color='#2ca02c').encode(
                x=alt.X('Kênh bán hàng:N', title='Kênh'),
                y=alt.Y('AOV:Q', title='AOV (₫)'),
                tooltip=['Kênh bán hàng:N', 'AOV:Q']
            ).properties(height=250, title='AOV')
            st.altair_chart(chart_aov, use_container_width=True)
        with bar4:
            chart_discount = alt.Chart(channel_df).mark_bar(color='#d62728').encode(
                x=alt.X('Kênh bán hàng:N', title='Kênh'),
                y=alt.Y('Giảm giá:Q', title='Giảm giá (₫)'),
                tooltip=['Kênh bán hàng:N', 'Giảm giá:Q']
            ).properties(height=250, title='Giảm giá')
            st.altair_chart(chart_discount, use_container_width=True)

        # Commentary on channel performance
        if not channel_df.empty:
            # Highest performers by metric
            top_rev = channel_df.loc[channel_df['Doanh thu thuần'].idxmax()]
            top_orders = channel_df.loc[channel_df['Đơn hàng'].idxmax()]
            top_aov = channel_df.loc[channel_df['AOV'].idxmax()]
            top_discount = channel_df.loc[channel_df['Giảm giá'].idxmax()]
            st.write(
                f"Kênh **{top_rev['Kênh bán hàng']}** tạo ra doanh thu thuần cao nhất (**{top_rev['Doanh thu thuần']:,.0f} ₫**), "
                f"trong khi kênh **{top_orders['Kênh bán hàng']}** có số đơn hàng cao nhất (**{int(top_orders['Đơn hàng'])}** đơn). "
                f"AOV cao nhất thuộc về kênh **{top_aov['Kênh bán hàng']}** với **{top_aov['AOV']:,.0f} ₫**/đơn. "
                f"Kênh sử dụng giảm giá nhiều nhất là **{top_discount['Kênh bán hàng']}** (" 
                f"**{top_discount['Giảm giá']:,.0f} ₫** giảm giá)."
            )

    # ---------- Tab 4: Phân phối ----------
    with tab_phanphoi:
        st.subheader("Phân phối dữ liệu")
        # Histogram – Phân phối Doanh thu thuần theo ngày
        hist1 = alt.Chart(filtered_revenue).mark_bar().encode(
            x=alt.X('Doanh thu thuần:Q', bin=alt.Bin(maxbins=30), title='Doanh thu thuần (₫)'),
            y=alt.Y('count():Q', title='Số ngày'),
            tooltip=['count()']
        ).properties(height=300, title='Phân phối Doanh thu thuần')
        # Histogram – Phân phối Đơn hàng theo ngày
        hist2 = alt.Chart(filtered_revenue).mark_bar(color='#ff7f0e').encode(
            x=alt.X('Đơn hàng:Q', bin=alt.Bin(maxbins=30), title='Đơn hàng'),
            y=alt.Y('count():Q', title='Số ngày'),
            tooltip=['count()']
        ).properties(height=300, title='Phân phối Đơn hàng')
        col_hist1, col_hist2 = st.columns(2)
        with col_hist1:
            st.altair_chart(hist1, use_container_width=True)
        with col_hist2:
            st.altair_chart(hist2, use_container_width=True)
        # Scatter plot – Đơn hàng vs Doanh thu thuần
        scatter = alt.Chart(filtered_revenue).mark_circle(opacity=0.6).encode(
            x=alt.X('Đơn hàng:Q', title='Đơn hàng'),
            y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)'),
            tooltip=['Ngày:T', 'Đơn hàng:Q', 'Doanh thu thuần:Q']
        ).properties(height=400, title='Đơn hàng vs Doanh thu thuần')
        st.altair_chart(scatter, use_container_width=True)

        # Commentary on distributions
        if not filtered_revenue.empty:
            median_rev = filtered_revenue['Doanh thu thuần'].median()
            median_orders = filtered_revenue['Đơn hàng'].median()
            st.write(
                f"Phần lớn ngày có doanh thu thuần quanh **{median_rev:,.0f} ₫** và số đơn hàng trung vị khoảng **{int(median_orders)}** đơn. "
                f"Các histogram giúp nhận ra phân bố lệch và các ngày doanh thu/đơn hàng vượt trội hoặc thấp bất thường."
            )




    # Xu hướng theo ngày sẽ được hiển thị trong tab "Theo ngày" bên dưới

    # (Phân tích sâu hơn đã được rút gọn để tập trung vào các biểu đồ chính)

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



if __name__ == "__main__":
    main()