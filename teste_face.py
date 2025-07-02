import face_recognition
import cv2

# Carrega a imagem
imagem = face_recognition.load_image_file("uploads/2ad47ae2-569e-4a5e-ba1c-83819fa67c36_Locomotion 72.png")

# Detecta os rostos
face_locations = face_recognition.face_locations(imagem)

print(f"{len(face_locations)} rosto(s) encontrado(s).")

# Mostra a imagem com as marcações
for top, right, bottom, left in face_locations:
    cv2.rectangle(imagem, (left, top), (right, bottom), (0, 255, 0), 2)

# Converte de RGB para BGR e exibe
cv2.imshow('Resultado', cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR))
cv2.waitKey(0)
cv2.destroyAllWindows()
