import streamlit as st
import duckdb
import pandas as pd

# ----------------------------
# 🧾 고객 주문 내역 조회 (위쪽)
# ----------------------------
st.markdown("## 🔍 고객 주문 내역 조회")

input_name = st.text_input("조회할 고객 이름을 입력하세요:", key="order_search_name")

if st.button("조회 시작", key="order_search_btn"):

    if len(input_name.strip()) == 0:
        st.warning("⚠️ 고객 이름을 입력해주세요.")
    else:
        query_sql = f"""
            SELECT 
                C.name   AS 고객명,
                B.bookname AS 서적명,
                O.saleprice AS 판매가,
                O.orderdate AS 주문일
            FROM Customer AS C
            JOIN Orders   AS O ON C.custid = O.custid
            JOIN Book     AS B ON O.bookid = B.bookid
            WHERE C.name = ?
            ORDER BY O.orderdate DESC;
        """
        try:
            df = conn.execute(query_sql, [input_name]).df()

            if df.empty:
                # 고객 테이블에 존재 여부 확인
                check_sql = "SELECT * FROM Customer WHERE name = ?;"
                customer_found = conn.execute(check_sql, [input_name]).df()

                if not customer_found.empty:
                    st.info(f"ℹ️ 고객 '{input_name}'님은 등록되어 있으나 주문 기록이 없습니다.")
                else:
                    st.error(f"🔴 고객 '{input_name}'님은 데이터베이스에 등록되어 있지 않습니다.")
            else:
                st.subheader(f"📦 '{input_name}'님의 주문 내역")
                st.dataframe(df)

        except Exception as e:
            st.error(f"조회 중 오류 발생: {e}")

# 구분선
st.markdown("---")

# ----------------------------
# 📌 아래 탭: 고객조회 / 거래 입력
# ----------------------------
tab1, tab2 = st.tabs(["고객조회", "거래 입력"])

# =====================================
# 1️⃣ 고객조회 탭
# =====================================
with tab1:
    st.markdown("### 고객조회")

    search_name = st.text_input("고객명", value=input_name, key="customer_search_name")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        do_search = st.button("고객 조회", key="btn_customer_search")
    with col_b:
        show_all = st.button("전체 고객 보기", key="btn_customer_all")

    if do_search:
        if len(search_name.strip()) == 0:
            st.warning("⚠️ 고객 이름을 입력해주세요.")
        else:
            try:
                cdf = conn.execute(
                    "SELECT * FROM Customer WHERE name = ?;",
                    [search_name],
                ).df()
                if cdf.empty:
                    st.error(f"🔴 고객 '{search_name}'님은 아직 등록되지 않았습니다.")
                    st.write("⬇ 아래에서 새 고객으로 등록할 수 있습니다.")

                    # 새 고객 추가 폼
                    with st.form("add_customer_form"):
                        new_name = st.text_input("고객 이름", value=search_name)
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
                                st.success(f"🟢 고객 '{new_name}'이(가) 새로 등록되었습니다.")

                                result_df = conn.execute(
                                    "SELECT * FROM Customer WHERE name = ?;",
                                    [new_name],
                                ).df()
                                st.dataframe(result_df)
                            except Exception as e:
                                st.error(f"❌ 고객 추가 중 오류 발생: {e}")
                else:
                    st.success(f"🟢 고객 '{search_name}' 정보입니다.")
                    st.dataframe(cdf)
            except Exception as e:
                st.error(f"고객 조회 중 오류 발생: {e}")

    if show_all:
        try:
            all_cust = conn.execute("SELECT * FROM Customer ORDER BY custid;").df()
            st.dataframe(all_cust)
        except Exception as e:
            st.error(f"전체 고객 조회 중 오류 발생: {e}")

# =====================================
# 2️⃣ 거래 입력 탭
# =====================================
with tab2:
    st.markdown("### 거래 입력")

    try:
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
                selected_customer = st.selectbox(
                    "👤 고객 선택",
                    customers,
                    format_func=lambda c: f"{c['custid']} - {c['name']}",
                )

                selected_book = st.selectbox(
                    "📚 도서 선택",
                    books,
                    format_func=lambda b: f"{b['bookid']} - {b['bookname']} (정가 {b['price']})",
                )

                default_price = 0
                if selected_book is not None and "price" in selected_book:
                    try:
                        default_price = int(selected_book["price"])
                    except Exception:
                        default_price = 0

                saleprice = st.number_input(
                    "💲 판매가",
                    min_value=0,
                    value=default_price,
                    step=1000,
                )

                orderdate = st.date_input(
                    "📅 주문일",
                    value=pd.Timestamp.today().date(),
                )

                submitted = st.form_submit_button("💾 거래 저장")

                if submitted:
                    try:
                        new_orderid = conn.execute(
                            "SELECT COALESCE(MAX(orderid), 0) + 1 AS new_id FROM Orders"
                        ).fetchone()[0]

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
                                orderdate,
                            ],
                        )

                        st.success(f"✅ 새 주문이 저장되었습니다. (orderid = {new_orderid})")

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
