# setup_db.py 내용
import duckdb

DB_NAME = 'madang.db'
conn = duckdb.connect(database=DB_NAME)


# 🌟 고객님 이름 추가 🌟
customer_name = '김재희'  # 👈 반드시 여기에 정확한 이름을 입력하세요!
customer_address = '대한민국 수원' 
add_customer_sql = f"""
INSERT INTO Customer (custid, name, address, phone)
VALUES (6, '{customer_name}', '{customer_address}', '000-0000-0000');
"""
try:
    conn.execute(add_customer_sql)
    print(f"✅ '{customer_name}'님의 정보가 Customer 테이블에 추가되었습니다.")
except Exception as e:
    print(f"⚠️ 고객 추가 중 오류 발생: {e}") 

conn.close()