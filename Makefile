deploy:
	fly deploy

parar:
	fly scale count 0

ligar:
	fly scale count 1

maquinas:
	fly machines list
