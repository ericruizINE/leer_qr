import cv2
import csv
import base64
import hmac
import hashlib
import io
import os
from datetime import datetime

# Librerías para el PDF
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import qrcode

def procesar_qr():
    # Inicializar el detector de QR nativo de OpenCV (No requiere libzbar)
    detector = cv2.QRCodeDetector()
    
    # Intentar abrir la cámara (0 es la predeterminada)
    #cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('http://10.35.16.110:8080/video')
    
    if not cap.isOpened():
        print("Error: No se pudo acceder a la cámara.")
        return

    print("Pipeline de lectura activo... Buscando QR.")
    qr_leido = False
    secreto = 'xgbjbr68m4oyr7xv8xrg4g1nceftc24t'

    # Timeout de seguridad para evitar bucles infinitos en Jenkins (opcional)
    start_time = datetime.now()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar frame.")
            break
        
        # Detectar y decodificar el QR usando OpenCV
        valor, puntos, _ = detector.detectAndDecode(frame)
        
        if valor:
            datos = valor
            print(f"\nQR detectado: {datos}")
            
            # --- Lógica de procesamiento de cadena ---
            ultimo_pipe = datos.rfind('|')
            if ultimo_pipe != -1:
                cadena = datos[:ultimo_pipe]
                sha256_esperado = datos[ultimo_pipe + 1:]
            else:
                cadena = datos
                sha256_esperado = ''
            
            cadena_base64 = base64.b64encode(cadena.encode('utf-8')).decode('utf-8')
            hmac_hash = hmac.new(
                secreto.encode('utf-8'),
                cadena_base64.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            valido = hmac_hash == sha256_esperado
            print(f"Base64: {cadena_base64}")
            print(f"HMAC-SHA256 generado: {hmac_hash}")
            print(f"Validación: {'✓ Correcto' if valido else '✗ Incorrecto'}")
            
            # --- Guardar en CSV ---
            csv_file = 'qr_lecturas.csv'
            file_exists = os.path.isfile(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Fecha', 'Cadena', 'Base64', 'SHA256_Esperado', 'SHA256_Generado', 'Estatus'])
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cadena, cadena_base64, sha256_esperado, hmac_hash, valido])
            
            # --- Generar PDF ---
            fecha_actual = datetime.now()
            nombre_pdf = f"validacion_qr_{fecha_actual.strftime('%Y%m%d_%H%M%S')}.pdf"
            doc = SimpleDocTemplate(nombre_pdf, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
            elementos = []
            styles = getSampleStyleSheet()
            estilo_grande = ParagraphStyle('Grande', parent=styles['Normal'], fontSize=10, leading=14, wordWrap='LTR')
            
            titulo = Paragraph("<b>VALIDACIÓN QR - DPIT</b>", styles['Title'])
            elementos.append(titulo)
            elementos.append(Spacer(1, 0.2*inch))
            
            datos_tabla = [
                ['Campo', 'Valor'],
                ['Fecha de Lectura', fecha_actual.strftime('%Y-%m-%d %H:%M:%S')],
                ['Cadena Original', Paragraph(cadena, estilo_grande)],
                ['Base64', Paragraph(cadena_base64, estilo_grande)],
                ['SHA256 Esperado', Paragraph(sha256_esperado, estilo_grande)],
                ['SHA256 Generado', Paragraph(hmac_hash, estilo_grande)],
                ['Estado', 'Correcto' if valido else 'Incorrecto']
            ]
            
            tabla = Table(datos_tabla, colWidths=[2.2*inch, 6.8*inch])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.green if valido else colors.red),
            ]))
            
            elementos.append(tabla)
            elementos.append(Spacer(1, 0.2*inch))
            
            # Re-generar imagen del QR para el PDF
            qr_img = qrcode.make(datos)
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            elementos.append(Paragraph("<b>QR Leído:</b>", styles['Heading2']))
            elementos.append(Image(qr_buffer, width=1.5*inch, height=1.5*inch))
            
            doc.build(elementos)
            print(f"PDF generado: {nombre_pdf}")
            qr_leido = True

        # Salir si ya se leyó el QR o si pasa mucho tiempo (ej. 2 minutos)
        if qr_leido or (datetime.now() - start_time).seconds > 120:
            break

    cap.release()
    print("Proceso finalizado.")

if __name__ == "__main__":
    procesar_qr()
