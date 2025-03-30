import numpy as np
import multiprocessing as mp
import time
import random
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import ctypes
from functools import partial

def generar_datos_prueba(tamano=10000000, valor_max=100000000):
    datos = np.random.randint(0, valor_max, tamano)
    datos = np.sort(datos)
    return datos

def busqueda_binaria_secuencial(arr, objetivo):
    izquierda, derecha = 0, len(arr) - 1
    
    while izquierda <= derecha:
        medio = (izquierda + derecha) // 2

        if arr[medio] == objetivo:
            return medio
        elif arr[medio] < objetivo:
            izquierda = medio + 1
        else:
            derecha = medio - 1
    return -1

def _buscar_en_segmento(arr, objetivo, inicio, fin, result_dict, segment_id):
    if inicio <= fin:
        if arr[inicio] <= objetivo <= arr[fin]:
            izquierda, derecha = inicio, fin
            while izquierda <= derecha:
                medio = (izquierda + derecha) // 2
                
                if arr[medio] == objetivo:
                    result_dict[segment_id] = medio 
                    return
                elif arr[medio] < objetivo:
                    izquierda = medio + 1
                else:
                    derecha = medio - 1
                    
    result_dict[segment_id] = -1

def busqueda_binaria_paralela(arr, objetivo, num_procesos=4):
    n = len(arr)
    
    segmento_tamano = n // num_procesos
    limites = [(i * segmento_tamano, 
               min((i + 1) * segmento_tamano - 1, n - 1)) 
               for i in range(num_procesos)]
    
    manager = mp.Manager()
    resultados = manager.dict()
    
    procesos = []
    for i in range(num_procesos):
        inicio, fin = limites[i]
        p = mp.Process(
            target=_buscar_en_segmento,
            args=(arr, objetivo, inicio, fin, resultados, i)
        )
        procesos.append(p)
        p.start()
    
    for p in procesos:
        p.join()

    for i in range(num_procesos):
        if resultados[i] != -1:
            return resultados[i]
    
    return -1

def _buscar_avanzado(arr, objetivo, izquierda, derecha, segmento_tamano, result_array):
    num_segmentos = (derecha - izquierda + 1 + segmento_tamano - 1) // segmento_tamano
    
    process_id = mp.current_process()._identity[0] % num_segmentos
    start = izquierda + process_id * segmento_tamano
    end = min(start + segmento_tamano - 1, derecha)
    left, right = start, end
    while left <= right and result_array[0] == -1:
        mid = (left + right) // 2
        
        if arr[mid] == objetivo:
            with result_array.get_lock():
                if result_array[0] == -1:
                    result_array[0] = mid
            return
        elif arr[mid] < objetivo:
            left = mid + 1
        else:
            right = mid - 1

def busqueda_binaria_paralela_avanzada(arr, objetivo, num_procesos=4):
    n = len(arr)
    if objetivo < arr[0] or objetivo > arr[n-1]:
        return -1
    
    izquierda, derecha = 0, n - 1
    for _ in range(3): 
        medio = (izquierda + derecha) // 2
        if arr[medio] == objetivo:
            return medio
        elif arr[medio] < objetivo:
            izquierda = medio + 1
        else:
            derecha = medio - 1

    if izquierda > derecha:
        return -1
    
    result_array = mp.Array('i', [1])
    result_array[0] = -1  
    
    segmento_tamano = max(1, (derecha - izquierda + 1) // num_procesos)
    procesos = []
    for _ in range(num_procesos):
        p = mp.Process(
            target=_buscar_avanzado,
            args=(arr, objetivo, izquierda, derecha, segmento_tamano, result_array)
        )
        procesos.append(p)
        p.start()
    
    for p in procesos:
        p.join()
    
    return result_array[0]

def _worker_busqueda_multiple(arr, objetivos, resultados, proceso_id, num_procesos):
    for i in range(proceso_id, len(objetivos), num_procesos):
        objetivo = objetivos[i]
        indice = busqueda_binaria_secuencial(arr, objetivo)
        resultados[objetivo] = indice

def busqueda_multiple_paralela(arr, objetivos, num_procesos=4):
    manager = mp.Manager()
    resultados = manager.dict()
    
    procesos = []
    for i in range(num_procesos):
        p = mp.Process(
            target=_worker_busqueda_multiple,
            args=(arr, objetivos, resultados, i, num_procesos)
        )
        procesos.append(p)
        p.start()

    for p in procesos:
        p.join()

    return dict(resultados)

def evaluar_rendimiento(tamaños=[1000000, 10000000], num_busquedas=100, max_procesos=8):
    resultados = {
        'secuencial': [],
        'paralelo_basico': [],
        'paralelo_avanzado': [],
        'tamaños': tamaños
    }
    
    for tamano in tamaños:
        print(f"Generando datos de prueba ({tamano} elementos)...")
        datos = generar_datos_prueba(tamano)
        busquedas = [datos[random.randint(0, tamano-1)] for _ in range(num_busquedas)]
        
        print("Ejecutando prueba secuencial...")
        tiempo_inicio = time.time()
        for objetivo in busquedas:
            busqueda_binaria_secuencial(datos, objetivo)
        tiempo_secuencial = time.time() - tiempo_inicio
        resultados['secuencial'].append(tiempo_secuencial)
        print(f"Tiempo secuencial: {tiempo_secuencial:.4f} segundos")
        
        tiempos_basico = []
        tiempos_avanzado = []
        
        for num_procesos in range(2, max_procesos + 1, 2):
            print(f"Ejecutando prueba paralela básica con {num_procesos} procesos...")
            tiempo_inicio = time.time()
            for objetivo in busquedas:
                busqueda_binaria_paralela(datos, objetivo, num_procesos)
            tiempo_paralelo = time.time() - tiempo_inicio
            tiempos_basico.append((num_procesos, tiempo_paralelo))
            print(f"Tiempo paralelo básico ({num_procesos} procesos): {tiempo_paralelo:.4f} segundos")
            
            print(f"Ejecutando prueba paralela avanzada con {num_procesos} procesos...")
            tiempo_inicio = time.time()
            for objetivo in busquedas:
                busqueda_binaria_paralela_avanzada(datos, objetivo, num_procesos)
            tiempo_paralelo = time.time() - tiempo_inicio
            tiempos_avanzado.append((num_procesos, tiempo_paralelo))
            print(f"Tiempo paralelo avanzado ({num_procesos} procesos): {tiempo_paralelo:.4f} segundos")
        
        resultados['paralelo_basico'].append(tiempos_basico)
        resultados['paralelo_avanzado'].append(tiempos_avanzado)
    
    return resultados

def visualizar_resultados(resultados):
    fig = plt.figure(figsize=(15, 10))
    
    for i, tamano in enumerate(resultados['tamaños']):
        plt.subplot(2, len(resultados['tamaños']), i + 1)
        procesos_basico = [t[0] for t in resultados['paralelo_basico'][i]]
        speedup_basico = [resultados['secuencial'][i] / t[1] for t in resultados['paralelo_basico'][i]]
        plt.plot(procesos_basico, speedup_basico, 'o-', label='Paralelo básico')
        procesos_avanzado = [t[0] for t in resultados['paralelo_avanzado'][i]]
        speedup_avanzado = [resultados['secuencial'][i] / t[1] for t in resultados['paralelo_avanzado'][i]]
        plt.plot(procesos_avanzado, speedup_avanzado, 's-', label='Paralelo avanzado')
        
        plt.plot(procesos_basico, procesos_basico, '--', label='Speedup ideal')
        
        plt.title(f"Speedup vs Núm. Procesos (Tamaño: {tamano})")
        plt.xlabel("Número de procesos")
        plt.ylabel("Speedup")
        plt.grid(True)
        plt.legend()
        
        plt.subplot(2, len(resultados['tamaños']), i + 1 + len(resultados['tamaños']))
        tiempo_sec = resultados['secuencial'][i]
        tiempos_basico = [t[1] for t in resultados['paralelo_basico'][i]]
        tiempos_avanzado = [t[1] for t in resultados['paralelo_avanzado'][i]]
        
        plt.bar(0, tiempo_sec, width=0.4, label='Secuencial')
        x_basico = [1 + j for j in range(len(procesos_basico))]
        x_avanzado = [1.5 + j for j in range(len(procesos_avanzado))]
        
        plt.bar(x_basico, tiempos_basico, width=0.4, label='Paralelo Básico')
        plt.bar(x_avanzado, tiempos_avanzado, width=0.4, label='Paralelo Avanzado')
        x_ticks = [0] + [(x_basico[j] + x_avanzado[j]) / 2 for j in range(len(x_basico))]
        x_labels = ['1'] + [str(procesos_basico[j]) for j in range(len(procesos_basico))]
        plt.xticks(x_ticks, x_labels)
        
        plt.title(f"Tiempo de ejecución (tamaño: {tamano})")
        plt.xlabel("Número de procesos")
        plt.ylabel("Tiempo (segundos)")
        plt.grid(True)
        plt.legend()
    
    plt.tight_layout()
    plt.savefig('resultados_busqueda_binaria_paralela.png')
    plt.close()

def main():
    print("=== DEMOSTRACIÓN DE BÚSQUEDA BINARIA PARALELA ===")
    print("Iniciando pruebas de rendimiento...")
    tamaños = [10000000, 50000000]
    num_busquedas = 50  
    max_procesos = mp.cpu_count()  
    
    print(f"Número de procesadores disponibles: {max_procesos}")
    max_procesos = min(8, max_procesos) 
    resultados = evaluar_rendimiento(tamaños, num_busquedas, max_procesos)
    
    print("Generando gráficas de resultados...")
    visualizar_resultados(resultados)
    print("Gráficas guardadas en 'resultados_busqueda_binaria_paralela.png'")
    
    print("\n=== DEMOSTRACIÓN DE USO BÁSICO ===")
    tamano_demo = 10000000
    print(f"Generando arreglo ordenado de {tamano_demo} elementos...")
    datos = generar_datos_prueba(tamano_demo)
    
    indice_objetivo = random.randint(0, tamano_demo - 1)
    valor_objetivo = datos[indice_objetivo]
    print(f"Buscando el valor {valor_objetivo} (presente en el índice {indice_objetivo})...")
    
    inicio = time.time()
    resultado_secuencial = busqueda_binaria_secuencial(datos, valor_objetivo)
    tiempo_secuencial = time.time() - inicio
    
    inicio = time.time()
    resultado_paralelo = busqueda_binaria_paralela(datos, valor_objetivo, 4)
    tiempo_paralelo = time.time() - inicio
    
    inicio = time.time()
    resultado_avanzado = busqueda_binaria_paralela_avanzada(datos, valor_objetivo, 4)
    tiempo_avanzado = time.time() - inicio
    
    print(f"\nResultados de búsqueda para {valor_objetivo}:")
    print(f"  Secuencial: índice {resultado_secuencial} (tiempo: {tiempo_secuencial:.6f} s)")
    print(f"  Paralelo básico: índice {resultado_paralelo} (tiempo: {tiempo_paralelo:.6f} s)")
    print(f"  Paralelo avanzado: índice {resultado_avanzado} (tiempo: {tiempo_avanzado:.6f} s)")
    
    print("\n=== DEMOSTRACIÓN DE BÚSQUEDA MÚLTIPLE ===")
    num_valores = 10
    valores_buscar = [datos[random.randint(0, tamano_demo - 1)] for _ in range(num_valores)]
    print(f"Buscando {num_valores} valores diferentes...")
    
    inicio = time.time()
    resultados_multiples = busqueda_multiple_paralela(datos, valores_buscar, 4)
    tiempo_multiple = time.time() - inicio
    
    print(f"Búsqueda múltiple completada en {tiempo_multiple:.6f} segundos")
    print(f"Resultados: {resultados_multiples}")

    print("\n=== PRUEBA FINALIZADA ===")

if __name__ == "__main__":
    mp.freeze_support()
    main()