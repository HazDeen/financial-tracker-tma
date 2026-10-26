import json, urllib.request, http.cookiejar
from datetime import date
cookies=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
def api(path,data=None,method=None):
    req=urllib.request.Request('http://127.0.0.1:8000/api/v1'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'},method=method)
    try:
        with opener.open(req) as r: return json.load(r) if r.status!=204 else None
    except urllib.error.HTTPError as e:
        if e.code!=409: raise
api('/auth/register',{'login':'alex.demo','password':'Demo-finance-2026!'})
api('/auth/login',{'login':'alex.demo','password':'Demo-finance-2026!'})
api('/analytics/balance',{'opening_balance':'38700.00'},'PUT')
entries=[('income','Зарплата','Зарплата за октябрь','65000',10),('expense','Продукты','Продукты на неделю','6450',12),('expense','Дом','Коммунальные платежи','6200',15),('expense','Транспорт','Проездной','2400',17),('expense','Кафе','Обед в городе','1600',19),('expense','Подписки','Музыка и фильмы','800',20),('expense','Продукты','Покупки в супермаркете','2000',22)]
report=api('/analytics/monthly?year=2026&month=10')
if not report['transactions']:
    for kind,category,description,amount,day in entries: api('/transactions/',{'transaction_type':kind,'category':category,'description':description,'amount':amount,'transaction_date':f'2026-10-{day:02}T00:00:00Z'})
if not api('/recurring/'):
    for title,amount,kind,category,day,next_date in [('Интернет дома','900','expense','Дом',23,'2026-10-23'),('Аренда квартиры','18000','expense','Дом',24,'2026-10-24'),('Зарплата','40000','income','Зарплата',25,'2026-10-25'),('Яндекс Плюс','449','expense','Подписки',26,'2026-10-26'),('Аванс','25000','income','Зарплата',10,'2026-11-10')]:
        api('/recurring/',{'title':title,'amount':amount,'transaction_type':kind,'category':category,'billing_day':day,'next_payment_date':next_date})
print('Local demo prepared')
