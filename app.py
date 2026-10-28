import math
import unicodedata
from html import escape
from pathlib import Path

import streamlit as st
from core import BRANDS, load_data, search
from recommendation import (
    CAFFEINE_LABEL,
    CATEGORY_LABEL,
    MENU,
    SIZE_LABEL,
    SURVEY,
    recommend,
)


st.set_page_config(
    page_title="CoffeePick · 저가커피 메뉴 비교",
    page_icon="☕",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "images"

MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

NA = "확인 자료 없음"

BRAND_COLORS = {
    "컴포즈커피": "#C8961E",
    "메가MGC커피": "#A14314",
    "빽다방": "#5B7FB5",
}


def normalize(value):
    return unicodedata.normalize("NFC", str(value)).strip().casefold()


@st.cache_data(show_spinner=False)
def read_photo(path_string, modified_ns, size):
    path = Path(path_string)
    mime = MIME.get(path.suffix.lower().lstrip("."))
    if mime is None:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def find_photo(brand, menu, variant):
    target = normalize(str(brand) + "_" + str(menu) + "_" + str(variant))
    try:
        if not IMG_DIR.is_dir():
            return None
        for path in sorted(IMG_DIR.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            if path.suffix.lower().lstrip(".") not in MIME:
                continue
            if normalize(path.stem) == target:
                info = path.stat()
                return read_photo(str(path), info.st_mtime_ns, info.st_size)
    except OSError:
        return None
    return None


def number(value):
    if value is None or value == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def price_text(value):
    value = number(value)
    return NA if value is None else format(value, ",.0f") + "원"


def rating_text(row):
    value = number(row.get("rating"))
    if value is None:
        return NA
    scale = number(row.get("rating_scale"))
    text = format(value, "g")
    if scale is not None and scale > 0:
        text += "/" + format(scale, "g")
    normalized = number(row.get("rating_normalized"))
    if normalized is not None:
        text += " (5점 환산 " + format(normalized, ".2f") + ")"
    return text


def pick_menu(name):
    st.session_state["q"] = name


def render_card(row, cheapest):
    brand = str(row.get("brand") or "")
    menu = str(row.get("menu_name") or "")
    variant = str(row.get("variant") or "")
    color = BRAND_COLORS.get(brand, "#8B5E3C")
    price = number(row.get("price_krw"))
    is_cheapest = cheapest is not None and price == cheapest
    badge = "<span style='font-size:0.8rem;color:#2E7D32;font-weight:800;margin-left:8px;'>🏷️ 최저가</span>" if is_cheapest else ""

    with st.container(border=True):
        header = (
            "<div style='border-left:6px solid " + color + ";padding:2px 0 6px 12px;'>"
            "<div style='font-size:0.8rem;font-weight:700;color:" + color + ";'>"
            + escape(brand) + "</div>"
            "<div style='font-size:1.25rem;font-weight:800;line-height:1.3;color:#4B2E20;'>"
            + escape(menu)
            + " <span style='font-size:0.8rem;color:#806451;'>" + escape(variant) + "</span></div>"
            "<div style='font-size:1.5rem;font-weight:800;color:#E85D04;'>"
            + escape(price_text(price)) + badge + "</div>"
            "</div>"
        )
        st.markdown(header, unsafe_allow_html=True)
        photo = find_photo(brand, menu, variant)
        if photo is not None:
            st.image(photo, use_container_width=True)
        else:
            st.caption("📷 등록된 이미지가 없습니다")
        volume = number(row.get("volume_ml"))
        volume_label = NA if volume is None else format(volume, ",.0f") + "mL"
        st.write("🥤 용량: " + volume_label)
        st.write("⭐ 평점: " + rating_text(row))
        st.write("👅 맛 평가: " + str(row.get("taste") or NA))
        st.write("💬 리뷰: " + str(row.get("review") or NA))
        source_fields = [
            ("메뉴", "menu_source_url", None),
            ("가격", "price_source_url", "price_krw"),
            ("용량", "volume_source_url", "volume_ml"),
            ("평점", "rating_source_url", "rating"),
            ("맛 평가", "taste_source_url", "taste"),
            ("리뷰", "review_source_url", "review"),
        ]
        for label, field, metric in source_fields:
            url = str(row.get(field) or "").strip()
            if not url.startswith(("https://", "http://")):
                continue
            if metric is not None and row.get(metric) in (None, ""):
                continue
            st.link_button(label + " 출처", url)
        st.caption("확인일 " + str(row.get("verified_at") or NA))


st.markdown(
    """
<style>
:root {
  --text-color: #4B2E20;
}
.stApp {
  background: linear-gradient(135deg, #FFF3D6 0%, #FFE0C2 50%, #FFD3E0 100%);
  color: #4B2E20;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stMetricValue"] {
  color: #4B2E20;
}
.stApp [data-baseweb="input"] input,
.stApp input[type="text"],
.stApp textarea {
  color: #4B2E20 !important;
  -webkit-text-fill-color: #4B2E20;
  background-color: #fff;
  caret-color: #4B2E20;
}
.stApp [data-testid="stButton"] > button,
.stApp [data-testid="stFormSubmitButton"] > button {
  color: #fff !important;
  background-color: #4B2E20 !important;
  border-color: #4B2E20 !important;
}
.stApp [data-testid="stButton"] > button *,
.stApp [data-testid="stFormSubmitButton"] > button * {
  color: #fff !important;
  -webkit-text-fill-color: #fff;
}
.stApp button[kind="primary"] {
  color: #fff !important;
  background-color: #4B2E20 !important;
}
.stApp [data-testid="stAlert"] {
  color: #fff !important;
  background-color: #4B2E20;
}
.stApp [data-testid="stAlert"] * {
  color: #fff !important;
}
.block-container { max-width: 1120px; padding-top: 2rem; }
h1, h2, h3, p, label, .stMarkdown { color: #3E2723 !important; }

[data-testid="stVerticalBlockBorderWrapper"] {
  background: #FFFDF8;
  border: 1px solid #E4D8C2;
  border-radius: 22px;
  box-shadow: 0 6px 20px rgba(111,78,55,0.14);
}

.stButton > button, .stLinkButton > a {
  background: #6F4E37 !important;
  color: #FFF8EF !important;
  font-weight: 800 !important;
  border: none !important;
  border-radius: 999px !important;
  padding: 0.5rem 1.1rem !important;
  box-shadow: 0 4px 0 #4E3626 !important;
  transition: transform .08s ease, box-shadow .08s ease !important;
}
.stButton > button:hover, .stLinkButton > a:hover {
  transform: translateY(2px) !important;
  box-shadow: 0 2px 0 #4E3626 !important;
  background: #855C40 !important;
}
.stButton > button:active {
  transform: translateY(4px) !important;
  box-shadow: 0 0 0 #4E3626 !important;
}

[data-testid="stHorizontalBlock"] .stButton > button {
  background: #C9A27A !important;
  color: #3E2723 !important;
  box-shadow: 0 4px 0 #A9825B !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
  background: #D8B890 !important;
  box-shadow: 0 2px 0 #A9825B !important;
}

.stTextInput input, div[data-baseweb="select"] > div {
  background: #FFFDF8 !important;
  color: #3E2723 !important;
  border-radius: 14px !important;
  border: 1px solid #6F4E37 !important;
}

span[data-baseweb="tag"] {
  background: #8B5E3C !important;
  color: #FFF8EF !important;
}
span[data-baseweb="tag"] svg { fill: #FFF8EF !important; }

[data-baseweb="radio"] div[aria-checked="true"] > div:first-child {
  background: #6F4E37 !important;
  border-color: #6F4E37 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #3E2723 !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("☕ CoffeePick")
st.write("컴포즈커피 · 메가MGC커피 · 빽다방, 같은 메뉴를 한눈에 비교해요!")
st.info(
    "확인된 CSV 자료만 표시합니다. 미확인 값은 0점·0원이 아닌 '확인 자료 없음'으로 "
    "표시합니다. 가격은 지점·옵션·시점에 따라 달라질 수 있어요."
)

if "q" not in st.session_state:
    st.session_state["q"] = ""

query_col, brand_col = st.columns([3, 2])
with query_col:
    query = st.text_input("메뉴 검색", key="q", placeholder="예: 아메리카노, 라떼")
with brand_col:
    selected = st.multiselect("비교 브랜드", list(BRANDS), default=list(BRANDS))

variant_col, sort_col, reload_col = st.columns([3, 3, 1])
with variant_col:
    variant_label = st.radio("옵션", ["전체", "HOT", "ICE"], horizontal=True)
with sort_col:
    sort_label = st.radio("정렬", ["가격 낮은 순", "평점 높은 순"], horizontal=True)
with reload_col:
    if st.button("새로고침", help="CSV나 이미지를 변경한 후 누르세요."):
        st.cache_data.clear()
        st.rerun()

rows, warnings = load_data(BASE_DIR / "data" / "menus.csv")

if rows:
    names = sorted({str(row["menu_name"]) for row in rows})[:8]
    for start in range(0, len(names), 4):
        chip_cols = st.columns(4)
        for col, name in zip(chip_cols, names[start:start + 4]):
            col.button(
                name,
                key="chip_" + name,
                on_click=pick_menu,
                args=(name,),
                use_container_width=True,
            )

if not rows:
    st.warning(
        "표시할 확인 데이터가 없어요. data/menus.csv와 아래 데이터 확인 안내를 "
        "확인해 주세요."
    )
elif not selected:
    st.info("비교할 브랜드를 하나 이상 선택해 주세요.")
elif not query.strip():
    st.info("메뉴명을 입력하거나 위 메뉴 버튼을 눌러 주세요.")
else:
    sort_key = "rating" if sort_label == "평점 높은 순" else "price"
    results = search(rows, query, selected, sort_key)
    if variant_label != "전체":
        results = [
            row
            for row in results
            if str(row.get("variant", "")).strip().upper() == variant_label
        ]
    if not results:
        st.info(query + " 검색 결과가 없어요. 다른 메뉴명으로 검색해 주세요.")
    else:
        prices = [number(row.get("price_krw")) for row in results]
        prices = [value for value in prices if value is not None]
        cheapest = min(prices) if prices else None
        best = next(
            (
                row
                for row in results
                if cheapest is not None
                and number(row.get("price_krw")) == cheapest
            ),
            None,
        )
        stat_cols = st.columns(3)
        stat_cols[0].metric("검색 결과", str(len(results)) + "건")
        stat_cols[1].metric("최저가", price_text(cheapest))
        best_label = NA if best is None else str(best["brand"]) + " " + str(best["variant"])
        stat_cols[2].metric("최저가 메뉴", best_label)
        missing = [
            brand
            for brand in selected
            if not any(row["brand"] == brand for row in results)
        ]
        if missing:
            st.caption("확인 메뉴 데이터가 없는 브랜드: " + ", ".join(missing))
        for start in range(0, len(results), 3):
            card_cols = st.columns(3)
            for col, row in zip(card_cols, results[start:start + 3]):
                with col:
                    render_card(row, cheapest)

with st.expander("✨ 음료 추천", expanded=False):
    st.caption(
        "취향, 기분, 예산을 바탕으로 음료를 추천해요. "
        "답하고 싶은 항목만 선택해도 됩니다."
    )

    answers = {}
    with st.form("drink_recommendation"):
        for section_key, section in SURVEY.items():
            st.markdown("**" + section["title"] + "**")
            answers[section_key] = {}

            for question in section["questions"]:
                labels = [option[1] for option in question["options"]]
                values_by_label = {
                    label: value for value, label in question["options"]
                }
                widget_key = "recommend_answer_" + question["id"]

                if question["multi"]:
                    picked = st.multiselect(
                        question["text"],
                        labels,
                        key=widget_key,
                        placeholder="선택 안 해도 돼요",
                    )
                    if picked:
                        answers[section_key][question["id"]] = [
                            values_by_label[label] for label in picked
                        ]
                else:
                    picked = st.radio(
                        question["text"],
                        labels,
                        index=None,
                        key=widget_key,
                        horizontal=True,
                    )
                    if picked is not None:
                        answers[section_key][question["id"]] = values_by_label[picked]

        submitted = st.form_submit_button("추천받기", type="primary")

    def reset_recommendation_answers():
        for section in SURVEY.values():
            for question in section["questions"]:
                st.session_state.pop(
                    "recommend_answer_" + question["id"], None
                )

    st.button("추천 조건 초기화", on_click=reset_recommendation_answers)

    if submitted:
        recommendation = recommend(MENU, answers, top_n=5)
        if recommendation["mode"] == "popular":
            st.info("선택한 항목이 없어 인기 메뉴를 보여드려요.")

        for index, result in enumerate(recommendation["results"], start=1):
            item = result["item"]
            temperatures = "/".join(
                "차가움" if temperature == "ice" else "따뜻함"
                for temperature in item["temps"]
            )
            sizes = "/".join(SIZE_LABEL[size] for size in item["sizes"])
            details = [
                CATEGORY_LABEL[item["category"]],
                f'{item["price"]:,}원',
                temperatures,
                "카페인 " + CAFFEINE_LABEL[item["caffeine"]],
                sizes + " 사이즈",
            ]
            score = (
                ""
                if result["score"] is None
                else f' · {result["score"]:.1f}점'
            )
            with st.container(border=True):
                st.markdown(f'**{index}. {item["name"]}**{score}')
                st.caption(" · ".join(details))
                if result["reasons"]:
                    st.success("추천 이유: " + ", ".join(result["reasons"]))
                if result["unmet"]:
                    st.warning("완화된 조건: " + ", ".join(result["unmet"]))

if warnings:
    with st.expander("데이터 확인 안내 (" + str(len(warnings)) + "건)"):
        for warning in warnings:
            st.warning(str(warning))
