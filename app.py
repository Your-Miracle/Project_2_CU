import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
API_KEY = 'XACWAsknx3Upz0V4ARcBUDaHfprlUKHl' #Наш API
#Открываем сайт  - http://127.0.0.1:5000/

# Функция по поиску координат города:
def get_location_key(city):
    try:
        url = f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={API_KEY}&q={city}&language=ru"
        response = requests.get(url) #Отправляем GET запрос
        # Проверяем ответ
        response.raise_for_status()
        data = response.json()
        # Проверяем на существование города
        if len(data) <= 0:
            return {"error": "Город не существует. Пожалуйста, перепроверьте данные"}
        return data[0]['Key']

    # Если лимит запросов превышен:
    except requests.exceptions.HTTPError as e:
        if response.status_code == 503:
            return {"error": "Лимит запросов превышен"}
        return {"error": {e}}

    except requests.exceptions.RequestException as e:
        return {"error": "Невозможно получить данные о городе."}


# Функция получения данных о погоде по координатам:
def get_weather_data(loc):
    try:
        forecast_url = f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{loc}?apikey={API_KEY}&metric=true"
        # Отправляем GET запрос
        forecast_response = requests.get(forecast_url)
        # Проверяем ответ
        forecast_response.raise_for_status()
        return forecast_response.json()
    # Если лимит запросов был превышен:
    except requests.exceptions.HTTPError as e:
        if forecast_response.status_code == 503:
            return {"error": "Лимит запросов превышен"}
        return {"error": e}

    except requests.exceptions.RequestException as e:
        return {"error": "Невозможно получить данные о погоде в городе. Попробуйте снова"}

#Эта функция обрабатывает данные о погоде, полученные из предыдущей функции
def process_weather_data(data):
    if data and 'DailyForecasts' in data:
        forecast = data['DailyForecasts'][0]

        mitemperature = forecast['Temperature']['Minimum']['Value']
        matemperature = forecast['Temperature']['Maximum']['Value']
        averaget = round(0.5 * (mitemperature + matemperature), 2)

        if forecast['Day'].get('HasPrecipitation', False):
            rain_prob_day = 100
        else:
            rain_prob_day = 0

        if forecast['Night'].get('HasPrecipitation', False):
            rain_prob_night = 100
        else:
            rain_prob_night = 0

        averager = 0.5 * (rain_prob_day + rain_prob_night)

        wind_speed_day = forecast['Day'].get('Wind', {}).get('Speed', {}).get('Value', 0)
        wind_speed_night = forecast['Night'].get('Wind', {}).get('Speed', {}).get('Value', 0)
        averagew = 0.5 * (wind_speed_day + wind_speed_night)

        info = {'average_temperature': averaget, 'average_rain_probability': averager, 'average_wind_speed': averagew}
        return info
    else:
        return "Нет данных о погоде."


# Проверка благоприятности погодных условий
def check_bad_weather(t, w, r):
    if t < -15 or t >= 32: #Погода считается экстремальной при температуре выше 32,5 C
        return "Условия неблагоприятны - экстремальная температура!"
    if w > 39: #Скорость ветра считается сильной (6 баллов), если превышает скорость 39 км в час
        return "Условия неблагоприятны - ветер более 5 баллов!"
    if r >= 75: #При вероятности осадков 75% и выше погодные условия неблагоприятны
        return "Условия неблагоприятны - вероятность осадков слишком высока!"
    return "Условия благоприятны."



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Вытаскиваем названия городов из формы:
        start_city = request.form.get('start_city', '').strip()
        end_city = request.form.get('end_city', '').strip()

        # Запрашиваем координаты городов:
        start_location_key = get_location_key(start_city)
        end_location_key = get_location_key(end_city)

        # Проверяем ошибки:
        if "error" in start_location_key or "error" in end_location_key:
            error_message = start_location_key.get("error") or end_location_key.get("error")
            return render_template('index.html', error=error_message)

        # Просим.. молим о данных обоих городов
        start_weather = get_weather_data(start_location_key)
        end_weather = get_weather_data(end_location_key)

        # Проверяем на ошибки:
        if "error" in start_weather or "error" in end_weather:
            error_message = start_weather.get("error") or end_weather.get("error")
            return render_template('index.html', error=error_message)

        # Обрабатываем полученные данные:
        start_processed = process_weather_data(start_weather)
        end_processed = process_weather_data(end_weather)

        # Проверка результатов обработки:
        if isinstance(start_processed, str) or isinstance(end_processed, str):
            error_message = start_processed if isinstance(start_processed, str) else end_processed
            return render_template('index.html', error=error_message)

        # Оцениваем погоду:
        start_evaluation = check_bad_weather(
            start_processed['average_temperature'],
            start_processed['average_wind_speed'],
            start_processed['average_rain_probability']
        )

        end_evaluation = check_bad_weather(
            end_processed['average_temperature'],
            end_processed['average_wind_speed'],
            end_processed['average_rain_probability']
        )

        # Результат:
        result = {
            'evaluation': f"{start_city}: {start_evaluation}, {end_city}: {end_evaluation}",
            'temperature': f"{start_city}: {start_processed['average_temperature']} °C, {end_city}: {end_processed['average_temperature']} °C",
            'wind_speed': f"{start_city}: {start_processed['average_wind_speed']} км/ч, {end_city}: {end_processed['average_wind_speed']} км/ч",
            'rain_probability': f"{start_city}: {start_processed['average_rain_probability']} %, {end_city}: {end_processed['average_rain_probability']} %"
        }

        return render_template('index.html', result=result)

    # Отображаем страницу с формой при GET-запросе:
    return render_template('index.html')


# Запускаем Flask
if __name__ == '__main__':
    app.run(debug=True)
