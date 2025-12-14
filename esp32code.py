import time
import network
import ujson
from machine import Pin, I2C
from umqtt.simple import MQTTClient
import uhashlib


WIFI_SSID = "INFINITUM0D9E_2.4"
WIFI_PASS = "Valeria2494"

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)

    print("Conectando a WiFi...")
    while not wlan.isconnected():
        time.sleep(0.5)

    print("WiFi conectada:", wlan.ifconfig())
    return wlan

BROKER = "broker.hivemq.com"   
TOPIC_PUB = b"lock/attempts"
TOPIC_SUB = b"lock/responses"

def mqtt_callback(topic, msg):
    msg = msg.decode()
    print("Respuesta del servidor:", msg)

    if lcd:
        lcd.clear()
        lcd.move_to(0, 0)
        if msg == "allow":
            lcd.putstr("  ACCESO OK")
        else:
            lcd.putstr("  ACCESO FAIL")

        time.sleep(2)
        lcd.clear()
        lcd.putstr("Ingrese Codigo:")
        lcd.move_to(0, 1)


class I2C_LCD:
    LCD_CHR = 1
    LCD_CMD = 0
    LCD_CLEARDISPLAY = 0x01

    def __init__(self, i2c, addr, cols, rows):
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self.backlight = 0x08

        self.command(0x33)
        self.command(0x32)
        self.command(0x28)
        self.command(0x0C)
        self.command(0x06)
        self.command(self.LCD_CLEARDISPLAY)
        time.sleep_ms(2)

    def write_byte(self, data, mode):
        bh = (data & 0xF0) | mode | self.backlight
        self.i2c.writeto(self.addr, bytes([bh | 0x04]))
        time.sleep_us(50)
        self.i2c.writeto(self.addr, bytes([bh]))

        bl = ((data << 4) & 0xF0) | mode | self.backlight
        self.i2c.writeto(self.addr, bytes([bl | 0x04]))
        time.sleep_us(50)
        self.i2c.writeto(self.addr, bytes([bl]))

    def command(self, cmd):
        self.write_byte(cmd, self.LCD_CMD)

    def data(self, dat):
        self.write_byte(dat, self.LCD_CHR)

    def putstr(self, s):
        for c in s:
            self.data(ord(c))

    def move_to(self, col, row):
        offsets = [0x00, 0x40, 0x14, 0x54]
        self.command(0x80 | (col + offsets[row]))

    def clear(self):
        self.command(self.LCD_CLEARDISPLAY)
        time.sleep_ms(2)


SDA_PIN = 21
SCL_PIN = 22
LCD_I2C_ADDR = 0x27
LCD_COLS = 16
LCD_ROWS = 2

i2c = I2C(0, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=400000)
devices = i2c.scan()
lcd = None

if LCD_I2C_ADDR in devices:
    lcd = I2C_LCD(i2c, LCD_I2C_ADDR, LCD_COLS, LCD_ROWS)
    lcd.clear()
    lcd.putstr("Ingrese Codigo:")
    lcd.move_to(0, 1)
else:
    print("ERROR: No LCD detectado.")


COL_PINS = [17, 16, 4, 2]   # Columnas
ROW_PINS = [27, 19, 18, 5]  # Filas

KEYPAD_KEYS = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

cols = [Pin(p, Pin.OUT) for p in COL_PINS]
rows = [Pin(p, Pin.IN, Pin.PULL_UP) for p in ROW_PINS]

for c in cols:
    c.value(1)


def getKey():
    for j in range(4):
        cols[j].value(0)
        for i in range(4):
            if rows[i].value() == 0:
                time.sleep_ms(50)
                if rows[i].value() == 0:
                    while rows[i].value() == 0:
                        time.sleep_ms(10)
                    cols[j].value(1)
                    return KEYPAD_KEYS[i][j]
        cols[j].value(1)
    return None


def md5(texto):
    h = uhashlib.md5(texto.encode())
    raw = h.digest()
    return ''.join('{:02x}'.format(b) for b in raw)

conectar_wifi()

client = MQTTClient("esp32_client", BROKER)
client.set_callback(mqtt_callback)
client.connect()
client.subscribe(TOPIC_SUB)

print("MQTT conectado")

codigo = ""
lcd.move_to(0, 1)


while True:
    client.check_msg()
    key = getKey()

    if key:

        # Reinicio
        if key == "#":
            codigo = ""
            lcd.clear()
            lcd.putstr("Ingrese Codigo:")
            lcd.move_to(0, 1)
            continue

        # Borrar
        if key == "*":
            if len(codigo) > 0:
                codigo = codigo[:-1]
                lcd.move_to(0, 1)
                lcd.putstr(" " * 16)
                lcd.move_to(0, 1)
                lcd.putstr(codigo)
            continue

        # Solo dígitos válidos
        if key in "0123456789":
            if len(codigo) < 16:
                codigo += key
                lcd.move_to(0, 1)
                lcd.putstr(codigo)

        # Enviar PIN con "D"
        if key == "D":
            codigo = codigo.strip()

            if len(codigo) > 0:
                h = md5(codigo)
                print("PIN:", codigo)
                print("HASH:", h)

                data = ujson.dumps({"pin_hash": h})
                client.publish(TOPIC_PUB, data)

                lcd.clear()
                lcd.putstr("ENVIADO...")
                time.sleep(1)

            codigo = ""
            lcd.clear()
            lcd.putstr("Ingrese Codigo:")
            lcd.move_to(0, 1)

    time.sleep_ms(50)
