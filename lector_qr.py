import cv2
from pyzbar.pyzbar import decode
import csv
from datetime import datetime
import base64
import hmac
import hashlib
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import qrcode
import io
import os

cap = cv2.VideoCapture(0)
print("Presione 'q' para salir")
qr_leido = False
secreto = 'xgbjbr68m4oyr7xv8xrg4g1nceftc24t'

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    for qr in decode(frame):
        datos = qr.data.decode('utf-8')
        print(f"\nQR detectado: {datos}")
        
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
        
        with open('qr_lecturas.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['Fecha', 'Cadena', 'Base64', 'SHA256_Esperado', 'SHA256_Generado', 'Estatus'])
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cadena, cadena_base64, sha256_esperado, hmac_hash, valido])
        
        # Generar PDF
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
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (0, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.green if valido else colors.red),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2*inch))
        
        titulo_qr = Paragraph("<b>QR Leído:</b>", styles['Heading2'])
        elementos.append(titulo_qr)
        elementos.append(Spacer(1, 0.1*inch))
        
        # Generar QR
        qr_img = qrcode.make(datos)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
        elementos.append(qr_image)
        
        doc.build(elementos)
        print(f"PDF generado: {nombre_pdf}")
        
        print("Cadena guardada en qr_lecturas.csv")
        qr_leido = True
        cv2.rectangle(frame, (qr.rect.left, qr.rect.top), 
                     (qr.rect.left + qr.rect.width, qr.rect.top + qr.rect.height), 
                     (0, 255, 0), 2)
    
    if "JENKINS_HOME" not in os.environ:
        cv2.imshow('Lector QR', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q') or qr_leido:
        break

cap.release()
cv2.destroyAllWindows()
