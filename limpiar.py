import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from io import StringIO
from datetime import datetime

# ============================================================
# 👇 SOLO TENÉS QUE CAMBIAR ESTAS 3 COSAS 👇
# ============================================================

# 1. El ID de tu archivo en Google Drive (el que está en la URL)
FILE_ID = "1_UnddMEVHI-TOU-PUBUVWme9pS07X6GqCxQ7KERSNS4"  # Ejemplo: "1ABC123_DEF456..."

# 2. El nombre de tu Google Sheets (donde están los datos limpios)
SHEET_NAME = "Dashboard Datos"  # Ejemplo: "Ventas Limpias"

# 3. El nombre de la pestaña (worksheet) dentro de ese Google Sheets
WORKSHEET_NAME = "ventas_limpias"  # Ejemplo: "datos_procesados"

# ============================================================
# NO TOCAS NADA DE ACÁ PARA ABAJO (a menos que sepas lo que hacés)
# ============================================================

def descargar_csv_desde_drive(file_id):
    """Descarga un archivo CSV público desde Google Drive usando su ID"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lanza un error si la descarga falla
        
        # Detectar si es un archivo CSV o si Google mostró una página de advertencia
        if 'google drive - virus warning' in response.text.lower():
            # Extraer el link directo de descarga de la página de advertencia
            import re
            match = re.search(r'confirm=([^&]+)', response.text)
            if match:
                confirm = match.group(1)
                url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"
                response = requests.get(url)
                response.raise_for_status()
        
        return response.text
    except Exception as e:
        print(f"❌ Error al descargar el archivo: {e}")
        raise

def conectar_google_sheets():
    """Conecta a Google Sheets usando las credenciales desde variable de entorno"""
    try:
        # Leer credenciales desde la variable de entorno (seteada en GitHub Secrets)
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_json:
            raise Exception("No se encontró la variable de entorno GOOGLE_CREDENTIALS")
        
        creds_dict = json.loads(creds_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ Error al conectar con Google Sheets: {e}")
        raise

def limpiar_datos(csv_texto):
    """Limpia los datos del CSV y calcula métricas"""
    try:
        # Leer CSV desde texto
        df = pd.read_csv(StringIO(csv_texto))
        
        # Mostrar columnas encontradas (para debug)
        print(f"📊 Columnas encontradas: {df.columns.tolist()}")
        
        # Ajustá estos nombres según las columnas de tu CSV de milocal.app
        # Ejemplo: si la fecha se llama "Fecha" en lugar de "fecha"
        # date_column = 'Fecha' if 'Fecha' in df.columns else 'fecha'
        
        # Convertir fechas
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        elif 'Fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        elif 'date' in df.columns:
            df['fecha'] = pd.to_datetime(df['date'], errors='coerce')
        else:
            print("⚠️ No se encontró columna de fecha, se usará índice como fecha")
            df['fecha'] = datetime.now()
        
        # Limpiar datos nulos
        df = df.dropna(subset=['fecha'])
        
        # Identificar columna de total (puede llamarse "total", "monto", "precio")
        total_col = None
        for col in ['total', 'Total', 'monto', 'Monto', 'precio', 'Precio', 'Total Amount']:
            if col in df.columns:
                total_col = col
                break
        
        if total_col:
            df['total'] = pd.to_numeric(df[total_col], errors='coerce')
        else:
            print("⚠️ No se encontró columna de total, se calculará con cantidad * precio")
            if 'cantidad' in df.columns and 'precio_unitario' in df.columns:
                df['total'] = df['cantidad'] * df['precio_unitario']
            else:
                df['total'] = 0
        
        # Calcular métricas
        total_ventas = df['total'].sum()
        ticket_promedio = df['total'].mean()
        
        # Top productos (si existe columna de producto)
        producto_top = "No disponible"
        if 'producto' in df.columns:
            producto_top = df.groupby('producto')['total'].sum().idxmax()
        elif 'Producto' in df.columns:
            producto_top = df.groupby('Producto')['total'].sum().idxmax()
        
        # Agregar fecha de procesamiento
        df['fecha_procesamiento'] = datetime.now()
        
        print(f"✅ Datos limpiados: {len(df)} filas")
        print(f"💰 Ventas totales: ${total_ventas:,.2f}")
        print(f"🎫 Ticket promedio: ${ticket_promedio:,.2f}")
        
        return df
    except Exception as e:
        print(f"❌ Error al limpiar datos: {e}")
        raise

def actualizar_google_sheets(client, df, sheet_name, worksheet_name):
    """Actualiza el Google Sheets con los datos limpios"""
    try:
        # Abrir la hoja de cálculo
        sheet = client.open(sheet_name)
        
        # Seleccionar o crear la pestaña
        try:
            worksheet = sheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
        
        # Limpiar datos existentes
        worksheet.clear()
        
        # Subir encabezados y datos
        if len(df) > 0:
            # Encabezados
            worksheet.update('A1', [df.columns.tolist()])
            # Datos
            worksheet.update('A2', df.values.tolist())
        
        print(f"✅ Google Sheets actualizado: {sheet_name} / {worksheet_name}")
    except Exception as e:
        print(f"❌ Error al actualizar Google Sheets: {e}")
        raise

def main():
    print("🚀 Iniciando proceso de limpieza...")
    
    # 1. Descargar CSV desde Google Drive
    print("📥 Descargando CSV desde Google Drive...")
    csv_texto = descargar_csv_desde_drive(FILE_ID)
    
    # 2. Limpiar datos
    print("🧹 Limpiando datos...")
    df_limpio = limpiar_datos(csv_texto)
    
    # 3. Conectar a Google Sheets
    print("🔌 Conectando a Google Sheets...")
    client = conectar_google_sheets()
    
    # 4. Actualizar Google Sheets
    print("📤 Subiendo datos limpios...")
    actualizar_google_sheets(client, df_limpio, SHEET_NAME, WORKSHEET_NAME)
    
    print("✅ Proceso completado con éxito!")

if __name__ == "__main__":
    main()                   
