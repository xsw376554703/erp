# coding:utf-8
from datetime import datetime
import json
import re
import time

from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse
from django.shortcuts import render_to_response

from article.models import ZizaijiaArticleType, ZizaijiaArticle
from buddhist.ceremony.models import BuddnistCeremonyCommodity, \
    BuddnistCeremonyCommodityPics, BuddnistCeremonyType, BuddnistCeremonyShop
from temple.models import Temple , ZizaijiaTempleWebsiteImageTextList, \
    ZizaijiaTempleWebsiteSort, ZizaijiaTempleWebsiteAbbot, \
    ZizaijiaTempleWebsiteIntrodaction, ZizaijiaTempleWebsiteIntrodactionPics, \
    ZizaijiaTempleWebsiteMeritBox, ZizaijiaTempleWebsiteImageText, ZizaijiaTempleWebsiteCalendar, \
    ZizaijiaTempleWebsiteCalendarList, ZizaijiaTempleWebsiteCalendarDay, \
    ZizaijiaTempleWebsiteQuickEntry, ZizaijiaTempleWebsiteQuickEntryLink
from charity.models import DailyCharity,DailyCharityFabulous,DailyCharityImg,DailyCharityOpenAuto,\
    DailyCharityOrder,DailyCharitySpec,DailyCharityUser
from __builtin__ import str
from volunteer.models import ZizaijiaTempleActivity
from myerp.settings import SevericeType
from utils.StringUtils import Encryptstr

# 活动管理首页
@login_required
def getTemple(request):
    result = {}
    temple = Temple.objects.get(id=request.user.temple_id)
    print temple.id
    result['temple'] = Temple.toDic(temple)
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取佛事列表
@login_required
def getCeremonyList(request):
    result = {}
    templeId = request.user.temple_id
    pageNumber = request.GET.get('pageNumber')
    imageTextId = request.GET.get('imageTextId', 0)
    if pageNumber is None:
        pageNumber = 0
    if pageNumber == '0' or pageNumber == 0:
        buddnistCeremonyCommodityCnt = BuddnistCeremonyCommodity.objects.raw('select * from `buddnist_ceremony_commodity` where shop_id in(select id from `buddnist_ceremony_shop` where temple_id in(select id from `temple` where id = %d)) and op_status >= 0'%(int(templeId)))
        listCnt = len(list(buddnistCeremonyCommodityCnt))
        listLength = 10
        pageCnt = listCnt%listLength
        if pageCnt > 0:
            pageCnt = int(listCnt/listLength)+1
        result['listCnt'] = listCnt
        result['listLength'] = listLength
        result['pageCnt'] = pageCnt
    else:
        result['listCnt'] = 0
        result['listLength'] = 0
        result['pageCnt'] = 0        
    buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.raw('select * from `buddnist_ceremony_commodity` where shop_id in(select id from `buddnist_ceremony_shop` where temple_id in(select id from `temple` where id = %d)) and op_status >=0 order by add_time desc limit %d,%d'%(int(templeId),int(pageNumber)*10,10))
    buddnistCeremonyCommodityList2 = []
    for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
        buddnistCeremonyCommodityMap = {}
        buddnistCeremonyCommodityPicsList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=buddnistCeremonyCommodity.id).filter(op_status=0)
        buddnistCeremonyCommodityMap['name'] = buddnistCeremonyCommodity.name
        buddnistCeremonyCommodityMap['id'] = buddnistCeremonyCommodity.id
        buddnistCeremonyCommodityMap['isEnd'] = buddnistCeremonyCommodity.is_end
        if imageTextId > 0:
            zizaijiaTempleWebsiteImageTextList = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=imageTextId).filter(buddnist_ceremony_commodity_id=buddnistCeremonyCommodity.id).filter(op_status=0)
            if len(zizaijiaTempleWebsiteImageTextList) > 0:
                buddnistCeremonyCommodityMap['isChoose'] = 1
            else:
                buddnistCeremonyCommodityMap['isChoose'] = 0
        if len(buddnistCeremonyCommodityPicsList) > 0:
            buddnistCeremonyCommodityPics = buddnistCeremonyCommodityPicsList[0]
            buddnistCeremonyCommodityMap['pic'] = buddnistCeremonyCommodityPics.pic_url
        else:
            buddnistCeremonyCommodityMap['pic'] = ''
        progressType = 0
        #未开始
        if buddnistCeremonyCommodity.start_time is not None:
            if (buddnistCeremonyCommodity.start_time-datetime.now()).total_seconds() > 0:
                progressType = 1
            # 进行中
            elif buddnistCeremonyCommodity.is_end == 0:
                progressType = 2
            # 已结束
            elif buddnistCeremonyCommodity.is_end == 1:
                progressType = 3
        #进行中
        elif buddnistCeremonyCommodity.is_end == 0:
            progressType = 2
        #已结束
        elif buddnistCeremonyCommodity.is_end == 1:
            progressType = 3
        #未审核
        elif buddnistCeremonyCommodity.op_status == 1:
            progressType = 4
        buddnistCeremonyCommodityMap['progressType'] = progressType
        buddnistCeremonyCommodityList2.append(buddnistCeremonyCommodityMap)
    if len(buddnistCeremonyCommodityList2) >= 10:
        result['pageNumber'] = int(pageNumber)+1
    else:
        result['pageNumber'] = -1
    result['data'] = buddnistCeremonyCommodityList2
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取佛事类型列表
@login_required
def getCeremonyTypeList(request):
    result = {}
    templeId = request.user.temple_id
    buddnistCeremonyTypeList = BuddnistCeremonyType.objects.raw('select * from `buddnist_ceremony_type` where shop_id in(select id from `buddnist_ceremony_shop` where temple_id in(select id from `temple` where id = %d)) and status = 0 order by add_time'%(int(templeId)))
    buddnistCeremonyTypeList2 = [] 
    allBuddnistCeremonyTypeMap = {}
    allBuddnistCeremonyTypeMap['id'] = 0
    allBuddnistCeremonyTypeMap['sort'] = 0
    allBuddnistCeremonyTypeMap['status'] = 0
    allBuddnistCeremonyTypeMap['update_time'] = time.strftime("%Y-%m-%d %X", time.localtime())
    allBuddnistCeremonyTypeMap['name'] = '全部'
    allBuddnistCeremonyTypeMap['addition'] = 0
    allBuddnistCeremonyTypeMap['shop_id'] = 0
    allBuddnistCeremonyTypeMap['add_time'] = time.strftime("%Y-%m-%d %X", time.localtime())    
    buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.raw('select * from `buddnist_ceremony_commodity` where `shop_id` in (select id from `buddnist_ceremony_shop` where `temple_id`  = %d) and `op_status` = 0  order by is_end,update_time desc limit 10'%(templeId))
    picList = []
    for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
        picMap = {}
        buddnistCeremonyCommodityPicsList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=buddnistCeremonyCommodity.id).filter(op_status=0)
        if len(buddnistCeremonyCommodityPicsList) > 0:
            picMap['title'] = buddnistCeremonyCommodity.name
            picMap['url'] = buddnistCeremonyCommodityPicsList[0].pic_url
            progressType = 0
            #未开始
            if buddnistCeremonyCommodity.start_time is not None:
                if (buddnistCeremonyCommodity.start_time-datetime.now()).total_seconds() > 0:
                    progressType = 1
                # 进行中
                elif buddnistCeremonyCommodity.is_end == 0:
                    progressType = 2
                # 已结束
                elif buddnistCeremonyCommodity.is_end == 1:
                    progressType = 3
            #进行中
            elif buddnistCeremonyCommodity.is_end == 0:
                progressType = 2
            #已结束
            elif buddnistCeremonyCommodity.is_end == 1:
                progressType = 3
            picMap['progressType'] = progressType
            picList.append(picMap)  
    allBuddnistCeremonyTypeMap['pics'] = picList
    buddnistCeremonyTypeList2.append(allBuddnistCeremonyTypeMap)
    for buddnistCeremonyType in buddnistCeremonyTypeList:
        buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.raw('select * from `buddnist_ceremony_commodity` where `commodity_type_id` = %d and `op_status` = 0  order by is_end,update_time desc limit 10'%(buddnistCeremonyType.id))
        picList = []
        for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
            picMap = {}
            buddnistCeremonyCommodityPicsList = BuddnistCeremonyCommodityPics.objects.filter(commodity_id=buddnistCeremonyCommodity.id).filter(op_status=0)
            if len(buddnistCeremonyCommodityPicsList) > 0:
                picMap['title'] = buddnistCeremonyCommodity.name
                picMap['url'] = buddnistCeremonyCommodityPicsList[0].pic_url
                progressType = 0
                #未开始
                if buddnistCeremonyCommodity.start_time is not None:
                    if (buddnistCeremonyCommodity.start_time-datetime.now()).total_seconds() > 0:
                        progressType = 1
                    # 进行中
                    elif buddnistCeremonyCommodity.is_end == 0:
                        progressType = 2
                    # 已结束
                    elif buddnistCeremonyCommodity.is_end == 1:
                        progressType = 3
                #进行中
                elif buddnistCeremonyCommodity.is_end == 0:
                    progressType = 2
                #已结束
                elif buddnistCeremonyCommodity.is_end == 1:
                    progressType = 3
                picMap['progressType'] = progressType
                picList.append(picMap)
        buddnistCeremonyTypeMap = BuddnistCeremonyType.toDic(buddnistCeremonyType)
        buddnistCeremonyTypeMap['pics'] = picList
        buddnistCeremonyTypeList2.append(buddnistCeremonyTypeMap)
    result['data'] = buddnistCeremonyTypeList2
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取文章类型列表
def getArticleTypeList(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    zizaijiaArticleTypeList = ZizaijiaArticleType.objects.filter(temple_id=templeId).filter(op_status=0)
    dataList = []
    dataMap1 = {}
    dataMap1['id'] = 0
    dataMap1['name'] = '全部'
    zizaijiaArticleList1 = ZizaijiaArticle.objects.filter(temple_id=templeId).filter(status=2).order_by('-add_time')[0:10]
    picList1 = []
    for zizaijiaArticle in zizaijiaArticleList1:
        picMap = {}
        picMap['title'] = zizaijiaArticle.title
        picMap['pic'] = zizaijiaArticle.pic
        picList1.append(picMap) 
    dataMap1['picList'] = picList1  
    dataList.append(dataMap1)
    for zizaijiaArticleType in zizaijiaArticleTypeList:
        dataMap = {}
        dataMap['id'] = zizaijiaArticleType.id
        dataMap['name'] = zizaijiaArticleType.name
        zizaijiaArticleList = ZizaijiaArticle.objects.filter(type_id=zizaijiaArticleType.id).filter(status=2).order_by('-add_time')[0:10]
        picList = []
        for zizaijiaArticle in zizaijiaArticleList:
            picMap = {}
            picMap['title'] = zizaijiaArticle.title
            picMap['pic'] = zizaijiaArticle.pic
            picList.append(picMap)
        dataMap['picList'] = picList
        dataList.append(dataMap)
    
    result['data'] = dataList
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取文章列表
def getArticleList(request):
    result = {}
    imageTextId = request.GET.get('imageTextId', 0)
    pageNumber = request.GET.get('pageNumber',0)
    pageSize = request.GET.get('pageSize',10)
    user = request.user
    templeId = user.temple_id
    if pageNumber == '0' or pageNumber == 0:
        listCnt = ZizaijiaArticle.objects.filter(status=2).filter(temple_id=templeId).count()
        listLength = 10
        pageCnt = listCnt%listLength
        if pageCnt > 0:
            pageCnt = int(listCnt/listLength)+1
        result['listCnt'] = listCnt
        result['listLength'] = listLength
        result['pageCnt'] = pageCnt
    else:
        result['listCnt'] = 0
        result['listLength'] = 0
        result['pageCnt'] = 0     
    zizaijiaArticleList = ZizaijiaArticle.objects.filter(status=2).filter(temple_id=templeId).order_by('-add_time')[int(pageNumber)*int(pageSize):int(pageNumber)*int(pageSize)+int(pageSize)]
    dataList = []
    for zizaijiaArticle in zizaijiaArticleList:
        dataMap = {} 
        dataMap['id'] = zizaijiaArticle.id
        dataMap['title'] = zizaijiaArticle.title
        dataMap['pic'] = zizaijiaArticle.pic
        zizaijiaTempleWebsiteImageTextList = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=imageTextId).filter(article_id=zizaijiaArticle.id).filter(op_status=0)
        if len(list(zizaijiaTempleWebsiteImageTextList)) > 0:
            dataMap['isChoose'] = 1
        else:
            dataMap['isChoose'] = 0
        dataList.append(dataMap)
    if len(list(zizaijiaArticleList)) >= int(pageSize):
        result['pageNumber'] = int(pageNumber)+1
    else:
        result['pageNumber'] = -1        
    result['data'] = dataList
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

#获取已经添加的微站组件信息
@login_required
def getWebsiteSubassembly(request):
    result = {}
    templeId = request.user.temple_id
    zizaijiaTempleWebsiteSortList = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId).filter(op_status=0).order_by('sort')
    zizaijiaTempleWebsiteSortList2 = []
    #1寺庙简介组件 2方丈说组件 3图文列表组件 4功德箱组件
    for zizaijiaTempleWebsiteSort in zizaijiaTempleWebsiteSortList:
        zizaijiaTempleWebsiteSortMap = ZizaijiaTempleWebsiteSort.toDic(zizaijiaTempleWebsiteSort)
        if zizaijiaTempleWebsiteSort.type == 1:
            zizaijiaTempleWebsiteIntrodaction = ZizaijiaTempleWebsiteIntrodaction.objects.get(id=zizaijiaTempleWebsiteSort.message_id)
            zizaijiaTempleWebsiteIntrodactionPicsList = ZizaijiaTempleWebsiteIntrodactionPics.objects.filter(introdaction_id=zizaijiaTempleWebsiteIntrodaction.id).filter(op_status=0)
            
            zizaijiaTempleWebsiteIntrodactionMap = ZizaijiaTempleWebsiteIntrodaction.toDic(zizaijiaTempleWebsiteIntrodaction)
            zizaijiaTempleWebsiteIntrodactionPicsList2 = []
            for zizaijiaTempleWebsiteIntrodactionPics in zizaijiaTempleWebsiteIntrodactionPicsList:
                 zizaijiaTempleWebsiteIntrodactionPicsList2.append(ZizaijiaTempleWebsiteIntrodactionPics.toDic(zizaijiaTempleWebsiteIntrodactionPics))
            zizaijiaTempleWebsiteIntrodactionMap['pic'] = zizaijiaTempleWebsiteIntrodactionPicsList2
            
            zizaijiaTempleWebsiteSortMap['message'] = zizaijiaTempleWebsiteIntrodactionMap
            
        elif zizaijiaTempleWebsiteSort.type == 2:
            zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.get(id=zizaijiaTempleWebsiteSort.message_id)
            zizaijiaTempleWebsiteAbbotMap = ZizaijiaTempleWebsiteAbbot.toDic(zizaijiaTempleWebsiteAbbot)
            
            zizaijiaTempleWebsiteSortMap['message'] = zizaijiaTempleWebsiteAbbotMap
            
        elif zizaijiaTempleWebsiteSort.type == 3:
            # print zizaijiaTempleWebsiteSort.message_id
            zizaijiaTempleWebsiteImageText = ZizaijiaTempleWebsiteImageText.objects.get(id=zizaijiaTempleWebsiteSort.message_id)
            
            zizaijiaTempleWebsiteImageTextMap = ZizaijiaTempleWebsiteImageText.toDic(zizaijiaTempleWebsiteImageText)
            
            zizaijiaTempleWebsiteImageTextList1 = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=zizaijiaTempleWebsiteImageText.id).filter(op_status=0).order_by('sort')
            zizaijiaTempleWebsiteImageTextList2 = []
            for zizaijiaTempleWebsiteImageTextList in zizaijiaTempleWebsiteImageTextList1:
                zizaijiaTempleWebsiteImageTextListMap = ZizaijiaTempleWebsiteImageTextList.toDic(zizaijiaTempleWebsiteImageTextList)
                if zizaijiaTempleWebsiteImageText.show_type == 1:
                    buddnistCeremonyCommodity = BuddnistCeremonyCommodity.objects.filter(id=zizaijiaTempleWebsiteImageTextList.buddnist_ceremony_commodity_id)
                    progressType = 0
                    if len(list(buddnistCeremonyCommodity)) > 0:
                        #未开始
                        if buddnistCeremonyCommodity[0].start_time is not None:
                            if (buddnistCeremonyCommodity[0].start_time-datetime.now()).total_seconds() > 0:
                                progressType = 1
                            # 进行中
                            elif buddnistCeremonyCommodity[0].is_end == 0:
                                progressType = 2
                            # 已结束
                            elif buddnistCeremonyCommodity[0].is_end == 1:
                                progressType = 3
                        #进行中
                        elif buddnistCeremonyCommodity[0].is_end == 0:
                            progressType = 2
                        #已结束
                        elif buddnistCeremonyCommodity[0].is_end == 1:
                            progressType = 3
                    zizaijiaTempleWebsiteImageTextListMap['progressType'] = progressType
                zizaijiaTempleWebsiteImageTextList2.append(zizaijiaTempleWebsiteImageTextListMap)
            zizaijiaTempleWebsiteImageTextMap['templeWebsiteImageTextlist'] = zizaijiaTempleWebsiteImageTextList2    
            
            zizaijiaTempleWebsiteSortMap['message'] = zizaijiaTempleWebsiteImageTextMap
            
        elif zizaijiaTempleWebsiteSort.type == 4:
            zizaijiaTempleWebsiteMeritBox = ZizaijiaTempleWebsiteMeritBox.objects.get(id=zizaijiaTempleWebsiteSort.message_id)
            zizaijiaTempleWebsiteMeritBoxMap = ZizaijiaTempleWebsiteMeritBox.toDic(zizaijiaTempleWebsiteMeritBox)
            
            zizaijiaTempleWebsiteSortMap['message'] = zizaijiaTempleWebsiteMeritBoxMap

        elif zizaijiaTempleWebsiteSort.type == 5:
            calendar = ZizaijiaTempleWebsiteCalendar.objects.get(id=zizaijiaTempleWebsiteSort.message_id)
            calendarMap = {}
            calendarMap['calendarId'] = calendar.id
            # date = time.strftime("%Y-%m-%d", time.localtime())
            # calendarDayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(calendarId=calendar.id, \
            #                 calendarDate__gte=date)[0:30]
            # if len(calendarDayList) > 0:
            #     dateList = []
            #     for calendarDay in calendarDayList:
            #         dateList.append(str(calendarDay.calendarDate))
            #     calendarMap['list'] = dateList
            sql1 = 'select * from zizaijia_temple_website_calendar_day where temple_id=' + str(templeId) + \
                   ' and calendarId=' + str(calendar.id) + ' and status=0'
            date = time.strftime("%Y-%m-%d", time.localtime())
            sql1 += " and calendarDate>='" + date + "'"
            sql1 += " order by calendarDate asc"
            sql1 += ' limit 0,5'
            print sql1
            eventdayList = list(ZizaijiaTempleWebsiteCalendarDay.objects.raw(sql1))
            eventDays = []
            if len(eventdayList) > 0:
                for eventday in eventdayList:
                    events = {}
                    events['date'] = str(eventday.calendarDate)
                    sql2 = "select * from zizaijia_temple_website_calendar_list where temple_id=" + str(templeId) + \
                           " and calendarId=" + str(calendar.id) + " and status=0 and calendarDate='" + str(
                        eventday.calendarDate) + "'"
                    eventList = list(ZizaijiaTempleWebsiteCalendar.objects.raw(sql2))
                    eventListArray = []
                    if len(eventList) > 0:
                        for event in eventList:
                            eventMap = {}
                            eventMap['id'] = event.id
                            eventMap['title'] = event.title
                            eventMap['cover_pic'] = event.cover_pic
                            eventMap['commodityId'] = event.commodityId
                            if event.commodityId > 0:
                                commodityList = BuddnistCeremonyCommodity.objects.filter(id=event.commodityId)
                                if len(commodityList) > 0:
                                    commodityPic = BuddnistCeremonyCommodityPics.objects \
                                        .filter(commodity_id=event.commodityId, op_status=0).first()
                                    eventMap['commodityName'] = commodityList[0].name
                                    eventMap['commodityPic'] = commodityPic.pic_url
                                else:
                                    eventMap['commodityName'] = ''
                                    eventMap['commodityPic'] = ''
                            else:
                                eventMap['commodityName'] = ''
                                eventMap['commodityPic'] = ''
                            eventListArray.append(eventMap)
                    events['events'] = eventListArray
                    eventDays.append(events)
            zizaijiaTempleWebsiteSortMap['message'] = eventDays
            total = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId, calendarId=calendar.id,
                                                                    status=0)\
                .filter(calendarDate__gte=date).count()
            zizaijiaTempleWebsiteSortMap['total'] = total
            zizaijiaTempleWebsiteSortMap['pageNumber'] = 1
            
        #快捷入口组件查询
        elif zizaijiaTempleWebsiteSort.type == 6:
            dataMap = {}
            zizaijiaTempleWebsiteQuickEntry = ZizaijiaTempleWebsiteQuickEntry.objects.filter(id=zizaijiaTempleWebsiteSort.message_id)
            if len(list(zizaijiaTempleWebsiteQuickEntry)) > 0:
                zizaijiaTempleWebsiteQuickEntry = zizaijiaTempleWebsiteQuickEntry[0]
                dataMap['id'] = zizaijiaTempleWebsiteQuickEntry.id
                dataMap['title'] = zizaijiaTempleWebsiteQuickEntry.title
                zizaijiaTempleWebsiteQuickEntryLinkList = ZizaijiaTempleWebsiteQuickEntryLink.objects.filter(quick_entry_id = zizaijiaTempleWebsiteQuickEntry.id).filter(op_status=0)
                linkList = []
                for zizaijiaTempleWebsiteQuickEntryLink in zizaijiaTempleWebsiteQuickEntryLinkList:
                    linkMap = {}
                    linkMap['id'] = zizaijiaTempleWebsiteQuickEntryLink.id
                    linkMap['pic'] = zizaijiaTempleWebsiteQuickEntryLink.pic
                    linkMap['name'] = zizaijiaTempleWebsiteQuickEntryLink.name
                    linkMap['link'] = zizaijiaTempleWebsiteQuickEntryLink.link
                    linkMap['type'] = zizaijiaTempleWebsiteQuickEntryLink.type
                    linkMap['quick_entry_id'] = zizaijiaTempleWebsiteQuickEntryLink.quick_entry_id
                    linkMap['link_type'] = zizaijiaTempleWebsiteQuickEntryLink.link_type
                    linkMap['message_id'] = zizaijiaTempleWebsiteQuickEntryLink.message_id
                    linkList.append(linkMap)
                dataMap['linkList'] = linkList
            zizaijiaTempleWebsiteSortMap['message'] = dataMap
        
        zizaijiaTempleWebsiteSortList2.append(zizaijiaTempleWebsiteSortMap)
    result['data'] = zizaijiaTempleWebsiteSortList2
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")


# #添加和更新所有组件
# @login_required
# def updateAndAddSubassembly(request):
#     result = {}
#     subassemblyList = request.POST.get('subassemblyList')
#     templeId = request.user.temple_id
#     subassemblyList = json.loads(subassemblyList)
#     subassemblyIdList = []
#     for subassembly in subassemblyList:
#         #1寺庙简介组件 2方丈说组件 3图文列表组件 4功德箱组件 5佛历
#         messageId = 0
#         if subassembly['type'] == 1:
#             zizaijiaTempleWebsiteIntrodaction = None
#             if subassembly['id'] != 0:
#                 zizaijiaTempleWebsiteIntrodaction = ZizaijiaTempleWebsiteIntrodaction.objects.get(id=subassembly['id'])
#                 zizaijiaTempleWebsiteIntrodaction.province = subassembly['province']
#                 zizaijiaTempleWebsiteIntrodaction.city = subassembly['city']
#                 zizaijiaTempleWebsiteIntrodaction.describe = subassembly['describe']
#                 zizaijiaTempleWebsiteIntrodaction.area = subassembly['area']
#                 zizaijiaTempleWebsiteIntrodaction.save()
#             else:
#                 zizaijiaTempleWebsiteIntrodaction = ZizaijiaTempleWebsiteIntrodaction.objects.create(province=subassembly['province'],city=subassembly['city'],describe=subassembly['describe'],area=subassembly['area'],temple_id=templeId,op_status=0,add_time=datetime.now(),update_time=datetime.now())
#             messageId = zizaijiaTempleWebsiteIntrodaction.id
#             delZizaijiaTempleWebsiteIntrodactionPics = ZizaijiaTempleWebsiteIntrodactionPics.objects.filter(introdaction_id=zizaijiaTempleWebsiteIntrodaction.id).filter(op_status=0)
#             for delPic in delZizaijiaTempleWebsiteIntrodactionPics:
#                 delPic.op_status = -1
#                 delPic.save()
#             for pics in subassembly['pics']:
#                 ZizaijiaTempleWebsiteIntrodactionPics.objects.create(img_url=pics['url'],introdaction_id=zizaijiaTempleWebsiteIntrodaction.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),sort=pics['sort'])
#         elif subassembly['type'] == 2:
#             if subassembly['id'] != 0:
#                 zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.get(id=subassembly['id'])
#                 zizaijiaTempleWebsiteAbbot.img_url = subassembly['img_url']
#                 zizaijiaTempleWebsiteAbbot.religion_name = subassembly['religion_name']
#                 zizaijiaTempleWebsiteAbbot.religion_prorerb = subassembly['religion_prorerb']
#                 zizaijiaTempleWebsiteAbbot.save()
#             else:
#                 zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.create(img_url=subassembly['img_url'],religion_name=subassembly['religion_name'],religion_prorerb=subassembly['religion_prorerb'],temple_id=templeId,add_time=datetime.now(),update_time=datetime.now())
#             messageId = zizaijiaTempleWebsiteAbbot.id
#         elif subassembly['type'] == 3:
#             if subassembly['id'] != 0:
#                 zizaijiaTempleWebsiteImageText = ZizaijiaTempleWebsiteImageText.objects.get(id=subassembly['id'])
#                 zizaijiaTempleWebsiteImageText.content_type = subassembly['content_type']
#                 zizaijiaTempleWebsiteImageText.show_type = subassembly['show_type']
#                 zizaijiaTempleWebsiteImageText.buddnist_ceremony_type_id = subassembly['buddnist_ceremony_type_id']
#                 zizaijiaTempleWebsiteImageText.list_num = subassembly['list_num']
#                 zizaijiaTempleWebsiteImageText.show_list_type = subassembly['show_list_type']
#                 zizaijiaTempleWebsiteImageText.is_show_title = subassembly['is_show_title']
#                 zizaijiaTempleWebsiteImageText.is_show_more = subassembly['is_show_more']
#                 zizaijiaTempleWebsiteImageText.title = subassembly['title']
#                 zizaijiaTempleWebsiteImageText.article_type_id = subassembly['article_type_id']
#                 zizaijiaTempleWebsiteImageText.save()
#                 messageId = subassembly['id']
#             else:
#                 zizaijiaTempleWebsiteImageText = ZizaijiaTempleWebsiteImageText.objects.create(content_type=subassembly['content_type'],show_type=subassembly['show_type'],buddnist_ceremony_type_id=subassembly['buddnist_ceremony_type_id'],list_num=subassembly['list_num'],show_list_type=subassembly['show_list_type'],is_show_title=subassembly['is_show_title'],is_show_more=subassembly['is_show_more'],temple_id=templeId,add_time=datetime.now(),update_time=datetime.now(),op_status=0,title=subassembly['title'],article_type_id=subassembly['article_type_id'])
#                 messageId = zizaijiaTempleWebsiteImageText.id
#             print messageId
#             zizaijiaTempleWebsiteImageTextList1 = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=messageId)
#
#             for zizaijiaTempleWebsiteImageTextList in zizaijiaTempleWebsiteImageTextList1:
#                 zizaijiaTempleWebsiteImageTextList.op_status = -1
#                 zizaijiaTempleWebsiteImageTextList.save()
#
#             for imageTestList in subassembly['imageTestList']:
#                 if imageTestList['commodityId'] != 0:
#                     if SevericeType == 1:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId='+str(imageTestList['commodityId']),image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#                     elif SevericeType == 2:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId='+str(imageTestList['commodityId'])+'&isTest=2',image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#                     elif SevericeType == 3:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId='+str(imageTestList['commodityId'])+'&isTest=1',image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#                 else:
#                     if SevericeType == 1:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/article/articleIndex?articleId='+str(imageTestList['articleId']),image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#                     elif SevericeType == 2:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/article/articleIndex?articleId='+str(imageTestList['articleId'])+'&isTest=2',image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#                     elif SevericeType == 3:
#                         ZizaijiaTempleWebsiteImageTextList.objects.create(buddnist_ceremony_commodity_id=imageTestList['commodityId'],link_url='https://wx.zizaihome.com/article/articleIndex?articleId='+str(imageTestList['articleId'])+'&isTest=1',image_text_id=zizaijiaTempleWebsiteImageText.id,op_status=0,add_time=datetime.now(),update_time=datetime.now(),title=imageTestList['title'],pic=imageTestList['pic'],article_id=imageTestList['articleId'],sort=imageTestList['sort'])
#
#         elif subassembly['type'] == 4:
#             if subassembly['id'] != 0:
#                 zizaijiaTempleWebsiteMeritBox = ZizaijiaTempleWebsiteMeritBox.objects.get(id=subassembly['id'])
#                 zizaijiaTempleWebsiteMeritBox.title = subassembly['title']
#                 zizaijiaTempleWebsiteMeritBox.show_list_num = subassembly['show_list_num']
#                 zizaijiaTempleWebsiteMeritBox.is_show_real_time_list = subassembly['is_show_real_time_list']
#                 zizaijiaTempleWebsiteMeritBox.is_show_month_list = subassembly['is_show_month_list']
#                 zizaijiaTempleWebsiteMeritBox.is_show_total_list = subassembly['is_show_total_list']
#                 zizaijiaTempleWebsiteMeritBox.save()
#             else:
#                 zizaijiaTempleWebsiteMeritBox = ZizaijiaTempleWebsiteMeritBox.objects.create(title=subassembly['title'],show_list_num=subassembly['show_list_num'],add_time=datetime.now(),update_time=datetime.now(),temple_id=templeId,op_status=0,is_show_real_time_list = subassembly['is_show_real_time_list'],is_show_month_list = subassembly['is_show_month_list'],is_show_total_list = subassembly['is_show_total_list'])
#             messageId = zizaijiaTempleWebsiteMeritBox.id
#         elif subassembly['type'] == 5:
#             if int(subassembly['id']) != 0:
#                 if subassembly.has_key('events'):
#                     for event in subassembly['events']:
#                         addDate = event['date']
#                         dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId,
#                                                                                   calendarId=subassembly['id'], \
#                                                                                   calendarDate=addDate, status=0)
#                         if len(dayList) == 0:
#                             day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=subassembly['id'], \
#                                                                    calendarDate=addDate)
#                             day.save()
#                         commodityId = event['commodityId'] if event.has_key('commodityId') else 0
#                         title = event['title'] if commodityId == 0 else ""
#                         # cover_pic = event['cover_pic'] if commodityId == 0 else ""
#                         tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId, calendarId=subassembly['id'], \
#                                                                              calendarDate=addDate, title=title, commodityId=commodityId,\
#                                                                                    status=0)
#                         if len(tmpList) == 0:
#                             calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId, calendarId=subassembly['id'], \
#                                                                                  calendarDate=addDate, title=title,
#                                                                                  # cover_pic=cover_pic,
#                                                                                  commodityId=commodityId)
#                             calendarListItem.save()
#                 messageId = int(subassembly['id'])
#             else:
#                 calendar = ZizaijiaTempleWebsiteCalendar(temple_id=templeId, status=0)
#                 calendar.save()
#                 if subassembly.has_key('events'):
#                     for event in subassembly['events']:
#                         addDate = event['date']
#                         dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId,
#                                                                                   calendarId=calendar.id, \
#                                                                                   calendarDate=addDate, status=0)
#                         if len(dayList) == 0:
#                             day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=calendar.id, \
#                                                                    calendarDate=addDate)
#                             day.save()
#                         commodityId = event['commodityId'] if event.has_key('commodityId') else 0
#                         title = event['title'] if commodityId == 0 else ""
#                         # cover_pic = event['cover_pic'] if commodityId == 0 else ""
#                         tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
#                                                                                    calendarId=calendar.id, \
#                                                                                    calendarDate=addDate, title=title,
#                                                                                    commodityId=commodityId,\
#                                                                                    status=0)
#                         if len(tmpList) == 0:
#                             calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId, calendarId=calendar.id, \
#                                                                                  calendarDate=addDate, title=title,
#                                                                                  # cover_pic=cover_pic,
#                                                                                  commodityId=commodityId)
#                             calendarListItem.save()
#                 messageId = calendar.id
#         #快捷入口组件更新或者添加
#         elif subassembly['type'] == 6:
#             zizaijiaTempleWebsiteQuickEntry = None
#             if subassembly['id'] != 0:
#                 zizaijiaTempleWebsiteQuickEntry = ZizaijiaTempleWebsiteQuickEntry.objects.filter(id=subassembly['id'])
#                 if len(list(zizaijiaTempleWebsiteQuickEntry)) > 0:
#                     zizaijiaTempleWebsiteQuickEntry = zizaijiaTempleWebsiteQuickEntry[0]
#                 zizaijiaTempleWebsiteQuickEntry.title = subassembly['title']
#                 zizaijiaTempleWebsiteQuickEntry.save()
#                 zizaijiaTempleWebsiteQuickEntryLinkList = ZizaijiaTempleWebsiteQuickEntryLink.objects.filter(quick_entry_id=zizaijiaTempleWebsiteQuickEntry.id)
#                 for zizaijiaTempleWebsiteQuickEntryLink in zizaijiaTempleWebsiteQuickEntryLinkList:
#                     zizaijiaTempleWebsiteQuickEntryLink.op_status = -1
#                     zizaijiaTempleWebsiteQuickEntryLink.save()
#             else:
#                 zizaijiaTempleWebsiteQuickEntry = ZizaijiaTempleWebsiteQuickEntry.objects.create(title=subassembly['title'],add_time=datetime.now(),update_time=datetime.now())
#             print zizaijiaTempleWebsiteQuickEntry.id
#             for link1 in subassembly['linkList']:
#                 print link1
#                 ZizaijiaTempleWebsiteQuickEntryLink.objects.create(pic=link1['pic'],name=link1['name'],link=link1['link'],type=link1['type'],add_time=datetime.now(),update_time=datetime.now(),quick_entry_id=zizaijiaTempleWebsiteQuickEntry.id,op_status=0,link_type=link1['linkType'],message_id=link1['messageId'])
#             messageId = zizaijiaTempleWebsiteQuickEntry.id
#
#         if subassembly['sortId'] != 0:
#             # print str(subassembly['sortId'])+'================'
#             zizaijiaTempleWebsiteSort = ZizaijiaTempleWebsiteSort.objects.get(id=subassembly['sortId'])
#             zizaijiaTempleWebsiteSort.sort = subassembly['sort']
#             zizaijiaTempleWebsiteSort.message_id = messageId
#             zizaijiaTempleWebsiteSort.type = subassembly['type']
#             zizaijiaTempleWebsiteSort.save()
#             subassemblyIdList.append(subassembly['sortId'])
#         else:
#             zizaijiaTempleWebsiteSort = ZizaijiaTempleWebsiteSort.objects.create(type=subassembly['type'],message_id=messageId,add_time=datetime.now(),update_time=datetime.now(),op_status=0,temple_id=templeId,sort=subassembly['sort'])
#             subassemblyIdList.append(zizaijiaTempleWebsiteSort.id)
#
#     zizaijiaTempleWebsiteSortList = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId)
#     for zizaijiaTempleWebsiteSort in zizaijiaTempleWebsiteSortList:
#         if zizaijiaTempleWebsiteSort.id not in subassemblyIdList:
#             zizaijiaTempleWebsiteSort.op_status = -1
#             zizaijiaTempleWebsiteSort.save()
#     if SevericeType == 1:
#         result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId='+str(templeId)
#     elif SevericeType == 2:
#         result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId='+str(templeId)+"&isTest=2"
#     elif SevericeType == 3:
#         result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId='+str(templeId)+"&isTest=1"
#     result['msg'] = '保存成功'
#     result['result'] = 1
#     return HttpResponse(json.dumps(result), content_type="application/json")
    
#跳转到寺庙微站创建页


# 添加和更新所有组件
@login_required
def updateAndAddSubassembly(request):
    result = {}
    subassembly = request.POST.get('subassembly')
    templeId = request.user.temple_id
    subassembly = json.loads(subassembly)
    # subassemblyIdList = []
    # for subassembly in subassemblyList:
    # 1寺庙简介组件 2方丈说组件 3图文列表组件 4功德箱组件 5佛历
    messageId = 0
    if subassembly['type'] == 1:
        zizaijiaTempleWebsiteIntrodaction = None
        if subassembly['id'] != 0:
            zizaijiaTempleWebsiteIntrodaction = ZizaijiaTempleWebsiteIntrodaction.objects.get(id=subassembly['id'])
            zizaijiaTempleWebsiteIntrodaction.province = subassembly['province']
            zizaijiaTempleWebsiteIntrodaction.city = subassembly['city']
            zizaijiaTempleWebsiteIntrodaction.describe = subassembly['describe']
            zizaijiaTempleWebsiteIntrodaction.area = subassembly['area']
            zizaijiaTempleWebsiteIntrodaction.save()
        else:
            zizaijiaTempleWebsiteIntrodaction = ZizaijiaTempleWebsiteIntrodaction.objects.create(
                province=subassembly['province'], city=subassembly['city'], describe=subassembly['describe'],
                area=subassembly['area'], temple_id=templeId, op_status=0, add_time=datetime.now(),
                update_time=datetime.now())
        messageId = zizaijiaTempleWebsiteIntrodaction.id
        delZizaijiaTempleWebsiteIntrodactionPics = ZizaijiaTempleWebsiteIntrodactionPics.objects.filter(
            introdaction_id=zizaijiaTempleWebsiteIntrodaction.id).filter(op_status=0)
        delZizaijiaTempleWebsiteIntrodactionPics.update(op_status=-1)
        # for delPic in delZizaijiaTempleWebsiteIntrodactionPics:
        #     delPic.op_status = -1
        #     delPic.save()
        for pics in subassembly['pics']:
            ZizaijiaTempleWebsiteIntrodactionPics.objects.create(img_url=pics['url'],
                                                                 introdaction_id=zizaijiaTempleWebsiteIntrodaction.id,
                                                                 op_status=0, add_time=datetime.now(),
                                                                 update_time=datetime.now(), sort=pics['sort'])
    elif subassembly['type'] == 2:
        if subassembly['id'] != 0:
            zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.get(id=subassembly['id'])
            zizaijiaTempleWebsiteAbbot.img_url = subassembly['img_url']
            zizaijiaTempleWebsiteAbbot.religion_name = subassembly['religion_name']
            zizaijiaTempleWebsiteAbbot.religion_prorerb = subassembly['religion_prorerb']
            zizaijiaTempleWebsiteAbbot.save()
        else:
            zizaijiaTempleWebsiteAbbot = ZizaijiaTempleWebsiteAbbot.objects.create(img_url=subassembly['img_url'],
                                                                                   religion_name=subassembly[
                                                                                       'religion_name'],
                                                                                   religion_prorerb=subassembly[
                                                                                       'religion_prorerb'],
                                                                                   temple_id=templeId,
                                                                                   add_time=datetime.now(),
                                                                                   update_time=datetime.now())
        messageId = zizaijiaTempleWebsiteAbbot.id
    elif subassembly['type'] == 3:
        if subassembly['id'] != 0:
            zizaijiaTempleWebsiteImageText = ZizaijiaTempleWebsiteImageText.objects.get(id=subassembly['id'])
            zizaijiaTempleWebsiteImageText.content_type = subassembly['content_type']
            zizaijiaTempleWebsiteImageText.show_type = subassembly['show_type']
            zizaijiaTempleWebsiteImageText.buddnist_ceremony_type_id = subassembly['buddnist_ceremony_type_id']
            zizaijiaTempleWebsiteImageText.list_num = subassembly['list_num']
            zizaijiaTempleWebsiteImageText.show_list_type = subassembly['show_list_type']
            zizaijiaTempleWebsiteImageText.is_show_title = subassembly['is_show_title']
            zizaijiaTempleWebsiteImageText.is_show_more = subassembly['is_show_more']
            zizaijiaTempleWebsiteImageText.title = subassembly['title']
            zizaijiaTempleWebsiteImageText.article_type_id = subassembly['article_type_id']
            zizaijiaTempleWebsiteImageText.save()
            messageId = subassembly['id']
        else:
            zizaijiaTempleWebsiteImageText = ZizaijiaTempleWebsiteImageText.objects.create(
                content_type=subassembly['content_type'], show_type=subassembly['show_type'],
                buddnist_ceremony_type_id=subassembly['buddnist_ceremony_type_id'], list_num=subassembly['list_num'],
                show_list_type=subassembly['show_list_type'], is_show_title=subassembly['is_show_title'],
                is_show_more=subassembly['is_show_more'], temple_id=templeId, add_time=datetime.now(),
                update_time=datetime.now(), op_status=0, title=subassembly['title'],
                article_type_id=subassembly['article_type_id'])
            messageId = zizaijiaTempleWebsiteImageText.id
        print messageId
        #zizaijiaTempleWebsiteImageTextList1 = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=messageId)

        zizaijiaTempleWebsiteImageTextList1 = ZizaijiaTempleWebsiteImageTextList.objects.filter(image_text_id=messageId,op_status=0).update(op_status=-1)

        # for zizaijiaTempleWebsiteImageTextList in zizaijiaTempleWebsiteImageTextList1:
        #     zizaijiaTempleWebsiteImageTextList.op_status = -1
        #     zizaijiaTempleWebsiteImageTextList.save()

        for imageTestList in subassembly['imageTestList']:
            if imageTestList['commodityId'] != 0:
                if SevericeType == 1:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId=' + str(
                            imageTestList['commodityId']), image_text_id=zizaijiaTempleWebsiteImageText.id, op_status=0,
                        add_time=datetime.now(), update_time=datetime.now(), title=imageTestList['title'],
                        pic=imageTestList['pic'], article_id=imageTestList['articleId'], sort=imageTestList['sort'])
                elif SevericeType == 2:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId=' + str(
                            imageTestList['commodityId']) + '&isTest=2',
                        image_text_id=zizaijiaTempleWebsiteImageText.id, op_status=0, add_time=datetime.now(),
                        update_time=datetime.now(), title=imageTestList['title'], pic=imageTestList['pic'],
                        article_id=imageTestList['articleId'], sort=imageTestList['sort'])
                elif SevericeType == 3:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/commodity/commodityAuth?commodityId=' + str(
                            imageTestList['commodityId']) + '&isTest=1',
                        image_text_id=zizaijiaTempleWebsiteImageText.id, op_status=0, add_time=datetime.now(),
                        update_time=datetime.now(), title=imageTestList['title'], pic=imageTestList['pic'],
                        article_id=imageTestList['articleId'], sort=imageTestList['sort'])
            else:
                if SevericeType == 1:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/article/articleIndex?articleId=' + str(
                            imageTestList['articleId']), image_text_id=zizaijiaTempleWebsiteImageText.id, op_status=0,
                        add_time=datetime.now(), update_time=datetime.now(), title=imageTestList['title'],
                        pic=imageTestList['pic'], article_id=imageTestList['articleId'], sort=imageTestList['sort'])
                elif SevericeType == 2:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/article/articleIndex?articleId=' + str(
                            imageTestList['articleId']) + '&isTest=2', image_text_id=zizaijiaTempleWebsiteImageText.id,
                        op_status=0, add_time=datetime.now(), update_time=datetime.now(), title=imageTestList['title'],
                        pic=imageTestList['pic'], article_id=imageTestList['articleId'], sort=imageTestList['sort'])
                elif SevericeType == 3:
                    ZizaijiaTempleWebsiteImageTextList.objects.create(
                        buddnist_ceremony_commodity_id=imageTestList['commodityId'],
                        link_url='https://wx.zizaihome.com/article/articleIndex?articleId=' + str(
                            imageTestList['articleId']) + '&isTest=1', image_text_id=zizaijiaTempleWebsiteImageText.id,
                        op_status=0, add_time=datetime.now(), update_time=datetime.now(), title=imageTestList['title'],
                        pic=imageTestList['pic'], article_id=imageTestList['articleId'], sort=imageTestList['sort'])

    elif subassembly['type'] == 4:
        if subassembly['id'] != 0:
            zizaijiaTempleWebsiteMeritBox = ZizaijiaTempleWebsiteMeritBox.objects.get(id=subassembly['id'])
            zizaijiaTempleWebsiteMeritBox.title = subassembly['title']
            zizaijiaTempleWebsiteMeritBox.show_list_num = subassembly['show_list_num']
            zizaijiaTempleWebsiteMeritBox.is_show_real_time_list = subassembly['is_show_real_time_list']
            zizaijiaTempleWebsiteMeritBox.is_show_month_list = subassembly['is_show_month_list']
            zizaijiaTempleWebsiteMeritBox.is_show_total_list = subassembly['is_show_total_list']
            zizaijiaTempleWebsiteMeritBox.save()
        else:
            zizaijiaTempleWebsiteMeritBox = ZizaijiaTempleWebsiteMeritBox.objects.create(title=subassembly['title'],
                                                                                         show_list_num=subassembly[
                                                                                             'show_list_num'],
                                                                                         add_time=datetime.now(),
                                                                                         update_time=datetime.now(),
                                                                                         temple_id=templeId,
                                                                                         op_status=0,
                                                                                         is_show_real_time_list=
                                                                                         subassembly[
                                                                                             'is_show_real_time_list'],
                                                                                         is_show_month_list=subassembly[
                                                                                             'is_show_month_list'],
                                                                                         is_show_total_list=subassembly[
                                                                                             'is_show_total_list'])
        messageId = zizaijiaTempleWebsiteMeritBox.id
    elif subassembly['type'] == 5:
        if int(subassembly['id']) != 0:
            if subassembly.has_key('events'):
                for event in subassembly['events']:
                    addDate = event['date']
                    dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId,
                                                                              calendarId=subassembly['id'], \
                                                                              calendarDate=addDate, status=0)
                    if len(dayList) == 0:
                        day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=subassembly['id'], \
                                                               calendarDate=addDate)
                        day.save()
                    commodityId = event['commodityId'] if event.has_key('commodityId') else 0
                    title = event['title'] if commodityId == 0 else ""
                    # cover_pic = event['cover_pic'] if commodityId == 0 else ""
                    tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
                                                                               calendarId=subassembly['id'], \
                                                                               calendarDate=addDate, title=title,
                                                                               commodityId=commodityId, \
                                                                               status=0)
                    if len(tmpList) == 0:
                        calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId,
                                                                             calendarId=subassembly['id'], \
                                                                             calendarDate=addDate, title=title,
                                                                             # cover_pic=cover_pic,
                                                                             commodityId=commodityId)
                        calendarListItem.save()
            messageId = int(subassembly['id'])
        else:
            calendar = ZizaijiaTempleWebsiteCalendar(temple_id=templeId, status=0)
            calendar.save()
            if subassembly.has_key('events'):
                for event in subassembly['events']:
                    addDate = event['date']
                    dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId,
                                                                              calendarId=calendar.id, \
                                                                              calendarDate=addDate, status=0)
                    if len(dayList) == 0:
                        day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=calendar.id, \
                                                               calendarDate=addDate)
                        day.save()
                    commodityId = event['commodityId'] if event.has_key('commodityId') else 0
                    title = event['title'] if commodityId == 0 else ""
                    # cover_pic = event['cover_pic'] if commodityId == 0 else ""
                    tmpList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId,
                                                                               calendarId=calendar.id, \
                                                                               calendarDate=addDate, title=title,
                                                                               commodityId=commodityId, \
                                                                               status=0)
                    if len(tmpList) == 0:
                        calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId, calendarId=calendar.id, \
                                                                             calendarDate=addDate, title=title,
                                                                             # cover_pic=cover_pic,
                                                                             commodityId=commodityId)
                        calendarListItem.save()
            messageId = calendar.id
    # 快捷入口组件更新或者添加
    elif subassembly['type'] == 6:
        zizaijiaTempleWebsiteQuickEntry = None
        if subassembly['id'] != 0:
            zizaijiaTempleWebsiteQuickEntry = ZizaijiaTempleWebsiteQuickEntry.objects.filter(id=subassembly['id'])
            if len(list(zizaijiaTempleWebsiteQuickEntry)) > 0:
                zizaijiaTempleWebsiteQuickEntry = zizaijiaTempleWebsiteQuickEntry[0]
            zizaijiaTempleWebsiteQuickEntry.title = subassembly['title']
            zizaijiaTempleWebsiteQuickEntry.save()
            zizaijiaTempleWebsiteQuickEntryLinkList = ZizaijiaTempleWebsiteQuickEntryLink.objects.filter(
                quick_entry_id=zizaijiaTempleWebsiteQuickEntry.id,op_status=0).update(op_status=-1)
            # for zizaijiaTempleWebsiteQuickEntryLink in zizaijiaTempleWebsiteQuickEntryLinkList:
            #     zizaijiaTempleWebsiteQuickEntryLink.op_status = -1
            #     zizaijiaTempleWebsiteQuickEntryLink.save()
        else:
            zizaijiaTempleWebsiteQuickEntry = ZizaijiaTempleWebsiteQuickEntry.objects.create(title=subassembly['title'],
                                                                                             add_time=datetime.now(),
                                                                                             update_time=datetime.now())
        print zizaijiaTempleWebsiteQuickEntry.id
        for link1 in subassembly['linkList']:
            print link1
            ZizaijiaTempleWebsiteQuickEntryLink.objects.create(pic=link1['pic'], name=link1['name'], link=link1['link'],
                                                               type=link1['type'], add_time=datetime.now(),
                                                               update_time=datetime.now(),
                                                               quick_entry_id=zizaijiaTempleWebsiteQuickEntry.id,
                                                               op_status=0, link_type=link1['linkType'],
                                                               message_id=link1['messageId'])
        messageId = zizaijiaTempleWebsiteQuickEntry.id

    sortId = subassembly['sortId']
    # 新建组件
    if sortId < 1:
        # 调整顺序
        zizaijiaTempleWebsiteSortList = ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId, op_status=0)
        for sortModel in zizaijiaTempleWebsiteSortList:
            sortNum = sortModel.sort
            if sortNum >= subassembly['sort']:
                sortModel.sort = sortNum + 1
                sortModel.save()
        zizaijiaTempleWebsiteSort = ZizaijiaTempleWebsiteSort.objects.create(type=subassembly['type'],
                                                                             message_id=messageId,
                                                                             add_time=datetime.now(),
                                                                             update_time=datetime.now(), op_status=0,
                                                                             temple_id=templeId,
                                                                             sort=subassembly['sort'])
    if SevericeType == 1:
        result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId=' + str(templeId)
    elif SevericeType == 2:
        result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId=' + str(
            templeId) + "&isTest=2"
    elif SevericeType == 3:
        result['templeWebsiteUrl'] = 'https://wx.zizaihome.com/commodity/templateWebsiteInfo?templeId=' + str(
            templeId) + "&isTest=1"
    result['msg'] = '保存成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

#删除组件
@login_required
def delSubassembly(request):
    result = {}
    templeId = request.user.temple_id
    #req = json.loads(request.body)
    websiteSortId= request.GET.get('sortId')
    #websiteSortId=req["sortId"]
    num=0
    zizaijiaTempleWebsiteSort=ZizaijiaTempleWebsiteSort.objects.filter(id=int(websiteSortId))
    if len(zizaijiaTempleWebsiteSort)>0 :
        for wSort in  zizaijiaTempleWebsiteSort:
            wSort.op_status=-1
            num=wSort.sort
            wSort.save()
    # zizaijiaTempleWebsiteSort.op_status=-1
    # zizaijiaTempleWebsiteSort.save()
    zizaijiaTempleWebsiteSortList=ZizaijiaTempleWebsiteSort.objects.filter(temple_id=templeId,op_status=0)
    for sortModel in zizaijiaTempleWebsiteSortList :
        sortNum=int(sortModel.sort)
        if sortNum>num :
            sortModel.sort=sortNum-1
            sortModel.save()
    result['msg']='成功'
    result['result']=1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def temple_index(request):
    return render_to_response('temple/index.html')

@login_required
def createCalendar(request):
    templeId = request.user.temple_id
    calendar = ZizaijiaTempleWebsiteCalendar(temple_id=templeId, status=0)
    calendar.save()
    result = {}
    result['calendarId'] = calendar.id
    result['msg'] = '创建成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def addCalendarEvent(request):
    result = {}
    templeId = request.user.temple_id
    calendarEvent = request.POST.get('calendarEvent', None)
    if calendarEvent is not None:
        calendarId = calendarEvent['calendarId']
        if calendarEvent.has_key('events'):
            for event in calendarEvent['events']:
                addDate = event['date']
                dayList = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId, calendarId=calendarId, \
                                                                calendarDate=addDate, status=0)
                if len(dayList) == 0:
                    day = ZizaijiaTempleWebsiteCalendarDay(temple_id=templeId, calendarId=calendarId, \
                                                                calendarDate=addDate)
                    day.save()
                commodityId = event['commodityId'] if event.has_key('commodityId') else 0
                title = event['title'] if commodityId == 0 else ""
                # cover_pic = event['cover_pic'] if commodityId == 0 else ""
                calendarListItem = ZizaijiaTempleWebsiteCalendarList(temple_id=templeId, calendarId=calendarId, \
                                    calendarDate=addDate, title=title,
                                                                     # cover_pic=cover_pic,
                                    commodityId=commodityId)
                calendarListItem.save()
    result['msg'] = '保存成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def delCalendar(request):
    templeId = request.user.temple_id
    calendarId = request.POST.get('calendarId', 0)
    ZizaijiaTempleWebsiteCalendar.objects.filter(temple_id=templeId, id=calendarId).update(status=-1)
    result = {}
    result['msg'] = '删除成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def delCalendarEvent(request):
    templeId = request.user.temple_id
    calendarId = request.POST.get('calendarId', 0)
    eventId = request.POST.get('eventId', 0)
    eventDate = request.POST.get('eventDate', '')
    ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId, id=eventId, calendarId=calendarId)\
                            .update(status=-1)
    dayList = ZizaijiaTempleWebsiteCalendarList.objects.filter(temple_id=templeId, calendarId=calendarId, \
                                                              calendarDate=eventDate, status=0)
    if len(dayList) == 0:
        ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId, calendarDate=eventDate, calendarId=calendarId) \
            .update(status=-1)
    result = {}
    result['msg'] = '删除成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def calendarEventList(request):
    templeId = request.user.temple_id
    dateList = request.GET.get('dateList', '')
    calendarId = request.GET.get('calendarId', '')
    pageNumber = request.GET.get('pageNumber', 0)
    pageSize = request.GET.get('pageSize', 5)
    result = {}
    date = time.strftime("%Y-%m-%d", time.localtime())
    sql1 = 'select * from zizaijia_temple_website_calendar_day where temple_id='+ str(templeId)+ \
           ' and calendarId=' + str(calendarId) + ' and status=0'
    if dateList != '':
        dates = " and calendarDate in ( "
        for date in str(dateList).split(','):
            dates += "'" + date + "',"
        dates = dates[0:-1]
        dates += ")"
        sql1 += dates
    else:
        sql1 += " and calendarDate>='" + date + "'"
    total = ZizaijiaTempleWebsiteCalendarDay.objects.filter(temple_id=templeId, calendarId=calendarId, status=0) \
        .filter(calendarDate__gte=date).count()
    sql1 += " order by calendarDate asc"
    sql1 += ' limit '+str(int(pageNumber)*int(pageSize))+','+str(pageSize)
    print sql1
    eventdayList = list(ZizaijiaTempleWebsiteCalendarDay.objects.raw(sql1))
    if len(eventdayList) > 0:
        eventDays = []
        for eventday in eventdayList:
            events = {}
            events['date'] = str(eventday.calendarDate)
            sql2 = "select * from zizaijia_temple_website_calendar_list where temple_id="+ str(templeId)+\
                  " and calendarId="+str(calendarId) + " and status=0 and calendarDate='"+str(eventday.calendarDate)+"'"
            eventList = list(ZizaijiaTempleWebsiteCalendar.objects.raw(sql2))
            eventListArray = []
            if len(eventList) > 0:
                for event in eventList:
                    eventMap = {}
                    eventMap['id'] = event.id
                    eventMap['title'] = event.title
                    eventMap['cover_pic'] = event.cover_pic
                    eventMap['commodityId'] = event.commodityId
                    if event.commodityId > 0:
                        commodityList = BuddnistCeremonyCommodity.objects.filter(id=event.commodityId)
                        if len(commodityList) > 0:
                            commodityPic = BuddnistCeremonyCommodityPics.objects\
                                .filter(commodity_id=event.commodityId, op_status=0).first()
                            eventMap['commodityName'] = commodityList[0].name
                            eventMap['commodityPic'] = commodityPic.pic_url
                        else:
                            eventMap['commodityName'] = ''
                            eventMap['commodityPic'] = ''
                    else:
                        eventMap['commodityName'] = ''
                        eventMap['commodityPic'] = ''
                    eventListArray.append(eventMap)
            events['events'] = eventListArray
            eventDays.append(events)
        result['list'] = eventDays
        if len(eventdayList) >= int(pageSize):
            result['pageNumber'] = int(pageNumber)+1
        else:
            result['pageNumber'] = -1
    result['total'] = total
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

# @login_required
def getQuickEntryTypeList(request):
    result = {}
    templeId = request.user.temple_id
    dataList = []
    dataMap1 = {}
    dataMap1['name'] = '佛事日历'
    zizaijiaTempleWebsiteSort = ZizaijiaTempleWebsiteSort.objects.filter(type=5).filter(op_status=0).filter(temple_id=templeId)
    if len(list(zizaijiaTempleWebsiteSort)) > 0:
        zizaijiaTempleWebsiteSort = zizaijiaTempleWebsiteSort[0]
        if SevericeType == 1:
            dataMap1['url'] = 'http://wx.zizaihome.com/website/calendar?templeId='+str(templeId)+'&componentId='+str(zizaijiaTempleWebsiteSort.message_id)
        elif SevericeType == 2:
            dataMap1['url'] = 'http://test2.zizaihome.com/website/calendar?templeId='+str(templeId)+'&componentId='+str(zizaijiaTempleWebsiteSort.message_id)
        elif SevericeType == 3:
            dataMap1['url'] = 'http://test.zizaihome.com/website/calendar?templeId='+str(templeId)+'&componentId='+str(zizaijiaTempleWebsiteSort.message_id)
    else:
       dataMap1['url'] = '' 
    dataMap1['link_type'] = 1
    dataMap1LinkList = []
    dataMap1['linkList'] = dataMap1LinkList
    dataList.append(dataMap1)
    dataMap2 = {}
    dataMap2['name'] = '佛事'
    dataMap2['url'] = ''
    dataMap2['link_type'] = 2
    buddnistCeremonyShop = BuddnistCeremonyShop.objects.filter(temple_id=templeId)[0]
    buddnistCeremonyCommodityList = BuddnistCeremonyCommodity.objects.filter(shop_id=buddnistCeremonyShop.id).filter(op_status=0).filter(is_end=0).order_by('-add_time')
    dataMap2LinkList = []
    for buddnistCeremonyCommodity in buddnistCeremonyCommodityList:
        linkMap = {}
        linkMap['message_id'] = buddnistCeremonyCommodity.id
        linkMap['name'] = buddnistCeremonyCommodity.name
        if SevericeType == 1:
            linkMap['url'] = 'http://wx.zizaihome.com/commodity/commodityAuth?commodityId='+str(buddnistCeremonyCommodity.id)
        elif SevericeType == 2:
            linkMap['url'] = 'http://test2.zizaihome.com/commodity/commodityAuth?commodityId='+str(buddnistCeremonyCommodity.id)+'&isTest=2'
        elif SevericeType == 3:
            linkMap['url'] = 'http://test.zizaihome.com/commodity/commodityAuth?commodityId='+str(buddnistCeremonyCommodity.id)+'&isTest=1'
        dataMap2LinkList.append(linkMap)
    dataMap2['linkList'] = dataMap2LinkList
    dataList.append(dataMap2)
    dataMap3 = {}
    dataMap3['name'] = '义工'
    dataMap3['url'] = ''
    dataMap3['link_type'] = 3
    zizaijiaTempleActivityList = ZizaijiaTempleActivity.objects.filter(temple_id=templeId).order_by('-add_time')
    dataMap3LinkList = []
    for zizaijiaTempleActivity in zizaijiaTempleActivityList:
        linkMap = {}
        linkMap['message_id'] = zizaijiaTempleActivity.id
        linkMap['name'] = zizaijiaTempleActivity.activity_name
        if SevericeType == 1:
            linkMap['url'] = 'http://wx.zizaihome.com/yg?templeId='+str(templeId)+'&activityId='+str(zizaijiaTempleActivity.id)
        elif SevericeType == 2:
            linkMap['url'] = 'http://test2.zizaihome.com/yg?templeId='+str(templeId)+'&activityId='+str(zizaijiaTempleActivity.id)+'&isTest=2'
        elif SevericeType == 3:
            linkMap['url'] = 'http://test.zizaihome.com/yg?templeId='+str(templeId)+'&activityId='+str(zizaijiaTempleActivity.id)+'&isTest=1'
        dataMap3LinkList.append(linkMap)
    dataMap3['linkList'] = dataMap3LinkList
    dataList.append(dataMap3)
    dataMap4 = {}
    dataMap4['name'] = '功德箱'
    if SevericeType == 1:
        dataMap4['url'] = 'http://wx.zizaihome.com/commodity/meritBoxAuth?templeId='+str(templeId)
    elif SevericeType == 2:
        dataMap4['url'] = 'http://test2.zizaihome.com/commodity/meritBoxAuth?templeId='+str(templeId)+'&isTest=2'
    elif SevericeType == 3:
        dataMap4['url'] = 'http://test.zizaihome.com/commodity/meritBoxAuth?templeId='+str(templeId)+'&isTest=1'
    dataMap4['link_type'] = 4
    dataMap4LinkList = []
    dataMap4['linkList'] = dataMap4LinkList
    dataList.append(dataMap4)
    dataMap5 = {}
    dataMap5['name'] = '文章'
    dataMap5['url'] = ''
    dataMap5['link_type'] = 5
    dataMap5LinkList = []
    zizaijiaArticleList = ZizaijiaArticle.objects.filter(temple_id=templeId).filter(status=2).order_by('-add_time')
    for zizaijiaArticle in zizaijiaArticleList:
        linkMap = {}
        linkMap['message_id'] = zizaijiaArticle.id
        linkMap['name'] = zizaijiaArticle.title
        if SevericeType == 1:
            linkMap['url'] = 'http://wx.zizaihome.com/article/articleIndex?articleId='+str(zizaijiaArticle.id)
        elif SevericeType == 2:
            linkMap['url'] = 'http://test2.zizaihome.com/article/articleIndex?articleId='+str(zizaijiaArticle.id)+'&isTest=2'
        elif SevericeType == 3:
            linkMap['url'] = 'http://test.zizaihome.com/article/articleIndex?articleId='+str(zizaijiaArticle.id)+'&isTest=1'
        dataMap5LinkList.append(linkMap)        
    dataMap5['linkList'] = dataMap5LinkList    
    dataList.append(dataMap5) 
    dataMap6 = {}
    dataMap6['name'] = '微供奉'
    if SevericeType == 1:
        dataMap6['url'] = 'http://wx.zizaihome.com/buddhaWall/buddhaWallIndex?templeId='+Encryptstr.encrypt(str(templeId))
    elif SevericeType == 2:
        dataMap6['url'] = 'http://test2.zizaihome.com/buddhaWall/buddhaWallIndex?templeId='+Encryptstr.encrypt(str(templeId))+'&isTest=2'
    elif SevericeType == 3:
        dataMap6['url'] = 'http://test.zizaihome.com/buddhaWall/buddhaWallIndex?templeId='+Encryptstr.encrypt(str(templeId))+'&isTest=1'
    dataMap6['link_type'] = 6
    dataMap6LinkList = []
    dataMap6['linkList'] = dataMap6LinkList    
    dataList.append(dataMap6)
    dataMap7 = {}
    dataMap7['name'] = '日行一善'
    charityList = DailyCharity.objects.filter(templeId=templeId, opStatus=0)
    dataMap7LinkList = []
    for charity in charityList:
        linkMap = {}
        linkMap['message_id'] = charity.id
        linkMap['name'] = charity.name
        if SevericeType == 1:
            linkMap['url'] = 'http://wx.zizaihome.com/charity/getIndexHtml?charityId=' + str(charity.id)
        elif SevericeType == 2:
            linkMap['url'] = 'http://test2.zizaihome.com/charity/getIndexHtml?charityId=' + str(charity.id) + '&isTest=2'
        elif SevericeType == 3:
            linkMap['url'] = 'http://test.zizaihome.com/charity/getIndexHtml?charityId=' + str(charity.id) + '&isTest=1'
        dataMap7LinkList.append(linkMap)
    dataMap7['link_type'] = 7
    dataMap7['linkList'] = dataMap7LinkList
    dataList.append(dataMap7)
    result['data'] = dataList
    result['result'] = 1
    result['msg'] = '获取成功'
    return HttpResponse(json.dumps(result), content_type="application/json")




