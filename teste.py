import cv2

# Caminhos para os arquivos que você acabou de baixar
prototxt = "deploy.prototxt.txt"
model = "res10_300x300_ssd_iter_140000.caffemodel"

# Carrega a rede neural
net = cv2.dnn.readNetFromCaffe(prototxt, model)
print("Modelo carregado com sucesso!")

