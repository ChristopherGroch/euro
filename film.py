from quart import Quart, render_template,jsonify
from quart_rate_limiter import RateLimiter, timedelta, rate_limit
import pandas as pd
from requests_html import AsyncHTMLSession
from datetime import date
from collections import defaultdict

app = Quart(__name__)
rate_limiter = RateLimiter(app)

wyniki = pd.read_csv('wyniki_formated.csv')
wyniki['R1'] = wyniki['R1'].replace({'Czechia':'Czech Republic'})
wyniki['R2'] = wyniki['R2'].replace({'Czechia':'Czech Republic'})

names = {
    'Unnamed: 0': 'Numer',
    'Unnamed: 1': 'Data',
    'Unnamed: 2': 'Godzina',
    'Unnamed: 3': 'R1',
    'Unnamed: 4': 'R2',
    'Adrian': 'Adrian_R1', 'Unnamed: 6': 'Adrian_R2',
    'Bartek': 'Bartek_R1', 'Unnamed: 9': 'Bartek_R2',
    'Damian': 'Damian_R1', 'Unnamed: 12': 'Damian_R2',
    'Daniel': 'Daniel_R1', 'Unnamed: 15': 'Daniel_R2',
    'Gines': 'Gines_R1', 'Unnamed: 18': 'Gines_R2',
    'Jacek': 'Jacek_R1', 'Unnamed: 21': 'Jacek_R2',
    'Łukasz': 'Łukasz_R1', 'Unnamed: 24': 'Łukasz_R2',
    'Marek': 'Marek_R1', 'Unnamed: 27': 'Marek_R2',
    'Mateusz': 'Mateusz_R1', 'Unnamed: 30': 'Mateusz_R2',
    'Michał': 'Michał_R1', 'Unnamed: 33': 'Michał_R2',
    'Milosz': 'Miłosz_R1', 'Unnamed: 36': 'Miłosz_R2',
    'Robert': 'Robert_R1', 'Unnamed: 39': 'Robert_R2',
    'Sławek': 'Sławek_R1', 'Unnamed: 42': 'Sławek_R2',
    'Tomasz P.': 'Tomasz_R1', 'Unnamed: 45': 'Tomasz_R2'
}

uczestnicy = [
    'Adrian', 'Bartek', 'Damian', 'Daniel', 'Gines', 'Jacek', 'Łukasz',
    'Marek', 'Mateusz', 'Michał', 'Miłosz', 'Robert', 'Sławek', 'Tomasz'
]
nums = []
urls = []

async def fetch():
    li = 'https://www.flashscore.com/football/europe/euro/#/EcpQtcVi/live'
    asession = AsyncHTMLSession()
    r = await asession.get(li)
    await r.html.arender()
    f = r.html.find('div.leagues--live.contest--leagues')[0].find('a.eventRowLink')
    uss = []
    for e in f:
        uss.append(e.xpath('//@href')[0])
    dzis = ' ' + str(date.today()).split('-')[2] + '.' + str(date.today()).split('-')[1] + '.' + str(date.today()).split('-')[0]


    numbers = []
    for k in uss:
        teams = []
        result = []
        asession = AsyncHTMLSession()
        r = await asession.get(k)
        await r.html.arender()

        times = r.html.find("div.detailScore__wrapper")
        times = times[0].text
        tt = r.html.find("a.participant__participantName.participant__overflow ")
        teams.append(tt[0].text)
        teams.append(tt[1].text)
        if times == '-':
            result.append(0)
            result.append(0)
        else:
            result.append(int(times.split('-')[0]))
            result.append(int(times.split('-')[1]))
        numbers.append(wyniki[(wyniki['Data'] == dzis) & ((wyniki['R1'] == teams[0]) | (wyniki['R2'] == teams[1]))]['Numer'].values[0])
    return uss,numbers

async def getData(url, num):
    asession = AsyncHTMLSession()
    r = await asession.get(url)
    await r.html.arender()

    times = r.html.find("div.detailScore__wrapper")
    times = times[0].text
    result = []
    teams = []
    tt = r.html.find("a.participant__participantName.participant__overflow ")
    teams.append(tt[0].text)
    teams.append(tt[1].text)
    if times == '-':
        result.append(0)
        result.append(0)
    else:
        result.append(int(times.split('-')[0]))
        result.append(int(times.split('-')[1]))
    df = wyniki
    scores = pd.DataFrame(uczestnicy, columns=['Uczestnik'])
    scores['Result'] = 0
    scores['R1'] = result[0]
    scores['R2'] = result[1]
    scores['pR1'] = scores.apply(lambda x: df[df['Numer'] == num][x['Uczestnik'] + '_R1'], axis=1)
    scores['pR2'] = scores.apply(lambda x: df[df['Numer'] == num][x['Uczestnik'] + '_R2'], axis=1)
    scores['Result'] = scores.apply(lambda x: 1 if ((x['R1'] == x['pR1']) and (x['R2'] == x['pR2'])) else -1
                                    if ((x['pR1'] < x['R1']) or (x['pR2'] < x['R2'])) else 0, axis=1)
    return scores.to_dict(orient='records'), result[0], result[1], teams[0], teams[1]

@app.before_serving
async def startup():
    global urls
    global nums
    urls,nums = await fetch()

@app.route('/')
@rate_limit(10, timedelta(seconds=10))
async def index():
    data = []
    for url, num in zip(urls,nums):
        participants, R1, R2, team1, team2 = await getData(url, num)
        data.append({
            'participants': participants,
            'R1': R1,
            'R2': R2,
            'team1': team1,
            'team2': team2
        })
    return await render_template('index.html', data=data)

@app.route('/data')
@rate_limit(10, timedelta(seconds=10))
async def get_data():
    data = []
    for url, num in zip(urls, nums):
        participants, R1, R2, team1, team2 = await getData(url, num)
        data.append({
            'participants': participants,
            'R1': R1,
            'R2': R2,
            'team1': team1,
            'team2': team2
        })
    return jsonify(data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5009, debug=False)
