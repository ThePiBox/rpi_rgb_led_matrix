import rp2
import _thread
from machine import Pin
from time import sleep
import gc

"""
Módulo para controlar la Matriz de LEDs RGB 8x8 de 52Pi (https://wiki.52pi.com/index.php?title=EP-0075)
con la tarjeta de microcontrolador Raspberry Pi Pico y Micro Python.

Basado en la descripción del producto del propio fabricante. También de algnas ideas encontradas en
el foro de Raspberry Pi (https://forums.raspberrypi.com/viewtopic.php?t=296528) y en el códgo fuente y
la interfaz de programación del Sense HAT de Raspberrry Pi (https://github.com/astro-pi/python-sense-hat).

El módulo usa un PIO de la Raspberry Pi Pico y 3 GPIO, además de los pines de voltaje y GND.

TODO:
*** La función update() que se encarga de mantener actualizado el display puede ser llamada desde un
thread secundario o usando un Timer.
*** Usa lock para evitar problemas al ser usado en un segundo thread.
*** Usa llamadas al Garbage Collector para evitar problemas derivados de un uso ecesivo de memoria.
*** Mejorar la descripción y documentación de uso (hacerlo estándar?).

Publicado bajo licencia GPLv3.
El presente código se presenta como está, sin garantías de ningún tipo. El usuario asume la responsabilidad
total de cualquier resultado que pueda surgir de su uso o de la imposibilidad de usarlo.
"""

# set_init: Inicia en High. Se usará para el CE, que baja cuando se va a enviar datos
# out_init: Inicia en Low. Se usara para la transmisión de datos (MOSI)
# sideset_init: Inicia en High. Se usará para el clock
@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH, out_init=rp2.PIO.OUT_LOW, sideset_init=rp2.PIO.OUT_LOW)
def refresh_matrix():
    # El registro x será siempre 0. Asi cuando no haya más datos, la pantalla se pondrá negra.
    # Esto evitará que la ultima hilera recibida se quede encendida más tiempo que
    # las otras, causando destellos no deseados.
    set(x, 0)
    
    wrap_target()
    set(y, 31) # el registro y se usa como contador de loop
    
    pull(noblock) # si no hay más datos se tomará el valor de x
    set(pins, 0) # ce baja para iniciar la transferencia de datos hacia la matriz
    
    label("bitloop")
    out(pins, 1) .side(1) # se transfiere un bit por out, se sube side como un tick de reloj
    nop() .side(0) # se baja side como un tick de reloj
    jmp(y_dec, "bitloop") # se decrementa y, se hace loop si no ha llegado a 0
    
    set(pins, 1) # ce sube para indicar el fin de transferencia de datos
    wrap()

class Matrix:  
    def __init__(self, sm, clk, ce, mosi):
        # Creamos el array que servirá de buffer para la imagen.
        # Nuestro buffer almacena 64 valores, cada uno con los valores RGB de cada pixel.
        self._fb_0 = []
        
        for index in range(64):
            self._fb_0.append(0)
            
        # Creamos los arrays que servirán como almacén de la información de la imagen
        # para cada grado de intensidad de color. Cada array tiene 8 valores.
        # Cada valor corresponde a una fila de la matriz. Cada valor tiene 8 bytes.
        # 3 bytes representan los componentes RGB de la imagen y el ùltimo byte indica
        # el número de fila. Esta es la información que se envía directamente a la matriz LED.
        # Por característica de la matriz, los colores se almacenan como RBG, no RGB.
        self._shade_0 = [0xffffff01,0xffffff02,0xffffff04,0xffffff08,0xffffff10,0xffffff20,0xffffff40,0xffffff80]
        self._shade_1 = [0xffffff01,0xffffff02,0xffffff04,0xffffff08,0xffffff10,0xffffff20,0xffffff40,0xffffff80]
        self._shade_2 = [0xffffff01,0xffffff02,0xffffff04,0xffffff08,0xffffff10,0xffffff20,0xffffff40,0xffffff80]
        self._shade_3 = [0xffffff01,0xffffff02,0xffffff04,0xffffff08,0xffffff10,0xffffff20,0xffffff40,0xffffff80]
        self._fb_shade = [self._shade_0, self._shade_1, self._shade_2, self._shade_3]
        
        # Creamos el mapa de rotación que trasladará los
        # pixeles independientes de la imagen de entrada
        # a su posición final, dependiendo de la rotación
        # que se le haya aplicado a la imagen
        self._rotation_map = {}
        self._rotation = 0
        
        rotation_0 = []
        for n in range(64):
            rotation_0.append(n)
            
        self._rotation_map[0]=rotation_0
        
        for n in range(3):
            self._rotation_map[90*(n+1)]=[0]*64
            
            for row in range(8):
                for col in range(8):
                    self._rotation_map[90*(n+1)][row*8+col] = self._rotation_map[90*n][(7-col)*8+row]
        
        # lock para conrolar el acceso a los buffers de imagen desde distintos threads            
        self._fb_lock = _thread.allocate_lock() 
                    
        # Calculamos la frecuencia de procesamiento de la state machine y la
        # frecuencia de actualización del display dependiendo de la cantidad
        # de niveles de brillo seleccionada
        
        # 32 bits por fila, x 8 filas, x 3 colores, x fps (60-75), x 8 instrucciones de la SM,
        # = 368640 Hz. Eso se multiplica por la cantidad de shades
        self._shades = 4
        self._shade_threshold = self.get_shades_thresholds(self._shades)
        
        fps = 60
        freq = 32 * 8 * 3 * 8 * fps * self._shades
        
        self._brightness_levels = 8
        
        #sm_freq = freq * (self._brightness_levels + shades)
        sm_freq = 244140*6
        timer_freq = fps * (self._brightness_levels + self._shades)
        self._period = 1 / timer_freq
        
        # Definición de los parámetros de la State Machine que usaremos para controlar la matriz de LEDs
        # sm = state machine
        # sideset pin = CLK
        # set pin = CE
        # out pin = MOSI
        self._sm = rp2.StateMachine(sm, refresh_matrix, freq=sm_freq, out_base=Pin(mosi), set_base=Pin(ce), sideset_base=Pin(clk))
        self._sm.active(1)
    
    def update(self):
        # Actualizamos la pantalla, línea por línea
        # Lo hacemos color por color, para asegurar un brillo homogéneo.
        
        while True:            
            # Adquirimos el lock. Los buffers de imagen no deben cambiar mientras refrescamos la matriz de LEDs
            #self._fb_lock.acquire()
            
            for shade in range(self._shades):                
                for row in range(8):
                    
                    self._sm.put(self._fb_shade[shade][row] | 0x00ffff00)
                    self._sm.put(self._fb_shade[shade][row] | 0xff00ff00)
                    self._sm.put(self._fb_shade[shade][row] | 0xffff0000)
                    
            #sleep(0.01)
                    
            gc.collect()
                    
            # Dejamos el lock
            #self._fb_lock.release()            
            
    def set_pixels(self, new_img):
        # Copiamos los datos de la imagen a nuestor buffer interno.
        # Los valores RGB de cada pixel se empaquetan en un solo número por pixel.
        # Así nuestro buffer tiene 64 valores, cada valor ocupando 3 bytes (1 por color).
        # Con esto almacenamos una copia de la imagen que podemos usar para acceder a los datos
        # originales deser necesario pero ocupando menos memoria.
        for index in range (64):
            color = new_img[index].copy()
            self._fb_0[index] = (color[0]<<16) + (color[1]<<8) + color[2]
        
        # Llenamos los buffers de color con los datos de la imagen.
        # Cada buffer de color tiene 8 valores que representan las filas de la matriz de LEDs.
        # Cada valor (fila) tiene 4 bytes, que representan 4 niveles de intensidad por pixel.
        # De esa manera se puede definir cuando un color permanecerá más o menos tiempo encendido
        # y crear el efecto de intensidad. Combinando distintas intensidades de cada comonente RGB
        # se puede crear combinaciones de colores distintas.
        
        # El valor de cada byte dependerá del valor original del color en la imagen recibida.
        
        # Adquirimos el lock
        #self._fb_lock.acquire()
        
        for row in range(8):           
            for shade in range (self._shades):
                threshold = self._shade_threshold[shade]
                r = 0
                g = 0
                b = 0
            
                for column in range(8):
                    r = r<<1
                    g = g<<1
                    b = b<<1
                    
                    pixel = new_img[self._rotation_map[self._rotation][8 * row + 7 - column]]                    
                    
                    if pixel[0] > threshold:
                        pass
                    else:
                        r += 1
                        
                    if pixel[1] > threshold:
                        pass
                    else:
                        g += 1
                        
                    if pixel[2] > threshold:
                        pass
                    else:
                        b += 1

                self._fb_shade[shade][row] = (r<<24) + (b<<16) + (g<<8) + (2**row)
                
        #gc.collect()
        
        # Dejamos el lock
        #self._fb_lock.release()

    def get_pixels(self):
        # Retornamos una copia de la imagen actualmente almacenada en memoria.    
        current_image = []
        for index in range(64):
            pixel = self._fb_0[index]
            r = (pixel & 0xff0000) >> 16
            g = (pixel & 0x00ff00) >> 8
            b = (pixel & 0xff)
            current_image.append([r,g,b])
                
        return current_image
                
    def set_pixel(self, x, y, color):
        # Cambiamos el valor del pixel de la imagen almacenada por el
        # valor recibido
        self._fb_0[y*8+x] = (color[0]<<16) + (color[1]<<8) + color[2]
            
        # Ajustamos el valor de los buffers de colores directamente
        # a partir del valor de color recibido, tomando en cuenta
        # la rotacón establecida. Lo hacemos así en lugar de llamar
        # a set_pixels para que sea más eficiente. De lo contrario habría
        # que hacer un movimiento de datos enorme (todos los pixeles por color)
        # para cambiar solo un pixel.
        
        # Calculamos la fila afectada por el cambio de color, tomando en cuenta
        # la rotación
        row = int(self._rotation_map[self._rotation][(8*y+(7-x))]/8)
        
        for shade in range(self._shades):
            threshold = self._shade_threshold[shade]
            r = 0
            g = 0
            b = 0
            
            # Creamos los bytes de color para la fila afectada
            for column in range(8):
                r = r<<1
                g = g<<1
                b = b<<1                 
                
                c = self._fb_0[self._rotation_map[self._rotation][8 * row + 7 - column]]                
                cr = (c & 0xff0000) >> 16
                cg = (c & 0x00ff00) >> 8
                cb = (c & 0xff)
                
                pixel = [cr, cg, cb]                
                
                if pixel[0] > threshold:
                    pass
                else:
                    r += 1
                    
                if pixel[1] > threshold:
                    pass
                else:
                    g += 1
                    
                if pixel[2] > threshold:
                    pass
                else:
                    b += 1
                    
            # Adquirimos el lock
            #self._fb_lock.acquire()

            # Reemplazamos los bytes de color en la fila afectadac para el shade actual
            self._fb_shade[shade][row] = (r<<24) + (b<<16) + (g<<8) + (2**row)

            # Dejamos el lock
            #self._fb_lock.release()
        
        #gc.collect()
            
    def get_pixel(self, x, y):
        pixel = self._fb_0[y*8+x]
        
        r = (pixel & 0xff0000) >> 16
        g = (pixel & 0x00ff00) >> 8
        b = (pixel & 0xff)
        
        return [r,g,b]
        
        
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, r):
        self.set_rotation(r)
        
    def set_rotation(self, new_rotation=0, redraw=True):
        if new_rotation in self._rotation_map.keys():
            self._rotation = new_rotation
        else:
            raise ValueError('La rotación debe ser 0, 90, 180 o 270 grados')
        
        if redraw:
            self.set_pixels(self.get_pixels())
            
    def get_shades_thresholds(self, shades):
        interval = int(255/shades)
        v = 0
        thresholds = []
         
        for x in range(shades):
            thresholds.append(v)
            v += interval
        
        return thresholds

