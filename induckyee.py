import streamlit as st
import duckdb
import pandas as pd
import os
import time

# -------------------------------------------------
# 0. 페이지 설정
# -------------------------------------------------
st.set_page_config(page_title="DuckDB 마당 매니저", layout="wide")

# -------------------------------------------------
# 1. DuckDB 연결
# -------------------------------------------------
DB_FILE = "madang.db"

@st.cache_resource
def get_connection():
    if not os.path.exists(DB_FILE):
        st.error(f"'{DB_FILE}' 파일을 찾을 수 없습니다. 같은 폴더에 두고 다시 실행하세요.")
        st.stop()
    return duckdb.connect(DB_FILE, read_only=False)

conn = get_connection()

def query_df(sql: str, params=None) -> pd.DataFrame:
    """SELECT → DataFrame"""
    if params is None:
        return conn.execute(sql).df()
    return conn.execute(sql, params).df()

def execute_sql(sql: str, params=None) -> None:
    """INSERT/UPDATE/DELETE 실행"""
    if params is None:
        conn.execute(sql)
    else:
        conn.execute(sql, params)
    conn.commit()

# -------------------------------------------------
# 2. 도서 목록 (거래 입력용 selectbox)
# -------------------------------------------------
try:
    book_df = query_df("SELECT bookid, bookname FROM Book ORDER BY bookid;")
    books = [None] + [f"{int(row.bookid)},{row.bookname}" for _, row in book_df.iterrows()]
except Exception as e:
    st.error(f"Book 테이블 조회 중 오류: {e}")
    st.stop()

# -------------------------------------------------
# 3. 사이드바: 전체 테이블 보기
# -------------------------------------------------
st.sidebar.header("📂 전체 테이블 보기")

if st.sidebar.checkbox("Customer 테이블 보기"):
    try:
        st.sidebar.dataframe(query_df("SELECT * FROM Customer;"))
    except Exception as e:
        st.sidebar.error(f"Customer 조회 오류: {e}")

if st.sidebar.checkbox("Book 테이블 보기"):
    try:
        st.sidebar.dataframe(query_df("SELECT * FROM Book;"))
    except Exception as e:
        st.sidebar.error(f"Book 조회 오류: {e}")

if st.sidebar.checkbox("Orders 테이블 보기"):
    try:
        st.sidebar.dataframe(query_df("SELECT * FROM Orders;"))
    except Exception as e:
        st.sidebar.error(f"Orders 조회 오류: {e}")

# -------------------------------------------------
# 4. 상단 UI (induck 스타일) - 고객 주문 내역 조회
# -------------------------------------------------
st.title("📚 DuckDB 마당 매니저")
st.caption("Madang DB 데이터를 DuckDB 기반으로 조회하고 거래를 입력하는 웹 애플리케이션입니다.")

st.header("🔍 고객 주문 내역 조회")

input_name = st.text_input("조회할 고객 이름을 입력하세요:", value="")

if st.button("조회 시작") or input_name:
    if not input_name:
        st.warning("⚠️ 고객 이름을 입력해주세요.")
    else:
        query_sql = """
            SELECT 
                T1.name      AS 고객명,
                T3.bookname  AS 서적명,
                T2.saleprice AS 판매가,
                T2.orderdate AS 주문일
            FROM Customer AS T1
            INNER JOIN Orders AS T2 ON T1.custid = T2.custid
            INNER JOIN Book   AS T3 ON T2.bookid = T3.bookid
            WHERE T1.name = ?;
        """
        try:
            df = query_df(query_sql, [input_name])

            if df.empty:
                check_df = query_df("SELECT * FROM Customer WHERE name = ?;", [input_name])
                if not check_df.empty:
                    st.success(f"🟢 고객 '{input_name}'님은 등록되어 있으나 주문 기록이 없습니다.")
                else:
                    st.error(f"🔴 고객 '{input_name}'님은 데이터베이스에 등록되어 있지 않습니다. "
                             "아래 ‘고객조회/거래 입력’ 탭에서 신규 고객으로 등록할 수 있습니다.")
            else:
                st.subheader(f"📦 '{input_name}'님의 주문 내역")
                st.dataframe(df)
        except Exception as e:
            st.error(f"❌ 쿼리 실행 오류: {e}")

st.markdown("---")

# -------------------------------------------------
# 5. 하단 탭: 고객조회 / 거래 입력 (madang_manager + 확장)
# -------------------------------------------------

# 세션 상태 초기화
if "custid" not in st.session_state:
    st.session_state["custid"] = None
if "cust_name" not in st.session_state:
    st.session_state["cust_name"] = ""
if "is_new_cust" not in st.session_state:
    st.session_state["is_new_cust"] = False

tab1, tab2 = st.tabs(["고객조회", "거래 입력"])

# -------------------------#
# 5-1. 고객조회 탭
# -------------------------#
with tab1:
    st.subheader("고객조회")

    name_for_tabs = st.text_input("고객명", value=st.session_state["cust_name"])

    if name_for_tabs:
        # 1) 고객 기본 정보 조회
        cust_df = query_df(
            "SELECT custid, name, address, phone FROM Customer WHERE name = ?;",
            [name_for_tabs]
        )

        # 2) 고객 거래 내역 조회
        orders_sql = """
            SELECT c.custid, c.name, b.bookname, o.orderdate, o.saleprice
            FROM Customer c
            JOIN Orders   o ON c.custid = o.custid
            JOIN Book     b ON o.bookid = b.bookid
            WHERE c.name = ?;
        """
        orders_df = query_df(orders_sql, [name_for_tabs])

        if cust_df.empty:
            st.warning("📥 이 이름은 Customer 테이블에 없습니다. 신규 고객으로 등록 가능합니다.")
            st.session_state["custid"] = None
            st.session_state["cust_name"] = name_for_tabs
            st.session_state["is_new_cust"] = True
        else:
            custid = int(cust_df.loc[0, "custid"])
            st.session_state["custid"] = custid
            st.session_state["cust_name"] = name_for_tabs
            st.session_state["is_new_cust"] = False

            st.info(
                f"고객번호: {custid}  |  이름: {cust_df.loc[0,'name']}  |  "
                f"주소: {cust_df.loc[0,'address']}  |  전화: {cust_df.loc[0,'phone']}"
            )

            if orders_df.empty:
                st.warning("해당 고객의 거래 내역이 없습니다.")
            else:
                st.write("📦 기존 거래 내역")
                st.dataframe(orders_df)

# -------------------------#
# 5-2. 거래 입력 탭
# -------------------------#
with tab2:
    st.subheader("거래 입력")

    custid = st.session_state.get("custid")
    cust_name = st.session_state.get("cust_name")
    is_new   = st.session_state.get("is_new_cust", False)

    if not cust_name:
        st.info("먼저 '고객조회' 탭에서 고객명을 입력해 주세요.")
    else:
        if is_new:
            st.markdown("### 🆕 신규 고객 등록 + 첫 거래 입력")
            st.write(f"등록할 고객명: **{cust_name}**")

            address = st.text_input("주소", key="new_addr")
            phone   = st.text_input("전화번호", key="new_phone")

        else:
            st.markdown("### 기존 고객 거래 입력")
            st.write(f"**고객번호:** {custid}")
            st.write(f"**고객명:** {cust_name}")
            address = None
            phone   = None

        select_book = st.selectbox("구매 서적:", books, index=0)
        bookid = None
        if select_book:
            bookid = int(select_book.split(",")[0])

        price = st.text_input("금액", key="price_input")

        dt = time.strftime("%Y-%m-%d", time.localtime())

        if st.button("거래 입력"):
            # 공통 입력 검증
            if not bookid:
                st.error("구매 서적을 선택해 주세요.")
            elif not price.isdigit():
                st.error("금액은 숫자로만 입력해 주세요.")
            elif is_new and (not address or not phone):
                st.error("신규 고객 등록 시 주소와 전화번호를 모두 입력해 주세요.")
            else:
                try:
                    # 1) 신규 고객이면 Customer에 먼저 추가
                    if is_new:
                        max_cust_df = query_df("SELECT MAX(custid) AS max_id FROM Customer;")
                        max_custid = max_cust_df["max_id"][0]
                        max_custid = int(max_custid) if max_custid is not None else 0
                        new_custid = max_custid + 1

                        insert_cust_sql = """
                            INSERT INTO Customer (custid, name, address, phone)
                            VALUES (?, ?, ?, ?);
                        """
                        execute_sql(insert_cust_sql, [new_custid, cust_name, address, phone])

                        st.session_state["custid"] = new_custid
                        st.session_state["is_new_cust"] = False  # 이제 기존 고객됨
                        custid_to_use = new_custid
                    else:
                        custid_to_use = custid

                    # 2) Orders에 거래 추가
                    max_order_df = query_df("SELECT MAX(orderid) AS max_id FROM Orders;")
                    max_orderid = max_order_df["max_id"][0]
                    max_orderid = int(max_orderid) if max_orderid is not None else 0
                    new_orderid = max_orderid + 1

                    insert_order_sql = """
                        INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate)
                        VALUES (?, ?, ?, ?, ?);
                    """
                    execute_sql(
                        insert_order_sql,
                        [new_orderid, custid_to_use, bookid, int(price), dt]
                    )

                    st.success("✅ 신규 거래가 입력되었습니다.")
                    if is_new:
                        st.success("🆕 고객 정보도 함께 등록되었습니다.")
                except Exception as e:
                    st.error(f"거래(또는 고객) 입력 중 오류가 발생했습니다: {e}")
