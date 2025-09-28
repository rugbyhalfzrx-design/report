import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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
    try:
        # 複数のファイル名とエンコーディングを試行
        file_options = [
            ('Sample - Superstore.csv', 'latin-1'),
            ('Sample - Superstore.csv', 'utf-8'),
            ('Superstore.csv', 'latin-1'),
            ('Superstore.csv', 'utf-8')
        ]

        df = None
        for filename, encoding in file_options:
            try:
                df = pd.read_csv(filename, encoding=encoding)
                st.success(f"✅ データファイル '{filename}' を読み込みました")
                break
            except (FileNotFoundError, UnicodeDecodeError):
                continue

        if df is None:
            st.error("❌ データファイルが見つかりません")
            st.info("'Sample - Superstore.csv' または 'Superstore.csv' ファイルが同じディレクトリにあることを確認してください")
            st.stop()

    except Exception as e:
        st.error(f"データ読み込みエラー: {str(e)}")
        st.stop()

    # データの基本チェック
    required_columns = ['Order Date', 'Sales', 'Profit', 'Region', 'Category']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"必要な列が不足しています: {missing_columns}")
        st.stop()

    # 日付変換と追加的な特徴量作成
    try:
        # 日付変換
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
        if 'Ship Date' in df.columns:
            df['Ship Date'] = pd.to_datetime(df['Ship Date'], errors='coerce')
        else:
            df['Ship Date'] = df['Order Date']  # Ship Dateがない場合はOrder Dateを使用

        # 無効な日付を除去
        df = df.dropna(subset=['Order Date'])

        # 基本的な時間特徴量
        df['Year'] = df['Order Date'].dt.year
        df['Month'] = df['Order Date'].dt.month
        df['Quarter'] = df['Order Date'].dt.quarter
        df['Weekday'] = df['Order Date'].dt.day_name()
        df['YearMonth'] = df['Order Date'].dt.to_period('M').astype(str)

        # 配送日数計算
        df['Shipping_Days'] = (df['Ship Date'] - df['Order Date']).dt.days
        df['Shipping_Days'] = df['Shipping_Days'].fillna(0)  # NaN値を0に置換

    except Exception as e:
        st.error(f"日付処理エラー: {str(e)}")
        st.stop()

    # 安全な利益率計算
    try:
        df['Profit_Margin'] = 0.0
        # ゼロ除算を避けて利益率を計算
        valid_sales_mask = (df['Sales'] != 0) & (df['Sales'].notna()) & (df['Profit'].notna())
        if valid_sales_mask.any():
            df.loc[valid_sales_mask, 'Profit_Margin'] = (
                df.loc[valid_sales_mask, 'Profit'] / df.loc[valid_sales_mask, 'Sales'] * 100
            ).round(2)

        # 無限値と異常値を修正
        df['Profit_Margin'] = df['Profit_Margin'].replace([np.inf, -np.inf], 0)
        df['Profit_Margin'] = df['Profit_Margin'].clip(-1000, 1000)  # -1000%から1000%に制限

    except Exception as e:
        st.error(f"利益率計算エラー: {str(e)}")
        df['Profit_Margin'] = 0.0

    # データ型の確認と修正
    numeric_columns = ['Sales', 'Profit', 'Quantity', 'Discount']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

# 安全なグラフ作成関数
def safe_histogram(data, column, title, nbins=50, x_label=None, y_label='頻度'):
    """安全なヒストグラム作成"""
    try:
        if column not in data.columns:
            st.warning(f"列 '{column}' が見つかりません")
            return None

        clean_data = data[column].dropna()
        if len(clean_data) == 0:
            st.warning(f"{title}: データが空です")
            return None

        # plotlyのヒストグラムは nbins パラメータを使用
        fig = px.histogram(
            x=clean_data,
            nbins=min(nbins, len(clean_data.unique())),
            title=title,
            labels={'x': x_label or column, 'y': y_label}
        )
        return fig
    except Exception as e:
        st.error(f"{title}の作成でエラー: {str(e)}")
        return None

def safe_scatter(data, x_col, y_col, color_col=None, title="", sample_size=1000):
    """安全な散布図作成"""
    try:
        # データのサンプリングと前処理
        if len(data) > sample_size:
            sample_data = data.sample(n=sample_size, random_state=42)
        else:
            sample_data = data.copy()

        # 必要な列の存在確認
        required_cols = [x_col, y_col]
        if color_col:
            required_cols.append(color_col)

        missing_cols = [col for col in required_cols if col not in sample_data.columns]
        if missing_cols:
            st.warning(f"列が見つかりません: {missing_cols}")
            return None

        # NaN値と異常値を除去
        sample_data = sample_data.dropna(subset=required_cols)
        if len(sample_data) == 0:
            st.warning(f"{title}: 有効なデータがありません")
            return None

        # 散布図作成
        fig_kwargs = {
            'data_frame': sample_data,
            'x': x_col,
            'y': y_col,
            'title': title,
            'opacity': 0.7
        }

        if color_col:
            fig_kwargs['color'] = color_col

        fig = px.scatter(**fig_kwargs)
        return fig

    except Exception as e:
        st.error(f"{title}の作成でエラー: {str(e)}")
        return None

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
    try:
        years = sorted(df['Year'].dropna().unique())
        selected_years = st.sidebar.multiselect(
            "📅 年を選択",
            options=years,
            default=years
        )
    except:
        selected_years = []

    # 地域フィルター
    try:
        regions = sorted(df['Region'].dropna().unique())
        selected_regions = st.sidebar.multiselect(
            "🌍 地域を選択",
            options=regions,
            default=regions
        )
    except:
        selected_regions = []

    # カテゴリフィルター
    try:
        categories = sorted(df['Category'].dropna().unique())
        selected_categories = st.sidebar.multiselect(
            "📦 カテゴリを選択",
            options=categories,
            default=categories
        )
    except:
        selected_categories = []

    # データフィルタリング
    filtered_df = df.copy()

    if selected_years:
        filtered_df = filtered_df[filtered_df['Year'].isin(selected_years)]
    if selected_regions:
        filtered_df = filtered_df[filtered_df['Region'].isin(selected_regions)]
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]

    # データが空の場合の処理
    if len(filtered_df) == 0:
        st.warning("⚠️ 選択した条件に該当するデータがありません。フィルターを調整してください。")
        return

    # 損失データの計算
    try:
        loss_orders = filtered_df[filtered_df['Profit'] < 0]
        total_loss = abs(loss_orders['Profit'].sum()) if len(loss_orders) > 0 else 0
        loss_rate = len(loss_orders) / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
    except:
        total_loss = 0
        loss_rate = 0

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
        total_orders = filtered_df['Order ID'].nunique() if 'Order ID' in filtered_df.columns else len(filtered_df)
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
        try:
            monthly_sales = filtered_df.groupby('YearMonth')['Sales'].sum().reset_index()
            if len(monthly_sales) > 0:
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
        except Exception as e:
            st.error(f"月別売上トレンドエラー: {str(e)}")

        # 3つのコラム
        col1, col2, col3 = st.columns(3)

        with col1:
            # 地域別売上
            try:
                region_sales = filtered_df.groupby('Region')['Sales'].sum().reset_index()
                if len(region_sales) > 0:
                    fig_region = px.pie(
                        region_sales,
                        values='Sales',
                        names='Region',
                        title='🌍 地域別売上分布'
                    )
                    st.plotly_chart(fig_region, use_container_width=True)
            except Exception as e:
                st.error(f"地域別売上エラー: {str(e)}")

        with col2:
            # 地域別顧客数
            try:
                if 'Customer ID' in filtered_df.columns:
                    region_customers = filtered_df.groupby('Region')['Customer ID'].nunique().reset_index()
                    region_customers.columns = ['Region', 'Customer_Count']

                    if len(region_customers) > 0:
                        fig_region_customers = px.bar(
                            region_customers,
                            x='Region',
                            y='Customer_Count',
                            title='👥 地域別顧客数',
                            color='Customer_Count',
                            color_continuous_scale='Greens',
                            text='Customer_Count'
                        )
                        fig_region_customers.update_traces(texttemplate='%{text}', textposition='outside')
                        st.plotly_chart(fig_region_customers, use_container_width=True)
                else:
                    st.info("顧客IDデータが利用できません")
            except Exception as e:
                st.error(f"地域別顧客数エラー: {str(e)}")

        with col3:
            # カテゴリ別売上
            try:
                category_sales = filtered_df.groupby('Category')['Sales'].sum().reset_index()
                if len(category_sales) > 0:
                    fig_category = px.bar(
                        category_sales,
                        x='Category',
                        y='Sales',
                        title='📦 カテゴリ別売上',
                        color='Sales',
                        color_continuous_scale='Blues'
                    )
                    st.plotly_chart(fig_category, use_container_width=True)
            except Exception as e:
                st.error(f"カテゴリ別売上エラー: {str(e)}")

    with tab2:
        # 年別比較
        try:
            yearly_sales = filtered_df.groupby('Year').agg({
                'Sales': 'sum',
                'Profit': 'sum'
            }).reset_index()

            if 'Order ID' in filtered_df.columns:
                yearly_orders = filtered_df.groupby('Year')['Order ID'].nunique().reset_index()
                yearly_sales = yearly_sales.merge(yearly_orders, on='Year', how='left')

            if len(yearly_sales) > 0:
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
        except Exception as e:
            st.error(f"年別売上エラー: {str(e)}")

        # セグメント分析
        col1, col2 = st.columns(2)

        with col1:
            try:
                if 'Segment' in filtered_df.columns:
                    segment_sales = filtered_df.groupby('Segment')['Sales'].sum().reset_index()
                    if len(segment_sales) > 0:
                        fig_segment = px.pie(
                            segment_sales,
                            values='Sales',
                            names='Segment',
                            title='👥 セグメント別売上'
                        )
                        st.plotly_chart(fig_segment, use_container_width=True)
                else:
                    st.info("セグメント情報が利用できません")
            except Exception as e:
                st.error(f"セグメント分析エラー: {str(e)}")

        with col2:
            # トップ10製品
            try:
                if 'Product Name' in filtered_df.columns:
                    top_products = filtered_df.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index()
                    if len(top_products) > 0:
                        fig_products = px.bar(
                            top_products,
                            x='Sales',
                            y='Product Name',
                            orientation='h',
                            title='🏆 トップ10製品（売上）'
                        )
                        fig_products.update_layout(height=400)
                        st.plotly_chart(fig_products, use_container_width=True)
                else:
                    st.info("商品名情報が利用できません")
            except Exception as e:
                st.error(f"トップ製品分析エラー: {str(e)}")

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
                try:
                    region_loss = loss_orders.groupby('Region')['Profit'].sum().abs().reset_index()
                    region_loss.columns = ['Region', 'Loss']
                    if len(region_loss) > 0:
                        fig_region_loss = px.bar(
                            region_loss,
                            x='Region',
                            y='Loss',
                            title='🌍 地域別損失額',
                            color='Loss',
                            color_continuous_scale='Reds'
                        )
                        st.plotly_chart(fig_region_loss, use_container_width=True)
                except Exception as e:
                    st.error(f"地域別損失エラー: {str(e)}")

            with col2:
                # カテゴリ別損失
                try:
                    category_loss = loss_orders.groupby('Category')['Profit'].sum().abs().reset_index()
                    category_loss.columns = ['Category', 'Loss']
                    if len(category_loss) > 0:
                        fig_category_loss = px.pie(
                            category_loss,
                            values='Loss',
                            names='Category',
                            title='📦 カテゴリ別損失分布',
                            color_discrete_sequence=px.colors.sequential.Reds_r
                        )
                        st.plotly_chart(fig_category_loss, use_container_width=True)
                except Exception as e:
                    st.error(f"カテゴリ別損失エラー: {str(e)}")

        else:
            st.success("🎉 選択された期間・条件では損失は発生していません！")

    with tab4:
        st.subheader("🚀 高度なビジネス分析")

        # 地域別詳細分析
        st.markdown("### 🌍 地域別詳細分析")
        try:
            if 'Customer ID' in filtered_df.columns:
                # 地域別総合分析
                regional_analysis = filtered_df.groupby('Region').agg({
                    'Sales': ['sum', 'mean'],
                    'Profit': ['sum', 'mean'],
                    'Customer ID': 'nunique',
                    'Discount': 'mean'
                }).round(2)

                regional_analysis.columns = ['総売上', '平均売上', '総利益', '平均利益', '顧客数', '平均割引率']
                regional_analysis['利益率'] = (regional_analysis['総利益'] / regional_analysis['総売上'] * 100).round(2)
                regional_analysis['顧客単価'] = (regional_analysis['総売上'] / regional_analysis['顧客数']).round(2)

                col1, col2 = st.columns(2)

                with col1:
                    # 地域別顧客数と売上の関係
                    fig_region_scatter = px.scatter(
                        x=regional_analysis['顧客数'],
                        y=regional_analysis['総売上'],
                        size=regional_analysis['利益率'],
                        hover_name=regional_analysis.index,
                        title='📊 地域別：顧客数 vs 売上（バブルサイズ=利益率）',
                        labels={'x': '顧客数', 'y': '総売上'},
                        color=regional_analysis['利益率'],
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig_region_scatter, use_container_width=True)

                with col2:
                    # 地域別顧客単価
                    fig_customer_value = px.bar(
                        x=regional_analysis.index,
                        y=regional_analysis['顧客単価'],
                        title='💰 地域別顧客単価',
                        labels={'x': '地域', 'y': '顧客単価 ($)'},
                        color=regional_analysis['顧客単価'],
                        color_continuous_scale='Blues',
                        text=regional_analysis['顧客単価']
                    )
                    fig_customer_value.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                    st.plotly_chart(fig_customer_value, use_container_width=True)

                # 地域別統計テーブル
                st.subheader("📋 地域別統合レポート")
                st.dataframe(regional_analysis, use_container_width=True)

            else:
                st.info("顧客IDデータが利用できないため、地域別詳細分析をスキップします")
        except Exception as e:
            st.error(f"地域別詳細分析エラー: {str(e)}")

        st.markdown("---")

        # 配送方法分析
        if 'Ship Mode' in filtered_df.columns:
            st.markdown("### 📦 配送方法分析")
            try:
                shipping_analysis = filtered_df.groupby('Ship Mode').agg({
                    'Sales': 'sum',
                    'Profit': 'sum',
                    'Shipping_Days': 'mean'
                }).round(2)

                if 'Order ID' in filtered_df.columns:
                    order_counts = filtered_df.groupby('Ship Mode')['Order ID'].count()
                    shipping_analysis['注文数'] = order_counts

                shipping_analysis.columns = ['売上', '利益', '平均配送日数', '注文数']
                shipping_analysis['利益率'] = (shipping_analysis['利益'] / shipping_analysis['売上'] * 100).round(2)

                col1, col2 = st.columns(2)

                with col1:
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
                    st.dataframe(shipping_analysis, use_container_width=True)

            except Exception as e:
                st.error(f"配送方法分析エラー: {str(e)}")

        # 利益率分析
        st.markdown("### 🎯 利益率分析")
        col1, col2 = st.columns(2)

        with col1:
            # 利益率の分布
            fig = safe_histogram(
                filtered_df,
                'Profit_Margin',
                '📈 利益率の分布',
                nbins=50,
                x_label='利益率(%)'
            )
            if fig:
                try:
                    mean_profit = filtered_df['Profit_Margin'].mean()
                    fig.add_vline(x=mean_profit, line_dash="dash", line_color="red")
                except:
                    pass
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # カテゴリ別利益率
            try:
                category_profit = filtered_df.groupby('Category')['Profit_Margin'].mean().reset_index()
                category_profit = category_profit.dropna()

                if len(category_profit) > 0:
                    fig_category_profit = px.bar(
                        category_profit,
                        x='Category',
                        y='Profit_Margin',
                        title='📦 カテゴリ別平均利益率',
                        color='Profit_Margin',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig_category_profit, use_container_width=True)
            except Exception as e:
                st.error(f"カテゴリ別利益率エラー: {str(e)}")

        # 季節性分析
        st.markdown("### 🍃 季節性分析")
        col1, col2 = st.columns(2)

        with col1:
            # 四半期別分析
            try:
                quarterly_sales = filtered_df.groupby(['Year', 'Quarter'])['Sales'].sum().reset_index()
                quarterly_sales['Year_Quarter'] = quarterly_sales['Year'].astype(str) + '-Q' + quarterly_sales['Quarter'].astype(str)

                if len(quarterly_sales) > 0:
                    fig_quarterly = px.line(
                        quarterly_sales,
                        x='Year_Quarter',
                        y='Sales',
                        title='📅 四半期別売上トレンド',
                        markers=True
                    )
                    fig_quarterly.update_xaxes(type='category')
                    st.plotly_chart(fig_quarterly, use_container_width=True)
            except Exception as e:
                st.error(f"四半期分析エラー: {str(e)}")

        with col2:
            # 曜日別パターン
            try:
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekday_sales = filtered_df.groupby('Weekday')['Sales'].mean().reindex(weekday_order, fill_value=0).reset_index()

                if len(weekday_sales) > 0:
                    fig_weekday = px.bar(
                        weekday_sales,
                        x='Weekday',
                        y='Sales',
                        title='📅 曜日別平均売上',
                        color='Sales',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_weekday, use_container_width=True)
            except Exception as e:
                st.error(f"曜日分析エラー: {str(e)}")

        # 割引分析
        if 'Discount' in filtered_df.columns:
            st.markdown("### 💸 割引効果分析")
            col1, col2 = st.columns(2)

            with col1:
                # 割引率 vs 売上の関係
                fig = safe_scatter(
                    filtered_df,
                    'Discount',
                    'Sales',
                    'Category',
                    '📊 割引率 vs 売上の関係'
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 割引率別利益率
                try:
                    valid_discount = filtered_df[(filtered_df['Discount'] >= 0) & (filtered_df['Discount'] <= 1)]
                    if len(valid_discount) > 5:  # 最低5件のデータが必要
                        discount_bins = pd.cut(valid_discount['Discount'], bins=5)
                        discount_profit = valid_discount.groupby(discount_bins)['Profit_Margin'].mean().reset_index()
                        discount_profit['Discount_Range'] = discount_profit['Discount'].astype(str)

                        fig_discount_profit = px.bar(
                            discount_profit,
                            x='Discount_Range',
                            y='Profit_Margin',
                            title='📈 割引率別平均利益率',
                            color='Profit_Margin',
                            color_continuous_scale='RdYlGn'
                        )
                        st.plotly_chart(fig_discount_profit, use_container_width=True)
                    else:
                        st.info("割引データが不十分です")
                except Exception as e:
                    st.error(f"割引分析エラー: {str(e)}")

        # 相関分析
        st.markdown("### 🔗 相関分析")
        try:
            numeric_cols = ['Sales', 'Profit', 'Profit_Margin']
            if 'Quantity' in filtered_df.columns:
                numeric_cols.append('Quantity')
            if 'Discount' in filtered_df.columns:
                numeric_cols.append('Discount')
            if 'Shipping_Days' in filtered_df.columns:
                numeric_cols.append('Shipping_Days')

            available_cols = [col for col in numeric_cols if col in filtered_df.columns]
            correlation_data = filtered_df[available_cols].select_dtypes(include=[np.number])

            if len(correlation_data.columns) >= 2:
                correlation_matrix = correlation_data.corr()

                fig_corr = px.imshow(
                    correlation_matrix,
                    text_auto=True,
                    aspect="auto",
                    title="🔗 数値変数間の相関係数",
                    color_continuous_scale='RdBu_r'
                )
                st.plotly_chart(fig_corr, use_container_width=True)

                st.markdown("""
                **相関係数の解釈:**
                - 1.0：完全な正の相関
                - 0.0：相関なし
                - -1.0：完全な負の相関
                """)
            else:
                st.info("相関分析に十分な数値データがありません")
        except Exception as e:
            st.error(f"相関分析エラー: {str(e)}")

    with tab5:
        st.subheader("📋 データサマリー")

        # データ基本情報
        col1, col2, col3 = st.columns(3)

        with col1:
            st.info(f"**レコード数**: {len(filtered_df):,}")

        with col2:
            try:
                start_date = filtered_df['Order Date'].min().strftime('%Y-%m-%d')
                end_date = filtered_df['Order Date'].max().strftime('%Y-%m-%d')
                st.info(f"**期間**: {start_date} ～ {end_date}")
            except:
                st.info("**期間**: データなし")

        with col3:
            customer_count = filtered_df['Customer ID'].nunique() if 'Customer ID' in filtered_df.columns else "N/A"
            st.info(f"**顧客数**: {customer_count:,}" if isinstance(customer_count, int) else f"**顧客数**: {customer_count}")

        # 統計情報
        st.subheader("📊 統計情報")
        try:
            stats = filtered_df.groupby(['Region', 'Category']).agg({
                'Sales': ['sum', 'mean', 'count'],
                'Profit': ['sum', 'mean']
            }).round(2)

            stats.columns = ['売上合計', '平均売上', '取引数', '利益合計', '平均利益']
            st.dataframe(stats, use_container_width=True)
        except Exception as e:
            st.error(f"統計情報エラー: {str(e)}")

        # 生データ表示
        st.subheader("📄 生データ（先頭100件）")
        try:
            display_columns = ['Order Date', 'Region', 'Category', 'Sales', 'Profit']
            if 'Customer Name' in filtered_df.columns:
                display_columns.insert(1, 'Customer Name')
            if 'Product Name' in filtered_df.columns:
                display_columns.insert(-2, 'Product Name')

            available_display_cols = [col for col in display_columns if col in filtered_df.columns]
            st.dataframe(
                filtered_df[available_display_cols].head(100),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"データ表示エラー: {str(e)}")

# 実行
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"アプリケーション実行エラー: {str(e)}")
        st.info("ページを再読み込みしてください")

# フッター
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
<p><strong>Superstore Analytics Dashboard</strong></p>
<p>Built with ❤️ using Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)
