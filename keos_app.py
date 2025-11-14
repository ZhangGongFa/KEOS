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
    """
    Chức năng chính của ứng dụng Streamlit.  Hàm này thiết lập bố cục trang,
    tải dữ liệu, xử lý các bộ lọc và trực quan hóa doanh thu bán hàng của Keos.
    Ngoài các biểu đồ gốc, hàm cũng bổ sung các tiện ích nâng cao như KPI
    theo năm, so sánh tháng/quý, bộ lọc kênh bán hàng và phần kết luận
    kèm gợi ý hành động.
    """
    # Cấu hình cơ bản cho trang
    st.set_page_config(
        page_title="Keos Business Dashboard",
        page_icon="🛍️",
        layout="wide",
    )

    # Tải dữ liệu
    sales_df, revenue_df_raw = get_data()
    revenue_df = preprocess_revenue(revenue_df_raw)

    # Sidebar — bộ lọc và lựa chọn
    with st.sidebar:
        st.header("Bộ lọc")
        # Phạm vi ngày tổng quát từ dữ liệu
        min_date = revenue_df['Ngày'].min().date()
        max_date = revenue_df['Ngày'].max().date()
        # Bộ lọc ngày: chọn khoảng thời gian
        st.write("Chọn khoảng thời gian:")
        date_range = st.date_input(
            label="",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Chọn ngày bắt đầu và ngày kết thúc. Nếu chỉ chọn một ngày, app sẽ tự động dùng ngày đó cho cả hai."
        )
        # Chuẩn hoá lựa chọn ngày để luôn có hai giá trị
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            if end_date is None:
                end_date = start_date
        else:
            # Trường hợp Streamlit cũ chỉ trả về một giá trị
            start_date = date_range
            end_date = date_range
        # Lựa chọn nhanh theo tháng
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
                # Ngày cuối cùng của tháng
                if month == 12:
                    end_date = date(year, 12, 31)
                else:
                    end_date = date(year, month + 1, 1) - pd.Timedelta(days=1)
            except Exception:
                pass
        # Phân cách
        st.markdown("---")
        st.caption("Lọc dữ liệu theo ngày hoặc theo tháng.")

    # Nội dung chính
    # Hiển thị logo ở đầu trang
    possible_logo_paths = [Path('logo.png'), Path('/home/oai/share/logo.png')]
    logo_path = None
    for p in possible_logo_paths:
        if p.exists():
            logo_path = str(p)
            break
    logo_cols = st.columns([1, 2, 1])
    with logo_cols[1]:
        if logo_path:
            st.image(logo_path, width=180)
        else:
            st.write("**Logo không tìm thấy.**")
    # Tiêu đề và mô tả
    st.title("Bảng điều khiển Kinh doanh Keos")
    st.write(
        "Ứng dụng này trực quan hóa dữ liệu bán hàng và doanh thu của Keos, "
        "giúp bạn hiểu rõ hơn về hiệu quả kinh doanh theo thời gian, theo tháng và theo kênh bán hàng."
    )

    # Lọc dữ liệu doanh thu theo phạm vi thời gian được chọn
    mask = (revenue_df['Ngày'].dt.date >= start_date) & (revenue_df['Ngày'].dt.date <= end_date)
    filtered_revenue = revenue_df.loc[mask]

    # ==================================================================
    # Phần 1: KPI nâng cao
    # Tính toán KPI tổng hợp cho năm hiện tại và so sánh với cùng kỳ năm trước
    current_year = revenue_df['Ngày'].dt.year.max()
    # Xác định ngày cuối cùng trong dữ liệu năm hiện tại để áp dụng YTD
    ytd_end_date = revenue_df[revenue_df['Ngày'].dt.year == current_year]['Ngày'].max().date()
    # Dữ liệu YTD năm hiện tại
    ytd_current = revenue_df[(revenue_df['Ngày'].dt.year == current_year) & (revenue_df['Ngày'].dt.date <= ytd_end_date)]
    # Dữ liệu cùng kỳ năm trước (nếu tồn tại)
    ytd_prev = revenue_df[(revenue_df['Ngày'].dt.year == (current_year - 1)) & (revenue_df['Ngày'].dt.month <= ytd_end_date.month) & (revenue_df['Ngày'].dt.day <= ytd_end_date.day)]
    # Tính toán các chỉ số
    def summarise_kpi(df_kpi: pd.DataFrame):
        total_orders = df_kpi['Đơn hàng'].sum()
        total_rev = df_kpi['Doanh thu thuần'].sum()
        total_profit = df_kpi['Tổng lợi nhuận'].sum()
        total_net_rev = total_rev  # đã là doanh thu thuần
        total_returns = df_kpi['Hoàn trả'].sum()
        aov = total_rev / total_orders if total_orders > 0 else 0
        profit_margin = (total_profit / total_rev * 100) if total_rev > 0 else 0
        return_rate = (total_returns / total_rev * 100) if total_rev > 0 else 0
        return {
            'orders': total_orders,
            'revenue': total_rev,
            'profit': total_profit,
            'profit_margin': profit_margin,
            'aov': aov,
            'return_rate': return_rate
        }
    kpi_current = summarise_kpi(ytd_current)
    kpi_prev = summarise_kpi(ytd_prev) if not ytd_prev.empty else {k: 0 for k in ['orders','revenue','profit','profit_margin','aov','return_rate']}
    # Tính delta
    def compute_delta(curr, prev):
        if prev == 0:
            return curr, None  # Không thể so sánh
        diff = curr - prev
        percent = diff / prev * 100
        return diff, percent
    # Hiển thị KPI nâng cao
    st.markdown("## 📌 Chỉ số tổng quan (YTD)")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    # Doanh thu
    diff_rev, pct_rev = compute_delta(kpi_current['revenue'], kpi_prev['revenue'])
    k1.metric(
        "Doanh thu thuần", 
        format_currency(kpi_current['revenue']),
        f"{diff_rev:,.0f} ₫ ({pct_rev:.1f}% )" if pct_rev is not None else "–"
    )
    # Đơn hàng
    diff_orders, pct_orders = compute_delta(kpi_current['orders'], kpi_prev['orders'])
    k2.metric(
        "Tổng đơn hàng", 
        f"{int(kpi_current['orders']):,}",
        f"{diff_orders:,.0f} ({pct_orders:.1f}% )" if pct_orders is not None else "–"
    )
    # Lợi nhuận gộp
    diff_profit, pct_profit = compute_delta(kpi_current['profit'], kpi_prev['profit'])
    k3.metric(
        "Lợi nhuận gộp", 
        format_currency(kpi_current['profit']),
        f"{diff_profit:,.0f} ₫ ({pct_profit:.1f}% )" if pct_profit is not None else "–"
    )
    # Biên lợi nhuận
    diff_pm, pct_pm = compute_delta(kpi_current['profit_margin'], kpi_prev['profit_margin'])
    k4.metric(
        "Biên lợi nhuận", 
        f"{kpi_current['profit_margin']:.1f}%", 
        f"{diff_pm:.1f}% ({pct_pm:.1f}% )" if pct_pm is not None else "–"
    )
    # AOV
    diff_aov, pct_aov = compute_delta(kpi_current['aov'], kpi_prev['aov'])
    k5.metric(
        "AOV", 
        format_currency(kpi_current['aov']),
        f"{diff_aov:,.0f} ₫ ({pct_aov:.1f}% )" if pct_aov is not None else "–"
    )
    # Tỷ lệ hoàn trả
    diff_rr, pct_rr = compute_delta(kpi_current['return_rate'], kpi_prev['return_rate'])
    k6.metric(
        "Tỷ lệ hoàn trả", 
        f"{kpi_current['return_rate']:.1f}%",
        f"{diff_rr:.1f}% ({pct_rr:.1f}% )" if pct_rr is not None else "–"
    )

    # ------------------------------------------------------------------
    # Phần 2: Xu hướng theo ngày
    st.markdown("## 📅 Xu hướng theo ngày")
    # Dữ liệu hàng ngày sắp xếp theo thời gian
    daily_df = filtered_revenue.sort_values('Ngày')
    # Biểu đồ đường cho Doanh thu thuần theo ngày
    line_revenue = alt.Chart(daily_df).mark_line(color='#1f77b4').encode(
        x=alt.X('Ngày:T', title='Ngày'),
        y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
        tooltip=['Ngày:T', 'Doanh thu thuần:Q']
    ).properties(height=300)
    st.altair_chart(line_revenue, use_container_width=True)
    # Biểu đồ đường cho Đơn hàng theo ngày
    line_orders = alt.Chart(daily_df).mark_line(color='#ff7f0e').encode(
        x=alt.X('Ngày:T', title='Ngày'),
        y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
        tooltip=['Ngày:T', 'Đơn hàng:Q']
    ).properties(height=300)
    st.altair_chart(line_orders, use_container_width=True)
    # Biểu đồ 2 trục: Đơn hàng & Doanh thu thuần theo ngày
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
    # Biểu đồ đường cho Tổng hoá đơn và Đã thu
    invoice_long = daily_df[['Ngày', 'Tổng hoá đơn', 'Đã thu']].melt('Ngày', var_name='Loại', value_name='Giá trị')
    line_invoices = alt.Chart(invoice_long).mark_line().encode(
        x=alt.X('Ngày:T', title='Ngày'),
        y=alt.Y('Giá trị:Q', title='Giá trị (₫)', axis=alt.Axis(format=',.0f')),
        color=alt.Color('Loại:N', title='Loại'),
        tooltip=['Ngày:T', 'Loại:N', 'Giá trị:Q']
    ).properties(height=300)
    st.altair_chart(line_invoices, use_container_width=True)
    # Top 10 ngày doanh thu cao nhất và chú thích
    if not daily_df.empty:
        top10 = daily_df.nlargest(10, 'Doanh thu thuần')
        bar_top = alt.Chart(top10).mark_bar(color='#17becf').encode(
            x=alt.X('Ngày:T', title='Ngày', sort=None),
            y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
            tooltip=['Ngày:T', 'Doanh thu thuần:Q', 'Đơn hàng:Q']
        ).properties(height=300, title='Top 10 ngày có doanh thu thuần cao nhất')
        st.altair_chart(bar_top, use_container_width=True)
        # Bình luận về ngày nổi bật
        top_rev_day = top10.iloc[0]
        st.write(
            f"Ngày **{top_rev_day['Ngày'].strftime('%d/%m/%Y')}** có doanh thu thuần cao nhất: "
            f"**{top_rev_day['Doanh thu thuần']:,.0f} ₫** với **{int(top_rev_day['Đơn hàng'])}** đơn hàng."
        )
        daily_df['AOV'] = daily_df.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
        top_aov_day = daily_df.loc[daily_df['AOV'].idxmax()]
        st.write(
            f"Ngày **{top_aov_day['Ngày'].strftime('%d/%m/%Y')}** có AOV cao nhất: "
            f"**{top_aov_day['AOV']:,.0f} ₫** với {int(top_aov_day['Đơn hàng'])} đơn hàng."
        )

    # ------------------------------------------------------------------
    # Phần 3: Xu hướng theo tháng và quý
    st.markdown("## 📆 Xu hướng theo tháng và quý")
    # Tính tổng hợp theo tháng trong phạm vi lọc
    month_df = filtered_revenue.copy()
    month_df['Year'] = month_df['Ngày'].dt.year
    month_df['Month'] = month_df['Ngày'].dt.month
    month_df['Quarter'] = month_df['Ngày'].dt.quarter
    month_summary = month_df.groupby(['Year', 'Month', 'Quarter']).agg({
        'Đơn hàng': 'sum',
        'Doanh thu': 'sum',
        'Doanh thu thuần': 'sum',
        'Giảm giá': 'sum',
        'Hoàn trả': 'sum'
    }).reset_index()
    # Tên tháng tiếng Việt
    month_names_local = {1:'Tháng 1',2:'Tháng 2',3:'Tháng 3',4:'Tháng 4',5:'Tháng 5',6:'Tháng 6',7:'Tháng 7',8:'Tháng 8',9:'Tháng 9',10:'Tháng 10',11:'Tháng 11',12:'Tháng 12'}
    month_summary['Tháng'] = month_summary['Month'].map(month_names_local)
    # AOV và tỷ lệ giảm giá
    month_summary['AOV'] = month_summary.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
    month_summary['Tỷ lệ giảm giá'] = month_summary.apply(lambda row: abs(row['Giảm giá'])/row['Doanh thu']*100 if row['Doanh thu']>0 else 0, axis=1)
    # Bảng tóm tắt theo quý
    quarter_summary = month_df.groupby(['Year','Quarter']).agg({
        'Đơn hàng': 'sum',
        'Doanh thu thuần': 'sum'
    }).reset_index()
    quarter_summary['Quý'] = quarter_summary['Quarter'].apply(lambda q: f"Q{int(q)}")
    # Biểu đồ tổng hợp tháng: Doanh thu thuần và Đơn hàng với màu theo quý
    bar_month_rev = alt.Chart(month_summary).mark_bar().encode(
        x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
        y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
        color=alt.Color('Quarter:O', title='Quý', scale=alt.Scale(domain=[1,2,3,4], range=['#2ca02c','#ffbb78','#ffbb78','#1f77b4'])),
        tooltip=['Year:N','Tháng:N','Doanh thu thuần:Q','Quarter:O']
    ).properties(height=300, title='Doanh thu thuần theo tháng (màu theo quý)')
    bar_month_orders = alt.Chart(month_summary).mark_line(point=True).encode(
        x=alt.X('Tháng:N', sort=list(month_names_local.values()), title='Tháng'),
        y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
        color=alt.value('#ff7f0e'),
        tooltip=['Year:N','Tháng:N','Đơn hàng:Q']
    ).properties(height=300, title='Đơn hàng theo tháng')
    # Hiển thị hai biểu đồ song song
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.altair_chart(bar_month_rev, use_container_width=True)
    with col_m2:
        st.altair_chart(bar_month_orders, use_container_width=True)
    # Biểu đồ tổng hợp theo quý: cột doanh thu, đường đơn hàng
    if not quarter_summary.empty:
        fig_quarter = make_subplots(specs=[[{"secondary_y": True}]])
        fig_quarter.add_trace(
            go.Bar(
                x=quarter_summary['Quý'],
                y=quarter_summary['Doanh thu thuần'],
                name='Doanh thu thuần',
                marker_color='#1f77b4'
            ),
            secondary_y=False
        )
        fig_quarter.add_trace(
            go.Scatter(
                x=quarter_summary['Quý'],
                y=quarter_summary['Đơn hàng'],
                name='Đơn hàng',
                mode='lines+markers',
                line=dict(color='#ff7f0e')
            ),
            secondary_y=True
        )
        fig_quarter.update_layout(
            title='Tổng hợp theo quý: Doanh thu thuần (cột) & Đơn hàng (đường)',
            legend=dict(orientation='h', x=0.1, y=1.15)
        )
        fig_quarter.update_yaxes(title_text='Doanh thu thuần (₫)', secondary_y=False)
        fig_quarter.update_yaxes(title_text='Đơn hàng', secondary_y=True)
        st.plotly_chart(fig_quarter, use_container_width=True)
    # Chú thích về mùa cao điểm và thấp điểm
    st.info(
        "**Ghi chú mùa vụ:** Quý 1 thường là mùa cao điểm (Tết), "
        "Quý 2–3 là mùa thấp với doanh thu giảm, Quý 4 là giai đoạn phục hồi và bùng nổ cuối năm." 
    )
    # Bình luận xu hướng tháng
    if not month_summary.empty:
        max_row = month_summary.loc[month_summary['Doanh thu thuần'].idxmax()]
        min_row = month_summary.loc[month_summary['Doanh thu thuần'].idxmin()]
        st.write(
            f"Tháng có doanh thu thuần cao nhất: **{max_row['Tháng']} {int(max_row['Year'])}** với "
            f"**{max_row['Doanh thu thuần']:,.0f} ₫**. Tháng thấp nhất: **{min_row['Tháng']} {int(min_row['Year'])}** "
            f"(**{min_row['Doanh thu thuần']:,.0f} ₫**)."
        )
        max_aov_row = month_summary.loc[month_summary['AOV'].idxmax()]
        st.write(
            f"AOV cao nhất ở **{max_aov_row['Tháng']} {int(max_aov_row['Year'])}**: "
            f"**{max_aov_row['AOV']:,.0f} ₫**/đơn hàng."
        )
        max_disc_row = month_summary.loc[month_summary['Tỷ lệ giảm giá'].idxmax()]
        st.write(
            f"Tỷ lệ giảm giá lớn nhất: **{max_disc_row['Tháng']} {int(max_disc_row['Year'])}** "
            f"với **{max_disc_row['Tỷ lệ giảm giá']:.1f}%** doanh thu."
        )

    # ------------------------------------------------------------------
    # Phần 4: So sánh kênh bán hàng
    st.markdown("## 🛒 So sánh kênh bán hàng")
    # Chuẩn bị dữ liệu kênh và bộ lọc kênh
    channel_df = sales_df.copy()
    channel_df['AOV'] = channel_df.apply(lambda row: row['Doanh thu thuần']/row['Đơn hàng'] if row['Đơn hàng']>0 else 0, axis=1)
    channel_options = channel_df['Kênh bán hàng'].unique().tolist()
    selected_channels = st.multiselect(
        "Chọn kênh muốn xem", 
        options=channel_options,
        default=channel_options
    )
    channel_filtered = channel_df[channel_df['Kênh bán hàng'].isin(selected_channels)]
    # Biểu đồ donut: tỷ trọng Doanh thu thuần theo kênh
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        pie_revenue = px.pie(
            channel_filtered,
            names='Kênh bán hàng',
            values='Doanh thu thuần',
            hole=0.4,
            title='Tỷ trọng Doanh thu thuần theo kênh'
        )
        st.plotly_chart(pie_revenue, use_container_width=True)
    with col_k2:
        pie_orders = px.pie(
            channel_filtered,
            names='Kênh bán hàng',
            values='Đơn hàng',
            hole=0.4,
            title='Tỷ trọng Đơn hàng theo kênh'
        )
        st.plotly_chart(pie_orders, use_container_width=True)
    # Biểu đồ kết hợp cột (Doanh thu) và đường (Đơn hàng) theo kênh
    if not channel_filtered.empty:
        fig_chan = make_subplots(specs=[[{"secondary_y": True}]])
        fig_chan.add_trace(
            go.Bar(
                x=channel_filtered['Kênh bán hàng'],
                y=channel_filtered['Doanh thu thuần'],
                name='Doanh thu thuần',
                marker_color='#1f77b4'
            ),
            secondary_y=False
        )
        fig_chan.add_trace(
            go.Scatter(
                x=channel_filtered['Kênh bán hàng'],
                y=channel_filtered['Đơn hàng'],
                name='Đơn hàng',
                mode='lines+markers',
                line=dict(color='#ff7f0e')
            ),
            secondary_y=True
        )
        fig_chan.update_layout(
            title='Doanh thu thuần (cột) & Đơn hàng (đường) theo kênh',
            legend=dict(orientation='h', x=0.1, y=1.15)
        )
        fig_chan.update_yaxes(title_text='Doanh thu thuần (₫)', secondary_y=False)
        fig_chan.update_yaxes(title_text='Đơn hàng', secondary_y=True)
        st.plotly_chart(fig_chan, use_container_width=True)
    # Biểu đồ thanh riêng lẻ: Doanh thu, Đơn hàng, AOV, Giảm giá
    bar1, bar2, bar3, bar4 = st.columns(4)
    with bar1:
        chart_rev = alt.Chart(channel_filtered).mark_bar().encode(
            x=alt.X('Kênh bán hàng:N', title='Kênh'),
            y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
            color=alt.Color('Kênh bán hàng:N', legend=None),
            tooltip=['Kênh bán hàng:N', 'Doanh thu thuần:Q']
        ).properties(height=250, title='Doanh thu thuần')
        st.altair_chart(chart_rev, use_container_width=True)
    with bar2:
        chart_orders = alt.Chart(channel_filtered).mark_bar(color='#ff7f0e').encode(
            x=alt.X('Kênh bán hàng:N', title='Kênh'),
            y=alt.Y('Đơn hàng:Q', title='Đơn hàng'),
            tooltip=['Kênh bán hàng:N', 'Đơn hàng:Q']
        ).properties(height=250, title='Đơn hàng')
        st.altair_chart(chart_orders, use_container_width=True)
    with bar3:
        chart_aov = alt.Chart(channel_filtered).mark_bar(color='#2ca02c').encode(
            x=alt.X('Kênh bán hàng:N', title='Kênh'),
            y=alt.Y('AOV:Q', title='AOV (₫)', axis=alt.Axis(format=',.0f')),
            tooltip=['Kênh bán hàng:N', 'AOV:Q']
        ).properties(height=250, title='AOV')
        st.altair_chart(chart_aov, use_container_width=True)
    with bar4:
        chart_discount = alt.Chart(channel_filtered).mark_bar(color='#d62728').encode(
            x=alt.X('Kênh bán hàng:N', title='Kênh'),
            y=alt.Y('Giảm giá:Q', title='Giảm giá (₫)', axis=alt.Axis(format=',.0f')),
            tooltip=['Kênh bán hàng:N', 'Giảm giá:Q']
        ).properties(height=250, title='Giảm giá')
        st.altair_chart(chart_discount, use_container_width=True)
    # Phân tích kênh bán hàng và gợi ý
    if not channel_filtered.empty:
        # Tính % đơn hàng và % doanh thu
        total_orders_all = channel_filtered['Đơn hàng'].sum()
        total_rev_all = channel_filtered['Doanh thu thuần'].sum()
        analysis_rows = []
        for _, row in channel_filtered.iterrows():
            pct_orders = row['Đơn hàng'] / total_orders_all * 100 if total_orders_all > 0 else 0
            pct_rev = row['Doanh thu thuần'] / total_rev_all * 100 if total_rev_all > 0 else 0
            analysis_rows.append({
                'Kênh': row['Kênh bán hàng'],
                'Đơn hàng': int(row['Đơn hàng']),
                '% Đơn hàng': pct_orders,
                '% Doanh thu': pct_rev,
                'AOV': row['AOV']
            })
        analysis_df = pd.DataFrame(analysis_rows)
        st.markdown("### Hiệu suất theo kênh")
        st.dataframe(analysis_df.style.format({
            'Đơn hàng': '{:,.0f}',
            '% Đơn hàng': '{:.1f}%',
            '% Doanh thu': '{:.1f}%',
            'AOV': '{:,.0f} ₫'
        }))
        # Nhận xét
        comments = []
        # Kênh có AOV cao nhất
        top_aov_channel = analysis_df.loc[analysis_df['AOV'].idxmax()]
        comments.append(f"Kênh **{top_aov_channel['Kênh']}** có AOV cao nhất (" \
                        f"{top_aov_channel['AOV']:,.0f} ₫) – cơ hội upsell.")
        # Kênh có AOV thấp nhất
        low_aov_channel = analysis_df.loc[analysis_df['AOV'].idxmin()]
        if low_aov_channel['Kênh'] != top_aov_channel['Kênh']:
            comments.append(f"Kênh **{low_aov_channel['Kênh']}** có AOV thấp nhất (" \
                            f"{low_aov_channel['AOV']:,.0f} ₫) – cần chiến lược upsell.")
        # Kênh chiếm tỷ trọng lớn
        if not analysis_df.empty:
            dominant_channel = analysis_df.loc[analysis_df['% Doanh thu'].idxmax()]
            if dominant_channel['% Doanh thu'] > 50:
                comments.append(f"Kênh **{dominant_channel['Kênh']}** chiếm hơn 50% doanh thu – cần giảm phụ thuộc.")
        st.markdown("**Nhận xét:**")
        for c in comments:
            st.markdown(f"- {c}")

    # ------------------------------------------------------------------
    # Phần 5: Phân phối dữ liệu
    st.markdown("## 📊 Phân phối dữ liệu")
    # Histogram phân phối Doanh thu thuần theo ngày
    hist1 = alt.Chart(filtered_revenue).mark_bar().encode(
        x=alt.X('Doanh thu thuần:Q', bin=alt.Bin(maxbins=30), title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
        y=alt.Y('count():Q', title='Số ngày'),
        tooltip=['count()']
    ).properties(height=300, title='Phân phối Doanh thu thuần')
    # Histogram phân phối Đơn hàng theo ngày
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
    # Biểu đồ scatter: Đơn hàng vs Doanh thu thuần
    scatter = alt.Chart(filtered_revenue).mark_circle(opacity=0.6).encode(
        x=alt.X('Đơn hàng:Q', title='Đơn hàng'),
        y=alt.Y('Doanh thu thuần:Q', title='Doanh thu thuần (₫)', axis=alt.Axis(format=',.0f')),
        tooltip=['Ngày:T', 'Đơn hàng:Q', 'Doanh thu thuần:Q']
    ).properties(height=400, title='Đơn hàng vs Doanh thu thuần')
    st.altair_chart(scatter, use_container_width=True)
    # Bình luận về phân phối
    if not filtered_revenue.empty:
        median_rev = filtered_revenue['Doanh thu thuần'].median()
        median_orders = filtered_revenue['Đơn hàng'].median()
        st.write(
            f"Phần lớn ngày có doanh thu thuần quanh **{median_rev:,.0f} ₫** và số đơn hàng trung vị khoảng "
            f"**{int(median_orders)}** đơn. Các histogram giúp nhận ra phân bố lệch và các ngày vượt trội." 
        )

    # ------------------------------------------------------------------
    # Phần 6: Hệ thống cảnh báo KPI
    st.markdown("## ⚠️ Cảnh báo KPI")
    warnings = []
    # Kiểm tra doanh thu giảm 3 tháng liên tiếp
    if not month_summary.empty:
        # Sắp xếp theo thời gian
        ms = month_summary.sort_values(['Year','Month'])
        decreasing_streak = False
        # Kiểm tra từng chuỗi 3 tháng liên tiếp
        for i in range(len(ms) - 2):
            if ms.iloc[i]['Doanh thu thuần'] > ms.iloc[i+1]['Doanh thu thuần'] > ms.iloc[i+2]['Doanh thu thuần']:
                decreasing_streak = True
                break
        if decreasing_streak:
            warnings.append("Doanh thu thuần giảm liên tiếp 3 tháng gần đây. 🔻")
    # Kiểm tra tỷ lệ hoàn trả >5%
    if kpi_current['return_rate'] > 5:
        warnings.append("Tỷ lệ hoàn trả vượt 5%. Vui lòng xem xét quy trình hậu mãi.")
    # Nếu có cảnh báo, hiển thị
    if warnings:
        for w in warnings:
            st.warning(w)
    else:
        st.success("Không có cảnh báo nghiêm trọng cho khoảng thời gian này.")

    # ------------------------------------------------------------------
    # Phần 7: Kết luận & gợi ý hành động
    st.markdown("## 📝 Kết luận & Gợi ý hành động")
    st.write(
        "Dựa trên các phân tích ở trên, sau đây là một số gợi ý nhằm tối ưu hiệu quả kinh doanh:")
    conclusions = [
        "Đẩy mạnh kênh Web để giảm phụ thuộc vào kênh có thị phần lớn nhất.",
        "Tăng AOV trên TikTok bằng cách triển khai gói combo và upsell.",
        "Đầu tư marketing vào giữa năm để lấp đầy khoảng trống doanh thu Q2–Q3.",
        "Kiểm soát giá vốn và tối ưu chi phí để duy trì biên lợi nhuận > 20%.",
        "Xem xét chương trình hoàn trả để giảm tỷ lệ hoàn trả xuống dưới 5%."
    ]
    for c in conclusions:
        st.markdown(f"- {c}")

    # ==================================================================
    # Dữ liệu chi tiết và tải xuống CSV
    st.markdown("### Dữ liệu chi tiết")
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
    # Nút tải xuống
    st.markdown("#### Tải xuống dữ liệu")
    csv_data = filtered_revenue.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="Tải dữ liệu CSV",
        data=csv_data,
        file_name=f"Keos_Doanhthu_{start_date}_den_{end_date}.csv",
        mime="text/csv"
    )


    


if __name__ == "__main__":
    main()