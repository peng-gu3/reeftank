import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.title("🤖 로봇 시야 진단기")

# 👇 선생님의 키를 여기에 그대로 두세요!
ROBOT_KEY = """
{
  "type": "service_account",
  "project_id": "reef-e23b5",
  "private_key_id": "b3a4d11962e6b31a469f1e26a50aa7e8e85ad1a7",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDOYfNgbwJskSq8\nR23lxBP2JzARFG4myiXkJ6uVA/tuHrTcIrw2SFmKcle5/AeXXc7KMLvHf+VNfMXW\nxeglERw5EL3eHe1UX1ByUGVnWHz8pypsjIdo8LdtRHldgzrz7mrlK1BGnCp+2iqL\n7fo2bnasCug/WoDir2khYZcYMKETF3jQ7YbiRgNWGkXimBrjQtSld4KV0fi2e8PM\nKFmd6Zzw6tIu7VvUAdGmp0fDiLp8Xv3DWIEVarmb40p4CIWXW/4Lc3ZlhXDLe3fI\nRUZCWFHGeNoHtfTBlhAlDZoUkFc2OFsibrcUk2gHvGj7fOeFHGcYFBFwG2JR7Spl\nwXBkFd1tAgMBAAECggEAGdVp/RK4N3XOZyX7zCyIoSHTovevOBzKtG4AzNTkRqsC\nUaHpdFQHHUzlzUqOerSL24RRJQ5N2i65pwI75lPnd/8v/Rs653pM3BpTLyYE8y1L\noq3Oj2S+WSeel4WDPiCEce5DjKskqJ9PfxeJYAHgyfVNkAyYoId7fem025rOttBa\nS/gmDtLPy526xnbsCdWycmIDMQWp/a7l2ELaMf9FikfpjKUL0bNqhcRGZElcSCYU\nQGHmaoK8DnpNox3rmbu37Lb42ppGislhpv12f5WshWYswPlBPrXUo26u7gLgDtcT\n5BRVTfBqaeYv4Co76TKtp9bGgLuonc2LFOh2zVEDcwKBgQDnO32EEn78RR8utMNy\nUTkMxI9fvjkspr/mrTaeFK3kPhm/JQG7D9w2t9KweU+6g6Qt5WeaEq15349ALdCI\nGGBhdntix8hlGmwWoW7ckUa0J5L3lIgPmQmXYWRa6WiH74H31rQrTxP8UUfxeVhQ\nOEYD2OAoTZs52x/iFQhhGJUFOwKBgQDkfRE0qhWd31y49iMYW89inKj88PDYUI11\nkuJ9XMf2AF2V5m+dn0z3AEfwkaVQf7dp4uXokuQ9L4vBWRIxVx9idmPkUiMt1EtU\nGI6flVI1j7XGhAfFHFhAvbDRjP41rDDVcXMyV3U0j8GRmfModTcpo8RSgJEPmAwO\nrdM8NR5ddwKBgQCm1n+rqYTCFEV5d6eFdiFJmxEvrZqnIvFXSScdTCJjioMdLWBg\nTgM/38Y+2miyVIVDMEBeJJfSVYGQdv39FEmGSOyhyzBF8piGg5fvwUpYdi1OQXci\nefM3rGeySLLJUgBeiCWbEgWDikn0au9TgibSY8roiYY0amxIvZA8LnZnPQKBgFIV\nfDDnSYzFyZHJGyKNGRvcG/mCtYOArNEoS6Wtx0hhKT3I4yBFMmkp+K48JJ+ewk2P\n7fh3jPdONW7oiNig6+17irdjqq+0LLuxdstt4XLMhgkjNYdif3ICs5sUg97UVVbY\nwwG62ahgXLHqFKjcM00KQGVDOtnXTb2YROLEUnxRAoGAJRe67TQdzfDYcxdX2JAx\nF+5o5jV4PyUmX7dHxcZHQfwEGUxBnw1OzRRbT4ZSZMYqsr4LSXaUCQVMhkDbvPmn\nLxcErtRpbjKWpf89PQzNGIrYujhMzODJAOBGTPuHDe4hCWu6sPyizBNzHAwgcolB\nv3CSENcbP/a4ZqDfs/GeGVE=\n-----END PRIVATE KEY-----\n",
  "client_email": "reef-bot@reef-e23b5.iam.gserviceaccount.com",
  "client_id": "101105675500933645721",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/reef-bot%40reef-e23b5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

try:
    creds_dict = json.loads(ROBOT_KEY, strict=False)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    st.success("✅ 로봇 로그인 성공!")
    
    # 로봇이 볼 수 있는 모든 시트 가져오기
    sheets = client.openall()
    
    st.write(f"📋 **로봇이 발견한 시트 목록 ({len(sheets)}개):**")
    
    if len(sheets) == 0:
        st.error("🚨 로봇이 아무 파일도 못 보고 있습니다! 'Google Drive API'가 꺼져있거나, 공유가 안 된 것입니다.")
    else:
        for sheet in sheets:
            st.write(f"- 📄 **{sheet.title}** (ID: `{sheet.id}`)")
            
except Exception as e:
    st.error(f"❌ 에러 발생: {e}")
