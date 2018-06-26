# coding:utf-8
import HTMLParser
from datetime import datetime, timedelta, date
import json
import os
import string
import sys
import time
from urllib import unquote
import uuid

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models.aggregates import Sum
from django.http.response import HttpResponse, StreamingHttpResponse
from django.shortcuts import render_to_response
from django.utils.http import urlencode
from qiniu import put_file, Auth, etag
import xlwt

from buddhist.ceremony.models import BuddnistCeremonyCommodityOrder
from common.tools import file_iterator
from myapi.UploadPicClient import UploadPicClient
from temple.models import ZizaijiaTempleWebsiteCalendarList, ZizaijiaTempleWebsiteCalendarDay, \
    ZizaijiaTempleWebsiteCalendar, ZizaijiaTempleWebsiteSort, ZizaijiaTempleWebsiteAbbot, \
    Temple
from utils import printerUtil, poolUtil
from volunteer.models import WeixinUser


reload(sys)
sys.setdefaultencoding('utf8')

@login_required
def meritBoxGetList(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    pageNumber = request.GET.get('pageNumber')
    pageSize = request.GET.get('pageSize')
    if pageNumber is None:
        pageNumber = 0
    if pageSize is None:
        pageSize = 20
    startTime = request.GET.get('startTime')
    endTime = request.GET.get('endTime')
    print int(pageNumber)*int(pageSize)
    print int(pageSize)
    if startTime is not None and startTime != '':
        startTime = str(startTime)+' 00:00:00'
        startTime = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')
    if endTime is not None and endTime != '':
        endTime = str(endTime)+' 23:59:59'
        endTime = datetime.strptime(endTime,'%Y-%m-%d %H:%M:%S')
    buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.filter(temple_id=templeId).filter(pay_type=1).filter(commodity_id=0)
    if startTime is not None and startTime != '':
        buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.filter(pay_time__gte=startTime)
    if endTime is not None and endTime != '':
        buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.filter(pay_time__lte=endTime)
    buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.order_by('-pay_time')[int(pageNumber)*int(pageSize):int(pageNumber)*int(pageSize)+int(pageSize)]
    buddnistCeremonyCommodityOrderList2 = []
    for buddnistCeremonyCommodityOrder in buddnistCeremonyCommodityOrderList:
        orderMap = {}
        if buddnistCeremonyCommodityOrder.abbot_id == 0:
            orderMap['source'] = '功德箱'
        else:
            zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.filter(id=buddnistCeremonyCommodityOrder.abbot_id)
            if len(list(zizaijiaTempleWebsiteAbbot)) > 0:
                orderMap['source'] = '供养'+str(zizaijiaTempleWebsiteAbbot[0].religion_name)
#         buddnistCeremonyUser = BuddnistCeremonyUser.objects.filter(id=buddnistCeremonyCommodityOrder.user_id)
#         if len(list(buddnistCeremonyUser)) > 0:
        weixinUser = WeixinUser.objects.filter(id=buddnistCeremonyCommodityOrder.user_id)
        if len(list(weixinUser)) > 0:
            orderMap['nickName'] = weixinUser[0].nick_name
            orderMap['headImg'] = weixinUser[0].head_img
        else:
            weixinUser = WeixinUser.objects.filter(chanzai_id=buddnistCeremonyCommodityOrder.user_id)
            if len(list(weixinUser)) > 0:
                orderMap['nickName'] = weixinUser[0].nick_name
                orderMap['headImg'] = weixinUser[0].head_img                    
        orderMap['price'] = buddnistCeremonyCommodityOrder.price
        orderMap['addTime'] = buddnistCeremonyCommodityOrder.pay_time.strftime('%Y-%m-%d %H:%M:%S')
        orderMap['wish'] = buddnistCeremonyCommodityOrder.subdivideName
        buddnistCeremonyCommodityOrderList2.append(orderMap)
    if len(list(buddnistCeremonyCommodityOrderList)) >= int(pageSize):
        result['pageNumber'] = int(pageNumber)+1
    else:
        result['pageNumber'] = -1
    result['data'] = buddnistCeremonyCommodityOrderList2
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def meritBoxSumGet(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    priceSum = BuddnistCeremonyCommodityOrder.objects.filter(temple_id=templeId).filter(pay_type=1).filter(commodity_id=0).aggregate(Sum("price"))
    today = date.today()
    tomorrow = today + timedelta(days=1)
    priceDaySum = BuddnistCeremonyCommodityOrder.objects.filter(temple_id=templeId).filter(pay_type=1).filter(commodity_id=0).filter(add_time__gte=today).filter(add_time__lte=tomorrow).aggregate(Sum("price"))
    # 获取当月的第一天
    firstDay = datetime.today() + timedelta(days= -datetime.today().day + 1)    
    priceMonthSum = BuddnistCeremonyCommodityOrder.objects.filter(temple_id=templeId).filter(pay_type=1).filter(commodity_id=0).filter(add_time__gte=firstDay).filter(add_time__lte=tomorrow).aggregate(Sum("price"))
    if priceSum['price__sum'] is None:
        result['priceSum'] = 0
    else:
        result['priceSum'] = priceSum['price__sum']
    if priceDaySum['price__sum'] is None:
        result['priceDaySum'] = 0
    else:
        result['priceDaySum'] = priceDaySum['price__sum']
    if priceMonthSum['price__sum'] is None:
        result['priceMonthSum'] = 0
    else:
        result['priceMonthSum'] = priceMonthSum['price__sum']        
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json") 

@login_required
def meritBoxDownloadExcel(request):
    user = request.user
    templeId = user.temple_id    
    startTime = request.GET.get('startTime')
    endTime = request.GET.get('endTime')    
    buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.filter(temple_id=templeId).filter(pay_type=1).filter(commodity_id=0).order_by('-add_time')
    if startTime is not None and startTime != '':
        startTime = str(startTime)+' 00:00:00'
        startTime = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')
    if endTime is not None and endTime != '':
        endTime = str(endTime)+' 23:59:59'
        endTime = datetime.strptime(endTime,'%Y-%m-%d %H:%M:%S')
    if startTime is not None and startTime != '':
        buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.filter(pay_time__gte=startTime)
    if endTime is not None and endTime != '':
        buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.filter(pay_time__lte=endTime)
    buddnistCeremonyCommodityOrderList = buddnistCeremonyCommodityOrderList.order_by('-pay_time')
    if len(list(buddnistCeremonyCommodityOrderList)) <= 0:
        return HttpResponse('没有查找到数据')
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('功德箱',cell_overwrite_ok=True)
    style = xlwt.XFStyle()
    font = xlwt.Font()
    font.name = 'SimSun' # 指定“宋体”
    style.font = font         
    listNum = 0
    ws.write(listNum, 0, '随喜者')     
    ws.write(listNum, 1, '来源')
    ws.write(listNum, 2, '随喜金额')
    ws.write(listNum, 3, '随喜时间')
    for buddnistCeremonyCommodityOrder in buddnistCeremonyCommodityOrderList:
        listNum = listNum+1
        orderMap = {}
        if buddnistCeremonyCommodityOrder.abbot_id == 0:
            ws.write(listNum, 1, '功德箱')  
        else:
            zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.filter(id=buddnistCeremonyCommodityOrder.abbot_id)
            if len(list(zizaijiaTempleWebsiteAbbot)) > 0:
                ws.write(listNum, 1, '供养'+str(zizaijiaTempleWebsiteAbbot[0].religion_name))
#         buddnistCeremonyUser = BuddnistCeremonyUser.objects.filter(id=buddnistCeremonyCommodityOrder.user_id)
#         if len(list(buddnistCeremonyUser)) > 0:
        weixinUser = WeixinUser.objects.filter(id=buddnistCeremonyCommodityOrder.user_id)
        if len(list(weixinUser)) > 0:
            ws.write(listNum, 0, weixinUser[0].nick_name)
        else:
            weixinUser = WeixinUser.objects.filter(chanzai_id=buddnistCeremonyCommodityOrder.user_id)
            if len(list(weixinUser)) > 0:
                ws.write(listNum, 0, weixinUser[0].nick_name)                
        ws.write(listNum, 2, buddnistCeremonyCommodityOrder.price)
        if buddnistCeremonyCommodityOrder.pay_time != None: 
            ws.write(listNum, 3, buddnistCeremonyCommodityOrder.pay_time.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            ws.write(listNum, 3, "")
    the_file_name = "./download/功德箱.xls"
    wb.save(the_file_name)
    response = StreamingHttpResponse(file_iterator(the_file_name))
    response['Content-Type'] = 'application/octet-stream'
    temple = Temple.objects.filter(id=templeId)
    fileName = str(temple[0].name)+'功德箱'
    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(fileName+'.xls')
    return response       

@login_required
def meritBoxIndex(request):
    return render_to_response('temple/donate_box.html')