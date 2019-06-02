status = {'heater': False,
          'humidifier': False,
          'fan': False,
          'led': False}
# 'dryer' : False}

auto_settings = None
manu_settings = None

temp = [i for i in range(100)]
humid = [i*2 for i in range(100)]
co2 = [i*3 for i in range(100)]
time = ''
