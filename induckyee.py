import streamlit as st
import duckdb
import pandas as pd

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="Madang 고객 주문 관리", layout="wide")
st.title("📚 Madang 고객 주문 관리 시스템")

# -----------------------------
# DuckDB 연결
# -----------------------------
DB_FILE = "madang.db"
conn = duckdb.connect(DB_FILE)


# -----------------------------
# 입력 UI
# -----------------------------
input_name = st.text_input("고객 이름을 입력하세요", "")

# -----------------------------
# 조회 버튼 클릭 시 실행
# -----------------------------
if st.button("조회 시작") or len(input_name) > 0:

    # 이름이 비었으면 경고
    if len(input_name) == 0:
        st.warning("⚠️ 고객 이름을 입력해주세요.")
        st.stop()

    # 주문 조회 SQL
    query_sql = """
        SELECT 
            T1.name AS 고객명, 
            T3.bookname AS 서적명, 
            T2.saleprice AS 판매가, 
            T2.orderdate AS 주문일
        FROM Customer AS T1
        INNER JOIN Orders AS T2 ON T1.custid = T2.custid
        INNER JOIN Book AS T3 ON T2.bookid = T3.bookid
        WHERE T1.name = ?;
    """

    try:
        df = conn.execute(query_sql, [input_name]).df()

        # -----------------------------
        # 주문 내역이 없는 경우
        # -----------------------------
        if df.empty:
            check_sql = "SELECT * FROM Customer WHERE name = ?;"
            customer_found = conn.execute(check_sql, [input_name]).df()

            # 고객은 있지만 주문이 없음
            if not customer_found.empty:
                st.info(f"ℹ️ 고객 '{input_name}'님은 등록되어 있으나 주문 기록이 없습니다.")

            # 고객 자체가 없음 → 신규 고객 등록
            else:
                st.warning(f"🔴 고객 '{input_name}'님은 아직 데이터베이스에 없습니다.")
                st.write("⬇ 아래에서 새 고객으로 등록할 수 있습니다.")

                # 신규 고객 등록 폼
                with st.form("add_customer_form"):
                    new_name = st.text_input("고객 이름", value=input_name)
                    new_address = st.text_input("주소")
                    new_phone = st.text_input("전화번호")
                    submitted = st.form_submit_button("고객 추가")

                    if submitted:
                        try:
                            insert_sql = """
                                INSERT INTO Customer (custid, name, address, phone)
                                SELECT COALESCE(MAX(custid), 0) + 1, ?, ?, ?
                                FROM Customer;
                            """
                            conn.execute(insert_sql, [new_name, new_address, new_phone])

                            st.success(f"🟢 고객 '{new_name}'이(가) 성공적으로 등록되었습니다!")

                            # 방금 등록된 고객 정보 확인
                            result_df = conn.execute(
                                "SELECT * FROM Customer WHERE name = ?;",
                                [new_name]
                            ).df()
                            st.dataframe(result_df)

                        except Exception as e:
                            st.error(f"❌ 고객 추가 중 오류 발생: {e}")

        # -----------------------------
        # 주문 내역이 있는 경우
        # -----------------------------
        else:
            st.subheader(f"📦 '{input_name}'님의 주문 내역")
            st.dataframe(df)

    except Exception as e:
        st.error(f"조회 중 오류 발생: {e}")
  

# -------------------------------------------------
# 🔽 거래(Orders) 입력 섹션
# -------------------------------------------------
st.markdown("## 🧾 거래(Orders) 입력")

try:
    # 1) 고객 / 도서 목록 불러오기
    cust_df = conn.execute("SELECT custid, name FROM Customer ORDER BY custid").df()
    book_df = conn.execute("SELECT bookid, bookname, price FROM Book ORDER BY bookid").df()

    if cust_df.empty:
        st.warning("⚠️ Customer 테이블에 데이터가 없습니다. 먼저 고객을 등록해주세요.")
    elif book_df.empty:
        st.warning("⚠️ Book 테이블에 데이터가 없습니다. 먼저 도서를 등록해주세요.")
    else:
        customers = cust_df.to_dict("records")
        books = book_df.to_dict("records")

        with st.form("order_form"):
            # 고객 선택
            selected_customer = st.selectbox(
                "👤 고객 선택",
                customers,
                format_func=lambda c: f"{c['custid']} - {c['name']}",
            )

            # 도서 선택
            selected_book = st.selectbox(
                "📚 도서 선택",
                books,
                format_func=lambda b: f"{b['bookid']} - {b['bookname']} (정가 {b['price']})",
            )

            # 기본 판매가 = 책 정가
            default_price = 0
            if selected_book is not None and "price" in selected_book and pd.notna(selected_book["price"]):
                try:
                    default_price = int(selected_book["price"])
                except Exception:
                    default_price = 0

            saleprice = st.number_input(
                "💲 판매가",
                min_value=0,
                value=default_price,
                step=1000
            )

            # 주문일 (기본값: 오늘)
            orderdate = st.date_input("📅 주문일", value=pd.Timestamp.today().date())

            submitted = st.form_submit_button("💾 거래 저장")

            if submitted:
                try:
                    # 새 orderid 할당
                    new_orderid = conn.execute(
                        "SELECT COALESCE(MAX(orderid), 0) + 1 AS new_id FROM Orders"
                    ).fetchone()[0]

                    # INSERT 실행
                    conn.execute(
                        """
                        INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [
                            new_orderid,
                            selected_customer["custid"],
                            selected_book["bookid"],
                            saleprice,
                            orderdate
                        ],
                    )

                    st.success(f"✅ 새 주문이 저장되었습니다. (orderid = {new_orderid})")

                    # 방금 저장한 주문 간단히 보여주기
                    last_row = conn.execute(
                        """
                        SELECT O.orderid, C.name AS 고객명, B.bookname AS 도서명,
                               O.saleprice, O.orderdate
                        FROM Orders O
                        JOIN Customer C ON O.custid = C.custid
                        JOIN Book B ON O.bookid = B.bookid
                        WHERE O.orderid = ?
                        """,
                        [new_orderid],
                    ).df()
                    st.dataframe(last_row)

                except Exception as e:
                    st.error(f"❌ 거래 저장 중 오류 발생: {e}")

except Exception as e:
    st.error(f"거래 입력 섹션 로딩 중 오류: {e}")

