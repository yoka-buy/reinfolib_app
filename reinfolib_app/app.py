"""
Copyright (C) 2013, Rob Story

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import streamlit as st
import polars as pl
import folium
from streamlit_folium import st_folium


@st.cache_data
def read_data():
    return pl.read_csv("data/data.csv")


df = read_data()

price_category_list = df["PriceCategory"].unique().sort(descending=True).to_list()
period_list = df["Period"].unique().sort(descending=True).to_list()
prefecture_list = df["Prefecture"].unique().sort().to_list()

st.header("成約坪単価Viewer")


with st.expander("絞り込み条件", expanded=True):
    st.subheader("地域")
    col1, col2 = st.columns(2)
    # with col2:
    #     prefecture_search = st.text_input("検索ワード（都道府県）")

    # with col1:
    #     prefecture = st.selectbox(
    #         "都道府県", [s for s in prefecture_list if prefecture_search in s]
    #     )
    prefecture = "福岡県"

    municipality_list = (
        df.filter(pl.col("Prefecture") == prefecture)["Municipality"]
        .unique()
        .sort()
        .to_list()
    )
    with col2:
        municipality_search = st.text_input("検索ワード（市区町村）")

    with col1:
        municipality = st.selectbox(
            "市区町村", [s for s in municipality_list if municipality_search in s]
        )

    st.subheader("価格情報区分")
    price_category = st.selectbox(
        "価格情報区分",
        price_category_list,
        help=(
            "「不動産取引価格情報」とは、土地・建物の取引を対象としたアンケート調査の結果得られた回答について、"
            "個別の物件を特定できないよう加工した、国土交通省が保有し提供する不動産取引価格情報をいいます。"
            "「成約価格情報」とは、指定流通機構（レインズ）保有の不動産取引価格情報を、"
            "国土交通省が個別の不動産取引が特定できないよう加工し、消費者向け不動産取引情報サービスである、"
            "「レインズ・マーケット・インフォメーション」（RMI）にて公表している情報をいいます。"
        ),
    )

    st.subheader("時期")
    period = st.selectbox("時期", period_list)

    st.subheader("築年数")
    age_min, age_max = st.select_slider(
        "築年数",
        options=range(100),
        value=(0, 99),
        help="集計対象とする最小および最大の築年数を選んでください",
    )


df_extract = df.filter(
    (pl.col("PriceCategory") == price_category)
    & (pl.col("Prefecture") == prefecture)
    & (pl.col("Municipality") == municipality)
    & (age_min <= pl.col("Age"))
    & (pl.col("Age") <= age_max)
)


if df_extract.shape[0] == 0:
    st.warning("データがありません。絞り込み条件を変更してください。", icon="⚠️")
else:
    df_agg = (
        df_extract.group_by(
            "Period", "Municipality", "DistrictName", "Latitude", "Longitude"
        )
        .agg((pl.col("UnitPrice").mean() / 10000).cast(pl.Int16))
        .with_columns(pl.format("{}万円/坪", pl.col("UnitPrice")))
    )

    lat_mean, long_mean = (
        df_agg.select("Latitude", "Longitude").unique().mean().to_numpy().flatten()
    )

    m = folium.Map([lat_mean, long_mean], zoom_start=15)
    for row in df_agg.rows(named=True):
        popup = folium.Popup(row["UnitPrice"], min_width=50, max_width=100)

        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=popup,
            tooltip=row["DistrictName"],
        ).add_to(m)

    st_folium(m, width=1200, height=800, returned_objects=[])


st.info(
    "「このサービスは、国土交通省の不動産情報ライブラリのAPI機能を使用していますが、提供情報の最新性、正確性、完全性等が保証されたものではありません。」",
)
