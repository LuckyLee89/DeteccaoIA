import cv2

# Caminhos
prototxt = "deploy.prototxt.txt"
model = "res10_300x300_ssd_iter_140000.caffemodel"
image_path = "foto.jpg"  # Substitua pelo nome da sua imagem

# Carrega a imagem e modelo
image = cv2.imread(image_path)
(h, w) = image.shape[:2]

net = cv2.dnn.readNetFromCaffe(prototxt, model)
blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                             (300, 300), (104.0, 177.0, 123.0))

net.setInput(blob)
detections = net.forward()

for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]

    if confidence > 0.5:
        box = detections[0, 0, i, 3:7] * [w, h, w, h]
        (startX, startY, endX, endY) = box.astype("int")

        cv2.rectangle(image, (startX, startY), (endX, endY),
                      (0, 255, 0), 2)

cv2.imshow("Resultado", image)
cv2.waitKey(0)
cv2.destroyAllWindows()

