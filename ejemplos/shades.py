"""
shades.py

Muestra las posibilidades de generación de colores de la matriz de LEDs 8x8 y el módulo
rpi_rgb_led_matrix con Micro Python en la placa Raspberry Pi Pico.

Usa las funciones set_pixel(...) y set_pixels(...) para controlar los LEDs de la matriz, ya sea
de forma independiente o pasando los datos de una imagen completa en una sola llamada.

La función update() de la matriz se llama desde un nuevo thread.

Se hace uso se gc.collect() para llamar al Garbage Collector y evitar qudarnos sin memoria.
Esto puede pasar porque movemos una buena cantidad de datos cuando copiamos las imágenes al
objeto Matrix.

Se usa la SM 0 de la Raspberry Pi Pico, y los GPIO 2, 3 y 4 para conectarse a los pines clk, ce y mosi
de la matriz de LEDs.

Publicado bajo licencia GPLv3.
El presente código se presenta como está, sin garantías de ningún tipo. El usuario asume la responsabilidad
total de cualquier resultado que pueda surgir de su uso o de la imposibilidad de usarlo.
"""

import time
from rpi_rgb_led_matrix import Matrix
from random import choice, randint
import _thread
import gc

print ("Comenzamos.")
print ("Prueba de combinación de colores.")

r = [255,0,0]
g = [0,255,0]
b = [0,0,255]

y = [255,255,0]
w = [255,255,255]
k = [0,0,0]
p = [255,0,255]

m = [40,40,40]

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

r = [255,0,0]
g = [0,255,0]
b = [0,0,255]

image2 = black.copy()

#machine.freq(190000000)

rgb_matrix = Matrix(0, 2, 3, 4)
_thread.start_new_thread(rgb_matrix.update, ())

#rgb_matrix.set_brightness(rgb_matrix.brightness_levels)

dly_mono = 0.5
dly_colores = 0.5

gc.collect()

print ("Combinaciones de rojo y verde.")
for t in range(20):
    for n in range (0,64):
        image2[n] = [randint(0,255),randint(0,255),0]
        
    rgb_matrix.set_pixels(image2)
    time.sleep(dly_mono)
  
gc.collect()

print ("Combinaciones de rojo y azul.")
for t in range(20):
    for n in range (0,64):
        image2[n] = [randint(0,255),0,randint(0,255)]
        
    rgb_matrix.set_pixels(image2)
    time.sleep(dly_mono)
  
gc.collect()

print ("Combinaciones de verde y azul.")
for t in range(20):
    for n in range (0,64):
        image2[n] = [0,randint(0,255),randint(0,255)]
        
    rgb_matrix.set_pixels(image2)
    time.sleep(dly_mono)
  
gc.collect()

print ("Combinaciones de rojo, verde y azul.")
for t in range(20):
    for n in range (0,64):
        image2[n] = [randint(0,255),randint(0,255),randint(0,255)]
        
    rgb_matrix.set_pixels(image2)
    time.sleep(dly_colores)
  
gc.collect()

print ("Añadimos al display colores definidos previamente.")
for x in range(25):
    rgb_matrix.set_pixel(randint(0,7), randint(0,7), choice([r,g,b,y,w,k,p]))
    time.sleep(dly_colores)

time.sleep(2)

print ("Limpiamos la pantalla.")

rgb_matrix.set_pixels(black)

print ("Prueba finalizada.")


