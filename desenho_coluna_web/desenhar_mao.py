import cv2
import numpy as np
import time
import sys
import os
from cvzone.HandTrackingModule import HandDetector
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor


# Conexão com PostgreSQL (Render)
DATABASE_URL = "postgresql://pacientes_web_user:uKk2h90mdG3FVesUsIBf2AuZqCbmfwnZ@dpg-cvu4v9h5pdvs73e4qec0-a.oregon-postgres.render.com/pacientes_web"
# Define a função get_db_connection() que conecta ao banco de dados remoto na Render.
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# Recebe ID do paciente via argumento de linha de comando
paciente_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0


# Inicializar detector
detector = HandDetector(detectionCon=0.7, maxHands=1) # Inicializa o detector de mão com 70% de confiança e detectando no máximo 1 mão.
# Captura de vídeo
cap = cv2.VideoCapture(0)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) 
# Tela preta para desenhar
canvas = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

# Variáveis de controle
prev_x, prev_y = None, None
initial_x = None

# Estados
countdown_started = False
capture_started = False
start_time = None
countdown_time = None
countdown_duration = 5
capture_duration = 7
first_hand_detected = False

frame_final = None  # Para salvar ao final



while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)

    # Aumentar contraste
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.equalizeHist(gray)
    frame = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    # Detectar mão
    hands, frame = detector.findHands(frame, flipType=False, draw=True)

    if hands and not first_hand_detected:
        first_hand_detected = True
        countdown_started = True
        countdown_time = time.time()

    if not first_hand_detected:
        cv2.putText(frame, "Aguardando mao...", (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,140,0), 2)

    if countdown_started and not capture_started:
        elapsed_countdown = time.time() - countdown_time
        if elapsed_countdown >= countdown_duration:
            capture_started = True
            start_time = time.time()
        else:
            remaining = countdown_duration - elapsed_countdown
            cv2.putText(frame, f"Iniciando em: {int(remaining) + 1}s", (10, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (124,252,0), 2)

    if capture_started:
        elapsed_time = time.time() - start_time
        if elapsed_time >= capture_duration:
            frame_final = frame.copy()
            break

        if hands:
            lmList = hands[0]['lmList']
            x, y = lmList[4][0], lmList[4][1]  # THUMB_TIP

            if initial_x is None:
                initial_x = x

            if prev_x is not None and prev_y is not None:
                dx = abs(x - prev_x)
                dy = abs(y - prev_y)
                if dx > 3 or dy > 3:
                    cv2.line(canvas, (prev_x, prev_y), (x, y), (255, 255, 255), 3)
            prev_x, prev_y = x, y

            # Referência para px -> cm
            x1, y1 = lmList[0][0], lmList[0][1]
            x2, y2 = lmList[17][0], lmList[17][1]
            ref_distance_px = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            ref_distance_cm = 8.0
            px_to_cm = ref_distance_cm / ref_distance_px if ref_distance_px != 0 else 0

        if initial_x is not None:
            cv2.line(frame, (initial_x, 0), (initial_x, frame.shape[0]), (255,0,255), 2)

        if prev_x is not None and initial_x is not None:
            distance_x = abs(prev_x - initial_x)
            distance_cm = distance_x * px_to_cm
            cv2.putText(frame, f"Distancia X: {distance_cm:.2f} cm", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Suavizar e fundir
        smooth_canvas = cv2.GaussianBlur(canvas, (9, 9), 0)
        frame = cv2.addWeighted(frame, 0.5, smooth_canvas, 0.5, 0)

    cv2.imshow("Desenho com os dedos", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or cv2.getWindowProperty("Desenho com os dedos", cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()

# Salvar imagem final
if frame_final is None:
    frame_final = np.zeros_like(canvas)

final_image = cv2.addWeighted(frame_final, 0.5, canvas, 0.5, 0)

# Salva imagem no disco
os.makedirs("static/imagens", exist_ok=True)
timestamp = time.strftime("%Y%m%d-%H%M%S")
filename = f"{paciente_id}_{timestamp}.png"
output_path = os.path.join("static/imagens", filename)

# Codifica a imagem como PNG em memória
_, img_encoded = cv2.imencode('.png', final_image)
img_bytes = img_encoded.tobytes()

# Salva no banco de dados como binário
try:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO imagens (paciente_id, imagem, data) VALUES (%s, %s, %s)",
              (paciente_id, psycopg2.Binary(img_bytes), datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    print("Imagem binária registrada no banco com sucesso!")
except Exception as e:
    print(f"Erro ao salvar imagem binária no banco: {e}")

