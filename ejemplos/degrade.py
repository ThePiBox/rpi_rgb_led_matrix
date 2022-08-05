"""
degrade.py

Muestra las posibilidades de generación de distintos niveles de brillo por color de la matriz de LEDs 8x8
usando el módulo rpi_rgb_led_matrix con Micro Python en la placa Raspberry Pi Pico.

Usa la función set_pixels(...) para pasar datos de la imagen completa a la matriz en una sola llamada.

Aplica rotación a la imagen para ver cómo esto afecta al cambio de brillo. 

La función update() de la matriz se llama desde un nuevo thread.

Se usa la SM 0 de la Raspberry Pi Pico, y los GPIO 2, 3 y 4 para conectarse a los pines clk, ce y mosi
de la matriz de LEDs.

Publicado bajo licencia GPLv3.
El presente código se presenta como está, sin garantías de ningún tipo. El usuario asume la responsabilidad
total de cualquier resultado que pueda surgir de su uso o de la imposibilidad de usarlo.
"""

import _thread
import gc
from time import sleep

from rpi_rgb_led_matrix import Matrix

threshold = [10,80,140,255]

k = [0,0,0]

black = [
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k,
    k,k,k,k,k,k,k,k
    ]

dly = 2

rgb_matrix = Matrix(0, 2, 3, 4)
_thread.start_new_thread(rgb_matrix.update, ())

print ("Comenzamos.")
print ("Prueba de niveles de brillo por color.")

for n in range (0,3):
    a = [0,0,0]
    b = [0,0,0]
    c = [0,0,0]
    d = [0,0,0]
    
    a[n] = threshold[0]
    b[n] = threshold[1]
    c[n] = threshold[2]
    d[n] = threshold[3]

    image = [
        a,a,a,a,a,a,a,a,
        b,b,b,b,b,b,b,b,
        b,b,b,b,b,b,b,b,
        b,b,b,b,b,b,b,b,
        c,c,c,c,c,c,c,c,
        c,c,c,c,c,c,c,c,
        d,d,d,d,d,d,d,d,
        d,d,d,d,d,d,d,d
        ]

    rgb_matrix.rotation = 0
    print ("0 grados.")
    
    rgb_matrix.set_pixels(image)
    sleep(dly)

    print ("Rotamos.")
    rgb_matrix.rotation = 270
    sleep(dly)

print ("Limpiamos la pantalla.")

rgb_matrix.set_pixels(black)

print ("Prueba finalizada.")
