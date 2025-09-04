import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
    try:
        # GitHub/相対パス
        df = pd.read_csv('Sample - Superstore.csv', encoding='latin-1')
    except FileNotFoundError:
        try:
            # 別のエンコーディングを試行
            df = pd.read_csv('Sample - Superstore.csv', encoding='utf-8')
        except FileNotFoundError:
            st.error("❌ データファイル 'Sample - Superstore.csv' が見つかりません")
            st.info("ファイルが同じディレクトリにあることを確認してください")
            st.stop()
    
    # 日付変換
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Year'] = df['Order Date'].dt.year
    df['Month'] = df['Order Date'].dt.month
    df['YearMonth'] = df['Order Date'].dt.to_period('M').astype(str)
    
    return df

# メイン実行
def main():
    # データ読み込み
    df = load_data()
    
    # タイトル
    st.title("📊 Superstore Analytics Dashboard")
    st.markdown("---")
    
    # サイドバーフィルター
    st.sidebar.title("🔍 フィルター")
    
    # 年フィルター
    years = sorted(df['Year'].unique())
    selected_years = st.sidebar.multiselect(
        "📅 年を選択",
        options=years,
        default=years
    )
    
    # 地域フィルター
    regions = sorted(df['Region'].unique())
    selected_regions = st.sidebar.multiselect(
        "🌍 地域を選択",
        options=regions,
        default=regions
    )
    
    # カテゴリフィルター
    categories = sorted(df['Category'].unique())
    selected_categories = st.sidebar.multiselect(
        "📦 カテゴリを選択",
        options=categories,
        default=categories
    )
    
    # データフィルタリング
    filtered_df = df[
        (df['Year'].isin(selected_years)) &
        (df['Region'].isin(selected_regions)) &
        (df['Category'].isin(selected_categories))
    ]
    
    # KPI表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = filtered_df['Sales'].sum()
        st.metric("💰 総売上", f"${total_sales:,.0f}")
    
    with col2:
        total_profit = filtered_df['Profit'].sum()
        profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
        st.metric("📈 総利益", f"${total_profit:,.0f}", f"{profit_margin:.1f}%")
    
    with col3:
        total_orders = filtered_df['Order ID'].nunique()
        st.metric("🛒 注文数", f"{total_orders:,}")
    
    with col4:
        avg_order = filtered_df['Sales'].mean()
        st.metric("💳 平均注文額", f"${avg_order:.2f}")
    
    st.markdown("---")
    
    # タブ作成
    tab1, tab2, tab3 = st.tabs(["📈 売上分析", "🎯 詳細分析", "📊 データ"])
    
    with tab1:
        # 月別売上トレンド
        monthly_sales = filtered_df.groupby('YearMonth')['Sales'].sum().reset_index()
        
        fig_monthly = px.line(
            monthly_sales,
            x='YearMonth',
            y='Sales',
            title='📅 月別売上トレンド',
            markers=True
        )
        fig_monthly.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # 2つのコラム
        col1, col2 = st.columns(2)
        
        with col1:
            # 地域別売上
            region_sales = filtered_df.groupby('Region')['Sales'].sum().reset_index()
            
            fig_region = px.pie(
                region_sales,
                values='Sales',
                names='Region',
                title='🌍 地域別売上分布'
            )
            st.plotly_chart(fig_region, use_container_width=True)
        
        with col2:
            # カテゴリ別売上
            category_sales = filtered_df.groupby('Category')['Sales'].sum().reset_index()
            
            fig_category = px.bar(
                category_sales,
                x='Category',
                y='Sales',
                title='📦 カテゴリ別売上',
                color='Sales',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_category, use_container_width=True)
    
    with tab2:
        # 年別比較
        yearly_sales = filtered_df.groupby('Year').agg({
            'Sales': 'sum',
            'Profit': 'sum',
            'Order ID': 'nunique'
        }).reset_index()
        
        fig_yearly = px.bar(
            yearly_sales,
            x='Year',
            y='Sales',
            title='📊 年別売上',
            text='Sales'
        )
        fig_yearly.update_traces(texttemplate='%{text:$,.0f}', textposition='outside')
        st.plotly_chart(fig_yearly, use_container_width=True)
        
        # セグメント分析
        col1, col2 = st.columns(2)
        
        with col1:
            segment_sales = filtered_df.groupby('Segment')['Sales'].sum().reset_index()
            
            fig_segment = px.pie(
                segment_sales,
                values='Sales',
                names='Segment',
                title='👥 セグメント別売上'
            )
            st.plotly_chart(fig_segment, use_container_width=True)
        
        with col2:
            # トップ10製品
            top_products = filtered_df.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index()
            
            fig_products = px.bar(
                top_products,
                x='Sales',
                y='Product Name',
                orientation='h',
                title='🏆 トップ10製品（売上）'
            )
            fig_products.update_layout(height=400)
            st.plotly_chart(fig_products, use_container_width=True)
    
    with tab3:
        st.subheader("📋 データサマリー")
        
        # データ基本情報
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**レコード数**: {len(filtered_df):,}")
        
        with col2:
            st.info(f"**期間**: {filtered_df['Order Date'].min().strftime('%Y-%m-%d')} ～ {filtered_df['Order Date'].max().strftime('%Y-%m-%d')}")
        
        with col3:
            st.info(f"**顧客数**: {filtered_df['Customer ID'].nunique():,}")
        
        # 統計情報
        st.subheader("📊 統計情報")
        
        stats = filtered_df.groupby(['Region', 'Category']).agg({
            'Sales': ['sum', 'mean', 'count'],
            'Profit': ['sum', 'mean'],
            'Quantity': 'sum'
        }).round(2)
        
        stats.columns = ['売上合計', '平均売上', '取引数', '利益合計', '平均利益', '数量合計']
        st.dataframe(stats, use_container_width=True)
        
        # 生データ表示
        st.subheader("📄 生データ（先頭100件）")
        display_columns = ['Order Date', 'Customer Name', 'Region', 'Category', 'Product Name', 'Sales', 'Profit']
        st.dataframe(
            filtered_df[display_columns].head(100),
            use_container_width=True
        )

# 実行
if __name__ == "__main__":
    main()

# フッター
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
<p><strong>Superstore Analytics Dashboard</strong></p>
<p>Built with ❤️ using Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)