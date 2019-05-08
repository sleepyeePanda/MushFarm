status = {'heater': False,
          'humidifier': False,
          'fan': False,
          'led': False}

# actual value and error range
# days and hours
# hours and minutes
auto_settings = {'temp': [0, 0],
                 'humid': [0, 0],
                 'co2': [0, 0],
                 'actTime': [0, 0]}

manu_settings = {'temp': [0, 0],
                 'humid': [0, 0],
                 'co2': [0, 0],
                 'growTime': [0, 0],
                 'humidifier': {'freq': [0, 0],
                                'act': [0, 0]}}


temp = [i for i in range(10)]
humid = [i*2 for i in range(10)]
co2 = [i*3 for i in range(10)]
time = ''
