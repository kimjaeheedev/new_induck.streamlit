import streamlit as st
import duckdb
import pandas as pd

if st.button("조회 시작") or len(input_name) > 0:

    if len(input_name) == 0:
        st.warning("⚠️ 고객 이름을 입력해주세요.")
        st.stop()

    # 주문 내역 조회 SQL
    query_sql = f"""
        SELECT 
            T1.name AS 고객명, 
            T3.bookname AS 서적명, 
            T2.saleprice AS 판매가, 
            T2.orderdate AS 주문일
        FROM Customer AS T1
        INNER JOIN Orders AS T2 ON T1.custid = T2.custid
        INNER JOIN Book AS T3 ON T2.bookid = T3.bookid
        WHERE T1.name = '{input_name}';
    """

    try:
        df = conn.execute(query_sql).df()

        # --------------------------------------------------------------------
        # 1️⃣ 주문 내역이 없는 경우 → Customer 테이블에서 존재 여부 다시 검색
        # --------------------------------------------------------------------
        if df.empty:

            check_sql = f"SELECT * FROM Customer WHERE name = '{input_name}';"
            customer_found = conn.execute(check_sql).df()

            # ▣ 고객은 있지만 주문이 없는 경우
            if not customer_found.empty:
                st.info(f"ℹ️ 고객 '{input_name}'님은 존재하지만 주문 기록이 없습니다.")

            # ▣ 고객 자체가 없으면 → 🔥 고객 추가 폼 표시
            else:
                st.warning(f"🔴 고객 '{input_name}'님은 존재하지 않습니다.")
                st.write("⬇ 아래에서 바로 고객으로 등록할 수 있어요!")

                with st.form("add_customer_form"):
                    new_name = st.text_input("고객 이름", value=input_name)
                    new_address = st.text_input("주소", value="")
                    new_phone = st.text_input("전화번호", value="")

                    submitted = st.form_submit_button("고객 추가")

                    if submitted:
                        try:
                            # custid 자동 증가
                            insert_sql = """
                                INSERT INTO Customer (custid, name, address, phone)
                                SELECT COALESCE(MAX(custid), 0) + 1, ?, ?, ?
                                FROM Customer;
                            """
                            conn.execute(insert_sql, [new_name, new_address, new_phone])

                            st.success(f"🟢 고객 '{new_name}'님이 성공적으로 등록되었습니다!")

                            # 추가된 정보 바로 보여주기
                            result_df = conn.execute(
                                "SELECT * FROM Customer WHERE name = ?;",
                                [new_name]
                            ).df()
                            st.dataframe(result_df)

                        except Exception as e:
                            st.error(f"❌ 고객 추가 중 오류 발생: {e}")

        # --------------------------------------------------------------------
        # 2️⃣ 주문 내역 존재 → 그대로 출력
        # --------------------------------------------------------------------
        else:
            st.subheader(f"📦 '{input_name}'님의 주문 내역")
            st.dataframe(df)

    except Exception as e:
        st.error(f"❌ 조회 중 오류 발생: {e}")
