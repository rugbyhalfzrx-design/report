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
    
    # 日付変換と追加的な特徴量作成
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%m/%d/%Y')
    df['Ship Date'] = pd.to_datetime(df['Ship Date'], format='%m/%d/%Y')
    df['Year'] = df['Order Date'].dt.year
    df['Month'] = df['Order Date'].dt.month
    df['Quarter'] = df['Order Date'].dt.quarter
    df['Weekday'] = df['Order Date'].dt.day_name()
    df['YearMonth'] = df['Order Date'].dt.to_period('M').astype(str)
    df['Shipping_Days'] = (df['Ship Date'] - df['Order Date']).dt.days
    df['Profit_Margin'] = (df['Profit'] / df['Sales'] * 100).round(2)
    df['Profit_Margin'] = df['Profit_Margin'].replace([np.inf, -np.inf], 0)
    
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 売上分析", "🎯 詳細分析", "⚠️ 損失分析", "🚀 高度な分析", "📊 データ"])
    
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
        fig_monthly.update_xaxes(type='category')
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
        fig_yearly.update_xaxes(type='category', tickmode='linear', dtick=1)
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
            fig_monthly_loss.update_xaxes(type='category')
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
        st.subheader("🚀 高度なビジネス分析")

        # 配送方法分析
        st.markdown("### 📦 配送方法分析")
        col1, col2 = st.columns(2)

        with col1:
            # 配送方法別売上と利益
            shipping_analysis = filtered_df.groupby('Ship Mode').agg({
                'Sales': 'sum',
                'Profit': 'sum',
                'Shipping_Days': 'mean',
                'Order ID': 'count'
            }).round(2)
            shipping_analysis.columns = ['売上', '利益', '平均配送日数', '注文数']
            shipping_analysis['利益率'] = (shipping_analysis['利益'] / shipping_analysis['売上'] * 100).round(2)

            fig_shipping = px.bar(
                x=shipping_analysis.index,
                y=shipping_analysis['売上'],
                title='🚚 配送方法別売上',
                labels={'x': '配送方法', 'y': '売上'},
                color=shipping_analysis['売上'],
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_shipping, use_container_width=True)

        with col2:
            # 配送日数 vs 利益率
            fig_shipping_efficiency = px.scatter(
                x=shipping_analysis['平均配送日数'],
                y=shipping_analysis['利益率'],
                size=shipping_analysis['注文数'],
                hover_name=shipping_analysis.index,
                title='📊 配送日数 vs 利益率',
                labels={'x': '平均配送日数', 'y': '利益率(%)'}
            )
            st.plotly_chart(fig_shipping_efficiency, use_container_width=True)

        st.dataframe(shipping_analysis, use_container_width=True)

        # 利益率分析
        st.markdown("### 🎯 利益率分析")
        col1, col2 = st.columns(2)

        with col1:
            # 利益率の分布
            fig_profit_dist = px.histogram(
                filtered_df,
                x='Profit_Margin',
                bins=50,
                title='📈 利益率の分布',
                labels={'x': '利益率(%)', 'y': '频度'}
            )
            fig_profit_dist.add_vline(x=filtered_df['Profit_Margin'].mean(), line_dash="dash", line_color="red")
            st.plotly_chart(fig_profit_dist, use_container_width=True)

        with col2:
            # カツゴリ別利益率
            category_profit = filtered_df.groupby('Category')['Profit_Margin'].mean().reset_index()
            fig_category_profit = px.bar(
                category_profit,
                x='Category',
                y='Profit_Margin',
                title='📦 カテゴリ別平均利益率',
                color='Profit_Margin',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_category_profit, use_container_width=True)

        # 季節性分析
        st.markdown("### 🍃 季節性分析")
        col1, col2 = st.columns(2)

        with col1:
            # 四半期別分析
            quarterly_sales = filtered_df.groupby(['Year', 'Quarter'])['Sales'].sum().reset_index()
            quarterly_sales['Year_Quarter'] = quarterly_sales['Year'].astype(str) + '-Q' + quarterly_sales['Quarter'].astype(str)

            fig_quarterly = px.line(
                quarterly_sales,
                x='Year_Quarter',
                y='Sales',
                title='📅 四半期別売上トレンド',
                markers=True
            )
            fig_quarterly.update_xaxes(type='category')
            st.plotly_chart(fig_quarterly, use_container_width=True)

        with col2:
            # 曜日別パターン
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_sales = filtered_df.groupby('Weekday')['Sales'].mean().reindex(weekday_order).reset_index()

            fig_weekday = px.bar(
                weekday_sales,
                x='Weekday',
                y='Sales',
                title='📅 曜日別平均売上',
                color='Sales',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_weekday, use_container_width=True)

        # 割引分析
        st.markdown("### 💸 割引効果分析")
        col1, col2 = st.columns(2)

        with col1:
            # 割引率 vs 売上の関係
            fig_discount_sales = px.scatter(
                filtered_df.sample(min(1000, len(filtered_df))),
                x='Discount',
                y='Sales',
                color='Category',
                title='📊 割引率 vs 売上の関係',
                labels={'x': '割引率', 'y': '売上'},
                opacity=0.7
            )
            st.plotly_chart(fig_discount_sales, use_container_width=True)

        with col2:
            # 割引率別利益率
            discount_bins = pd.cut(filtered_df['Discount'], bins=5, labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])
            discount_profit = filtered_df.groupby(discount_bins)['Profit_Margin'].mean().reset_index()

            fig_discount_profit = px.bar(
                discount_profit,
                x='Discount',
                y='Profit_Margin',
                title='📈 割引率別平均利益率',
                color='Profit_Margin',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_discount_profit, use_container_width=True)

        # リピート顧客分析
        st.markdown("### 🔄 リピート顧客分析")

        # 顧客別注文回数
        customer_orders = filtered_df.groupby('Customer ID').agg({
            'Order ID': 'nunique',
            'Sales': 'sum',
            'Profit': 'sum'
        }).reset_index()
        customer_orders.columns = ['Customer_ID', 'Order_Count', 'Total_Sales', 'Total_Profit']
        customer_orders['Customer_Type'] = customer_orders['Order_Count'].apply(
            lambda x: 'New (1回)' if x == 1 else 'Repeat (2+回)'
        )

        col1, col2 = st.columns(2)

        with col1:
            # 新規 vs リピートの売上比較
            customer_type_analysis = customer_orders.groupby('Customer_Type').agg({
                'Customer_ID': 'count',
                'Total_Sales': 'sum',
                'Total_Profit': 'sum'
            }).reset_index()
            customer_type_analysis.columns = ['顧客タイプ', '顧客数', '総売上', '総利益']

            fig_customer_type = px.pie(
                customer_type_analysis,
                values='総売上',
                names='顧客タイプ',
                title='👥 新規 vs リピート顧客の売上比率'
            )
            st.plotly_chart(fig_customer_type, use_container_width=True)

        with col2:
            # 注文回数の分布
            fig_order_dist = px.histogram(
                customer_orders,
                x='Order_Count',
                bins=20,
                title='📈 顧客別注文回数の分布',
                labels={'x': '注文回数', 'y': '顧客数'}
            )
            st.plotly_chart(fig_order_dist, use_container_width=True)

        st.dataframe(customer_type_analysis, use_container_width=True)

        # 成長率分析
        st.markdown("### 📈 成長率分析")

        if len(filtered_df['Year'].unique()) > 1:
            yearly_growth = filtered_df.groupby('Year')['Sales'].sum().reset_index()
            yearly_growth['Growth_Rate'] = yearly_growth['Sales'].pct_change() * 100
            yearly_growth['Growth_Rate'] = yearly_growth['Growth_Rate'].fillna(0)

            col1, col2 = st.columns(2)

            with col1:
                fig_growth = px.bar(
                    yearly_growth[yearly_growth['Year'] > yearly_growth['Year'].min()],
                    x='Year',
                    y='Growth_Rate',
                    title='📈 年次成長率',
                    labels={'x': '年', 'y': '成長率(%)'},
                    color='Growth_Rate',
                    color_continuous_scale='RdYlGn'
                )
                fig_growth.update_xaxes(type='category')
                st.plotly_chart(fig_growth, use_container_width=True)

            with col2:
                # 月別成長率（前年同月比）
                monthly_growth = filtered_df.groupby(['Year', 'Month'])['Sales'].sum().reset_index()
                monthly_growth['YoY_Growth'] = monthly_growth.groupby('Month')['Sales'].pct_change(periods=1) * 100
                monthly_growth = monthly_growth.dropna()
                monthly_growth['Year_Month'] = monthly_growth['Year'].astype(str) + '-' + monthly_growth['Month'].astype(str).str.zfill(2)

                fig_monthly_growth = px.line(
                    monthly_growth,
                    x='Year_Month',
                    y='YoY_Growth',
                    title='📅 月別成長率',
                    markers=True,
                    labels={'x': '年月', 'y': '成長率(%)'}
                )
                fig_monthly_growth.update_xaxes(type='category')
                st.plotly_chart(fig_monthly_growth, use_container_width=True)
        else:
            st.info("📊 成長率分析には複数年のデータが必要です")

        # 相関分析
        st.markdown("### 🔗 相関分析")

        # 数値変数の相関マトリックス
        numeric_cols = ['Sales', 'Profit', 'Quantity', 'Discount', 'Profit_Margin', 'Shipping_Days']
        correlation_matrix = filtered_df[numeric_cols].corr()

        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="🔗 数値変数間の相関係数",
            color_continuous_scale='RdBu_r'
        )
        st.plotly_chart(fig_corr, use_container_width=True)

        # 相関係数の解釈
        st.markdown("""
        **相関係数の解釈:**
        - 1.0：完全な正の相関
        - 0.0：相関なし
        - -1.0：完全な負の相関
        """)

    with tab5:
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
