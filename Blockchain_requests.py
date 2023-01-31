"""
Fichero de pruebas en el que se hace uso de las principales funciones del programa a modo de ejemplo. Para su uso será
necesario iniciar 3 terminales en los puertos 5000, 5001 y 5002 del host local.

AUTORES: SERGIO RODRÍGUEZ VIDAL Y JAIME PAZ RODRÍGUEZ
"""

import requests
import json

# Cabecera JSON (común a todas)
cabecera = {'Content-type': 'application/json', 'Accept': 'text/plain'}

r = requests.get('http://localhost:5000/system')
print(r.text)

# datos transaccion
transaccion_nueva = {'origen': 'nodoA', 'destino': 'nodoB', 'cantidad': 10}
r = requests.post('http://localhost:5000/transacciones/nueva', data=json.dumps(transaccion_nueva), headers=cabecera)
print(r.text)

r = requests.get('http://localhost:5000/minar')
print(r.text)

r = requests.get('http://localhost:5000/chain')
print(r.text)

direccion_nodos = {"direccion_nodos": ["http://localhost:5001", "http://localhost:5002"]}
r = requests.post('http://localhost:5000/nodos/registrar', data=json.dumps(direccion_nodos), headers=cabecera)
print(r.text)

transaccion_nueva = {'origen': 'nodoC', 'destino': 'nodoB', 'cantidad': 10}
r = requests.post('http://localhost:5000/transacciones/nueva', data=json.dumps(transaccion_nueva), headers=cabecera)
print(r.text)

r = requests.get('http://localhost:5000/minar')
print(r.text)

r = requests.get('http://localhost:5000/chain')
print(r.text)

transaccion_nueva = {'origen': 'nodoD', 'destino': 'nodoB', 'cantidad': 10}
r = requests.post('http://localhost:5001/transacciones/nueva', data=json.dumps(transaccion_nueva), headers=cabecera)
print(r.text)

r = requests.get('http://localhost:5001/minar')
print(r.text)

r = requests.get('http://localhost:5001/chain')
print(r.text)

r = requests.get('http://localhost:5002/minar')
print(r.text)

r = requests.get('http://localhost:5002/chain')
print(r.text)

transaccion_nueva = {'origen': 'nodoD', 'destino': 'nodoC', 'cantidad': 10}
r = requests.post('http://localhost:5002/transacciones/nueva', data=json.dumps(transaccion_nueva), headers=cabecera)
print(r.text)

r = requests.get('http://localhost:5002/minar')
print(r.text)

r = requests.get('http://localhost:5002/chain')
print(r.text)
