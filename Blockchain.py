"""
Blockchain.py es el módulo principal de la aplicación Blockchain_app.py. Este módulo contiene las clases y objetos
fundamentales que definen la Blockchain. En específico, se implementan los objetos: Transacción, Bloque y Blockchain.

AUTORES: SERGIO RODRÍGUEZ VIDAL Y JAIME PAZ RODRÍGUEZ
"""

import json
from datetime import datetime
from hashlib import sha256

from time import time
from typing import List, Dict, Optional, IO, Union

FileIO = Union[str, IO[str]]
TransactionLikeList = List[Optional[Dict]]


class Transaccion(object):
    def __init__(self, origen: str, destino: str, cantidad: int):
        """
        Constructor de la clase 'Transaccion'.
        :param origen: Originario de la transacción.
        :param destino: Destinatario de la transacción.
        :param cantidad: Cantidad de dinero enviada.
        """
        self.origen = origen
        self.destino = destino
        self.cantidad = cantidad
        self.timestamp = time()


class Bloque(object):
    def __init__(self, indice: int, transacciones: TransactionLikeList, hash_previo: str, timestamp: float,
                 prueba: int = 0, calcular_hash: bool = False):
        """
        Constructor de la clase 'Bloque'.
        :param indice: ID unico del bloque.
        :param transacciones: Lista de transacciones.
        :param hash_previo: hash previo.
        :param prueba:  prueba de trabajo.
        :param calcular_hash: Calcula el hash del bloque (default: False)
        """
        self.hash_bloque = None
        self.hash_previo = hash_previo
        self.indice = indice
        self.timestamp = timestamp
        self.prueba = prueba
        self.transacciones = transacciones
        if calcular_hash:
            self.hash_bloque = self.calcular_hash()

    def calcular_hash(self):
        """
        Método que devuelve el hash de un bloque.
        :return: hash del bloque
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return str(sha256(block_string.encode()).hexdigest())


class Blockchain(object):
    dificultad = 4

    def __init__(self):
        """
        Constructor de la clase
        """
        self.cadena = []
        self.transacciones_sin_confirmar = []
        self.primer_bloque()

    def __len__(self):
        """
        Devuelve la longitud de la blockchain
        :return: longitud
        """
        return len(self.cadena)

    def to_json(self, path_or_buf: FileIO, **kwargs):
        """
        Guarda la blockchain en un fichero JSON en un path o archivo indicado
        :param path_or_buf: path o fichero de guardado
        :param kwargs: Parámetros adicionales del JSON dump (indent por ejemplo)
        :return: None
        """
        if isinstance(path_or_buf, str):
            path_or_buf = open(path_or_buf, 'w')
        return json.dump(self.to_dict(), path_or_buf, **kwargs)

    def to_dict(self):
        """
        Convierte la blockchain a un diccionario
        :return: Diccionario de la blockchain
        """
        blockchain_dict = {
            'cadena': list(map(lambda block: block.__dict__, self.cadena)),
            'longitud': len(self),
            'date': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        return blockchain_dict

    @property
    def ultimo_bloque(self) -> Bloque:
        """
        Método que devuelve el último bloque del Blockchain
        :return: último bloque
        """
        return self.cadena[-1]

    def primer_bloque(self) -> Bloque:
        """
        Crea un primer bloque vacío que sirva de raíz para el resto de bloques
        :return: primer bloque
        """
        self.cadena.append(primer_bloque := Bloque(1, [], "1", calcular_hash=True, timestamp=time()))
        return primer_bloque

    @staticmethod
    def prueba_valida(bloque: Bloque, hash_bloque: str) -> bool:
        """
        Método que comprueba si el hash_bloque comienza con tantos ceros como la dificultad estipulada en el blockchain.
        Además, revisará que hash_bloque coincide con el valor devuelto del método de calcular hash del bloque.
        Si cualquiera de ambas comprobaciones es falsa, devolverá falso y en caso contrario, verdadero.
        :param bloque: Bloque a comprobar.
        :param hash_bloque: valor de hash bloque buscado
        :return: True o False, si coincide o no coincide con el bloque dado
        """
        return hash_bloque.startswith('0' * Blockchain.dificultad) and hash_bloque == bloque.calcular_hash()

    @staticmethod
    def prueba_trabajo(bloque: Bloque) -> str:
        """
        Algoritmo simple de prueba de trabajo:
        - Calculará el hash del bloque hasta que encuentre un hash que empiece
          por tantos ceros como dificultad.
        - Cada vez que el bloque obtenga un hash que no sea adecuado,
          incrementara en uno el campo de ``prueba del bloque''.
        :param bloque: objeto de tipo bloque.
        :return: el hash del nuevo bloque (dejará el campo de hash del bloque sin modificar).
        """
        bloque.prueba = 0

        hash_calculado = bloque.calcular_hash()
        while not hash_calculado.startswith('0' * Blockchain.dificultad):
            bloque.prueba += 1
            hash_calculado = bloque.calcular_hash()
        return hash_calculado

    def nuevo_bloque(self, hash_previo: str) -> Bloque:
        """
        Crea un nuevo bloque a partir de las transacciones que no están confirmadas.
        :param hash_previo: el hash del bloque anterior de la cadena
        :return: nuevo bloque
        """
        return Bloque(self.ultimo_bloque.indice + 1, self.transacciones_sin_confirmar, hash_previo, timestamp=time())

    def integra_bloque(self, bloque_nuevo: Bloque, hash_prueba: str) -> bool:
        """
        Método para integrar correctamente un bloque a la cadena de bloques. Debe comprobar que la prueba de hash es
        válida y que el hash del bloque último de la cadena coincida con el hash_previo del bloque que se va a
        integrar. Si pasa las comprobaciones, actualiza el hash del bloque a integrar, lo inserta en la cadena y hace
        un reset de las transacciones no confirmadas (vuelve a dejar la lista de transacciones no confirmadas a una
        lista vacía).
        :param bloque_nuevo: el nuevo bloque que se va a integrar.
        :param hash_prueba: prueba del hash del bloque.
        :return: bool. True si se consiguió integrar, False en caso contrario.
        """
        hash_previo = self.ultimo_bloque.hash_bloque
        if hash_previo != bloque_nuevo.hash_previo:
            return False

        if not self.prueba_valida(bloque_nuevo, hash_prueba):
            return False

        bloque_nuevo.hash_bloque = hash_prueba
        self.cadena.append(bloque_nuevo)
        self.transacciones_sin_confirmar = []
        return True

    def nueva_transaccion(self, origen: str, destino: str, cantidad: int) -> int:
        """
        Crea una nueva transaccion a partir de un origen, un destino y una cantidad y la incluye en las listas de
        transacciones.
        :param origen: Originario de la transacción.
        :param destino: Destinatario de la transacción.
        :param cantidad: la cantidad.
        :return: el hash del nuevo bloque (dejará el campo de hash del bloque sin modificar)
        """
        nueva_transaccion = Transaccion(origen, destino, cantidad)
        self.transacciones_sin_confirmar.append(nueva_transaccion.__dict__)
        return len(self.cadena) + 1
