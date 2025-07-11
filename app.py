import streamlit as st

st.write("안녕? 나는 곽민수야.")
st.error("집가고 싶다")
st.warning("쉬는시간은 언제냐")
text = st.text_input("텍스트 입력")

if len(text) != 0:
    st.error(text)

long_text = st.text_area("길게 써라")
if len(text) != 0:
    st.error(long_text)

slider = st.slider(label="슬라이더", min_value=0, max_value=10, step=1)
st.warning(slider)