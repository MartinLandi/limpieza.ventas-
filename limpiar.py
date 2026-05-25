import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

FILE_ID = "1_UnddMEVHI-TOU-PUBUVWme9pS07X6GqCxQ7KERSNS4"
SHEET_NAME = "Dashboard Datos"

def main():
    print("1. Descargando hoja de cálculo como CSV...")
    # 👇 ESTA ES LA URL CORRECTA PARA HOJAS DE CÁLCULO
    url = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=csv"
    response = requests.get(url)
    print(f"   Status: {response.status_code}")

    print("2. Conectando a Google Sheets...")
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    creds_dict = json.loads(creds_json)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    print("3. Subiendo datos...")
    sheet = client.open(SHEET_NAME)
    try:
        worksheet = sheet.worksheet("ventas_limpias")
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet("ventas_limpias", 1000, 20)

    lines = response.text.strip().split('\n')
    rows = [line.split(',') for line in lines]
    worksheet.update('A1', rows)
    print("✅ Listo.")

if __name__ == "__main__":
    main()
