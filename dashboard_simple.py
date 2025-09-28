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
    
    # 損失データの計算
    loss_orders = filtered_df[filtered_df['Profit'] < 0]
    total_loss = abs(loss_orders['Profit'].sum())
    loss_rate = len(loss_orders) / len(filtered_df) * 100 if len(filtered_df) > 0 else 0

    # KPI表示
    col1, col2, col3, col4, col5 = st.columns(5)
    
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

    with col5:
        st.metric("⚠️ 総損失", f"${total_loss:,.0f}", f"{loss_rate:.1f}%")
    
    st.markdown("---")
    
    # タブ作成
    tab1, tab2, tab3, tab4 = st.tabs(["📈 売上分析", "🎯 詳細分析", "⚠️ 損失分析", "📊 データ"])
    
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
        st.subheader("⚠️ 損失分析ダッシュボード")

        if len(loss_orders) > 0:
            # 損失サマリー
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("🔴 損失注文数", f"{len(loss_orders):,}")

            with col2:
                avg_loss = loss_orders['Profit'].mean()
                st.metric("📉 平均損失額", f"${abs(avg_loss):.2f}")

            with col3:
                worst_loss = loss_orders['Profit'].min()
                st.metric("💥 最大損失", f"${abs(worst_loss):.2f}")

            with col4:
                loss_vs_sales = (total_loss / total_sales * 100) if total_sales > 0 else 0
                st.metric("📊 損失率", f"{loss_vs_sales:.2f}%")

            st.markdown("---")

            # 損失分析グラフ
            col1, col2 = st.columns(2)

            with col1:
                # 地域別損失
                region_loss = loss_orders.groupby('Region')['Profit'].sum().abs().reset_index()
                region_loss.columns = ['Region', 'Loss']

                fig_region_loss = px.bar(
                    region_loss,
                    x='Region',
                    y='Loss',
                    title='🌍 地域別損失額',
                    color='Loss',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_region_loss, use_container_width=True)

            with col2:
                # カテゴリ別損失
                category_loss = loss_orders.groupby('Category')['Profit'].sum().abs().reset_index()
                category_loss.columns = ['Category', 'Loss']

                fig_category_loss = px.pie(
                    category_loss,
                    values='Loss',
                    names='Category',
                    title='📦 カテゴリ別損失分布',
                    color_discrete_sequence=px.colors.sequential.Reds_r
                )
                st.plotly_chart(fig_category_loss, use_container_width=True)

            # 月別損失トレンド
            monthly_loss = loss_orders.groupby('YearMonth')['Profit'].sum().abs().reset_index()
            monthly_loss.columns = ['YearMonth', 'Loss']

            fig_monthly_loss = px.line(
                monthly_loss,
                x='YearMonth',
                y='Loss',
                title='📅 月別損失トレンド',
                markers=True,
                line_shape='spline'
            )
            fig_monthly_loss.update_traces(line_color='red')
            fig_monthly_loss.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_monthly_loss, use_container_width=True)

            # セグメント別損失詳細
            col1, col2 = st.columns(2)

            with col1:
                # セグメント別損失
                segment_loss = loss_orders.groupby('Segment').agg({
                    'Profit': ['sum', 'mean', 'count']
                }).round(2)
                segment_loss.columns = ['総損失', '平均損失', '損失注文数']
                segment_loss['総損失'] = abs(segment_loss['総損失'])
                segment_loss['平均損失'] = abs(segment_loss['平均損失'])

                st.subheader("👥 セグメント別損失詳細")
                st.dataframe(segment_loss, use_container_width=True)

            with col2:
                # 最大損失商品TOP10
                top_loss_products = loss_orders.nsmallest(10, 'Profit')[['Product Name', 'Profit', 'Sales', 'Category']].copy()
                top_loss_products['Profit'] = abs(top_loss_products['Profit'])
                top_loss_products.columns = ['商品名', '損失額', '売上', 'カテゴリ']

                st.subheader("💥 最大損失商品TOP10")
                st.dataframe(top_loss_products, use_container_width=True)

            # 損失要因分析
            st.subheader("🔍 損失要因分析")

            # 割引と損失の関係
            discount_loss = loss_orders.copy()
            discount_loss['Discount_Range'] = pd.cut(
                discount_loss['Discount'],
                bins=[0, 0.1, 0.3, 0.5, 1.0],
                labels=['0-10%', '10-30%', '30-50%', '50%+']
            )

            discount_analysis = discount_loss.groupby('Discount_Range').agg({
                'Profit': ['sum', 'count'],
                'Sales': 'sum'
            }).round(2)
            discount_analysis.columns = ['総損失', '件数', '売上']
            discount_analysis['総損失'] = abs(discount_analysis['総損失'])

            col1, col2 = st.columns(2)

            with col1:
                fig_discount = px.bar(
                    x=discount_analysis.index,
                    y=discount_analysis['総損失'],
                    title='💸 割引率別損失額',
                    labels={'x': '割引率', 'y': '損失額'},
                    color=discount_analysis['総損失'],
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_discount, use_container_width=True)

            with col2:
                st.write("**割引率別損失分析**")
                st.dataframe(discount_analysis, use_container_width=True)

        else:
            st.success("🎉 選択された期間・条件では損失は発生していません！")

    with tab4:
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
