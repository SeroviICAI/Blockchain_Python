"""
Aplicación “web” del proyecto mediante la cual los usuarios podrán interactuar con las diversas funcionalidades de la
Blockchain. Esta aplicación será lanzada desde una terminal mediante el comando:

$ python Blockchain_app.py -p <especificar un puerto>

AUTORES: SERGIO RODRÍGUEZ VIDAL Y JAIME PAZ RODRÍGUEZ
"""

import Blockchain
import json
import requests

import platform
import socket
from argparse import ArgumentParser

from flask import Flask, jsonify, request
from threading import Semaphore, Timer
from typing import List

# Instancia del nodo
app = Flask(__name__)

# Instancia de la aplicación
blockchain = Blockchain.Blockchain()

# Nodos registrados en la red
nodos_red = set()

# Para saber mi ip
mi_ip = socket.gethostbyname(socket.gethostname())

# Semáforo mutex
mutex = Semaphore(1)


class ErrorIntegracionBloque(Exception):
    """
    Error al no poder integrar un bloque en la Blockchain.
    """
    def __init__(self):
        self.message = "El bloque no ha podido integrarse correctamente"
        super(ErrorIntegracionBloque, self).__init__()


@app.route('/system', methods=['GET'])
def obtener_detalles_nodo_actual():
    """
    Obtiene los detalles del nodo que los pida.
    :return: Respuesta en formato JSON
    """
    response = {
                'maquina': platform.machine(),
                'nombre_sistema': platform.system(),
                'version': platform.version()
                }
    return jsonify(response), 200


@app.route('/transacciones/nueva', methods=['POST'])
def nueva_transaccion():
    """
    Crea una nueva transacción en dicho nodo.
    :return: Respuesta en formato JSON.
    """
    values = request.get_json()
    # Comprobamos que todos los datos de la transaccion están completos
    required = ['origen', 'destino', 'cantidad']
    if not all(k in values for k in required):
        return 'Faltan valores', 400
    # Creamos una nueva transaccion aquí
    mutex.acquire()
    index = blockchain.nueva_transaccion(**values)
    mutex.release()
    response = {'mensaje': f'La transaccion se incluira en el bloque con indice {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def blockchain_completa():
    # Solamente permitimos la cadena de aquellos bloques finales que tienen hash
    mutex.acquire()
    chain = [bloque.__dict__ for bloque in blockchain.cadena if bloque.hash_bloque is not None]
    mutex.release()
    response = {
                'chain': chain,
                'longitud': len(chain)
                }
    return jsonify(response), 200


@app.route('/minar', methods=['GET'])
def minar():
    """
    Esta función mina la blockchain y se efectúa un pago al minero. En caso de no poder minar el bloque o existir algún
    conflicto, se eliminaría dicho pago.
    :return: Respuesta en formato JSON.
    """
    # No hay transacciones
    mutex.acquire()
    if not blockchain.transacciones_sin_confirmar:
        mutex.release()
        return {
                'mensaje': "No es posible crear un nuevo bloque. No hay transacciones"
                }
    mutex.release()
    # Se realiza pago al minero (con IP, mi_ip)
    mutex.acquire()
    blockchain.nueva_transaccion(origen="0", destino=mi_ip, cantidad=1)
    ultimo_bloque = blockchain.ultimo_bloque
    nuevo_bloque = blockchain.nuevo_bloque(hash_previo=ultimo_bloque.hash_bloque)
    prueba = blockchain.prueba_trabajo(nuevo_bloque)
    mutex.release()
    # Se comprueba si existen conflictos
    resuelve_conflicto = resuelve_conflictos()

    # Si ha habido conflictos, se resuelven y se remueven todas las transacciones
    if resuelve_conflicto:
        response = {
                    'mensaje': "Ha habido un conflicto. Esta cadena se ha actualizado con una version mas larga."
                    }
    else:
        mutex.acquire()
        resultado = blockchain.integra_bloque(nuevo_bloque, prueba)
        mutex.release()
        # Si no se pudo integrar correctamente, se remueve el pago al minero
        if not resultado:
            mutex.acquire()
            blockchain.transacciones_sin_confirmar.pop()
            mutex.release()
            response = {
                        'mensaje': "No es posible integrar el nuevo bloque."
                        }
        # Si sí se integra correctamente, se manda un mensaje de minado satisfactorio.
        else:
            response = {
                        'mensaje': f"El bloque {nuevo_bloque.indice} se ha minado satisfactoriamente."
                        }
    return jsonify(response), 200


@app.route('/nodos/registrar', methods=['POST'])
def registrar_nodos_completo():
    global blockchain, nodos_red
    # Extrae las direcciones de sus nuevos peers
    direccion_nodos = request.get_json().get('direccion_nodos')

    if direccion_nodos is None:
        return "Error: No se ha proporcionado una lista de nodos", 400
    # Actualiza su set de peers
    nodos_red.update(direccion_nodos)

    # Por cada nodo/peer, manda un diccionario copia de su blockchain, y los nuevos peers de dicho peer incluyéndose a
    # sí
    headers = {'Content-Type': "application/json"}
    for nodo in direccion_nodos:
        data = {
                'nodos_direcciones': [request.host_url, * [n for n in direccion_nodos if n != nodo]],
                'blockchain': blockchain.to_dict()
                }
        requests.post(nodo + "/nodos/registro_simple", data=json.dumps(data), headers=headers)

    response = {
                'mensaje': 'Se han incluido nuevos nodos en la red',
                'nodos_totales': list(nodos_red)
                }
    return jsonify(response), 201


@app.route('/nodos/registro_simple', methods=['POST'])
def registrar_nodo_actualiza_blockchain():
    """
    Esta función actualiza los nodos_red y blockchain a partir de unos dados. Puede haber algún error al crear la
    blockchain si esta no es correcta.
    :return: Respuesta en formato JSON
    """
    # Obtenemos la variable global de blockchain
    global blockchain, nodos_red

    # Extrae los input
    response = request.get_json()
    direccion_nodos = response.get("nodos_direcciones")
    # Actualiza sus peers
    nodos_red.update(direccion_nodos)

    # Crea una blockchain a partir de la leída
    blockchain_leida = response.get("blockchain")
    if blockchain_leida is None:
        return "El blockchain de la red está corrupto", 400
    else:
        mutex.acquire()
        blockchain = crear_blockchain_dump(blockchain_leida["cadena"])
        mutex.release()
    return "La blockchain del nodo" + str(mi_ip) + ":" + str(puerto) + "ha sido correctamente actualizada", 200


def crear_blockchain_dump(chain: List) -> Blockchain.Blockchain:
    """
    Crea un objeto Blockchain a partir de una cadena dada. En caso de haber habido un error al integrar bloques de
    esta cadena, entonces dará ErrorIntegracionBloque.
    :param chain: Cadena a partir de la cual se crea la blockchain.
    :return:
    """
    # Iniciamos una blockchain "vacía".
    blockchain = Blockchain.Blockchain()

    # Iteramos sobre cada bloque de la cadena y los integramos a la blockchain
    for index, data in enumerate(chain):
        bloque = Blockchain.Bloque(indice=data["indice"],
                                   transacciones=data["transacciones"],
                                   timestamp=data["timestamp"],
                                   hash_previo=data["hash_previo"],
                                   prueba=data["prueba"])
        prueba = data['hash_bloque']
        # El primer bloque es el mismo en todas las Blockchains, ya que se crea automáticamente, por lo que con cambiar
        # sus parámetros es necesario. No hace falta integrarlo.
        if index > 0:
            resultado = blockchain.integra_bloque(bloque, prueba)
            if not resultado:       # No se pudo integrar el bloque
                raise ErrorIntegracionBloque
        else:
            bloque.hash_bloque = prueba
            blockchain.cadena = [bloque]
    return blockchain


def resuelve_conflictos():
    """
    Mecanismo para establecer el consenso y resolver los conflictos. Para llegar a un consenso se escoge la cadena
    más larga.
    """
    global blockchain

    # Coge la longitud de la blockchain del nodo actual
    longitud_actual = len(blockchain)
    # Iniciamos una variable cadena_mas_larga, que podrá o no contener una cadena más larga que la actual (en caso de
    # existir)
    cadena_mas_larga = None
    # Por cada nodo, comprueba si su blockchain es mayor que la actual, y si es así, modifica la longitud actual por
    # esta y la cadena más larga también por esta.
    for nodo in nodos_red:
        response = requests.get(f'{nodo}/chain')
        longitud = response.json()['longitud']
        cadena = response.json()['chain']
        if longitud > longitud_actual:
            # Actualiza las variables
            longitud_actual = longitud
            cadena_mas_larga = cadena

    # Si hay una cadena más larga, haz que esta sea tu blockchain
    if cadena_mas_larga:
        blockchain = crear_blockchain_dump(cadena_mas_larga)
        return True
    else:
        print(blockchain)
        return False


def copia_seguridad():
    """
    Realiza una copia de seguridad de la blockchain cada 60 segundos.
    """
    # Iniciamos un temporizador cada 60 segundos
    timer = Timer(60., copia_seguridad)
    timer.daemon = True
    timer.start()
    # Creamos un JSON "copia de seguridad" con la blockchain de dicho nodo.
    blockchain.to_json(f'respaldo-nodo{mi_ip}-{puerto}.json', indent=2)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--puerto', default=5000, type=int, help='puerto para escuchar')
    args = parser.parse_args()
    puerto = args.puerto
    copia_seguridad()
    app.run(host='0.0.0.0', port=puerto)
