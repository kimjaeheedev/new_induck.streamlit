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

