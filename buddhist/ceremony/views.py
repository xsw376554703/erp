# coding:utf-8
import HTMLParser
from datetime import datetime, timedelta
import json
import os
import string
import sys
import time
from urllib import unquote
import uuid

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import F
from django.http.response import HttpResponse, StreamingHttpResponse
from django.shortcuts import render_to_response
from django.utils.http import urlencode
from qiniu import put_file, Auth, etag
import requests
import xlwt

from buddhaWall.models import TemplateModel, BuddhaWallOrderModel
from buddhist.ceremony.models import BuddnistCeremonyShop, BuddnistCeremonyCommodity, \
    BuddnistCeremonyCommodityOrder, BuddnistCeremonyBuyerInfo, BuddnistCeremonyCommoditySubdivide, \
    BuddnistCeremonyCommodityPics, Order, BuddnistCeremonyCommodityPostscript, \
    BuddnistCeremonyCommodityPostscriptSelectInput, BuddnistCeremonyType, \
    ZizaijiaSubdividePrinter, ZizaijiaPrinter, TempleContentManagerNotifyModel
from common.tools import file_iterator
from machine.models import TempleMeritMachineAdvertisementModel
from myapi.MegerImageClient import MegerImageClient
from myapi.UploadPicClient import UploadPicClient
from myerp.models import TempleTemplateModel
from myerp.settings import SevericeType
from temple.models import ZizaijiaTempleWebsiteCalendarList, ZizaijiaTempleWebsiteCalendarDay, \
    ZizaijiaTempleWebsiteCalendar, ZizaijiaTempleWebsiteSort, Temple, ZizaijiaTempleWebsiteImageTextList, \
    ZizaijiaTempleWebsiteImageText
from utils import printerUtil, poolUtil, pushUtil
from utils.StringUtils import Encryptstr
from volunteer.models import WeixinUser
from financialStatistics.models import ZizaijiaBill


# from buddhaWall.models import BuddhaWallOrderModel
reload(sys)
sys.setdefaultencoding('utf8')


@login_required
def cermony_index(request):
    return render_to_response('buddhist/order_manage.html')

@login_required
def orderNumGet(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    # sql = 'select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 0 and temple_id=%d and commodity_id>0'%(templeId)
    # result['total'] = len(list(BuddnistCeremonyCommodityOrder.objects.raw(sql)))
    commodityCount = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1, is_finish=0, temple_id=templeId, commodity_id__gt=0).count()
    buddhaWallCount = BuddhaWallOrderModel.objects.filter(isPay=1, templeId=templeId, status=1).count()
    result['commodityCount'] = commodityCount
    result['buddhaWallCount'] = buddhaWallCount
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取佛事订单管理数据
@login_required
def ceremonyGetList(request):

    type = str(request.GET.get('pageName')) #1获取未排单  2获取已排单 3获取已完成
    if type == 'tab1':
        type = 1
    elif type == 'tab2':
        type = 2        
    elif type == 'tab3':
        type = 3
    pageNum = int(request.GET.get('pageIndex'))
    
    pageSize = int(request.GET.get('pageSize'))
    
    beginDate = str(request.GET.get('beginDate'))
    endDate = str(request.GET.get('endDate'))
    
    commodityId = request.GET.get('buddishService')
    
    isSearchNoPic = request.GET.get('isSearchNoPic')
    
    orderByPriceType = request.GET.get('orderByPriceType')
    
    orderByTimeType = request.GET.get('orderByTimeType')
    
    searchNotPrint = request.GET.get('searchNotPrint')
    
    subdivideName = request.GET.get('subdivideName')
    
    
    if orderByTimeType is None or orderByTimeType == '' or orderByTimeType == '0':
        orderByTimeType = '1'
        
    orderBySqlStr = ''
    if orderByPriceType is not None and orderByPriceType != '' and orderByPriceType != '0':
        if orderByPriceType == '1':
            orderBySqlStr = 'order by price desc'
        else:
             orderBySqlStr = 'order by price'
        if orderByTimeType == '1':
            orderBySqlStr = orderBySqlStr+',pay_time desc'
        else:
            orderBySqlStr = orderBySqlStr+',pay_time'
    elif orderByTimeType == '1':
        orderBySqlStr = 'order by pay_time desc'
    else:
        orderBySqlStr = 'order by pay_time'
        
    user = request.user
    templeId = user.temple_id

    subid = request.GET.get('subid', 0)
    
    # shopStrSQL = ""
    # if templeId != "None" and templeId != '' and templeId is not None and templeId != '0':
    #     bcsList = BuddnistCeremonyShop.objects.filter(temple_id=templeId)
    #     shopStrSQL = "and commodity_id in ("
    #     for bcs in bcsList:
    #         bccList = BuddnistCeremonyCommodity.objects.filter(shop_id=bcs.id)
    #         for bcc in bccList:
    #             shopStrSQL += str(bcc.id) +','
    #     shopStrSQL = shopStrSQL+'0'
    #     shopStrSQL = shopStrSQL+')'
            
    
    commodityIdStrSql = ""
    if commodityId != "None" and commodityId != '' and commodityId is not None and commodityId != '-1':
        commodityIdStrSql = "and commodity_id = %i"%(int(commodityId))
        if subdivideName != "None" and subdivideName != '' and subdivideName is not None:
            commodityIdStrSql += " and subdivideName = '%s'"%(subdivideName)

    subIdStrSql = ""
    if subid != "None" and subid != '' and subid is not None and int(subid) > 0:
        subIdStrSql = "and subdiride_id = %i" % (int(subid))
    
    dateStrSQL = ""
    if beginDate != "None" and beginDate != '':
        beginDate = beginDate+' 00:00:00'
        endDate = endDate+' 23:59:59'
        dateStrSQL = "and pay_time >= '%s' and pay_time <= '%s'"%(beginDate,endDate)
    
    searchNoPic = ''    
    if isSearchNoPic != "None" and isSearchNoPic != '' and isSearchNoPic != '0'  and isSearchNoPic is not None:
        temple = Temple.objects.get(id=request.user.temple_id)
        buddnistCeremonyShop = BuddnistCeremonyShop.objects.get(temple_id=temple.id)
        buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.filter(shop_id=buddnistCeremonyShop.id).filter(op_status=0)
        commodityListSQL = ''
        for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
            if commodityListSQL == '':
                commodityListSQL = ' commodity_id in ('+str(buddnistCeremonyCommodity.id)
            else:
                commodityListSQL = commodityListSQL+','+str(buddnistCeremonyCommodity.id)
        if commodityListSQL != '':
            commodityListSQL = commodityListSQL+')'
        buddnistCeremonyCommodityList2 = BuddnistCeremonyCommodity.objects.filter(shop_id=buddnistCeremonyShop.id).filter(op_status=0)
        commodityListStr = ''
        subdivideListSQL = ''
        for buddnistCeremonyCommodity in buddnistCeremonyCommodityList2:
            if commodityListStr == '':
                commodityListStr = str(buddnistCeremonyCommodity.id)
            else:
                commodityListStr = commodityListStr+','+str(buddnistCeremonyCommodity.id)
        if commodityListStr != '':
            buddnistCeremonyCommoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.raw('select * from buddnist_ceremony_commodity_subdivide where commodity_id in('+str(commodityListStr)+') and price > 0 and op_status = 0')
            for buddnistCeremonyCommoditySubdivide in buddnistCeremonyCommoditySubdivideList:
                if subdivideListSQL == '':
                    subdivideListSQL = ' subdiride_id in('+str(buddnistCeremonyCommoditySubdivide.id)
                else:
                    subdivideListSQL = subdivideListSQL+','+str(buddnistCeremonyCommoditySubdivide.id)
        if buddnistCeremonyCommoditySubdivide != '':
            subdivideListSQL = subdivideListSQL+')'
        if commodityListSQL != '' and subdivideListSQL != '':
            searchNoPic = ' and ('+commodityListSQL+' or '+subdivideListSQL+')'
        else:
            searchNoPic = ' and '+commodityListSQL+subdivideListSQL
        searchNoPic = searchNoPic+' and (dispose_pic_url = "" or dispose_pic_url is NULL)'
        
    
    tel = str(request.GET.get('tel'))
    
#     bcuList = BuddnistCeremonyUser.objects.filter(mobile=tel)
#     telStrSQL = ""
#     userId = 0
#     if tel != '':
#         if len(list(bcuList)) > 0:
#             bcu = bcuList[0]
#             telStrSQL = "and buyer_info_id = %i"%bcu.id
#             userId = bcu.id
    telStrSQL = ""
    if tel != '' and tel is not None and tel != 'None':
        bciList = BuddnistCeremonyBuyerInfo.objects.filter(mobile=tel)
        bciIdStr = ""
        for bci in bciList:
            if bciIdStr == "":
                bciIdStr = str(bci.id)
            else:
                bciIdStr = bciIdStr+','+str(bci.id)
        if bciIdStr == '':
            telStrSQL = "and buyer_info_id in (0)"
        else:
            telStrSQL = "and buyer_info_id in (%s)"%bciIdStr
          
    notPrintSQL = ""
    if searchNotPrint == '1':
        notPrintSQL = "and is_print = 0"
        
        
    # print dateStrSQL+','+telStrSQL+','+commodityIdStrSql
    
    result = {}
    bccoList = [];
    if type == 1:
        # print 'select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 0 and temple_id='+str(templeId)+' and commodity_id>0 %s %s %s  %s %s %s order by pay_time desc limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,((pageNum)*pageSize),pageSize)
        bccoList = BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 0 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1 %s %s %s %s %s  %s %s limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,orderBySqlStr,((pageNum)*pageSize),pageSize))
        result['total'] = len(list(BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 0 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1 %s %s %s %s %s %s'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL))))
#         if dateStrSQL != "" and telStrSQL != "" and commodityIdStrSql != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=0).filter(add_time__gte=beginDate).filter(add_time__lte=endDate).filter(user_id=userId).filter(commodity_id=commodityId).count()
#         elif dateStrSQL != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=0).filter(add_time__gte=beginDate).filter(add_time__lte=endDate).count()            
#         elif telStrSQL != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=0).filter(user_id=userId).count()   
#         else:
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=0).count()                        
#     elif type == 2:
#         bccoList = BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_sort_order = 1 and is_finish = 0 order by add_time desc limit %i,10'%((pageNum-1)*10))
#         result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_sort_order=1).filter(is_finish=0).count()
    elif type == 2:
        # print 'select * from buddnist_ceremony_commodity_order where pay_type = 1 and temple_id='+str(templeId)+' and commodity_id>0  %s %s %s %s %s %s order by pay_time desc limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,((pageNum)*pageSize),pageSize)
        bccoList = BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1  %s %s %s %s %s %s %s limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,orderBySqlStr,((pageNum)*pageSize),pageSize))
        result['total'] = len(list(BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1 %s %s %s %s %s %s'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL))))
    elif type == 3:
        # print 'select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 1 and temple_id='+str(templeId)+' and commodity_id>0  %s %s %s %s %s %s order by pay_time desc limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,((pageNum)*pageSize),pageSize)
        bccoList = BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 1 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1  %s %s %s %s %s %s %s limit %i,%i'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL,orderBySqlStr,((pageNum)*pageSize),pageSize))
        result['total'] = len(list(BuddnistCeremonyCommodityOrder.objects.raw('select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 1 and temple_id='+str(templeId)+' and commodity_id>0 and conversion_type = 1 %s %s %s %s %s %s'%(dateStrSQL,telStrSQL,commodityIdStrSql,subIdStrSql,searchNoPic,notPrintSQL))))
#         if dateStrSQL != "" and telStrSQL != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=1).filter(add_time__gte=beginDate).filter(add_time__lte=endDate).filter(user_id=userId).count()
#         elif dateStrSQL != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=1).filter(add_time__gte=beginDate).filter(add_time__lte=endDate).count()            
#         elif telStrSQL != "":
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=1).filter(user_id=userId).count()   
#         else:
#             result['total'] = BuddnistCeremonyCommodityOrder.objects.filter(pay_type=1).filter(is_finish=1).count() 
#     print bccoList
    bccoList2 = []
    for bcco in bccoList:
        try:
            bccoMap = BuddnistCeremonyCommodityOrder.toDic(bcco)

            bcc = BuddnistCeremonyCommodity.objects.get(id=bcco.commodity_id)

            bccoMap['productName'] = bcc.name

            bccoMap['productSumPrice'] = bcco.price

            bccoMap['customerId'] = bcco.user_id

#             bcu = BuddnistCeremonyUser.objects.get(id=bcco.user_id)
#             bcu = BuddnistCeremonyBuyerInfo.objects.get(id=bcco.buyer_info_id)

            if subid is not None and int(subid) >0:
                sub = BuddnistCeremonyCommoditySubdivide.objects.get(id=subid)
                bccoMap['subName'] = sub.name
            else:
                bccoMap['subName'] = ''

#             bccoMap['user'] = BuddnistCeremonyUser.toDic(bcu)
            # print bcco.buyer_info_id
            bcbiList = BuddnistCeremonyBuyerInfo.objects.filter(id=bcco.buyer_info_id)

            bccoMap['orderTime'] = bccoMap['pay_time']
            
            bccoMap['add_time'] = bccoMap['pay_time']

            for bcbi in bcbiList:
                if bcbi.name != 'undefined' and bcbi.name != '' and bcbi.name is not None:
                    bccoMap['customerName'] = bcbi.name
                else:
                    bccoMap['customerName'] = ""
                if bcbi.mobile != 'undefined' and bcbi.mobile != '' and bcbi.mobile is not None:
                    bccoMap['customerTel'] = bcbi.mobile
                else:
                    bccoMap['customerTel'] = ""
                    
                           
                bcuMap = {}
                if bcbi.name != 'undefined' and bcbi.name != '' and bcbi.name is not None:
                    bcuMap['name'] = bcbi.name
                else:
                    bcuMap['name'] = ""
                if bcbi.mobile != 'undefined' and bcbi.mobile != '' and bcbi.mobile is not None:
                    bcuMap['mobile'] = bcbi.mobile
                else:
                    bcuMap['mobile'] = "" 
                if bcbi.address != 'undefined' and bcbi.address != '' and bcbi.address is not None:
                    bcuMap['address'] = bcbi.address
                else:
                    bcuMap['address'] = ""                                        
                bccoMap['user'] = bcuMap                     

            # bccoMap['commodity'] = BuddnistCeremonyCommodity.toDic(bcc)

            if bcco.subdiride_id != 0:
                bccs = BuddnistCeremonyCommoditySubdivide.objects.get(id=bcco.subdiride_id)

                if bccs:
                    bccoMap['productSize'] = bccs.name
                    bccoMap['productImg'] = bccs.pic_url

                bccoMap['subdivide'] = BuddnistCeremonyCommoditySubdivide.toDic(bccs)
            else:
                bccpList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=bcc.id)
                for bccp in bccpList:
                    bccoMap['productImg'] = bccp.pic_url
            posiscriptList = bccoMap['posiscript']
            posiscriptList = posiscriptList.replace('\\','\\\\')
            posiscriptList = posiscriptList.replace('\n',' ')
            posiscriptList = posiscriptList.replace('\\\\n', ' ')
            if posiscriptList[0] == '"':
                posiscriptList = posiscriptList[1:len(posiscriptList)]
            if posiscriptList[-1] == '"':
                posiscriptList = posiscriptList[0:-1]
            posiscriptJSONList = json.loads(posiscriptList)
#             posiscriptJSONList2 = []
#             for posiscriptJSON in posiscriptJSONList:
#                 if posiscriptJSON.has_key('type'):
#                     if posiscriptJSON['type'] != 4 and posiscriptJSON['type'] != 5 and posiscriptJSON['type'] != 6:
#                         posiscriptJSON.pop('type')
#                         posiscriptJSONList2.append(posiscriptJSON)
#                 else:
#                     posiscriptJSONList2.append(posiscriptJSON)
            bccoMap['posiscript'] = posiscriptJSONList
            if bccoMap['order_id'] != 0:
                order = Order.objects.get(id=bccoMap['order_id'])
                bccoMap['order_number'] = order.id
                bccoMap['outer_order_number'] = order.orderno
                bccoMap['running_number'] = order.wxtransactionid
            else:
                bccoMap['order_number'] = 0
                bccoMap['outer_order_number'] = 0
                bccoMap['running_number'] = 0

    #             if posiscriptJSON['type']:
    #                 print posiscriptJSON['type']
            if type == 1:
                bccoMap['qrcode'] = 'https://wx.zizaihome.com/commodity/commodityOrder?orderId='+Encryptstr.encrypt(str(bccoMap['id']))+'&pageType=1'
            else:
                bccoMap['qrcode'] = 'https://wx.zizaihome.com/commodity/commodityOrder?orderId='+Encryptstr.encrypt(str(bccoMap['id']))+'&pageType=2'
            bccoList2.append(bccoMap)
        except BaseException:
            print 'no user error userId='+ str(bcco.user_id)
        
    result['data'] =  bccoList2
    
    result['pageName'] =  type
    
    result['msg'] = '成功'
    
    result['result'] = 1
    
    return HttpResponse(json.dumps(result), content_type="application/json")


# 获取佛事订单管理数据
@login_required
def getCeremonyOrder(request):
    result = {}
    orderId = int(request.GET.get('orderId'))
    bccoMap = {}
    try:
        bcco = BuddnistCeremonyCommodityOrder.objects.get(id=orderId)
        bccoMap = BuddnistCeremonyCommodityOrder.toDic(bcco)

        bcc = BuddnistCeremonyCommodity.objects.get(id=bcco.commodity_id)

        bccoMap['productName'] = bcc.name

        bccoMap['productSumPrice'] = bcco.price

        bccoMap['customerId'] = bcco.user_id

        bccoMap['subName'] = ''

        bcbiList = BuddnistCeremonyBuyerInfo.objects.filter(id=bcco.buyer_info_id)

        bccoMap['orderTime'] = bccoMap['pay_time']

        bccoMap['add_time'] = bccoMap['pay_time']

        for bcbi in bcbiList:
            if bcbi.name != 'undefined' and bcbi.name != '' and bcbi.name is not None:
                bccoMap['customerName'] = bcbi.name
            else:
                bccoMap['customerName'] = ""
            if bcbi.mobile != 'undefined' and bcbi.mobile != '' and bcbi.mobile is not None:
                bccoMap['customerTel'] = bcbi.mobile
            else:
                bccoMap['customerTel'] = ""

            bcuMap = {}
            if bcbi.name != 'undefined' and bcbi.name != '' and bcbi.name is not None:
                bcuMap['name'] = bcbi.name
            else:
                bcuMap['name'] = ""
            if bcbi.mobile != 'undefined' and bcbi.mobile != '' and bcbi.mobile is not None:
                bcuMap['mobile'] = bcbi.mobile
            else:
                bcuMap['mobile'] = ""
            if bcbi.address != 'undefined' and bcbi.address != '' and bcbi.address is not None:
                bcuMap['address'] = bcbi.address
            else:
                bcuMap['address'] = ""
            bccoMap['user'] = bcuMap

        if bcco.subdiride_id != 0:
            bccs = BuddnistCeremonyCommoditySubdivide.objects.get(id=bcco.subdiride_id)

            if bccs:
                bccoMap['productSize'] = bccs.name
                bccoMap['productImg'] = bccs.pic_url

            bccoMap['subdivide'] = BuddnistCeremonyCommoditySubdivide.toDic(bccs)
        else:
            bccpList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=bcc.id)
            for bccp in bccpList:
                bccoMap['productImg'] = bccp.pic_url
        posiscriptList = bccoMap['posiscript']
        posiscriptList = posiscriptList.replace('\\', '\\\\')
        posiscriptList = posiscriptList.replace('\n', ' ')
        posiscriptList = posiscriptList.replace('\\\\n', ' ')
        if posiscriptList[0] == '"':
            posiscriptList = posiscriptList[1:len(posiscriptList)]
        if posiscriptList[-1] == '"':
            posiscriptList = posiscriptList[0:-1]
        posiscriptJSONList = json.loads(posiscriptList)
        bccoMap['posiscript'] = posiscriptJSONList
        if bccoMap['order_id'] != 0:
            order = Order.objects.get(id=bccoMap['order_id'])
            bccoMap['order_number'] = order.id
            bccoMap['outer_order_number'] = order.orderno
            bccoMap['running_number'] = order.wxtransactionid
        else:
            bccoMap['order_number'] = 0
            bccoMap['outer_order_number'] = 0
            bccoMap['running_number'] = 0

        if type == 1:
            bccoMap['qrcode'] = 'https://wx.zizaihome.com/commodity/commodityOrder?orderId=' + Encryptstr.encrypt(
                str(bccoMap['id'])) + '&pageType=1'
        else:
            bccoMap['qrcode'] = 'https://wx.zizaihome.com/commodity/commodityOrder?orderId=' + Encryptstr.encrypt(
                str(bccoMap['id'])) + '&pageType=2'
    except BaseException:
        print 'no user error userId=' + str(bcco.user_id)

    result['data'] = bccoMap
    result['msg'] = '成功'
    result['result'] = 1

    return HttpResponse(json.dumps(result), content_type="application/json")

#对订单进行排单
@login_required
def sortOrder(request):
    orderId = int(request.GET.get('orderId'))
    sortTime = str(request.GET.get('sortTime'))
    result = {}

    bcco = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
    if len(list(bcco)) > 0:
        bcco = bcco[0]
        if bcco.is_sort_order == 0:
            bcco.is_sort_order = 1
            bcco.sort_time = datetime.strptime(sortTime, "%Y-%m-%d").date()
            bcco.save()
            result['msg'] = '排单成功'
            result['result'] = 1
            return HttpResponse(json.dumps(result), content_type="application/json")
        else:
            result['msg'] = '已经排单'
            result['result'] = -1
            return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    
@login_required
def updateSortOrder(request):
    orderId = int(request.GET.get('orderId'))
    sortTime = str(request.GET.get('sortTime'))
    
    result = {}
    
    bcco = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
    if len(list(bcco)) > 0:
        bcco = bcco[0]
        bcco.sort_time = datetime.strptime(sortTime, "%Y-%m-%d").date()
        bcco.save()
        result['msg'] = '更新成功'
        result['result'] = 1
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")  

@login_required    
def finishOrder(request):
    orderId = int(request.GET.get('id'))
    remark = str(request.GET.get('remark').encode("utf-8"))
    
    result = {}
    
    bcco = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
    if len(list(bcco)) > 0:
        bcco = bcco[0]
        orderList = Order.objects.filter(id=bcco.order_id)
        order = None
        if len(list(orderList)) > 0:
            order = orderList[0]        
        if bcco.is_finish != 1:
            bcco.is_finish = 1
            bcco.remark = remark
            bcco.update_time = datetime.now()
            bcco.save()
            result['msg'] = '更新成功'
            result['result'] = 1
            
            if bcco.conversion_type == 2:
                bcco2 = BuddnistCeremonyCommodityOrder.objects.filter(conversion_order_id=bcco.id)
                if len(list(bcco2)) > 0:
                    bcco2 = bcco2[0]
                    bcco2.is_finish = 1
                    bcco2.remark = remark
                    bcco2.update_time = datetime.now()
                    bcco2.save()
            
            weixinUser = WeixinUser.objects.get(id=bcco.user_id);
            temple = Temple.objects.get(id=request.user.temple_id)
            buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.get(id=bcco.commodity_id)
            buddnistCeremonyCommoditySubdivideName = None
            if bcco.subdiride_id != 0:
                buddnistCeremonyCommoditySubdivide = BuddnistCeremonyCommoditySubdivide.objects.get(id=bcco.subdiride_id)
                buddnistCeremonyCommoditySubdivideName = buddnistCeremonyCommoditySubdivide.name
            args = [([weixinUser.wx_openid, temple.name, buddnistCeremonyCommodity.name, buddnistCeremonyCommoditySubdivideName, datetime.now(), bcco.id], None)]
            poolUtil.runPool(pushUtil.pushDisposeCommodityOrder, args)

            if bcco.name:
                pushArgs = [([request.get_host(),bcco.user_id, bcco.dispose_pic_url, bcco.name, bcco.id, temple.name], None)]
                poolUtil.runPool(pushUtil.pushFinishOrderToChanzai, pushArgs)

            if order:
                order.is_finished = 1
                order.save()
            # 标记需要管理员处理的订单为已处理
            TempleContentManagerNotifyModel.objects.filter(type=1, orderId=orderId).update(status=0)

            return HttpResponse(json.dumps(result), content_type="application/json")
        elif bcco.is_finish == 1:
            bcco.is_finish = 0
            bcco.remark = remark
            bcco.update_time = datetime.now()
            bcco.save()
            if order:
                order.is_finished = 0
                order.save()
            # 标记需要管理员处理的订单为已处理
            TempleContentManagerNotifyModel.objects.filter(type=1, orderId=orderId).update(status=1)

            result['msg'] = '更新成功'
            result['result'] = 1
            return HttpResponse(json.dumps(result), content_type="application/json")            
        else:
            result['msg'] = '已经标志完成'
            result['result'] = -1
            return HttpResponse(json.dumps(result), content_type="application/json")            
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")  

@login_required    
def finishMoreOrder(request):
    orderIds = request.POST.get('orderIds')
    pics = request.POST.get('pics')
    remark = str(request.POST.get('remark',"").encode("utf-8"))
    
    result = {}
    orderIdList = json.loads(orderIds)
    for orderId in orderIdList:
        bcco = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
        if len(list(bcco)) > 0:
            bcco = bcco[0]
            orderList = Order.objects.filter(id=bcco.order_id)
            order = None
            if len(list(orderList)) > 0:
                order = orderList[0]
            if bcco.is_finish != 1:
                bcco.is_finish = 1
                bcco.dispose_pic_url = pics
                bcco.remark = remark
                bcco.update_time = datetime.now();
                bcco.save()
                
                if bcco.conversion_type == 2:
                    bcco2 = BuddnistCeremonyCommodityOrder.objects.filter(conversion_order_id=bcco.id)
                    if len(list(bcco2)) > 0:
                        bcco2 = bcco2[0]
                        bcco2.is_finish = 1
                        bcco2.remark = remark
                        bcco2.update_time = datetime.now()
                        bcco2.save()
                
                weixinUser = WeixinUser.objects.get(id=bcco.user_id);
                temple = Temple.objects.get(id=request.user.temple_id)
                buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.get(id=bcco.commodity_id)
                buddnistCeremonyCommoditySubdivideName = None
                if bcco.subdiride_id != 0:
                    buddnistCeremonyCommoditySubdivide = BuddnistCeremonyCommoditySubdivide.objects.get(id=bcco.subdiride_id)
                    buddnistCeremonyCommoditySubdivideName = buddnistCeremonyCommoditySubdivide.name
                args = [([weixinUser.wx_openid, temple.name, buddnistCeremonyCommodity.name, buddnistCeremonyCommoditySubdivideName, datetime.now(), bcco.id], None)]
                poolUtil.runPool(pushUtil.pushDisposeCommodityOrder, args)

                pushArgs = [
                    ([request.get_host(), bcco.user_id, bcco.dispose_pic_url, bcco.name, bcco.id, temple.name], None)]
                poolUtil.runPool(pushUtil.pushFinishOrderToChanzai, pushArgs)

                if order:
                    order.is_finished = 1
                    order.save()

                # 标记需要管理员处理的订单为已处理
                TempleContentManagerNotifyModel.objects.filter(type=1, orderId=orderId).update(status=0)
                # 不知道是不是转单,也标记一下
                TempleContentManagerNotifyModel.objects.filter(type=3, orderId=orderId).update(status=0)
            elif bcco.is_finish == 1:
                bcco.is_finish = 0
                bcco.save()
                if order:
                    order.is_finished = 0
                    order.save()
                # 标记需要管理员处理的订单为已处理
                TempleContentManagerNotifyModel.objects.filter(type=1, orderId=orderId).update(status=1)
                # 不知道是不是转单,也标记一下
                TempleContentManagerNotifyModel.objects.filter(type=3, orderId=orderId).update(status=1)
    result['msg'] = '更新成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCommodityNameList(request):
    result = {}
    shopStrSQL = ""
    bcsList = BuddnistCeremonyShop.objects.filter(temple_id=request.user.temple_id)
    shopStrSQL = "and shop_id in ("
    for bcs in bcsList:
        if bcs.id != bcsList[0].id:
            shopStrSQL = shopStrSQL+','
        shopStrSQL = shopStrSQL+str(bcs.id)
    if bcsList.count() <= 0:
        shopStrSQL = shopStrSQL+'0'
    shopStrSQL = shopStrSQL+')'

    bccList = BuddnistCeremonyCommodity.objects.raw('select * from buddnist_ceremony_commodity where op_status = 0 %s order by add_time desc'%(shopStrSQL))

    bccList2 = []
    for bcc in bccList:
        bccMap = {}
        bccMap['name'] = bcc.name
        bccMap['commodityId'] = bcc.id
        bccsList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=bcc.id,op_status=0)
        bccsList2 = []
        for bccs in bccsList:
            bccsMap = {}
            bccsMap['name'] = bccs.name
            bccsMap['subdivideId'] = bccs.id
            bccsList2.append(bccsMap)
        bccMap['subdivideList'] = bccsList2
        bccList2.append(bccMap)
    result['data'] = bccList2
    result['result'] = 1
    result['msg'] = '成功'
    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def getCommoditySubtypeList(request):
    result = {}
    commodityId = request.GET.get("commodityId", 0)
    subtypeList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=commodityId, op_status=0)
    bccList2 = []
    for bcc in subtypeList:
        bccMap = {}
        bccMap['name'] = bcc.name
        bccMap['subid'] = bcc.id
        bccList2.append(bccMap)
    result['data'] = bccList2
    result['result'] = 1
    result['msg'] = '成功'
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def bcDownloadExcel(request):
    type = str(request.GET.get('pageName')) #1获取未排单  2获取已排单 3获取已完成
    if type == 'tab1':
        type = 1 
    elif type == 'tab3':
        type = 3
    beginDate = str(request.GET.get('beginDate'))
    endDate = str(request.GET.get('endDate'))
    
    commodityId = request.GET.get('buddishService')
    
    isSearchNoPic = request.GET.get('isSearchNoPic')
    
    subdirideId = request.GET.get('subdirideId')
    
    searchNotPrint = request.GET.get('searchNotPrint')
    
    templeId = request.user.temple_id
    
    sql1 = 'select cc.posiscript,cc.pay_time,cc.buy_num,cc.price,cc.name,dd.name,dd.mobile,cc.subdiride_id,cc.is_finish,cc.dispose_pic_url from (select aa.buyer_info_id,aa.posiscript,aa.add_time,aa.buy_num,aa.price,bb.name,aa.subdiride_id,aa.is_finish,aa.dispose_pic_url,aa.pay_time from (select * from buddnist_ceremony_commodity_order where pay_type = 1 and commodity_id > 0 and conversion_type = 1'
    sql1List = []
    
#     sql2 = 'select aa.posiscript,aa.add_time,aa.buy_num,aa.price,bb.name,cc.name,mobile,aa.subdiride_id from (select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 1'
#     sql2List = []
    
    shopStrSQL = ""
    if templeId != "None" and templeId != '' and templeId is not None and templeId != '0':
#         bcsList = BuddnistCeremonyShop.objects.filter(temple_id=templeId)
#         shopStrSQL = " and commodity_id in ("
#         for bcs in bcsList:
#             bccList = BuddnistCeremonyCommodity.objects.filter(shop_id=bcs.id)
#             for bcc in bccList:
#                 if bcc.id != bccList[0].id:
#                     shopStrSQL = shopStrSQL+','
#                 shopStrSQL = shopStrSQL+str(bcc.id)
#         if bcsList.count() <= 0:
#             shopStrSQL = shopStrSQL+'0'
#         shopStrSQL = shopStrSQL+')'
        shopStrSQL = " and temple_id = %s"
        sql1List.append(int(templeId))
        sql1 = sql1+shopStrSQL
#         sql2 = sql2+shopStrSQL 
       
    subdirideSQL = ""     
    if subdirideId != "None" and subdirideId != '' and subdirideId is not None and subdirideId != '0':
        subdirideSQL = " and subdiride_id = %s"
        sql1List.append(int(subdirideId))
        sql1 = sql1+subdirideSQL
    
    commodityName = ''
    isMoreCommodity = 0
    
    commodityIdStrSql = ""
    if commodityId != "None" and commodityId != '' and commodityId is not None and commodityId != '-1':
        buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
        if len(list(buddnistCeremonyCommodity)) > 0:
            commodityName = buddnistCeremonyCommodity[0].name
        commodityIdStrSql = " and commodity_id = %s"
        sql1List.append(int(commodityId))
#         sql2List.append(int(commodityId))
        sql1 = sql1+commodityIdStrSql
#         sql2 = sql2+commodityIdStrSql
    else:
        isMoreCommodity = 1 
    
    dateStrSQL = ""
    if beginDate != "None" and beginDate != '':
        beginDate = beginDate+' 00:00:00'
        endDate = endDate+' 23:59:59'
        dateStrSQL = " and pay_time >= %s and pay_time <= %s"
        sql1List.append(beginDate)
        sql1List.append(endDate)
#         sql2List.append(beginDate)
#         sql2List.append(endDate)        
        sql1 = sql1+dateStrSQL
#         sql2 = sql2+dateStrSQL
    
    tel = str(request.GET.get('tel'))
    
# #     bcuList = BuddnistCeremonyUser.objects.filter(mobile=tel)
#     bcuList = BuddnistCeremonyBuyerInfo.objects.filter(mobile=tel)
#     telStrSQL = ""
#     if tel != '':
#         if len(list(bcuList)) > 0:
#             bcu = bcuList[0]
#             telStrSQL = " and buyer_info_id = %s"
#             sql1List.append(bcu.id)
# #             sql2List.append(bcu.id)
#             sql1 = sql1+telStrSQL
# #             sql2 = sql2+telStrSQL
    if tel != '' and tel is not None and tel != 'None':
        bciList = BuddnistCeremonyBuyerInfo.objects.filter(mobile=tel)
        bciIdStr = ""
        for bci in bciList:
            if bciIdStr == "":
                bciIdStr = str(bci.id)
            else:
                bciIdStr = bciIdStr+','+str(bci.id)
        if bciIdStr == '':
            telStrSQL = " and buyer_info_id in (0)"
        else:
            telStrSQL = " and buyer_info_id in (%s)"%bciIdStr
        sql1 = sql1+telStrSQL

    searchNoPic = ''    
    if isSearchNoPic != "None" and isSearchNoPic != '' and isSearchNoPic != '0' and isSearchNoPic is not None:
        temple = Temple.objects.get(id=request.user.temple_id)
        buddnistCeremonyShop = BuddnistCeremonyShop.objects.get(temple_id=temple.id)
        buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.filter(shop_id=buddnistCeremonyShop.id).filter(op_status=0)
        commodityListSQL = ''
        for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
            if commodityListSQL == '':
                commodityListSQL = ' commodity_id in ('+str(buddnistCeremonyCommodity.id)
            else:
                commodityListSQL = commodityListSQL+','+str(buddnistCeremonyCommodity.id)
        if commodityListSQL != '':
            commodityListSQL = commodityListSQL+')'
        buddnistCeremonyCommodityList2 = BuddnistCeremonyCommodity.objects.filter(shop_id=buddnistCeremonyShop.id).filter(op_status=0)
        commodityListStr = ''
        subdivideListSQL = ''
        for buddnistCeremonyCommodity in buddnistCeremonyCommodityList2:
            if commodityListStr == '':
                commodityListStr = str(buddnistCeremonyCommodity.id)
            else:
                commodityListStr = commodityListStr+','+str(buddnistCeremonyCommodity.id)
        if commodityListStr != '':
            buddnistCeremonyCommoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.raw('select * from buddnist_ceremony_commodity_subdivide where commodity_id in('+str(commodityListStr)+') and price > 0 and op_status = 0')
            for buddnistCeremonyCommoditySubdivide in buddnistCeremonyCommoditySubdivideList:
                if subdivideListSQL == '':
                    subdivideListSQL = ' subdiride_id in('+str(buddnistCeremonyCommoditySubdivide.id)
                else:
                    subdivideListSQL = subdivideListSQL+','+str(buddnistCeremonyCommoditySubdivide.id)
        if buddnistCeremonyCommoditySubdivide != '':
            subdivideListSQL = subdivideListSQL+')'
        if commodityListSQL != '' and subdivideListSQL != '':
            searchNoPic = ' and ('+commodityListSQL+' or '+subdivideListSQL+')'
        else:
            searchNoPic = ' and '+commodityListSQL+subdivideListSQL
        searchNoPic = searchNoPic+' and (dispose_pic_url = "" or dispose_pic_url is NULL)'  
        
        sql1 = sql1+searchNoPic 
        
    if searchNotPrint == '1':
        sql1 = sql1+' and is_print = 0' 
            
    sql1 = sql1+' order by pay_time desc) as aa left join `buddnist_ceremony_commodity` as bb on aa.commodity_id = bb.id) as cc left join `buddnist_ceremony_buyer_info` as dd on cc.buyer_info_id = dd.id'
#     sql2 = sql2+' order by add_time desc) as aa,`buddnist_ceremony_commodity` as bb,`buddnist_ceremony_user` as cc where aa.`commodity_id` = bb.`id` and aa.`user_id` = cc.`id`'
#     print sql2
    
    sql = ""
    sqlList = []
#     if type == 1:
    sql = sql1
    sqlList = sql1List
    
    print sql
#     elif type == 3:
#         sql = sql2
#         sqlList = sql2List
        
       
#     'select * from buddnist_ceremony_commodity_order where pay_type = 1 and is_finish = 1 %s %s %s %s order by add_time desc'%(dateStrSQL,telStrSQL,commodityIdStrSql,shopStrSQL)
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('订单',cell_overwrite_ok=True)
    style = xlwt.XFStyle()
    font = xlwt.Font()
    font.name = 'SimSun' # 指定“宋体”
    style.font = font         
    listNum = 0
    ws.write(listNum, 0, '时间')     
    ws.write(listNum, 1, '购买次数')
    ws.write(listNum, 2, '总金额')
    ws.write(listNum, 3, '佛事名称')
    ws.write(listNum, 4, '微信昵称')
    ws.write(listNum, 5, '电话号码')
    ws.write(listNum, 6, '规格')
    ws.write(listNum, 7, '是否已标志完成')
    ws.write(listNum, 8, '附言')
    ws.write(listNum, 9, '是否有处理图片')
    posiscriptMap = {}
    cursor = connection.cursor()  
    cursor.execute(sql,sqlList)
    listNum2 = 8;
    dataList = cursor.fetchall()
    if len(list(dataList)) <= 0:
        return HttpResponse('该佛事没有可下载的订单')
    for convertList in dataList:
        listNum = listNum+1
        if convertList[1] == None:
            ws.write(listNum, 0, "")
        else:
            ws.write(listNum, 0, convertList[1].strftime('%Y-%m-%d %H:%M:%S'))
        ws.write(listNum, 1, convertList[2])
        ws.write(listNum, 2, convertList[3])
        ws.write(listNum, 3, convertList[4])
        if convertList[5] == 'undefined':
            ws.write(listNum, 4,'')
        else:
            ws.write(listNum, 4,convertList[5])
        if convertList[6] == 'undefined':    
            ws.write(listNum, 5,'')
        else:
            ws.write(listNum, 5, convertList[6])
        if convertList[7] != 0 and convertList[7] is not None:
            subdivideList = BuddnistCeremonyCommoditySubdivide.objects.filter(id=convertList[7])
            if len(subdivideList) > 0:
                ws.write(listNum, 6, subdivideList[0].name)
            else:
                ws.write(listNum, 6, '')
        else:
            ws.write(listNum, 6, '')
            
        if convertList[8] is not None:
            if convertList[8] == 1:
                ws.write(listNum, 7, '是')
            if convertList[8] == 0:
                ws.write(listNum, 7, '否') 
                
        if convertList[9] is None:
            ws.write(listNum, 9, '否')
        elif convertList[9] == '': 
            ws.write(listNum, 9, '否')
        else:
            ws.write(listNum, 9, '是')
            
        posiscriptList = convertList[0].replace('\\','\\\\')
        posiscriptList = posiscriptList.replace('\n',' ')
        posiscriptList = posiscriptList.replace('\\\\n', ' ')
        if posiscriptList[0] == '"':
            posiscriptList = posiscriptList[1:len(posiscriptList)]
        if posiscriptList[-1] == '"':
            posiscriptList = posiscriptList[0:-1]
        print posiscriptList
        posiscriptList = json.loads(posiscriptList)
#         for posiscript in posiscriptList:
#             if posiscript['name'] not in posiscriptMap.keys():
#                 posiscriptMap[posiscript['name']] = listNum2
#                 ws.write(0, listNum2, posiscript['name'])
#                 setVal = posiscript['value']
#                 if setVal == 'undefined':
#                     setVal = ''
#                 ws.write(listNum, listNum2, setVal)
#                 listNum2 = listNum2+1
#             else:
#                 setVal = posiscript['value']
#                 if setVal == 'undefined':
#                     setVal = ''                
#                 ws.write(listNum, posiscriptMap[posiscript['name']], setVal)
        if commodityId != "None" and commodityId != '' and commodityId is not None and commodityId != '-1':
            for posiscript in posiscriptList:
                if posiscript['name'] not in posiscriptMap.keys():
                    posiscriptMap[posiscript['name']] = listNum2
                    ws.write(0, listNum2, posiscript['name'])
                    setVal = posiscript['value']
                    if setVal == 'undefined':
                        setVal = ''
                    ws.write(listNum, listNum2, setVal)
                    listNum2 = listNum2+1
                else:
                    setVal = posiscript['value']
                    if setVal == 'undefined':
                        setVal = ''                
                    ws.write(listNum, posiscriptMap[posiscript['name']], setVal)
        else:
            posiscriptStr = ''
            for posiscript in posiscriptList:
                if posiscript['name'] not in posiscriptMap.keys():
                    setVal = posiscript['value']
                    if setVal == 'undefined':
                        setVal = ''
                    if posiscriptStr == '':
                        posiscriptStr = posiscript['name']+':'+setVal
                    else:
                        posiscriptStr = posiscriptStr+'\n'+posiscript['name']+':'+setVal                    
                else:
                    setVal = posiscript['value']
                    if setVal == 'undefined':
                        setVal = ''                
                    if posiscriptStr == '':
                        posiscriptStr = posiscript['name']+':'+setVal
                    else:
                        posiscriptStr = posiscriptStr+'\n'+posiscript['name']+':'+setVal 
            ws.write(listNum, 8, posiscriptStr)
    the_file_name = "./download/佛事订单.xls"
#     the_file_name = "test.xls"
    wb.save(the_file_name)
    response = StreamingHttpResponse(file_iterator(the_file_name))
    response['Content-Type'] = 'application/octet-stream'
    if commodityName is not None:
        fileName = commodityName.encode('utf-8')
    else:
        fileName = '所有订单'
    if isMoreCommodity == 1:
        fileName = '所有订单'
    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(fileName+'.xls')
    return response    
#     result = {}
#     return HttpResponse(json.dumps(result), content_type="application/json") 

@login_required    
def updateOrderRemark(request):
    orderId = int(request.GET.get('id'))
    remark = str(request.GET.get('remark').encode("utf-8"))
    
    result = {}
    
    bcco = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
    if len(list(bcco)) > 0:
        bcco = bcco[0]
        bcco.remark = remark
        bcco.save()
        result['msg'] = '更新成功'
        result['result'] = 1
        return HttpResponse(json.dumps(result), content_type="application/json")            
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def createCeremony(request):
    user = request.user
    templeId = user.temple_id
    req = json.loads(request.body)
    title = req['title']
    explain = req['explain']
    op_status = req['op_status']
    ceremonyTypeId = req['ceremonyTypeId']
    # 新增
    allow_showVistNum = req['allow_showVistNum']
    custom_introduce = req['custom_introduce']
    if req.has_key('printerId'):
        printer_id = req['printerId']
        is_open_printer = req['isOpenPrinter']
        if req.has_key('continuousPrintNum'):
            continuous_print_num = req['continuousPrintNum']
        else:
            continuous_print_num = 2
        if req.has_key('qrcodePrint'):
            qrcode_print = req['qrcodePrint']
        else:
            qrcode_print = 1
        if req.has_key('isPrintMobile'):
            is_print_mobile = req['isPrintMobile']
        else:
            is_print_mobile = 0
    else:
        printer_id = 0
        is_open_printer = 0
        continuous_print_num = 2
        qrcode_print = 0
        is_print_mobile = 0
    pics = req['pics']
    priceStr = str(req['price']) if req.has_key('price') else None
    price = -1
    random_money_list = ""
    if priceStr is not None and "," in priceStr:
        random_money_list = str(priceStr)
    elif priceStr is not None:
        price = float(priceStr)
    stock = req['stock'] if req.has_key('stock') else -1
    subdivideStr = req['subdivideStr'] if req.has_key('subdivideStr') else None
    detail = unquote(str(req['detail'])).decode('utf8')
    opName = req['opName']

    postScript = req['postScript']
    showClient = req['showClient']
    showStatictics = req['showStatictics']
    endTime = req['endTime']
    startTime = req['startTime']
    showEndTime = req['showEndTime']
    feedbackType = req['feedbackType']
    pay_succ_details_flag = req['pay_succ_details_flag']
    is_auto_finish = req['isAutoFinish']
    isEnd = 0
    payDetail = unquote(str(req['payDetail'])).decode('utf8')
    is_need_pay = 0 if price <= 0 and random_money_list == "" else 1


    # print '==========================='
    # print title
    # print ceremonyTypeId
    # print pics
    # print subdivideStr
    # print detail
    # print opName
    # print postScript
    # print showClient
    # print showStatictics
    # print endTime
    # print showEndTime
    # print isEnd
    # print payDetail
    # print '==========================='



    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    shopId = shop[0].id

    result = {}
    if title is None or ceremonyTypeId <= 0 or pics is None or detail is None or opName is None or payDetail is None:
        result['msg'] = '缺少主要参数'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        endDate = '2099-12-31 00:00:00'
        if endTime:
            endDate = datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")
        startDate = datetime.now()
        if startTime:
            startDate = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
        type = 2 if price < 0 and random_money_list != "" else 1
        ceremony = BuddnistCeremonyCommodity(name=title, details=detail, buy_btn_name=opName, is_show_participant=showClient, \
                                             is_show_cnt=showStatictics, end_time=endDate, is_show_time=showEndTime, \
                                             is_auto_finish=is_auto_finish, pay_succ_details=payDetail, op_status=op_status, shop_id=shopId, \
                                             commodity_type_id=ceremonyTypeId, random_money_list=random_money_list, stock=stock,\
                                             price=price, is_need_pay=is_need_pay, start_time=startDate, type=type,
                                             printer_id=printer_id,is_open_printer=is_open_printer,continuous_print_num=continuous_print_num,\
                                             qrcode_print=qrcode_print,explain=explain,is_print_mobile=is_print_mobile, temple_id=templeId, \
                                             feedbackType=feedbackType, pay_succ_details_flag=pay_succ_details_flag, \
                                             allow_showVistNum=allow_showVistNum,custom_introduce=custom_introduce)
        ceremony.save()
        for pic in pics:
            picModel = BuddnistCeremonyCommodityPics(commodity_id=ceremony.id, pic_url=pic, op_status=0)
            picModel.save()

        if subdivideStr:
            for j in subdivideStr:
                if j['name'] is None or j['pic'] is None:
                    result['msg'] = '缺少规格参数'
                    result['result'] = -2
                    return HttpResponse(json.dumps(result), content_type="application/json")
                else:
                    subPriceStr = str(j['price']) if j.has_key('price') else None
                    subPrice = -1
                    sub_random_money_list = ""
                    if subPriceStr is not None and "," in subPriceStr:
                        sub_random_money_list = str(subPriceStr)
                    elif subPriceStr is not None:
                        subPrice = float(subPriceStr)
                    sub_is_need_pay = 0 if subPrice <= 0 and sub_random_money_list == "" else 1
                    subtype= 2 if subPrice < 0 and sub_random_money_list != "" else 1
                    subEndDate = endDate
                    if j.has_key('endTime') and j['endTime'] != '':
                        subEndDate = datetime.strptime(j['endTime'], "%Y-%m-%d %H:%M:%S")
                    enroll_num = j['enroll_num'] if j.has_key('enroll_num') else 0
                    subdivideModel = BuddnistCeremonyCommoditySubdivide(commodity_id=ceremony.id, pic_url=j['pic'], \
                                                                        price=subPrice, stock=j['stock'], endTime=subEndDate,\
                                                                        op_status=0, name=j['name'], sort=j['sort'], \
                                                                        random_money_list=sub_random_money_list,\
                                                                        is_need_pay=sub_is_need_pay, type=subtype,explain=j['explain'],is_auto_finish=j['isAutoFinish'],subdivide_type=j['subdivide_type'],enroll_num=enroll_num)
                    subdivideModel.save()
                    #获取打印机数据列表,格式为{"printer":["printerId":1,"continuousPrint_num":1,"qrcodePrint":1]}
                    if j.has_key('printer'):
                        printerDataList = j['printer']
                        if printerDataList:
                            for printerData in printerDataList:
                                zizaijiaSubdividePrinter = ZizaijiaSubdividePrinter.objects.filter(printer_id=printerData['printerId']).filter(subdivide_id=subdivideModel.id).filter(op_status=0)
                                if len(list(zizaijiaSubdividePrinter)) == 0:
                                    ZizaijiaSubdividePrinter.objects.create(printer_id=printerData['printerId'],subdivide_id=subdivideModel.id,add_time=datetime.now(),update_time=datetime.now(),op_status=0,continuous_print_num=printerData['continuousPrintNum'],qrcode_print=printerData['qrcodePrint'],is_print_mobile=printerData['isPrintMobile'])
                    subpostScript = j['postScript']
                    if subpostScript:
                        for p in subpostScript:
                            subdateType = p['dataType'] if p.has_key('dataType') else 0
                            if int(p['inputType']) == 1 and p['name'] is None:
                                result['msg'] = '附言文本框需要填写内容'
                                result['result'] = -3
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 2 and p['name'] is None:
                                result['msg'] = '附言时间需要填写日期'
                                result['result'] = -4
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 3 and (p['prompt_text'] is None or p['name'] is None):
                                result['msg'] = '附言下拉框需要填写内容'
                                result['result'] = -5
                                return HttpResponse(json.dumps(result), content_type="application/json")
                            elif int(p['inputType']) == 3:
                                subpostScriptModel = BuddnistCeremonyCommodityPostscript(input_type=p['inputType'], \
                                                                                      name=p['name'], \
                                                                                      is_must=p['is_must'], \
                                                                                      data_change_type=p['dataType'],\
                                                                                      commodity_id=ceremony.id, \
                                                                                      op_status=0, \
                                                                                      font_length=p['font_length'],\
                                                                                      subdivide_id=subdivideModel.id,pic_num=p['pic_num'],describe=p['describe'])
                                subpostScriptModel.save()
                                for select in p['prompt_text']:
                                    subpostScriptSelectModel = BuddnistCeremonyCommodityPostscriptSelectInput(
                                        pposiscript_id=subpostScriptModel.id, \
                                        name=select, \
                                        op_status=0)
                                    subpostScriptSelectModel.save()

                            elif int(p['inputType']) == 4 and p['name'] is None:
                                result['msg'] = '附言联系人需要填写内容'
                                result['result'] = -6
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 5 and p['name'] is None:
                                result['msg'] = '附言电话号码需要填写内容'
                                result['result'] = -7
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 6 and p['name'] is None:
                                result['msg'] = '附言地址需要填写内容'
                                result['result'] = -8
                                return HttpResponse(json.dumps(result), content_type="application/json")
                            else:
                                isVerify = p['isVerify'] if p.has_key('isVerify') else 0
                                subpostScriptModel = BuddnistCeremonyCommodityPostscript(input_type=p['inputType'],\
                                                                                      name=p['name'], \
                                                                                      is_must=p['is_must'],\
                                                                                      prompt_text=p['prompt_text'], \
                                                                                      data_change_type=subdateType,\
                                                                                      commodity_id=ceremony.id,\
                                                                                      op_status=0, \
                                                                                      font_length=p['font_length'], \
                                                                                      subdivide_id=subdivideModel.id,\
                                                                                    pic_num=p['pic_num'],describe=p['describe'], \
                                                                                         isVerify=isVerify)
                                subpostScriptModel.save()

        if postScript:
            for j in postScript:
                dateType = j['dataType'] if j.has_key('dataType') else 0
                if j['inputType'] == 1 and j['name'] is None:
                    result['msg'] = '附言文本框需要填写内容'
                    result['result'] = -3
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 2 and j['name'] is None:
                    result['msg'] = '附言时间需要填写日期'
                    result['result'] = -4
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 3 and j['prompt_text'] is None  and j['name'] is None:
                    result['msg'] = '附言下拉框需要填写内容'
                    result['result'] = -5
                    return HttpResponse(json.dumps(result), content_type="application/json")
                elif j['inputType'] == 3:
                    postScriptModel = BuddnistCeremonyCommodityPostscript(input_type=j['inputType'],
                                                                          name=j['name'],
                                                                          is_must=j['is_must'],
                                                                          data_change_type=j['dataType'], commodity_id=ceremony.id,
                                                                          font_length=j['font_length'],
                                                                          op_status=0,subdivide_id=0,pic_num=j['pic_num'],describe=j['describe'])
                    postScriptModel.save()
                    for select in j['prompt_text']:
                        postScriptSelectModel = BuddnistCeremonyCommodityPostscriptSelectInput(pposiscript_id=postScriptModel.id,
                                                                                           name=select,
                                                                                            op_status=0)
                        postScriptSelectModel.save()

                elif j['inputType'] == 4 and j['name'] is None:
                    result['msg'] = '附言联系人需要填写内容'
                    result['result'] = -6
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 5 and j['name'] is None:
                    result['msg'] = '附言电话号码需要填写内容'
                    result['result'] = -7
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 6 and j['name'] is None:
                    result['msg'] = '附言地址需要填写内容'
                    result['result'] = -8
                    return HttpResponse(json.dumps(result), content_type="application/json")
                else:
                    isVerify = j['isVerify'] if j.has_key('isVerify') else 0
                    postScriptModel = BuddnistCeremonyCommodityPostscript(input_type=j['inputType'], name=j['name'],
                                                                          is_must=j['is_must'],
                                                                          prompt_text=j['prompt_text'],
                                                                          data_change_type=dateType, commodity_id=ceremony.id,
                                                                          font_length=j['font_length'],
                                                                          op_status=0,subdivide_id=0,pic_num=j['pic_num'],
                                                                          describe=j['describe'],isVerify=isVerify)
                    postScriptModel.save()

        result['msg'] = '添加成功'
        result['result'] = 0
        result['commodityId'] = ceremony.id
        ##未审核通过的佛事不弹框
        # cList1 = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
        #                                                 commodityId=ceremony.id, status=0)
        # cList2 = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status=0, type=5)
        # if len(cList1) == 0 and len(cList2) > 0:
        #     result['createCalendar'] = 1
        # else:
        #必弹窗

        result['createCalendar'] = 1
        result['createImageText'] = 1
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def createCeremonyType(request):
    # print request.body
    paramMap = json.load(request)
    name = paramMap['name']
    user = request.user
    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    shopId = shop[0].id
    result = {}
    if name is None or shopId <= 0:
        result['msg'] = '缺少参数'
        result['result'] = -1;
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        typeModel = BuddnistCeremonyType(name=name, shop_id=shopId, sort=0, status=0)
        typeModel.save()
        result['msg'] = '添加成功'
        result['result'] = 0
        result['typeId'] = typeModel.id
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def delCeremonyType(request):
    req = json.loads(request.body)
    id = req['id']
    result = {}
    if id <= 0:
        result['msg'] = '缺少参数'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        BuddnistCeremonyType.objects.filter(id=id).update(status=-1)
        result['msg'] = '删除成功'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")


# @login_required
def uploadPic(request):
    result = {}
    uploadPicClient = UploadPicClient()
    file_name = uploadPicClient.uploadPic(request)
    result['msg'] = '上传成功'
    result['result'] = 0
    result['url'] = file_name
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def uploadPicUEditor(request):
    actionConfig = request.GET.get('action', '')
    if actionConfig == 'config':
        data = {}
        imageAllowFiles = []
        imageAllowFiles.append('.png')
        imageAllowFiles.append('.jpg')
        imageAllowFiles.append('.jpeg')
        imageAllowFiles.append('.gif')
        imageAllowFiles.append('.bmp')
        data['imageAllowFiles'] = imageAllowFiles
        data['imageMaxSize'] = 4096000
        data['imageUrlPrefix'] = ''
        data['imageActionName'] = 'uploadPic'
        data['imageFieldName'] = 'file'
        data['imageInsertAlign'] = 'none'
        return HttpResponse(json.dumps(data), content_type="application/json")
    result = {}
    uploadPicClient = UploadPicClient()
    file_name = uploadPicClient.uploadPic(request)
    result['url'] = file_name
    result['type'] = '.jpg'
    result['state'] = 'SUCCESS'
    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def getCeremonyTypeList(request):
    user = request.user
    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    result = {}
    if len(shop) <=0:
        result['msg'] = '没有数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    shopId = shop[0].id
    typeList = BuddnistCeremonyType.objects.filter(shop_id=shopId, status=0)
    result = {}
    if len(typeList) > 0:
        typeL = []
        for type in typeList:
            typeMap = {}
            typeMap['name'] = type.name
            typeMap['ceremonyTypeId'] = type.id
            typeL.append(typeMap)
        result['msg'] = ''
        result['result'] = 0
        result['data'] = typeL
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '没有数据'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def createCeremonyIndex(request):
    id = int(request.GET.get('id', 0))
    user = request.user
    # shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    # result = {}
    # if len(shop) <= 0:
    #     result['msg'] = '没有数据'
    #     result['result'] = -1
    #     return HttpResponse(json.dumps(result), content_type="application/json")
    #
    # shopId = shop[0].id
    #
    # if id > 0:
    ceremonyList = BuddnistCeremonyCommodity.objects.filter(id=id, temple_id=user.temple_id)
    if len(ceremonyList) > 0:
        ceremony = ceremonyList[0]
        ceremonyMap = getCeremonyModelUtil(ceremony)

        # h = HTMLParser.HTMLParser()
        # result = h.unescape(json.dumps(ceremonyMap))
        result = json.dumps(ceremonyMap)
        # print result+'====================================='
        return render_to_response('buddhist/create.html', {'ceremonyMap': result})
    else:
        return render_to_response('buddhist/create.html', {'ceremonyMap': {}})

@login_required
def managerCeremonyIndex(request):
    return render_to_response('buddhist/manage.html')

@login_required
def selectCeremonyTemplate(request):
    return render_to_response('buddhist/template.html')

@login_required
def getCeremonyList(request):
    user = request.user
    templeId = user.temple_id
    temple = Temple.objects.filter(id=templeId).first()
    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    result = {}
    if len(shop) <= 0:
        result['msg'] = '没有数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")

    shopId = shop[0].id
    typeId = int(request.GET.get('typeId', 0))
    filterType = int(request.GET.get('filterType', 0))
    ceremonyName = str(request.GET.get('searchText', ''))
    pageSize = int(request.GET.get('pageSize', 25))
    pageNo = int(request.GET.get('pageIndex', 0))
    orderByJoinNum = request.GET.get('orderByJoinNum')
    orderByCollectMoney = request.GET.get('orderByCollectMoney')
    if pageNo < 0:
        pageNo = 0
    sql = 'select * from buddnist_ceremony_commodity where shop_id='+str(shopId)
    if typeId > 0:
        sql += ' and commodity_type_id='+str(typeId)
    if ceremonyName:
        sql += ' and name like "%%'+ceremonyName+'%%"'

    if filterType == 1:
        startDate = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        sql += ' and end_time>="'+str(startDate)+'" and is_end=0 and op_status=0  and start_time<="' + str(startDate) + '"'
    elif filterType == 2:
        sql += ' and op_status=1'
    elif filterType == 3:
        startDate = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        sql += ' and start_time>"' + str(startDate) + '" and op_status=0'
    elif filterType == 4:
        sql += ' and is_end=1 and op_status=0'
    elif filterType == 5:
        sql += ' and op_status=2'

    sql += ' and op_status>=0'
    sql1 = sql[:]
            
    if orderByJoinNum is not None and orderByJoinNum != '':
        if orderByJoinNum == '0':
            sql += ' order by join_num,id desc'
        elif orderByJoinNum == '1':
            sql += ' order by join_num desc,id desc'
                
    if orderByCollectMoney is not None and orderByCollectMoney != '':
        if orderByJoinNum is not None and orderByJoinNum != '':
            if orderByJoinNum == '0':
                sql += ',join_num,id desc'
            elif orderByJoinNum == '1':
                sql += ',join_num desc,id desc'
        else:
            if orderByCollectMoney == '0':
                sql += ' order by collect_money,id desc'
            elif orderByCollectMoney == '1':
                sql += ' order by collect_money desc,id desc'
            
    if (orderByJoinNum is None and orderByCollectMoney is None) or (orderByJoinNum == '' and orderByCollectMoney == ''):
        sql += ' order by id desc'
        
                
    sql += ' limit '+str(pageNo*pageSize)+","+str(pageSize)
                
    ceremonyList = list(BuddnistCeremonyCommodity.objects.raw(sql))
    data = []
    if len(ceremonyList) > 0:
        for ceremony in ceremonyList:
            ceremonyMap = {}
            ceremonyMap['id'] = ceremony.id
            ceremonyMap['name'] = ceremony.name
            ceremonyMap['join_num'] = 0 if ceremony.join_num is None else ceremony.join_num
            ceremonyMap['collect_money'] = 0 if ceremony.collect_money is None else ceremony.collect_money
            ceremonyMap['price'] = ceremony.price if ceremony.price is not None and ceremony.price > 0 else ""
            ceremonyMap['endTime'] = ceremony.end_time.strftime('%Y-%m-%d')
            printerNameList = []
            picList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=ceremony.id, op_status=0)
            if len(picList) > 0:
                ceremonyMap['pic'] = picList[0].pic_url
            subList =  BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=ceremony.id, op_status=0)
            if ceremony.price == 0 and (ceremony.random_money_list is None or ceremony.random_money_list == ''):
                ceremonyMap['price'] = '无需支付'
            if len(subList) > 0:
                minPrice = -2.00
                maxPrice = 0.00
                rnd = False
                for sub in subList:
                    zizaijiaSubdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=sub.id,op_status=0)
                    for zizaijiaSubdividePrinter in zizaijiaSubdividePrinterList:
                        zizaijiaPrinter = ZizaijiaPrinter.objects.filter(id=zizaijiaSubdividePrinter.printer_id)
                        if len(list(zizaijiaPrinter)) > 0:
                            zizaijiaPrinter = zizaijiaPrinter[0]
#                             if zizaijiaPrinter.address not in printerNameList:
#                                 printerNameList.append(zizaijiaPrinter.address)  
                        isAppend = 0
                        for printerName in printerNameList:                  
                            if printerName['printerId'] == zizaijiaPrinter.id:
                                printerName['subNameList'].append(sub.name)
                                isAppend = 1
                        if isAppend == 0:
                            printerName = {}
                            printerName['printerId'] = zizaijiaPrinter.id
                            printerName['address'] = zizaijiaPrinter.address
                            subNameList = []
                            subNameList.append(sub.name)
                            printerName['subNameList'] = subNameList
                            notBoundSubNameList = []
                            printerName['notBoundSubNameList'] = notBoundSubNameList
                            printerNameList.append(printerName)
                    zizaijiaPrinterList = ZizaijiaPrinter.objects.filter(temple_id=templeId)
                    for zizaijiaPrinter in zizaijiaPrinterList:
                        isBoundPrinter = 0
                        for zizaijiaSubdividePrinter in zizaijiaSubdividePrinterList:
                            if zizaijiaPrinter.id ==  zizaijiaSubdividePrinter.printer_id:
                                isBoundPrinter = 1
                        if isBoundPrinter == 0:
                            isAppend = 0
                            for printerName in printerNameList:                  
                                if printerName['printerId'] == zizaijiaPrinter.id:
                                    printerName['notBoundSubNameList'].append(sub.name)
                                    isAppend = 1
                            if isAppend == 0:
                                printerName = {}
                                printerName['printerId'] = zizaijiaPrinter.id
                                printerName['address'] = zizaijiaPrinter.address
                                subNameList = []
                                printerName['subNameList'] = subNameList
                                notBoundSubNameList = []
                                notBoundSubNameList.append(sub.name)
                                printerName['notBoundSubNameList'] = notBoundSubNameList
                                printerNameList.append(printerName)
                    if sub.random_money_list is not None and sub.random_money_list != '':
                        rnd = True
                        continue
                    try:
                        p = float(sub.price)
                        if minPrice == -2.00:
                            minPrice = p
                        if p > maxPrice:
                            maxPrice = p
                        elif p < minPrice:
                            minPrice = p
                    except ValueError:
                        #包含了随喜价格,就不显示
                        minPrice = -1.00
                if rnd is True:
                    ceremonyMap['price'] = '随喜'
                if minPrice >= 0 and minPrice != maxPrice:
                    if rnd is True:
                        ceremonyMap['price'] += '/'
                    ceremonyMap['price'] += '￥' + str(minPrice)+" - "+str(maxPrice)
                elif minPrice > 0 and minPrice == maxPrice:
                    if rnd is True:
                        ceremonyMap['price'] += '/'
                    ceremonyMap['price'] += '￥' + str(minPrice)
                elif minPrice == 0 and minPrice == maxPrice and rnd is False:
                    ceremonyMap['price'] = '无需支付'
                
            else:
                if ceremony.is_open_printer == 1:
                    printerIds = json.loads(ceremony.printer_id)
                    for printerId in printerIds:
                        zizaijiaPrinter = ZizaijiaPrinter.objects.filter(id=printerId)
                        if len(list(zizaijiaPrinter)) > 0:
                            zizaijiaPrinter = zizaijiaPrinter[0]
                        printerName = {}
                        printerName['printerId'] = zizaijiaPrinter.id
                        printerName['address'] = zizaijiaPrinter.address
                        subNameList = []
                        printerName['subNameList'] = subNameList
                        notBoundSubNameList = []
                        printerName['notBoundSubNameList'] = notBoundSubNameList                        
                        printerNameList.append(printerName)
            ceremonyMap['printerList'] = printerNameList
            ceremonyMap['status'] = ceremony.op_status
            ceremonyMap['isEnd'] = ceremony.is_end
            ceremonyMap['view_count'] = ceremony.view_count
            isStart = 0
            if ceremony.start_time is not None \
                    and ceremony.start_time < datetime.now()\
                    and ceremony.is_end == 0:
                isStart = 1
            ceremonyMap['isStart'] = isStart
            if SevericeType == 1:
                ceremonyMap['wx_url'] = "https://wx.zizaihome.com/commodity/commodityAuth?commodityId="+str(ceremony.id)
                ceremonyMap['preview_url'] = "https://wx.zizaihome.com/commodity/commodityInfo2?commodityId="+str(ceremony.id)+'&templeName=' + temple.name + '&templeId='+str(temple.id)
            elif SevericeType == 2:
                ceremonyMap['wx_url'] = "http://test2.zizaihome.com/commodity/commodityAuth?commodityId="+str(ceremony.id)+"&isTest=2"
                ceremonyMap['preview_url'] = "http://test2.zizaihome.com/commodity/commodityAuth?commodityId="+str(ceremony.id)+'&templeName=' + temple.name + '&templeId='+str(temple.id)
            elif SevericeType == 3:
                ceremonyMap['wx_url'] = "http://test.zizaihome.com/commodity/commodityAuth?commodityId="+str(ceremony.id)+"&isTest=1"
                ceremonyMap['preview_url'] = "http://test.zizaihome.com/commodity/commodityAuth?commodityId="+str(ceremony.id)+'&templeName=' + temple.name + '&templeId='+str(temple.id)
            data.append(ceremonyMap)

    if temple:
        zizaijiaPrinter = ZizaijiaPrinter.objects.filter(temple_id=temple.id)
        if len(list(zizaijiaPrinter)) > 0:
            result['isHavePrinter'] = 1
        else:
            result['isHavePrinter'] = 0
    else:
        result['isHavePrinter'] = 0
    result['msg'] = ''
    result['result'] = 0
    result['data'] = data
    result['total'] = len(list(BuddnistCeremonyCommodity.objects.raw(sql1.replace('*', 'id'))))
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCeremonyModel(request):
    id = int(request.GET.get('id'))
    user = request.user
    result = {}
    # shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    # if len(shop) <= 0:
    #     result['msg'] = '没有数据'
    #     result['result'] = -1
    #     return HttpResponse(json.dumps(result), content_type="application/json")
    #
    # shopId = shop[0].id

    ceremonyList = BuddnistCeremonyCommodity.objects.filter(id=id, temple_id=user.temple_id)
    if len(ceremonyList) > 0:
        ceremony = ceremonyList[0]

        result['msg'] = ''
        result['result'] = 0
        result['data'] = getCeremonyModelUtil(ceremony)
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '没有数据'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")

def getCeremonyModelUtil(ceremony,showTime=1):
    ceremonyMap = {}
    ceremonyMap['id'] = ceremony.id
    ceremonyMap['ceremonyTypeId'] = ceremony.commodity_type_id
    ceremonyMap['title'] = ceremony.name
    ceremonyMap['detail'] = ceremony.details
    ceremonyMap['opName'] = ceremony.buy_btn_name
    ceremonyMap['price'] = ceremony.price if ceremony.price >= 0 else ceremony.random_money_list
    ceremonyMap['stock'] = ceremony.stock
    ceremonyMap['explain'] = ceremony.explain
    ceremonyMap['feedbackType'] = ceremony.feedbackType
    ceremonyMap['pay_succ_details_flag'] = ceremony.pay_succ_details_flag
    ceremonyMap['allow_showVistNum']=ceremony.allow_showVistNum
    ceremonyMap['custom_introduce'] = ceremony.custom_introduce
    picList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=ceremony.id, op_status=0)
    if len(picList) > 0:
        pics = []
        for pic in picList:
            pics.append(pic.pic_url)
        ceremonyMap['pics'] = pics
    subList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=ceremony.id, op_status=0)
    if len(subList) > 0:
        subdivideStr = []
        for sub in subList:
            subMap = {}
            subMap['id'] = sub.id
            subMap['name'] = sub.name
            subMap['pic'] = sub.pic_url
            subMap['price'] = sub.random_money_list if sub.price == -1 else sub.price
            subMap['stock'] = sub.stock
            subMap['sort'] = sub.sort
            subMap['explain'] = sub.explain
            subMap['isAutoFinish'] = sub.is_auto_finish
            subMap['subdivide_type'] = sub.subdivide_type
            subMap['endTime'] = sub.endTime.strftime('%Y-%m-%d %H:%M:%S') if sub.endTime is not None else ""
            subMap['enroll_num'] = sub.enroll_num

            # 查找出与这个规格绑定的打印机
            printerList = []
            zizaijiaSubdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=sub.id).filter(
                op_status=0)
            for zizaijiaSubdividePrinter in zizaijiaSubdividePrinterList:
                printerMap = {}
                printerMap['printerId'] = zizaijiaSubdividePrinter.printer_id
                printerMap['continuousPrintNum'] = zizaijiaSubdividePrinter.continuous_print_num
                printerMap['qrcodePrint'] = zizaijiaSubdividePrinter.qrcode_print
                printerMap['isPrintMobile'] = zizaijiaSubdividePrinter.is_print_mobile
                printerList.append(printerMap)
            subMap['printer'] = printerList

            subpostScriptList = BuddnistCeremonyCommodityPostscript.objects.filter(commodity_id=ceremony.id, \
                                                                                   subdivide_id=sub.id, \
                                                                                   op_status=0)
            if len(subpostScriptList) > 0:
                subscriptList = []
                for subscript in subpostScriptList:
                    subScriptMap = {}
                    subScriptMap['id'] = subscript.id
                    subScriptMap['inputType'] = subscript.input_type
                    if subscript.input_type == 3:
                        subselectList = BuddnistCeremonyCommodityPostscriptSelectInput.objects.filter( \
                            pposiscript_id=subscript.id, op_status=0)
                        if len(subselectList) > 0:
                            subselectStr = []
                            for subselect in subselectList:
                                subselectMap = {}
                                subselectMap['id'] = subselect.id
                                subselectMap['name'] = subselect.name
                                subselectStr.append(subselectMap)
                            subScriptMap['prompt_text'] = subselectStr
                    else:
                        subScriptMap['prompt_text'] = subscript.prompt_text
                    subScriptMap['name'] = subscript.name
                    subScriptMap['is_must'] = subscript.is_must
                    subScriptMap['pic_num'] = subscript.pic_num
                    subScriptMap['dataType'] = subscript.data_change_type
                    subScriptMap['describe'] = subscript.describe
                    subScriptMap['font_length'] = subscript.font_length
                    subScriptMap['isVerify'] = subscript.isVerify
                    subscriptList.append(subScriptMap)

                subMap['postScript'] = subscriptList
            subdivideStr.append(subMap)
        ceremonyMap['subdivideStr'] = subdivideStr
    else:
        ceremonyMap['printerId'] = ceremony.printer_id
        ceremonyMap['isOpenPrinter'] = ceremony.is_open_printer
        ceremonyMap['continuousPrintNum'] = ceremony.continuous_print_num
        ceremonyMap['qrcodePrint'] = ceremony.qrcode_print
    postScriptList = BuddnistCeremonyCommodityPostscript.objects.filter(commodity_id=ceremony.id, \
                                                                        op_status=0, subdivide_id=0)
    if len(postScriptList) > 0:
        scriptList = []
        for script in postScriptList:
            scriptMap = {}
            scriptMap['id'] = script.id
            scriptMap['inputType'] = script.input_type
            if script.input_type == 3:
                selectList = BuddnistCeremonyCommodityPostscriptSelectInput.objects.filter(pposiscript_id=script.id, \
                                                                                           op_status=0)
                if len(selectList) > 0:
                    selectStr = []
                    for select in selectList:
                        selectMap = {}
                        selectMap['id'] = select.id
                        selectMap['name'] = select.name
                        selectStr.append(selectMap)
                    scriptMap['prompt_text'] = selectStr
            else:
                scriptMap['prompt_text'] = script.prompt_text
            scriptMap['name'] = script.name
            scriptMap['is_must'] = script.is_must
            scriptMap['pic_num'] = script.pic_num
            scriptMap['describe'] = script.describe
            scriptMap['dataType'] = script.data_change_type
            scriptMap['font_length'] = script.font_length
            scriptMap['isVerify'] = script.isVerify
            scriptList.append(scriptMap)

        ceremonyMap['postScript'] = scriptList
    ceremonyMap['showClient'] = ceremony.is_show_participant
    ceremonyMap['showStatictics'] = ceremony.is_show_cnt
    if showTime == 1:
        ceremonyMap['endTime'] = ceremony.end_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ceremonyMap['endTime'] = ''
    if ceremony.start_time is not None and showTime == 1:
        ceremonyMap['startTime'] = ceremony.start_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ceremonyMap['startTime'] = ''
    ceremonyMap['showEndTime'] = ceremony.is_show_time
    ceremonyMap['isEnd'] = ceremony.is_auto_finish
    ceremonyMap['status'] = ceremony.op_status
    ceremonyMap['isAutoFinish'] = ceremony.is_auto_finish
    ceremonyMap['payDetail'] = ceremony.pay_succ_details
    ceremonyMap['isPrintMobile'] = ceremony.is_print_mobile
    return ceremonyMap

@login_required
def delCeremonyModel(request):
    id = int(request.POST.get('id'))
    user = request.user
    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    result = {}
    if len(shop) <= 0:
        result['msg'] = '没有数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")

    shopId = shop[0].id
    templeId = shop[0].temple_id
    BuddnistCeremonyCommodity.objects.filter(id=id, shop_id=shopId).update(op_status=-1)

    #删除佛历相关的佛事内容
    eventList = ZizaijiaTempleWebsiteCalendarList.objects.filter(commodityId=id, status=0)
    ZizaijiaTempleWebsiteCalendarList.objects.filter(commodityId=id) \
        .update(status=-1)

    if len(eventList) > 0:
        for day in eventList:
            tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
                                                                       calendarDate=day.calendarDate, status=0)
            if len(tmpList) == 0:
                ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId, calendarDate=day.calendarDate) \
                    .update(status=-1)

    #删除微站展示的佛事
    ZizaijiaTempleWebsiteImageTextList.objects.filter(buddnist_ceremony_commodity_id=id).update(op_status=-1)

    #删除功德机展示的相应佛事
    TempleMeritMachineAdvertisementModel.objects.filter(type=2, contentId=id).update(status=-1)

    result['msg'] = '删除成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def editCeremony(request):
    user = request.user
    templeId = user.temple_id
    req = json.loads(request.body)
    id = req['id']
    title = req['title']
    explain = req['explain']
    op_status = req['op_status']
    ceremonyTypeId = req['ceremonyTypeId']
    #新增
    allow_showVistNum=req['allow_showVistNum']
    custom_introduce=req['custom_introduce']
    if req.has_key('printerId'):
        printer_id = req['printerId']
        is_open_printer = req['isOpenPrinter']
        continuous_print_num = req['continuousPrintNum']
        if req.has_key('qrcodePrint'):
            qrcode_print = req['qrcodePrint']
        else:
            qrcode_print = 1
        if req.has_key('isPrintMobile'):
            is_print_mobile = req['isPrintMobile']
        else:
            is_print_mobile = 0
    else:
        printer_id = 0
        is_open_printer = 0
        continuous_print_num = 0
        qrcode_print = 0
        is_print_mobile = 0
    priceStr = str(req['price']) if req.has_key('price') else None
    price = -1
    random_money_list = ""
    if priceStr is not None and "," in priceStr:
        random_money_list = str(priceStr)
    elif priceStr is not None:
        price = float(priceStr)
    stock = req['stock'] if req.has_key('stock') else -1
    pics = req['pics']
    subdivideStr = req['subdivideStr'] if req.has_key('subdivideStr') else None
    detail = unquote(str(req['detail'])).decode('utf8')
    opName = req['opName']
    postScript = req['postScript']
    showClient = req['showClient']
    showStatictics = req['showStatictics']
    endTime = req['endTime']
    startTime = req['startTime']
    showEndTime = req['showEndTime']
    feedbackType = req['feedbackType']
    pay_succ_details_flag = req['pay_succ_details_flag']
    is_auto_finish = req['isAutoFinish']
    isEnd = 0
    payDetail = unquote(str(req['payDetail'])).decode('utf8')
    is_need_pay = 0 if price <= 0 and random_money_list == "" else 1

    # print '==========================='
    # print title
    # print ceremonyTypeId
    # print pics
    # print subdivideStr
    # print detail
    # print opName
    # print postScript
    # print showClient
    # print showStatictics
    # print endTime
    # print showEndTime
    # print isEnd
    # print payDetail
    # print '==========================='



    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    shopId = shop[0].id

    result = {}
    if title is None or ceremonyTypeId <= 0 or pics is None or detail is None or opName is None or payDetail is None:
        result['msg'] = '缺少主要参数'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        endDate = '2099-12-31 00:00:00'
        if endTime:
            endDate = datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")


        type = 2 if price < 0 and random_money_list != "" else 1
        ceremonyList = BuddnistCeremonyCommodity.objects.filter(id=id, shop_id=shopId)
        ceremony = ceremonyList[0]

        startDate = ceremony.add_time
        if startTime:
            startDate = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")

        ceremony.name = title
        ceremony.details = detail
        ceremony.buy_btn_name = opName
        ceremony.is_show_participant = showClient
        ceremony.is_show_cnt = showStatictics
        ceremony.end_time = endDate
        if endDate < datetime.now():
            ceremony.is_end = 1
        else:
            ceremony.is_end = 0
        ceremony.is_show_time = showEndTime
        ceremony.is_auto_finish = is_auto_finish
        ceremony.pay_succ_details = payDetail
        ceremony.feedbackType = feedbackType
        ceremony.pay_succ_details_flag = pay_succ_details_flag
        if printer_id != 0:
            ceremony.printer_id = printer_id
            ceremony.is_open_printer = is_open_printer
            ceremony.continuous_print_num = continuous_print_num
            ceremony.qrcode_print = qrcode_print
            ceremony.is_print_mobile = is_print_mobile
        #天叔说,修改了数据还要保持已审核状态,所以屏蔽这个代码
        # ceremony.op_status = 1
        #增加了一个保存为草稿功能
        if op_status and int(op_status) != 0:
            ceremony.op_status = op_status
        ceremony.commodity_type_id = ceremonyTypeId
        ceremony.price = price
        ceremony.random_money_list = random_money_list
        ceremony.stock = stock
        ceremony.type = type
        ceremony.is_need_pay = is_need_pay
        ceremony.start_time = startDate
        ceremony.explain = explain
        #新增字段
        ceremony.allow_showVistNum=allow_showVistNum
        ceremony.custom_introduce=custom_introduce
        ceremony.save()

        #修改标题同步更新到微站佛事列表
        ZizaijiaTempleWebsiteImageTextList.objects.filter(buddnist_ceremony_commodity_id=id).update(title=title)


        BuddnistCeremonyCommodityPics.objects.filter(commodity_id=ceremony.id).update(op_status=-1)
        for pic in pics:
            picModel = BuddnistCeremonyCommodityPics(commodity_id=ceremony.id, pic_url=pic, op_status=0)
            picModel.save()

        #修改微站对应展示的佛事封面
        ZizaijiaTempleWebsiteImageTextList.objects.filter(buddnist_ceremony_commodity_id=ceremony.id)\
            .update(pic=pics[0])

        BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=ceremony.id).update(op_status=-1)
        if subdivideStr:
            for j in subdivideStr:
                if j['name'] is None or j['pic'] is None:
                    result['msg'] = '缺少规格参数'
                    result['result'] = -2
                    return HttpResponse(json.dumps(result), content_type="application/json")
                else:
                    subPriceStr = str(j['price']) if j.has_key('price') else None
                    subPrice = -1
                    sub_random_money_list = ""
                    if subPriceStr is not None and "," in subPriceStr:
                        sub_random_money_list = str(subPriceStr)
                    elif subPriceStr is not None:
                        subPrice = float(subPriceStr)
                    sub_is_need_pay = 0 if subPrice <= 0 and sub_random_money_list == "" else 1
                    subtype = 2 if subPrice < 0 and sub_random_money_list != "" else 1
                    subdivideModel = None
                    subEndDate = endDate
                    if j.has_key('endTime') and j['endTime'] != '':
                        subEndDate = datetime.strptime(j['endTime'], "%Y-%m-%d %H:%M:%S")
                    if j.has_key('id'):
                        subdivideModelList = BuddnistCeremonyCommoditySubdivide.objects.filter(id=j['id'])
                        subdivideModel = subdivideModelList[0]
                        subdivideModel.pic_url = j['pic']
                        subdivideModel.price = subPrice
                        subdivideModel.random_money_list = sub_random_money_list
                        subdivideModel.stock = j['stock']
                        subdivideModel.name = j['name']
                        subdivideModel.sort = j['sort']
                        subdivideModel.type = subtype
                        subdivideModel.is_need_pay = sub_is_need_pay
                        subdivideModel.op_status = 0
                        subdivideModel.endTime = subEndDate
                        subdivideModel.explain = j['explain']   
                        subdivideModel.is_auto_finish = j['isAutoFinish']  
                        subdivideModel.subdivide_type = j['subdivide_type']
                        subdivideModel.enroll_num = j['enroll_num'] if j.has_key('enroll_num') else 0
                        subdivideModel.save()
                        zizaijiaSubdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=j['id']).filter(op_status=0)
                        for zizaijiaSubdividePrinter in zizaijiaSubdividePrinterList:
                            zizaijiaSubdividePrinter.op_status = -1
                            zizaijiaSubdividePrinter.save()
                    else:
                        subdivideModel = BuddnistCeremonyCommoditySubdivide(commodity_id=ceremony.id, pic_url=j['pic'], \
                                                                            price=subPrice, stock=j['stock'], endTime=subEndDate,\
                                                                            op_status=0, name=j['name'], sort=j['sort'], \
                                                                            random_money_list=sub_random_money_list, \
                                                                            is_need_pay=sub_is_need_pay, type=subtype,explain=j['explain'],is_auto_finish=j['isAutoFinish'],subdivide_type=j['subdivide_type'])
                        subdivideModel.save()
                        
                    #获取打印机数据列表,格式为{"printer":["printerId":1,"continuousPrint_num":1,"qrcodePrint":1]}
                    if j.has_key('printer'):
                        printerDataList = j['printer']
                        if printerDataList:
                            for printerData in printerDataList:
                                zizaijiaSubdividePrinter = ZizaijiaSubdividePrinter.objects.filter(printer_id=printerData['printerId']).filter(subdivide_id=subdivideModel.id).filter(op_status=0)
                                if len(list(zizaijiaSubdividePrinter)) == 0:
                                    ZizaijiaSubdividePrinter.objects.create(printer_id=printerData['printerId'],subdivide_id=subdivideModel.id,add_time=datetime.now(),update_time=datetime.now(),op_status=0,continuous_print_num=printerData['continuousPrintNum'],qrcode_print=printerData['qrcodePrint'],is_print_mobile=printerData['isPrintMobile'])
                                
                    subpostScript = j['postScript']

                    BuddnistCeremonyCommodityPostscript.objects.filter(commodity_id=ceremony.id, \
                                                                       subdivide_id=subdivideModel.id).update(op_status=-1)
                    if subpostScript:
                        for p in subpostScript:
                            subdateType = p['dataType'] if p.has_key('dataType') else 0
                            if int(p['inputType']) == 1 and p['name'] is None:
                                result['msg'] = '附言文本框需要填写内容'
                                result['result'] = -3
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 2 and p['name'] is None:
                                result['msg'] = '附言时间需要填写日期'
                                result['result'] = -4
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 3 and (p['prompt_text'] is None or p['name'] is None):
                                result['msg'] = '附言下拉框需要填写内容'
                                result['result'] = -5
                                return HttpResponse(json.dumps(result), content_type="application/json")
                            elif int(p['inputType']) == 3:
                                subpostScriptModel = BuddnistCeremonyCommodityPostscript(input_type=p['inputType'], \
                                                                                         name=p['name'], \
                                                                                         is_must=p['is_must'], \
                                                                                         data_change_type=p['dataType'], \
                                                                                         commodity_id=ceremony.id, \
                                                                                         op_status=0, \
                                                                                         font_length=p['font_length'], \
                                                                                         subdivide_id=subdivideModel.id,pic_num=p['pic_num'])
                                subpostScriptModel.save()
                                for select in p['prompt_text']:
                                    subpostScriptSelectModel = BuddnistCeremonyCommodityPostscriptSelectInput( \
                                        pposiscript_id=subpostScriptModel.id, \
                                        name=select, \
                                        op_status=0)
                                    subpostScriptSelectModel.save()

                            elif int(p['inputType']) == 4 and p['name'] is None:
                                result['msg'] = '附言联系人需要填写内容'
                                result['result'] = -6
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 5 and p['name'] is None:
                                result['msg'] = '附言电话号码需要填写内容'
                                result['result'] = -7
                                return HttpResponse(json.dumps(result), content_type="application/json")

                            elif int(p['inputType']) == 6 and p['name'] is None:
                                result['msg'] = '附言地址需要填写内容'
                                result['result'] = -8
                                return HttpResponse(json.dumps(result), content_type="application/json")
                            else:
                                isVerify = p['isVerify'] if p.has_key('isVerify') else 0
                                subpostScriptModel = BuddnistCeremonyCommodityPostscript(input_type=p['inputType'],
                                                                                         name=p['name'],
                                                                                         is_must=p['is_must'],
                                                                                         prompt_text=p['prompt_text'],
                                                                                         data_change_type=subdateType,
                                                                                         commodity_id=ceremony.id,
                                                                                         op_status=0,
                                                                                         font_length=p['font_length'],
                                                                                         subdivide_id=subdivideModel.id,
                                                                                         pic_num=p['pic_num'],isVerify=isVerify)
                                subpostScriptModel.save()

        BuddnistCeremonyCommodityPostscript.objects.filter(commodity_id=ceremony.id, subdivide_id=0).update(op_status=-1)
        if postScript:
            for j in postScript:
                dateType = j['dataType'] if j.has_key('dataType') else 0
                if j['inputType'] == 1 and j['name'] is None:
                    result['msg'] = '附言文本框需要填写内容'
                    result['result'] = -3
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 2 and j['name'] is None:
                    result['msg'] = '附言时间需要填写日期'
                    result['result'] = -4
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 3 and j['prompt_text'] is None and j['name'] is None:
                    result['msg'] = '附言下拉框需要填写内容'
                    result['result'] = -5
                    return HttpResponse(json.dumps(result), content_type="application/json")
                elif j['inputType'] == 3:
                    if j.has_key('id'):
                        postScriptModelList = BuddnistCeremonyCommodityPostscript.objects.filter(id=j['id'])
                        postScriptModel = postScriptModelList[0]
                        postScriptModel.name = j['name']
                        postScriptModel.is_must = j['is_must']
                        postScriptModel.op_status = 0
                        postScriptModel.save()
                        #清除选项再添加
                        BuddnistCeremonyCommodityPostscriptSelectInput.objects.filter(pposiscript_id=postScriptModel.id).update(op_status=-1)
                        for select in j['prompt_text']:
                            postScriptSelectModel = BuddnistCeremonyCommodityPostscriptSelectInput( \
                                pposiscript_id=postScriptModel.id, \
                                name=select, \
                                op_status=0)
                            postScriptSelectModel.save()
                    else:
                        postScriptModel = BuddnistCeremonyCommodityPostscript(input_type=j['inputType'], \
                                                                              name=j['name'], \
                                                                              is_must=j['is_must'], \
                                                                              data_change_type=j['dataType'], \
                                                                              commodity_id=ceremony.id, \
                                                                              font_length=j['font_length'], \
                                                                              op_status=0,pic_num=j['pic_num'],describe=j['describe'])
                        postScriptModel.save()
                        for select in j['prompt_text']:
                            postScriptSelectModel = BuddnistCeremonyCommodityPostscriptSelectInput( \
                                pposiscript_id=postScriptModel.id, \
                                name=select, \
                                op_status=0)
                            postScriptSelectModel.save()

                elif j['inputType'] == 4 and j['name'] is None:
                    result['msg'] = '附言联系人需要填写内容'
                    result['result'] = -6
                    return HttpResponse(json.dumps(result), content_type="application/json")
                elif j['inputType'] == 5 and j['name'] is None:
                    result['msg'] = '附言电话号码需要填写内容'
                    result['result'] = -7
                    return HttpResponse(json.dumps(result), content_type="application/json")

                elif j['inputType'] == 6 and j['name'] is None:
                    result['msg'] = '附言地址需要填写内容'
                    result['result'] = -8
                    return HttpResponse(json.dumps(result), content_type="application/json")
                elif j.has_key('id'):
                    isVerify = j['isVerify'] if j.has_key('isVerify') else 0
                    postScriptModelList = BuddnistCeremonyCommodityPostscript.objects.filter(id=j['id'])
                    postScriptModel = postScriptModelList[0]
                    postScriptModel.input_type = j['inputType']
                    postScriptModel.name = j['name']
                    postScriptModel.is_must = j['is_must']
                    postScriptModel.prompt_text = j['prompt_text']
                    postScriptModel.data_change_type = dateType
                    postScriptModel.op_status = 0
                    postScriptModel.isVerify = isVerify
                    postScriptModel.save()
                else:
                    isVerify = j['isVerify'] if j.has_key('isVerify') else 0
                    postScriptModel = BuddnistCeremonyCommodityPostscript(input_type=j['inputType'], name=j['name'], \
                                                                          is_must=j['is_must'],
                                                                          prompt_text=j['prompt_text'], \
                                                                          data_change_type=dateType,
                                                                          commodity_id=ceremony.id,
                                                                          font_length=j['font_length'], \
                                                                          op_status=0,pic_num=j['pic_num'],describe=j['describe'],
                                                                          isVerify=isVerify)
                    postScriptModel.save()

        result['commodityId'] = ceremony.id
        cList1 = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
                                                                  commodityId=ceremony.id, status__gte=0)
        cList2 = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status__gte=0, type=5)

        if len(cList1) == 0 and len(cList2) > 0 and ceremony.op_status == 1:
            result['createCalendar'] = 1
        else:
            result['createCalendar'] = 0

        cList3 = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status__gte=0, type=3)
        cList4 = ZizaijiaTempleWebsiteImageText.objects.filter(temple_id=templeId,
                                                                   content_type=2,
                                                                   op_status__gte=0)
        cList5 = ZizaijiaTempleWebsiteImageTextList.objects.filter(buddnist_ceremony_commodity_id=ceremony.id,
                                                                   op_status__gte=0)
        if len(cList3) > 0 and len(cList4) > 0 and ceremony.op_status == 1 and len(cList5) == 0:
            result['createImageText'] = 1
        else:
            result['createImageText'] = 0

        result['msg'] = '修改成功'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def editCeremonyType(request):
    user = request.user
    req = json.loads(request.body)
    id = req['id']
    name = req['name']
    shop = BuddnistCeremonyShop.objects.filter(temple_id=user.temple_id)
    result = {}
    if len(shop) <= 0:
        result['msg'] = '没有数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        ceremonyTypeList = BuddnistCeremonyType.objects.filter(id=id)
        ceremonyType = ceremonyTypeList[0]
        ceremonyType.name = name
        ceremonyType.save()
        result['msg'] = '修改成功'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def previewCeremony(request):
    detail = unquote(str(request.POST.get('detail'))).decode('utf8')
    # print detail
    return render_to_response('pages/com.zzj.buddhistService/preview.html', {'code': detail})

@login_required
def addCeremonyCommodity2WebSite(request):
    user = request.user
    req = json.loads(request.body)
    result = {}
    commodityId = req['commodityId']
    calendar = req['calendar'] if req.has_key("calendar") else 0
    imagetext = req['imagetext'] if req.has_key("imagetext") else 0
    startTime = req['startTime']
    endTime = req['endTime']
    templeId = user.temple_id

    commodityModel = BuddnistCeremonyCommodity.objects.get(id=commodityId)

    if calendar == 1:
        cList = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status=0, type=5)
        if len(cList) > 0:
            ca = cList[0]
            d = datetime.strptime(startTime, "%Y-%m-%d")
            end = datetime.strptime(endTime, "%Y-%m-%d")
            delta = timedelta(days=1)
            while d <= end:
                addDate = d.strftime("%Y-%m-%d")
                d += delta
                dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId,
                                                                          calendarId=ca.message_id, \
                                                                          calendarDate=addDate, status=0)
                if len(dayList) == 0:
                    day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=ca.message_id, \
                                                           calendarDate=addDate)
                    day.save()
                title = ""
                tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId, calendarId=ca.message_id, \
                                                                           calendarDate=addDate, title=title,
                                                                           commodityId=commodityId, \
                                                                           status__gte=0)
                if len(tmpList) == 0:
                    calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId, calendarId=ca.message_id, \
                                                                         calendarDate=addDate, title=title,
                                                                         commodityId=commodityId, status=1)
                    calendarListItem.save()

    if imagetext == 1:
        cList = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status=0, type=3)
        if len(cList) > 0:
            for sortModel in cList:
                imagetextModel = ZizaijiaTempleWebsiteImageText.objects.get(id=sortModel.message_id)
                if imagetextModel.content_type == 2 and imagetextModel.show_type == 1:
                    imagetextList = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=imagetextModel.id, op_status__gte=0)
                    for imagetextListModel in imagetextList:
                        # print "imagetextListModel========="+str(imagetextListModel.id)
                        imagetextListModel.sort = F('sort')+1
                        imagetextListModel.save()

                    link_url = 'https://wx.zizaihome.com/commodity/commodityAuth?commodityId='+str(commodityModel.id)
                    if SevericeType == 2:
                        link_url += '&isTest=2'
                    elif SevericeType == 3:
                        link_url += '&isTest=1'
                    pic = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=commodityModel.id, op_status=0).first()

                    ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=commodityModel.id,
                                                                      link_url=link_url,
                                                                      image_text_id=imagetextModel.id,
                                                                      op_status=1, add_time=datetime.now(),
                                                                      update_time=datetime.now(),
                                                                      title=commodityModel.name,
                                                                      sort=1,
                                                                      pic=pic.pic_url,
                                                                      article_id=0)
    result['msg'] = '修改成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")

def xiumihtml(request):
    return render_to_response('pages/com.zzj.buddhistService/xiumi-ue-dialog-v5.html')

@login_required
def getPrinterList(request):
    result = {}
    zizaijiaPrinterList = ZizaijiaPrinter.objects.filter(temple_id=request.user.temple_id)
    zizaijiaPrinterList2 = []
    for zizaijiaPrinter in zizaijiaPrinterList:
        printerMap = {}
        printerMap['id'] = zizaijiaPrinter.id
        printerMap['address'] = zizaijiaPrinter.address
        zizaijiaPrinterList2.append(printerMap)
    result['data'] = zizaijiaPrinterList2
    result['msg'] = '获取成功'
#     if len(zizaijiaPrinterList2) == 0:
#         result['result'] = -1
#         return HttpResponse(json.dumps(result), content_type="application/json")
    result['result'] = 1 
    return HttpResponse(json.dumps(result), content_type="application/json")

def getPrinterStatus(request):
    req = json.loads(request.body)
    result = {}
    printerId = req['printerId']
    printer = ZizaijiaPrinter.objects.filter(id=printerId)
    if len(list(printer)) == 0:
        result['msg'] = '找不到该设备'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    resultData = printerUtil.queryPrinterStatus(printer[0].printer_sn)
    resultDataJSON = json.loads(resultData)
    result['msg'] = resultDataJSON['data']
    if resultDataJSON['ret'] == 0:
        result['result'] = 1
    else:
        result['result'] = -1
    return HttpResponse(json.dumps(result), content_type="application/json")
     
def getNeedPrintOrderNum(request):
#     BuddnistCeremonyCommodityOrder.objects.filter(temple_id=request.user.temple_id).filter(pay_type=1).filter()
#     req = json.loads(request.body)
    result = {}
#     commodityId = req['commodityId']
    commodityId = request.GET.get('commodityId')
    buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    if len(list(buddnistCeremonyCommodity)) == 0:
        result['msg'] = '找不到该佛事'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    buddnistCeremonyCommoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=buddnistCeremonyCommodity[0].id).filter(op_status=0)
    buddnistCeremonyCommodityOrderList = []
    if len(list(buddnistCeremonyCommoditySubdivideList)) > 0:
        subIdList = []
        for buddnistCeremonyCommoditySubdivide in buddnistCeremonyCommoditySubdivideList:
            printer = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=buddnistCeremonyCommoditySubdivide.id).filter(op_status=0)
            if len(list(printer)) > 0:
                subIdList.append(buddnistCeremonyCommoditySubdivide.id)
        subIdListStr = ''
        for subId in subIdList: 
            if subIdListStr == '':
                subIdListStr = subIdListStr+str(subId)
            else:
                subIdListStr = subIdListStr+','+str(subId)
        if subIdListStr != '':
            buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.raw('select * from `buddnist_ceremony_commodity_order` where `subdiride_id` in (%s) and `pay_type` = 1 and `is_print` = 0 and conversion_type = 1'%subIdListStr)
    else:
        if buddnistCeremonyCommodity[0].is_open_printer == 1 and buddnistCeremonyCommodity[0].printer_id != 0:
            buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.filter(commodity_id=buddnistCeremonyCommodity[0].id).filter(is_print=0).filter(pay_type=1).filter(conversion_type=1)
    orderNum = len(list(buddnistCeremonyCommodityOrderList))
    result['orderNum'] = orderNum
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")
        
def printOrder(request):
    result = {}
    commodityId = request.POST.get('commodityId')
    buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    if len(list(buddnistCeremonyCommodity)) == 0:
        result['msg'] = '找不到该佛事'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")
    buddnistCeremonyCommoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=buddnistCeremonyCommodity[0].id).filter(op_status=0)
    if len(list(buddnistCeremonyCommoditySubdivideList)) > 0:
        #遍历规格
        for buddnistCeremonyCommoditySubdivide in buddnistCeremonyCommoditySubdivideList:
            #查询规格绑定的所有打印机
            printerSubdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=buddnistCeremonyCommoditySubdivide.id).filter(op_status=0)
            if len(list(printerSubdividePrinterList)) > 0:
                #查询出该规格的所有订单
                buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.filter(subdiride_id=buddnistCeremonyCommoditySubdivide.id).filter(pay_type=1).filter(is_print=0).filter(conversion_type=1)
                #遍历出该规格的所有订单
                for buddnistCeremonyCommodityOrder in buddnistCeremonyCommodityOrderList:
                    args = [([str(buddnistCeremonyCommodityOrder.id)], None)]
                    poolUtil.runPool(printerUtil.pushPrinter2Zizaihome, args)
#                     requests.get('http://127.0.0.1:11001/zizaihome/printer?commodityOrderId='+str(buddnistCeremonyCommodityOrder.id))
    else:
        buddnistCeremonyCommodityOrderList = BuddnistCeremonyCommodityOrder.objects.filter(commodity_id=buddnistCeremonyCommodity[0].id).filter(is_print=0).filter(pay_type=1).filter(conversion_type=1)
        #遍历订单
        for buddnistCeremonyCommodityOrder in buddnistCeremonyCommodityOrderList:
            args = [([str(buddnistCeremonyCommodityOrder.id)], None)]
            poolUtil.runPool(printerUtil.pushPrinter2Zizaihome, args)
#             requests.get('http://127.0.0.1:11001/zizaihome/printer?commodityOrderId='+str(buddnistCeremonyCommodityOrder.id))
    result['msg'] = '打印成功成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")  

def printAppointOrder(request):
    req = json.loads(request.body)
    result = {}
    orderIdList = req['orderIdList']
    printerIdList = req['printerIdList']
    printNum = req['printNum']
    qrcodePrint = req['qrcodePrint']
    isPrintMobile = req['isPrintMobile']
#     print printerIdList
#     printerIdList = json.loads(printerIdList)
#     orderIdList = json.loads(orderIdList)
    for printerId in printerIdList:
        printer = ZizaijiaPrinter.objects.filter(id=printerId)
        if len(list(printer)) >= 0:
            printer = printer[0]
        for orderId in orderIdList:
            buddnistCeremonyCommodityOrder = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
            if len(list(buddnistCeremonyCommodityOrder)) >= 0:
                buddnistCeremonyCommodityOrder = buddnistCeremonyCommodityOrder[0]
            buddnistCeremonyCommodityOrder.is_print = 1
            buddnistCeremonyCommodityOrder.save()
            buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.filter(id=buddnistCeremonyCommodityOrder.commodity_id)
            if len(list(buddnistCeremonyCommodity)) > 0:
                buddnistCeremonyCommodity = buddnistCeremonyCommodity[0]
            saasUser = WeixinUser.objects.filter(id=buddnistCeremonyCommodityOrder.user_id)
            if len(list(saasUser)) > 0:
                saasUser = saasUser[0]
            buddnistCeremonyCommoditySubdivide = BuddnistCeremonyCommoditySubdivide.objects.filter(id=buddnistCeremonyCommodityOrder.subdiride_id)
            if len(list(buddnistCeremonyCommoditySubdivide)) > 0:
                buddnistCeremonyCommoditySubdivide = buddnistCeremonyCommoditySubdivide[0]
            else:
                buddnistCeremonyCommoditySubdivide = None
            args = [([buddnistCeremonyCommodityOrder, buddnistCeremonyCommodity, saasUser, printer, buddnistCeremonyCommoditySubdivide, int(printNum), int(qrcodePrint),int(isPrintMobile)], None)]
            poolUtil.runPool(printerUtil.printOrder, args)
    result['msg'] = '打印成功成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def templateList(request):
    user = request.user
    result = {}
    templateList = TemplateModel.objects.filter(status=0, type=1).order_by('sort')
    if len(templateList) > 0:
        templateArray = []
        for ceremony in templateList:
            templateMap = {}
            templateMap['name'] = ceremony.name
            templateMap['coverPic'] = ceremony.coverPic
            templateMap['id'] = ceremony.id
            templateArray.append(templateMap)
        result['data'] = templateArray
        result['msg'] = '获取成功'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCeremonyPreTemplate(request):
    user = request.user
    result = {}
    templateId = request.GET.get('templateId')
    templateModel = TemplateModel.objects.get(id=templateId)
    result['data'] = json.loads(templateModel.content)
    result['msg'] = '获取成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")



@login_required
def updateDisposePic(request):
    result = {}
    orderId = int(request.GET.get('id'))
    pic = request.GET.get('pic')

    order = BuddnistCeremonyCommodityOrder.objects.filter(id=orderId)
    if len(list(order)) > 0:
        order[0].dispose_pic_url = pic
        order[0].save()
    result['msg'] = '更新成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def saveCeremonyTemplate(request):
    user = request.user
    result = {}
    req = json.loads(request.body)
    templateId = req['templateId'] if req.has_key('templateId') else 0
    name = req['name'] if req.has_key('name') else ''
    content = req['content'] if req.has_key('content') else ''
    commodityId = req['commodityId'] if req.has_key('commodityId') else 0
    # print name+"--"+content+"----"+str(commodityId)
    ceremonyList = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    if len(ceremonyList) > 0:
        ceremony = ceremonyList[0]
        ceremonyMap = getCeremonyModelUtil(ceremony, 0)
        content = json.dumps(ceremonyMap)
        # print content
        model = TempleTemplateModel(name=name, content=content, type=1, templeId=user.temple_id)
        model.save()
    elif content != '':
        if templateId > 0:
            model = TempleTemplateModel.objects.get(id=templateId)
            model.content = json.dumps(content)
            model.save()
        else:
            model = TempleTemplateModel(name=name, content=json.dumps(content), type=1, templeId=user.temple_id)
            model.save()
    result['msg'] = '保存成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
def getCeremonyTemplate(request):
    result = {}
    templateId = request.GET.get('templateId')
    templateModel = TempleTemplateModel.objects.get(id=templateId)
    result['data'] = json.loads(templateModel.content)
    result['msg'] = '获取成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def delCeremonyTemplate(request):
    result = {}
    req = json.loads(request.body)
    templateId = req['templateId'] if req.has_key('templateId') else 0
    TempleTemplateModel.objects.filter(id=templateId).update(status=-1)
    result['msg'] = '获取成功'
    result['result'] = 0
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCeremonyTemplateList(request):
    user = request.user
    result = {}
    templateList = TempleTemplateModel.objects.filter(status=0, type=1, templeId=user.temple_id).order_by('sort')
    if len(templateList) > 0:
        templateArray = []
        for ceremony in templateList:
            templateMap = {}
            templateMap['name'] = ceremony.name
            templateMap['id'] = ceremony.id
            templateArray.append(templateMap)
        result['data'] = templateArray
        result['msg'] = '获取成功'
        result['result'] = 0
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        result['msg'] = '查找不到数据'
        result['result'] = -1
        return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCommoditySubdivide(request):
    result = {}
    req = json.loads(request.body)
    commodityId = req['commodityId']
    commodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    if len(list(commodity)) > 0:
        commodity = commodity[0]
        commoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=commodity.id,op_status=0).order_by('sort')
        dataMapList = []
        for commoditySubdivide in commoditySubdivideList:
            dataMap = {}
            dataMap['subdivideName'] = commoditySubdivide.name
            dataMap['id'] = commoditySubdivide.id
            dataMapList.append(dataMap)
        result['data'] = dataMapList
        result['msg'] = '成功'
        result['result'] = 1
    else:
        result['msg'] = '参数出错'
        result['result'] = -1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def addAndUpdateCommodity2Printer(request):
    result = {}
    req = json.loads(request.body)
    commodityId = req['commodityId']
    printer_id = req['printerId']
    is_open_printer = req['isOpenPrinter']
    continuous_print_num = req['continuousPrintNum']
    if req.has_key('qrcodePrint'):
        qrcode_print = req['qrcodePrint']
    else:
        qrcode_print = 1
    if req.has_key('isPrintMobile'):
        is_print_mobile = req['isPrintMobile']
    else:
        is_print_mobile = 0    
    subdividePrinter = req['subdividePrinter']
    if subdividePrinter  == '' or len(subdividePrinter) == 0 or subdividePrinter is None:
        commodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
        if len(list(commodity)) > 0:
            commodity = commodity[0]
            commodity.printer_id = printer_id
            commodity.is_open_printer = is_open_printer
            commodity.continuous_print_num = continuous_print_num
            commodity.qrcode_print = qrcode_print
            commodity.is_print_mobile = is_print_mobile
            commodity.save()
    else:
        for subdividePrinterData in subdividePrinter:
            subdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=subdividePrinterData['subdivideId']).filter(op_status=0)
            for subdividePrinter in subdividePrinterList:
                subdividePrinter.op_status = -1
                subdividePrinter.save()
            for printer in subdividePrinterData['printer']:
                print "printer=================="+str(printer)
                zizaijiaPrinter = ZizaijiaPrinter.objects.filter(id=printer['printerId'])
                if len(list(zizaijiaPrinter)) > 0:
                    ZizaijiaSubdividePrinter.objects.create(printer_id=printer['printerId'],subdivide_id=subdividePrinterData['subdivideId'],add_time=datetime.now(),update_time=datetime.now(),op_status=0,continuous_print_num=printer['continuousPrintNum'],qrcode_print=printer['qrcodePrint'],is_print_mobile=printer['isPrintMobile'])
    result['msg'] = '成功'
    result['result'] = 1            
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getCommodityPrinter(request):
    result = {}
    req = json.loads(request.body)
    commodityId = req['commodityId']
    commodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    dataMap = {}
    if len(list(commodity)) > 0:
        commodity = commodity[0]
        dataMap['printerId'] = commodity.printer_id
        dataMap['isOpenPrinter'] = commodity.is_open_printer
        dataMap['continuousPrintNum'] = commodity.continuous_print_num
        dataMap['qrcodePrint'] = commodity.qrcode_print
        dataMap['isPrintMobile'] = commodity.is_print_mobile    
        buddnistCeremonyCommoditySubdivideList = BuddnistCeremonyCommoditySubdivide.objects.filter(commodity_id=commodity.id).filter(op_status=0)
        subdividePrinter = [] 
        for buddnistCeremonyCommoditySubdivide in buddnistCeremonyCommoditySubdivideList:
            subdividePrinterMap = {}
            subdividePrinterMap["subdivideId"] = buddnistCeremonyCommoditySubdivide.id
            printerList = []
            zizaijiaSubdividePrinterList = ZizaijiaSubdividePrinter.objects.filter(subdivide_id=buddnistCeremonyCommoditySubdivide.id).filter(op_status=0)
            for zizaijiaSubdividePrinter in zizaijiaSubdividePrinterList:
                printerMap = {}
                printerMap['printerId'] = zizaijiaSubdividePrinter.printer_id
                printerMap['continuousPrintNum'] = zizaijiaSubdividePrinter.continuous_print_num
                printerMap['qrcodePrint'] = zizaijiaSubdividePrinter.qrcode_print
                printerMap['isPrintMobile'] = zizaijiaSubdividePrinter.is_print_mobile
                printerList.append(printerMap)
            subdividePrinterMap["printer"] = printerList
            subdividePrinter.append(subdividePrinterMap)
        dataMap['subdividePrinter'] = subdividePrinter
        result['data'] = dataMap
        result['msg'] = '成功'
        result['result'] = 1            
        return HttpResponse(json.dumps(result), content_type="application/json")
    result['msg'] = '找不到该佛事'
    result['result'] = -1     
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def endCommodity(request):
    result = {}
    req = json.loads(request.body)
    commodityId = req['commodityId']
    commodity = BuddnistCeremonyCommodity.objects.filter(id=commodityId)
    if len(list(commodity)) > 0:
        commodity = commodity[0]
        billList = ZizaijiaBill.objects.filter(commodity_id=commodityId)
        for bill in billList:
            bill.commodity_end_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" 手动结束佛事"
            bill.save()
        commodity.is_end = 1
        commodity.end_time = datetime.now()
        commodity.save()
    result['msg'] = '成功'
    result['result'] = 1            
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def getPoster(request):
    user = request.user
    templeId = user.temple_id
    temple = Temple.objects.filter(id=templeId).first()

    result = {}
    req = json.loads(request.body)
    commodityId = req['commodityId']
    title = req['title']
    picModel = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=commodityId, op_status=0).first()

    templeName = temple.name
    picUrl = picModel.pic_url
    url = "https://wx.zizaihome.com/commodity/commodityAuth?commodityId="+str(commodityId)

    meClient = MegerImageClient()
    re = meClient.commodityPoster(templeName,title,picUrl,url)

    result['download'] = re['data']
    result['pic'] = re['data']
    result['msg'] = '成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")
