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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 分析レポート", "📈 売上分析", "🎯 詳細分析", "⚠️ 損失分析", "🚀 高度な分析", "📊 データ"])

    with tab1:
        st.title("📊 Superstore事業改善提案書")
        st.markdown("---")

        # エグゼクティブサマリー
        st.header("🎯 エグゼクティブサマリー")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("現状認識")
            st.metric("総売上", "$2,297,200", help="年間売上高")
            st.metric("総利益", "$286,397", "利益率 12.47%")
            st.metric("重大課題", "18.7%の取引で損失", delta="-$156,131", delta_color="inverse")
            st.info("💡 **改善機会**: 利益率を18%以上に向上可能")

        with col2:
            st.subheader("改善効果予測")
            st.metric("年間利益増", "$500,000以上", "+66%向上")
            st.metric("損失削減", "68%減", "$156,131 → $50,000以下", delta_color="normal")
            st.metric("利益率向上", "+5.5ポイント", "12.47% → 18%")
            st.metric("投資回収期間", "6ヶ月", help="ROI 600%以上")

        st.markdown("---")

        # 主要課題
        st.header("📊 分析結果に基づく主要課題")

        # 課題1: 収益性
        st.subheader("🔴 1. 収益性の課題（緊急度：★★★）")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**深刻な損失商品**")
            st.code("""
商品別利益率:
• Tables: -8.56% ($17,725損失)
• Bookcases: -3.02% ($3,473損失)
• Supplies: -2.55% ($1,189損失)
            """)

        with col2:
            st.markdown("**Furnitureカテゴリの構造問題**")
            st.warning("""
- 利益率: わずか2.49% (他カテゴリは17%台)
- 損失取引率: 33.7% (3件に1件が損失)
- 根本原因: 高配送コスト + 過度な割引
            """)

        # 課題2: 割引戦略
        st.subheader("🔴 2. 割引戦略の非効率性（緊急度：★★★）")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**破綻している割引構造**")
            st.code("""
割引率別損失状況:
• 50%割引: 平均$310損失/件
• 60%割引: 平均$43損失/件
• 70%割引: 平均$96損失/件
• 80%割引: 平均$102損失/件
            """)

        with col2:
            st.markdown("**カテゴリ別割引問題**")
            st.error("""
- Technology 70%割引: 平均$851損失
- Office Supplies 80%割引: 平均$102損失
- Furniture 40-50%割引: 平均$216-238損失
            """)

        # 課題3: 地域・配送
        st.subheader("🔶 3. 地域・配送の最適化不足（緊急度：★★）")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**地域格差**")
            region_profit_data = {
                '地域': ['West', 'East', 'South', 'Central'],
                '利益率': [14.94, 13.48, 11.93, 7.92],
                '評価': ['優秀', '良好', '標準', '要改善']
            }
            st.dataframe(pd.DataFrame(region_profit_data), use_container_width=True)

        with col2:
            st.markdown("**配送効率問題**")
            st.info("""
- 配送遅延率: 7日超で一部地域に集中
- 配送ROI: 高速配送のコストと収益バランス未最適化
- 顧客満足度: 配送遅延によるリピート率低下
            """)

        st.markdown("---")

        # 戦略的改善提案
        st.header("💡 戦略的改善提案")

        # 改善戦略A
        st.subheader("🎯 A. 収益性改善戦略")

        tab_a1, tab_a2 = st.tabs(["問題商品の戦略転換", "Furnitureカテゴリ改革"])

        with tab_a1:
            st.markdown("**Tables・Bookcases対策**")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.success("**✅ 即座の対応**")
                st.markdown("""
- 現行商品の販売停止検討
- 在庫クリアランス（最小損失での処分）
                """)

            with col2:
                st.info("**✅ 中期対応**")
                st.markdown("""
- サプライヤー交渉（仕入コスト20%削減目標）
- 高付加価値商品への転換
- バンドル販売戦略
                """)

            with col3:
                st.warning("**✅ 長期対応**")
                st.markdown("""
- プレミアムライン開発
- カスタマイゼーションサービス導入
                """)

        with tab_a2:
            st.markdown("**収益構造の抜本改革**")

            furniture_target = pd.DataFrame({
                '項目': ['利益率目標', '商品ミックス見直し', '配送最適化', '価格戦略'],
                '現状': ['2.49%', '未整備', '非効率', '割引重視'],
                '目標': ['12%以上', '高利益商品比率60%', '大型商品専用配送', '付加価値重視']
            })
            st.dataframe(furniture_target, use_container_width=True)

        # 改善戦略B
        st.subheader("🎯 B. 割引戦略最適化")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**データ分析に基づく最適割引率**")
            discount_limits = pd.DataFrame({
                'カテゴリ': ['Furniture', 'Office Supplies', 'Technology'],
                '現在の割引上限': ['50%', '80%', '70%'],
                '推奨割引上限': ['15%', '25%', '30%'],
                '削減幅': ['-35%', '-55%', '-40%']
            })
            st.dataframe(discount_limits, use_container_width=True)

        with col2:
            st.markdown("**条件付き割引システム**")
            st.code("""
スマート割引ルール:
• 購入金額連動: $500以上で10%
               $1000以上で15%
• 数量連動: 10個以上で追加5%
• 季節限定: Q4のみ最大割引適用
• 顧客セグメント連動: VIP顧客に特別割引
            """)

        st.markdown("---")

        # 実装ロードマップ
        st.header("📅 実装ロードマップ")

        phase_tab1, phase_tab2, phase_tab3 = st.tabs(["🚨 Phase 1 (1-3ヶ月)", "📈 Phase 2 (3-6ヶ月)", "🚀 Phase 3 (6-12ヶ月)"])

        with phase_tab1:
            st.subheader("緊急改善")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Week 1-2**")
                st.markdown("""
- Tables・Bookcases新規販売停止
- 50%超割引の承認制導入
- 日次損失モニタリング開始
- 緊急対策チーム設置
                """)

            with col2:
                st.markdown("**Week 3-8**")
                st.markdown("""
- カテゴリ別割引上限設定
- 条件付き割引システム設計
- 競合価格調査開始
- 利益率モニタリング導入
                """)

            with col3:
                st.markdown("**Week 9-12**")
                st.markdown("""
- 配送遅延根本原因分析
- 地域別配送戦略策定
- ROI基準配送選択システム
- 在庫管理システム改善
                """)

        with phase_tab2:
            st.subheader("戦略展開")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Month 4-5: 商品戦略改革**")
                st.markdown("""
- 新商品ライン開発プロジェクト開始
- 高利益商品の販促キャンペーン
- バンドル商品企画・テスト販売
- サプライヤー交渉（コスト削減）
                """)

            with col2:
                st.markdown("**Month 5-6: 顧客戦略実装**")
                st.markdown("""
- RFMセグメント別マーケティング
- VIP顧客プログラム正式ローンチ
- パーソナライゼーション導入
- 顧客満足度調査・改善サイクル
                """)

        with phase_tab3:
            st.subheader("変革実現")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Month 7-9: システム高度化**")
                st.markdown("""
- 動的価格設定システム本格導入
- AI需要予測モデル運用開始
- 在庫最適化システム高度化
- リアルタイムダッシュボード完成
                """)

            with col2:
                st.markdown("**Month 10-12: 組織・文化変革**")
                st.markdown("""
- データアナリティクスチーム拡充
- 地域戦略組織の再編成
- 成果連動評価制度導入
- 継続改善文化の定着
                """)

        st.markdown("---")

        # 期待効果・ROI
        st.header("💰 期待効果・ROI予測")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("📊 短期効果 (3ヶ月)")
            st.metric("月間改善額", "$72,000")
            st.markdown("""
**内訳:**
- 損失削減: $39,000/月
- 割引最適化: $25,000/月
- 配送効率化: $8,000/月
            """)
            st.metric("ROI", "116%")

        with col2:
            st.subheader("📈 中期効果 (6ヶ月)")
            st.metric("売上成長", "+12%", "$275,664増")
            st.metric("合計価値創造", "$700,000+")
            st.metric("ROI", "600%以上")

        with col3:
            st.subheader("🚀 長期効果 (12ヶ月)")
            st.metric("年間売上", "$2,642,000+", "+15%成長")
            st.metric("年間利益", "$475,000+", "+66%向上")
            st.metric("利益率", "18%達成")

        st.markdown("---")

        # 最優先アクション
        st.header("⚡ 最優先アクション")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚨 今すぐ実行（24時間以内）")
            st.error("""
**緊急損失ストップ:**
- Tables商品新規注文停止指示
- Bookcases商品新規注文停止指示
- 50%超割引申請の承認制導入
- 日次損失レポート開始
- 緊急対策チーム招集
            """)

        with col2:
            st.subheader("📈 第1週実行項目")
            st.info("""
**分析環境構築:**
- 8つの分析スクリプト本格運用開始
- 週次ダッシュボード構築
- KPIモニタリング体制確立
- データ品質チェック実装
            """)

        st.markdown("---")

        # 成功のカギ
        st.header("🎉 成功のカギ")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**1️⃣ データドリブン意思決定**")
            st.markdown("""
- 定期分析の実施
- PDCAサイクル確立
- リアルタイムKPI監視
            """)

        with col2:
            st.markdown("**2️⃣ 段階的実行**")
            st.markdown("""
- 小さく始める
- リスク最小化
- 成功事例の横展開
            """)

        with col3:
            st.markdown("**3️⃣ 組織コミット**")
            st.markdown("""
- 経営陣リーダーシップ
- 現場の協力
- 成果共有文化
            """)

        with col4:
            st.markdown("**4️⃣ 継続改善**")
            st.markdown("""
- 定期的見直し
- 柔軟な対応
- イノベーション促進
            """)

        st.markdown("---")

        # フッター
        st.success("""
        **この提案書は、徹底的なデータ分析に基づいて作成されました。**

        速やかな実行により、年間$500,000以上の利益向上が期待できます。

        *予想投資回収期間: 6ヶ月 | ROI: 600%以上*
        """)
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
