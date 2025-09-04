import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ページ設定
st.set_page_config(
    page_title="Superstore Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データ読み込み関数
@st.cache_data
def load_data():
    df = pd.read_csv('Sample - Superstore.csv', encoding='latin-1')
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Year'] = df['Order Date'].dt.year
    df['Month'] = df['Order Date'].dt.month
    df['YearMonth'] = df['Order Date'].dt.to_period('M').astype(str)
    return df

@st.cache_data
def load_rfm_data():
    try:
        return pd.read_csv('C:\\Users\\fopwy\\OneDrive\\Desktop\\rfm_results.csv')
    except:
        return None

# データ読み込み
df = load_data()
rfm_data = load_rfm_data()

# サイドバー
st.sidebar.title("📊 Superstore Analytics")
st.sidebar.markdown("---")

# フィルター
selected_year = st.sidebar.multiselect(
    "年を選択",
    options=sorted(df['Year'].unique()),
    default=sorted(df['Year'].unique())
)

selected_region = st.sidebar.multiselect(
    "地域を選択", 
    options=df['Region'].unique(),
    default=df['Region'].unique()
)

selected_category = st.sidebar.multiselect(
    "カテゴリを選択",
    options=df['Category'].unique(), 
    default=df['Category'].unique()
)

# データフィルタリング
filtered_df = df[
    (df['Year'].isin(selected_year)) &
    (df['Region'].isin(selected_region)) &
    (df['Category'].isin(selected_category))
]

# メインタイトル
st.title("📊 Superstore Analytics Dashboard")
st.markdown("---")

# KPI表示
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_sales = filtered_df['Sales'].sum()
    st.metric("総売上", f"${total_sales:,.0f}")

with col2:
    total_profit = filtered_df['Profit'].sum()
    st.metric("総利益", f"${total_profit:,.0f}")

with col3:
    total_orders = filtered_df['Order ID'].nunique()
    st.metric("総注文数", f"{total_orders:,}")

with col4:
    avg_order_value = filtered_df['Sales'].mean()
    st.metric("平均注文額", f"${avg_order_value:.2f}")

st.markdown("---")

# タブ作成
tab1, tab2, tab3, tab4 = st.tabs(["📈 売上分析", "👥 RFM分析", "🔮 売上予測", "📊 詳細分析"])

with tab1:
    st.header("📈 売上分析")
    
    # 月別売上トレンド
    monthly_sales = filtered_df.groupby('YearMonth')['Sales'].sum().reset_index()
    fig_monthly = px.line(
        monthly_sales, 
        x='YearMonth', 
        y='Sales',
        title='月別売上トレンド',
        markers=True
    )
    fig_monthly.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_monthly, use_container_width=True)
    
    # 地域別・カテゴリ別分析
    col1, col2 = st.columns(2)
    
    with col1:
        # 地域別売上
        region_sales = filtered_df.groupby('Region')['Sales'].sum().reset_index()
        fig_region = px.pie(
            region_sales,
            values='Sales',
            names='Region', 
            title='地域別売上分布'
        )
        st.plotly_chart(fig_region, use_container_width=True)
    
    with col2:
        # カテゴリ別売上
        category_sales = filtered_df.groupby('Category')['Sales'].sum().reset_index()
        fig_category = px.bar(
            category_sales,
            x='Category',
            y='Sales',
            title='カテゴリ別売上',
            color='Sales'
        )
        st.plotly_chart(fig_category, use_container_width=True)
    
    # セグメント別分析
    segment_analysis = filtered_df.groupby('Segment').agg({
        'Sales': 'sum',
        'Profit': 'sum',
        'Order ID': 'nunique'
    }).reset_index()
    
    fig_segment = px.scatter(
        segment_analysis,
        x='Sales',
        y='Profit', 
        size='Order ID',
        color='Segment',
        title='セグメント別: 売上 vs 利益',
        hover_name='Segment'
    )
    st.plotly_chart(fig_segment, use_container_width=True)

with tab2:
    st.header("👥 RFM分析 - 顧客セグメンテーション")
    
    if rfm_data is not None:
        # RFM概要
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_recency = rfm_data['Recency'].mean()
            st.metric("平均最終購入からの日数", f"{avg_recency:.0f}日")
        
        with col2:
            avg_frequency = rfm_data['Frequency'].mean()  
            st.metric("平均購入頻度", f"{avg_frequency:.1f}回")
        
        with col3:
            avg_monetary = rfm_data['Monetary'].mean()
            st.metric("平均購入金額", f"${avg_monetary:,.0f}")
        
        # セグメント分布
        segment_counts = rfm_data['Segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        
        fig_rfm = px.pie(
            segment_counts,
            values='Count',
            names='Segment',
            title='顧客セグメント分布'
        )
        st.plotly_chart(fig_rfm, use_container_width=True)
        
        # RFMスコア分布
        col1, col2 = st.columns(2)
        
        with col1:
            fig_recency = px.histogram(
                rfm_data,
                x='Recency',
                title='最終購入からの日数分布',
                nbins=30
            )
            st.plotly_chart(fig_recency, use_container_width=True)
        
        with col2:
            fig_monetary = px.histogram(
                rfm_data,
                x='Monetary', 
                title='購入金額分布',
                nbins=30
            )
            st.plotly_chart(fig_monetary, use_container_width=True)
        
        # セグメント詳細テーブル
        segment_summary = rfm_data.groupby('Segment').agg({
            'Recency': 'mean',
            'Frequency': 'mean',
            'Monetary': ['mean', 'sum'],
            'Segment': 'count'
        }).round(2)
        
        segment_summary.columns = ['平均Recency', '平均Frequency', '平均Monetary', '総売上', '顧客数']
        st.subheader("セグメント別詳細")
        st.dataframe(segment_summary, use_container_width=True)
    else:
        st.warning("RFMデータが見つかりません。rfm_analysis.pyを実行してください。")

with tab3:
    st.header("🔮 売上予測")
    
    try:
        # 予測結果の読み込み
        forecast_data = pd.read_csv('C:\\Users\\fopwy\\OneDrive\\Desktop\\monthly_forecast.csv')
        
        # 2018年予測
        st.subheader("2018年上半期売上予測")
        
        fig_forecast = px.bar(
            forecast_data,
            x='Month',
            y='Predicted_Sales',
            title='2018年月別売上予測',
            color='Predicted_Sales'
        )
        fig_forecast.update_xaxis(tickmode='linear')
        st.plotly_chart(fig_forecast, use_container_width=True)
        
        # 予測サマリー
        total_forecast = forecast_data['Predicted_Sales'].sum()
        avg_monthly = forecast_data['Predicted_Sales'].mean()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("予測総売上（上半期）", f"${total_forecast:,.0f}")
        with col2:
            st.metric("月平均売上予測", f"${avg_monthly:,.0f}")
        
        # 過去実績との比較
        historical_monthly = df.groupby(['Year', 'Month'])['Sales'].sum().reset_index()
        historical_monthly['YearMonth'] = historical_monthly['Year'].astype(str) + '-' + historical_monthly['Month'].astype(str).str.zfill(2)
        
        fig_comparison = go.Figure()
        
        # 過去実績
        fig_comparison.add_trace(go.Scatter(
            x=historical_monthly['YearMonth'],
            y=historical_monthly['Sales'],
            mode='lines+markers',
            name='過去実績',
            line=dict(color='blue')
        ))
        
        # 予測値（2018年）
        forecast_months = ['2018-' + str(i).zfill(2) for i in range(1, 7)]
        fig_comparison.add_trace(go.Scatter(
            x=forecast_months,
            y=forecast_data['Predicted_Sales'],
            mode='lines+markers',
            name='2018年予測',
            line=dict(color='red', dash='dash')
        ))
        
        fig_comparison.update_layout(
            title='売上実績 vs 予測',
            xaxis_title='月',
            yaxis_title='売上'
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
        
    except FileNotFoundError:
        st.warning("予測データが見つかりません。sales_prediction.pyを実行してください。")

with tab4:
    st.header("📊 詳細分析")
    
    # トップ製品
    st.subheader("トップ10製品（売上別）")
    top_products = filtered_df.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index()
    
    fig_products = px.bar(
        top_products,
        x='Sales',
        y='Product Name',
        orientation='h',
        title='トップ10製品'
    )
    st.plotly_chart(fig_products, use_container_width=True)
    
    # 収益性分析
    st.subheader("カテゴリ別収益性")
    profitability = filtered_df.groupby('Category').agg({
        'Sales': 'sum',
        'Profit': 'sum'
    }).reset_index()
    profitability['Profit_Margin'] = (profitability['Profit'] / profitability['Sales']) * 100
    
    fig_profit = px.scatter(
        profitability,
        x='Sales',
        y='Profit',
        size='Profit_Margin',
        color='Category',
        title='売上 vs 利益（バブルサイズ=利益率）',
        hover_data=['Profit_Margin']
    )
    st.plotly_chart(fig_profit, use_container_width=True)
    
    # データテーブル
    st.subheader("データ詳細")
    st.dataframe(
        filtered_df[['Order Date', 'Customer Name', 'Category', 'Product Name', 'Sales', 'Profit', 'Region']].head(100),
        use_container_width=True
    )

# フッター
st.markdown("---")
st.markdown("**Superstore Analytics Dashboard** - Powered by Streamlit & Plotly")
