# !/usr/bin/env python
# -*-coding:utf-8-*-

import urllib.parse
import time
import requests
import requests.utils
import json
import qrcode
import re

appVersionCode = '6560300'
add_month, buy_num = '', ''
csrf = ''
s = requests.session()
s.headers = {
    'Host': 'api.bilibili.com',
    'DNT': '1',
    'Accept-Encoding': 'gzip',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0(Linux;Android 11) BiliApp/'+appVersionCode+' mobi_app/android network/2 os/android',
    'native_api_from': 'h5'
}

def login():
    headers = {
        'Host': 'passport.bilibili.com',
        'Referer': 'https://passport.bilibili.com/login',
        'User-Agent': 'Mozilla/5.0(Linux;Android 11) network/2 os/android'
    }
    res1 = s.get('https://passport.bilibili.com/qrcode/getLoginUrl', headers=headers,timeout=9).json()
    if not res1['code']:
        qrurl, oauthKey = res1['data']['url'], res1['data']['oauthKey']
        print('如无法扫描二维码，则可在已登录账号的浏览器访问以下链接：'+qrurl)  # 用于生成二维码的原链接
        make_qrcode(qrurl)
        headers.update({'Origin': 'https://passport.bilibili.com', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        data = 'oauthKey='+oauthKey+'&gourl=https%3A%2F%2Fwww.bilibili.com%2F'
        while True:
            time.sleep(3)
            res2 = s.post('https://passport.bilibili.com/qrcode/getLoginInfo', headers=headers, data=data, timeout=9).json()
            if res2['status']:
                loginurl = res2['data']['url']
                res3 = s.get(loginurl, headers=headers.update({'Host': urllib.parse.urlparse(loginurl).hostname}), timeout=9)
                if res3.status_code not in (200,302):
                    raise Exception(str(res3.status_code)+res3.text)
                save_cookies()
                return True
            elif res2['data'] in (-4,-5):  # 等待扫码
                print(json.dumps(res2))
            else:  # 超时或错误
                print(json.dumps(res2))
                return False
    else:
        print(json.dumps(res1))
        return False

def make_qrcode(url):
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    img.show()

def save_cookies():
    cookies_dic = requests.utils.dict_from_cookiejar(s.cookies)
    with open('.\\cookies.json', 'w+') as fc:
        fc.write(json.dumps(cookies_dic))

def read_cookies():
    try:
        with open('.\\cookies.json', 'r') as fc:
            cookies_str = fc.read()
    except FileNotFoundError:
        return False
    cookies_dict = json.loads(cookies_str)
    sessdata = cookies_dict['SESSDATA']
    expire = re.search('\d{10}', sessdata).group()
    if time.time() >= int(expire):
        print('cookies过期，请重新登录')
        return False
    else:
        requests.utils.cookiejar_from_dict(cookies_dict, cookiejar=s.cookies)
        return True

def get_userinfo():
    res = s.get('https://api.bilibili.com/x/web-interface/nav',timeout=9).json()
    if not res['code']:
        print(res['data']['uname']+'(uid:'+str(res['data']['mid'])+')已登录')
    else:
        print('获取用户信息失败：'+json.dumps(res))

def get_suitinfo():
    res = s.get('https://api.bilibili.com/x/garb/mall/item/suit/v2?item_id='+item_id, timeout=9).json()
    if not res['code']:
        print('装扮：'+res['data']['item']['name'])
    else:
        print('获取装扮信息失败：'+json.dumps(res))

def get_coupon():
    # TODO: 优惠券token处理，无券可用时data为null
    res = s.get('https://api.bilibili.com/x/garb/coupon/usable?item_id='+item_id, timeout=9)
    print(res.text)
    return json.loads(res.text)['data']

def create(coupon_token=''):
    data = 'item_id='+item_id+'&platform=android&currency=bp&add_month='+add_month+'&buy_num='+buy_num+'&coupon_token='+coupon_token+'&hasBiliapp=true&csrf='+csrf
    s.headers.update({'x-csrf-token': csrf, 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
    res = s.post('https://api.bilibili.com/x/garb/trade/create', data=data ,timeout=9)
    result = res.json()
    if not result['code']:
        confirm(result['data']['order_id'])
    else:
        print(res.text)

def confirm(order_id):
    post_data = 'order_id=' + order_id + '&csrf=' + csrf
    res = s.post('https://api.bilibili.com/x/garb/trade/confirm', data=post_data, timeout=9)
    result = res.json()
    if not result['code'] and result['data']['state']=='created':
        pay_data = result['data']['pay_data']
        pay(pay_data)
    elif result['data']['state']=='creating':
        print('正在创建订单')
        confirm(order_id)
    else:
        print(res.text)

def pay(data):
    data = data[:-1]+',"appName":"tv.danmaku.bili","appVersion":"'+appVersionCode+'","device":"ANDROID","network":"WiFi","payChannel":"bp","payChannelId":"99","realChannel":"bp","sdkVersion":"1.4.9"}'
    headers = {
        'Host': 'pay.bilibili.com', 'Content-Type': 'application/json', 'App-Key': 'android64', 'Buildid': appVersionCode,
        'User-Agent': 'Mozilla/5.0 BiliDroid/6.56.0 (bbcallen@gmail.com) os/android mobi_app/android build/'+appVersionCode+' network/2'
    }
    res = requests.post('https://pay.bilibili.com/payplatform/pay/pay', headers=headers, data=data.encode('utf-8'), timeout=9)
    result = res.json()
    if not result['errno']:
        pay_data = result['data']['payChannelParam']
        # 调试断点请打在此处，一旦完成下方的请求就扣钱了
        res2 = requests.post(result['data']['payChannelUrl'], headers=headers, data=pay_data.encode('utf-8'), timeout=9)
        print(res2.text)
    else:
        print(res.text)

if __name__ == '__main__':
    if not read_cookies() and not login():
        print('登录失败')
    else:
        get_userinfo()
        csrf = s.cookies.get('bili_jct')
        item_id = input('输入装扮编号（购买页面分享链接后面的数字）：')
        s.headers['Referer'] = 'https://www.bilibili.com/h5/mall/suit/detail?navhide=1&id='+item_id
        add_month = input('购买月份（默认-1，为永久）：') or '-1'
        buy_num = input('购买数量（默认1份，仅部分永久装扮支持多份）：') or '1'
        get_suitinfo()
        create()
