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
    page_title="Superstore Dashboard",
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
            ('Superstore.csv', 'latin-1')
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
    st.title("📊 Superstore Dashboard")
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

    # セグメントフィルター
    try:
        if 'Segment' in df.columns:
            segments = sorted(df['Segment'].dropna().unique())
            selected_segments = st.sidebar.multiselect(
                "👥 顧客セグメントを選択",
                options=segments,
                default=segments
            )
        else:
            selected_segments = []
    except:
        selected_segments = []

    # 配送方法フィルター
    try:
        if 'Ship Mode' in df.columns:
            ship_modes = sorted(df['Ship Mode'].dropna().unique())
            selected_ship_modes = st.sidebar.multiselect(
                "🚚 配送方法を選択",
                options=ship_modes,
                default=ship_modes
            )
        else:
            selected_ship_modes = []
    except:
        selected_ship_modes = []


    # 利益フィルター
    st.sidebar.markdown("---")
    profit_filter = st.sidebar.radio(
        "📊 利益フィルター",
        options=["すべて", "利益のみ", "損失のみ"],
        index=0
    )

    # データフィルタリング
    filtered_df = df.copy()

    # 基本フィルター
    if selected_years:
        filtered_df = filtered_df[filtered_df['Year'].isin(selected_years)]
    if selected_regions:
        filtered_df = filtered_df[filtered_df['Region'].isin(selected_regions)]
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]

    # 新しいフィルター
    if selected_segments and 'Segment' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Segment'].isin(selected_segments)]
    if selected_ship_modes and 'Ship Mode' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Ship Mode'].isin(selected_ship_modes)]


    # 利益フィルター
    if profit_filter == "利益のみ":
        filtered_df = filtered_df[filtered_df['Profit'] > 0]
    elif profit_filter == "損失のみ":
        filtered_df = filtered_df[filtered_df['Profit'] < 0]

    # データが空の場合の処理
    if len(filtered_df) == 0:
        st.warning("⚠️ 選択した条件に該当するデータがありません。フィルターを調整してください。")
        return

    # フィルター情報の表示
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 現在のフィルター状況")
    st.sidebar.info(f"**表示中のデータ**: {len(filtered_df):,}件 / {len(df):,}件")

    if len(filtered_df) < len(df):
        filter_info = []
        if len(selected_years) < len(years):
            filter_info.append(f"年: {len(selected_years)}件選択")
        if len(selected_regions) < len(regions):
            filter_info.append(f"地域: {len(selected_regions)}件選択")
        if len(selected_categories) < len(categories):
            filter_info.append(f"カテゴリ: {len(selected_categories)}件選択")
        if selected_segments and len(selected_segments) < len(segments):
            filter_info.append(f"セグメント: {len(selected_segments)}件選択")
        if selected_ship_modes and len(selected_ship_modes) < len(ship_modes):
            filter_info.append(f"配送: {len(selected_ship_modes)}件選択")
        if profit_filter != "すべて":
            filter_info.append(f"利益: {profit_filter}")

        if filter_info:
            st.sidebar.write("**適用中のフィルター:**")
            for info in filter_info:
                st.sidebar.write(f"• {info}")

    # リセットボタン
    if st.sidebar.button("🔄 フィルターをリセット"):
        try:
            st.rerun()
        except:
            st.experimental_rerun()

    # 損失データの計算
    try:
        loss_orders = filtered_df[filtered_df['Profit'] < 0]
        total_loss = abs(loss_orders['Profit'].sum()) if len(loss_orders) > 0 else 0
        loss_rate = len(loss_orders) / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
    except:
        total_loss = 0
        loss_rate = 0
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
    tab1, tab2, tab3, tab4, tab5= st.tabs(["📋 分析レポート", "📈 売上分析", "🎯 詳細分析", "⚠️ 損失分析", "🚀 高度な分析"])

    with tab1:
        st.title("📊 分析レポート")
        st.markdown("---")

        # 現状
        st.header("📈 現状")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総売上", "$2,297,200")
        with col2:
            st.metric("総利益", "$286,397")
        with col3:
            st.metric("利益率", "12.47%")
        with col4:
            st.metric("損失率", "18.7%", delta="-$156,131", delta_color="inverse")

        st.markdown("---")

        # 問題点
        st.header("⚠️ 問題点")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("1. 損失商品")
            problem1_df = pd.DataFrame({
                '商品': ['Tables', 'Bookcases', 'Supplies'],
                '利益率': ['-8.56%', '-3.02%', '-2.55%'],
                '損失額': ['$17,725', '$3,473', '$1,189']
            })
            st.dataframe(problem1_df, use_container_width=True)

            st.subheader("2. カテゴリ別利益率")
            problem3_df = pd.DataFrame({
                'カテゴリ': ['Furniture', 'Office Supplies', 'Technology'],
                '利益率': ['2.49%', '17.04%', '17.40%']
            })
            st.dataframe(problem3_df, use_container_width=True)

        with col2:
            st.subheader("3. 過度な割引")
            problem2_df = pd.DataFrame({
                '割引率': ['50%', '60%', '70%', '80%'],
                '平均損失/件': ['$310', '$43', '$96', '$102']
            })
            st.dataframe(problem2_df, use_container_width=True)

            st.subheader("4. 地域別利益率")
            problem4_df = pd.DataFrame({
                '地域': ['West', 'East', 'South', 'Central'],
                '利益率': ['14.94%', '13.48%', '11.93%', '7.92%']
            })
            st.dataframe(problem4_df, use_container_width=True)


        st.markdown("---")

        # 推奨事項
        st.header("💡 推奨事項")

        st.error("""
**対応:**
- Tables・Bookcaseの出荷停止
- 50%超割引の承認制導入
        """)

        discount_rec = pd.DataFrame({
            'カテゴリ': ['Furniture', 'Office Supplies', 'Technology'],
            '現在上限': ['50%', '80%', '70%'],
            '推奨上限': ['15%', '25%', '30%']
        })
        st.dataframe(discount_rec, use_container_width=True)

        st.markdown("---")

        # 期待効果の計算（実データに基づく）
        st.subheader("📈 期待効果（実データに基づく計算）")

        try:
            # 現在の損失額を計算
            current_total_loss = abs(filtered_df[filtered_df['Profit'] < 0]['Profit'].sum())

            # シナリオ1: 高割引率（50%以上）を制限した場合
            high_discount_loss = abs(filtered_df[(filtered_df['Profit'] < 0) & (filtered_df['Discount'] >= 0.5)]['Profit'].sum())

            # シナリオ2: 損失商品（Tables, Bookcases）を停止した場合
            if 'Sub-Category' in filtered_df.columns:
                problem_products_loss = abs(filtered_df[
                    (filtered_df['Profit'] < 0) &
                    (filtered_df['Sub-Category'].isin(['Tables', 'Bookcases']))
                ]['Profit'].sum())
            else:
                problem_products_loss = 0

            # シナリオ3: カテゴリ別割引率を推奨上限に制限した場合の推定効果
            furniture_excessive_discount_loss = abs(filtered_df[
                (filtered_df['Profit'] < 0) &
                (filtered_df['Category'] == 'Furniture') &
                (filtered_df['Discount'] > 0.15)
            ]['Profit'].sum()) if 'Category' in filtered_df.columns else 0

            # 総改善見込み（保守的な見積もり: 60%の削減）
            total_potential_improvement = (high_discount_loss + problem_products_loss + furniture_excessive_discount_loss) * 0.6

            # データの期間を取得
            date_range_months = (filtered_df['Order Date'].max() - filtered_df['Order Date'].min()).days / 30.44
            monthly_improvement = total_potential_improvement / date_range_months if date_range_months > 0 else 0

            # 期待効果テーブル
            effect_df = pd.DataFrame({
                '期間': ['3ヶ月', '6ヶ月', '12ヶ月'],
                '月間改善額': [
                    f'${monthly_improvement:,.0f}',
                    f'${monthly_improvement:,.0f}',
                    f'${monthly_improvement:,.0f}'
                ],
                '累計改善': [
                    f'${monthly_improvement * 3:,.0f}',
                    f'${monthly_improvement * 6:,.0f}',
                    f'${monthly_improvement * 12:,.0f}'
                ],
                'ROI': [
                    f'{(monthly_improvement * 3 / current_total_loss * 100):.1f}%' if current_total_loss > 0 else 'N/A',
                    f'{(monthly_improvement * 6 / current_total_loss * 100):.1f}%' if current_total_loss > 0 else 'N/A',
                    f'{(monthly_improvement * 12 / current_total_loss * 100):.1f}%' if current_total_loss > 0 else 'N/A'
                ]
            })
            st.dataframe(effect_df, use_container_width=True)

            # 改善案の詳細
            st.markdown("#### 💡 改善案の内訳")
            scenario_df = pd.DataFrame({
                'シナリオ': [
                    '高割引率（50%以上）の制限',
                    '損失商品（Tables/Bookcases）の出荷停止',
                    'Furniture割引上限15%への制限'
                ],
                '現在の損失額': [
                    f'${high_discount_loss:,.0f}',
                    f'${problem_products_loss:,.0f}',
                    f'${furniture_excessive_discount_loss:,.0f}'
                ],
                '期待削減率': ['80%', '100%', '50%'],
                '期待改善額': [
                    f'${high_discount_loss * 0.8:,.0f}',
                    f'${problem_products_loss * 1.0:,.0f}',
                    f'${furniture_excessive_discount_loss * 0.5:,.0f}'
                ]
            })
            st.dataframe(scenario_df, use_container_width=True)

            st.info(f"""
            **計算根拠:**
            - 現在の総損失額: ${current_total_loss:,.0f}
            - データ期間: {date_range_months:.1f}ヶ月
            - 総改善見込み: ${total_potential_improvement:,.0f}
            - 月間改善見込み: ${monthly_improvement:,.0f}
            """)

        except Exception as e:
            st.error(f"期待効果計算エラー: {str(e)}")
            st.warning("期待効果を計算できませんでした。データを確認してください。")
    with tab2:
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
        col1, col2 = st.columns(2)

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

    with tab3:
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

    with tab4:
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

    with tab5:
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

                # 地域別顧客単価（単独表示）
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
