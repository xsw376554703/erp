# coding:utf-8
import re
from datetime import datetime
import json
import socket
import sys
import time
import urllib

from bs4 import BeautifulSoup
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse, StreamingHttpResponse
from django.shortcuts import render_to_response
import xlwt

from article.models import ZizaijiaArticle, ZizaijiaArticlePay, \
    ZizaijiaArticleType
# from bs4 import BeautifulSoup
from common.tools import file_iterator
from temple.models import Temple, ZizaijiaTempleWebsiteImageTextList
from volunteer.models import WeixinUser
from datetime import date

reload(sys)
sys.setdefaultencoding('utf8')

def articleGetArticleList(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    pageNumber = request.GET.get('pageNumber')
    pageSize = request.GET.get('pageSize')
    status = request.GET.get('status')
    title = request.GET.get('title')
    typeId = request.GET.get('typeId')
    if pageNumber == 'None' or pageNumber == '' or pageNumber is None:
        pageNumber = 0
    if pageSize == 'None' or pageSize == '' or pageSize is None:
        pageSize = 20
    zizaijiaArticleList = ZizaijiaArticle.objects.filter(temple_id=templeId)
    if status != 'None' and status != '4' and status != '' and status is not None and status != '0':
        zizaijiaArticleList = zizaijiaArticleList.filter(status=status)
    else:
        zizaijiaArticleList = zizaijiaArticleList.exclude(status=4)
    if title != '' and title != 'None' and title is not None:
        zizaijiaArticleList = zizaijiaArticleList.filter(title__icontains=title)
    if typeId != '' and typeId != 'None' and typeId is not None and typeId != '0':
        zizaijiaArticleList = zizaijiaArticleList.filter(type_id=typeId)
    zizaijiaArticleList = zizaijiaArticleList.order_by('-add_time')[int(pageNumber)*int(pageSize):int(pageNumber)*int(pageSize)+int(pageSize)]
    zizaijiaArticleList2 = []
    for zizaijiaArticle in zizaijiaArticleList:
        articleMap = {}
        articleMap['id'] = zizaijiaArticle.id
        articleMap['title'] = zizaijiaArticle.title
        articleMap['pic'] = zizaijiaArticle.pic
        articleMap['read_num'] = zizaijiaArticle.read_num
        articleMap['zan_num'] = zizaijiaArticle.zan_num
        articleMap['price_sum'] = zizaijiaArticle.price_sum
        articleMap['status'] = zizaijiaArticle.status
        zizaijiaArticleList2.append(articleMap)
    if len(list(zizaijiaArticleList2)) >= int(pageSize):
        result['pageNumber'] = int(pageNumber)+1
    else:
        result['pageNumber'] = -1
    result['data'] = zizaijiaArticleList2
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def addArticle(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    title = request.POST.get('title')
    typeId = request.POST.get('typeId')
    pic = request.POST.get('pic')
    detail = request.POST.get('detail')
    isOpenSuiXi = request.POST.get('isOpenSuiXi')
    suixiList = request.POST.get('suixiList')
    suixiDetail = request.POST.get('suixiDetail')
    picIsShowDetail = request.POST.get('picIsShowDetail')
    status = request.POST.get('status')
    synopsis = request.POST.get('synopsis')
    suixiBtnName = request.POST.get('suixiBtnName')
    publicTime = request.POST.get('publicTime')
    isShowTemple = request.POST.get('isShowTemple')
    isShowTitle = request.POST.get('isShowTitle')
    isShowZanBtn = request.POST.get('isShowZanBtn')
    publicTime = str(publicTime)
    if publicTime != "":
        year,month,day = publicTime.split('-')
        publicTime = date(int(year),int(month),int(day))
    else:
        publicTime = None
    zizaijiaArticle = ZizaijiaArticle.objects.create(title=title,read_num=0,detail=detail,temple_id=templeId,add_time=datetime.now(),update_time=datetime.now(),status=status,zan_num=0,price_sum=0.0,pic=pic,synopsis=synopsis,btn_name=suixiBtnName,is_open_suixi=isOpenSuiXi,suixi_list=suixiList,suixi_detail=suixiDetail,pic_is_show_detail=picIsShowDetail,type_id=typeId,is_show_temple=isShowTemple,public_time=publicTime,is_show_title=isShowTitle,is_show_zan_btn=isShowZanBtn)
    result['articleId'] = zizaijiaArticle.id
    result['msg'] = '添加成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")   

def getArticle(request): 
    result = {}
    articleId = request.GET.get('articleId')
    article = ZizaijiaArticle.objects.filter(id=articleId)
    if len(list(article)) > 0:
        article = article[0]
    dataMap = {}
    dataMap['title'] = article.title
    dataMap['typeId'] = article.type_id
    dataMap['pic'] = article.pic
    dataMap['detail'] = article.detail
    dataMap['isOpenSuiXi'] = article.is_open_suixi
    dataMap['suixiList'] = article.suixi_list
    dataMap['suixiDetail'] = article.suixi_detail
    dataMap['picIsShowDetail'] = article.pic_is_show_detail
    dataMap['status'] = article.status
    dataMap['synopsis'] = article.synopsis
    dataMap['suixiBtnName'] = article.btn_name
    dataMap['isShowTemple'] = article.is_show_temple
    dataMap['isShowTitle'] = article.is_show_title
    dataMap['isShowZanBtn'] = article.is_show_zan_btn
    if article.public_time is not None:
        dataMap['publicTime'] =  str(article.public_time.year)+"-"+str(article.public_time.month)+"-"+str(article.public_time.day)
    else:
        dataMap['publicTime'] = ""
    result['data'] = dataMap
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def updateArticle(request):
    result = {}
    articleId = request.POST.get('articleId')
    title = request.POST.get('title')
    typeId = request.POST.get('typeId')
    pic = request.POST.get('pic')
    detail = request.POST.get('detail')
    isOpenSuiXi = request.POST.get('isOpenSuiXi')
    suixiList = request.POST.get('suixiList')
    suixiDetail = request.POST.get('suixiDetail')
    picIsShowDetail = request.POST.get('picIsShowDetail')
    status = request.POST.get('status')
    synopsis = request.POST.get('synopsis')
    suixiBtnName = request.POST.get('suixiBtnName')
    publicTime = request.POST.get('publicTime')
    isShowTemple = request.POST.get('isShowTemple')
    isShowTitle = request.POST.get('isShowTitle')
    isShowZanBtn = request.POST.get('isShowZanBtn')
    publicTime = str(publicTime)
#     publicTime = datetime.strptime(publicTime,'%Y-%m-%d')
    if publicTime != "":     
        year,month,day = publicTime.split('-')
        publicTime = date(int(year),int(month),int(day))
    else:
        publicTime = None
    article = ZizaijiaArticle.objects.filter(id=articleId)
    if len(list(article)) > 0:
        article = article[0]
    article.title = title
    article.type_id = typeId
    article.pic = pic
    article.detail = detail
    article.is_open_suixi = isOpenSuiXi
    article.suixi_list = suixiList
    article.suixi_detail = suixiDetail
    article.pic_is_show_detail = picIsShowDetail
    article.status = status
    article.synopsis = synopsis
    article.btn_name = suixiBtnName
    article.public_time = publicTime 
    article.is_show_temple = isShowTemple
    article.is_show_title = isShowTitle    
    article.is_show_zan_btn = isShowZanBtn        
    article.save()

    # 修改标题同步更新到微站文章列表
    ZizaijiaTempleWebsiteImageTextList.objects.filter(article_id=articleId).update(title=title)

    result['articleId'] = articleId
    result['msg'] = '更新成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")     

def delArticle(request):
    result = {}
    articleId = request.GET.get('articleId')
    article = ZizaijiaArticle.objects.filter(id=articleId)
    if len(list(article)) > 0:
        article = article[0]
    article.status = 4
    article.save()
    result['msg'] = '删除成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")      
    
def getArticleSuixiList(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    startTime = request.GET.get('startTime')
    endTime = request.GET.get('endTime')
    pageNumber = request.GET.get('pageNumber')
    pageSize = request.GET.get('pageSize')
    if pageNumber == '' or pageNumber == 'None' or pageNumber is None:
        pageNumber = 20    
    if pageSize == '' or pageSize == 'None' or pageSize is None:
        pageSize = 20
    zizaijiaArticlePayList = ZizaijiaArticlePay.objects.filter(temple_id=templeId).filter(pay_type=1)
    if startTime != '' and startTime != 'None' and startTime is not None:
        startTime = str(startTime)+' 00:00:00'
        startTime = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')  
        zizaijiaArticlePayList = zizaijiaArticlePayList.filter(pay_time__gte=startTime)
    if endTime != '' and endTime != 'None' and endTime is not None:
        endTime = str(endTime)+' 23:59:59'
        endTime = datetime.strptime(endTime,'%Y-%m-%d %H:%M:%S')
        zizaijiaArticlePayList = zizaijiaArticlePayList.filter(pay_time__lte=endTime)
    zizaijiaArticlePayList = zizaijiaArticlePayList.order_by('-pay_time')[int(pageNumber)*int(pageSize):int(pageNumber)*int(pageSize)+int(pageSize)]
    dataList = [] 
    for zizaijiaArticlePay in zizaijiaArticlePayList:
        dataMap = {}
        weixinUser = WeixinUser.objects.filter(id=zizaijiaArticlePay.user_id)
        dataMap['nickName'] =  weixinUser[0].nick_name
        dataMap['headImg'] =  weixinUser[0].head_img
        dataMap['price'] =  zizaijiaArticlePay.price
        dataMap['addTime'] =  zizaijiaArticlePay.add_time.strftime('%Y-%m-%d %H:%M:%S')
        zizaijiaArticle = ZizaijiaArticle.objects.filter(id=zizaijiaArticlePay.article_id)
        if len(list(zizaijiaArticle)) > 0:
            dataMap['title'] =  zizaijiaArticle[0].title
        dataList.append(dataMap)
    if len(list(zizaijiaArticlePayList)) >= int(pageSize):
        result['pageNumber'] = int(pageNumber)+1
    else:
        result['pageNumber'] = -1        
    result['data'] = dataList
    result['msg'] = '获取成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def getArticleSuixiExcel(request):
    user = request.user
    templeId = user.temple_id
    startTime = request.GET.get('startTime')
    endTime = request.GET.get('endTime')
    zizaijiaArticlePayList = ZizaijiaArticlePay.objects.filter(temple_id=templeId).filter(pay_type=1)
    if startTime != '' and startTime != 'None' and startTime is not None:
        startTime = str(startTime)+' 00:00:00'
        startTime = datetime.strptime(startTime,'%Y-%m-%d %H:%M:%S')  
        zizaijiaArticlePayList = zizaijiaArticlePayList.filter(pay_time__gte=startTime)
    if endTime != '' and endTime != 'None' and endTime is not None:
        endTime = str(endTime)+' 23:59:59'
        endTime = datetime.strptime(endTime,'%Y-%m-%d %H:%M:%S')
        zizaijiaArticlePayList = zizaijiaArticlePayList.filter(pay_time__lte=endTime)
    if len(list(zizaijiaArticlePayList)) <= 0:
        return HttpResponse('没有查找到数据')
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('功德箱',cell_overwrite_ok=True)
    style = xlwt.XFStyle()
    font = xlwt.Font()
    font.name = 'SimSun' # 指定“宋体”
    style.font = font         
    listNum = 0
    ws.write(listNum, 0, '文章')     
    ws.write(listNum, 1, '随喜者')
    ws.write(listNum, 2, '随喜金额')
    ws.write(listNum, 3, '随喜时间')        
    for zizaijiaArticlePay in zizaijiaArticlePayList:
        listNum = listNum+1
        weixinUser = WeixinUser.objects.filter(id=zizaijiaArticlePay.user_id)
        ws.write(listNum, 1, weixinUser[0].nick_name)
        ws.write(listNum, 2, zizaijiaArticlePay.price)
        if zizaijiaArticlePay.pay_time != None:
            ws.write(listNum, 3, zizaijiaArticlePay.pay_time.strftime('%Y-%m-%d %H:%M:%S'))
        else: 
            ws.write(listNum, 3, "")
        zizaijiaArticle = ZizaijiaArticle.objects.filter(id=zizaijiaArticlePay.article_id)
        if len(list(zizaijiaArticle)) > 0:
            ws.write(listNum, 0, zizaijiaArticle[0].title) 
    the_file_name = "./download/文章随喜.xls"
    wb.save(the_file_name)
    response = StreamingHttpResponse(file_iterator(the_file_name))
    response['Content-Type'] = 'application/octet-stream'
    temple = Temple.objects.filter(id=templeId)
    fileName = str(temple[0].name)+'文章随喜'
    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(fileName+'.xls')
    return response    
    
def addArticleType(request):
    result = {}
    user = request.user
    templeId = user.temple_id
    name = request.GET.get('name')
    zizaijiaArticleType = ZizaijiaArticleType.objects.create(name=name,temple_id=templeId,op_status=0,add_time=datetime.now(),update_time=datetime.now(),sort=0)
    result['id'] = zizaijiaArticleType.id
    result['msg'] = '添加成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def articleGetArticleTypeList(request): 
    result = {}
    user = request.user
    templeId = user.temple_id          
    zizaijiaArticleTypeList = ZizaijiaArticleType.objects.filter(temple_id=templeId).filter(op_status=0)
    dataList = []
    for zizaijiaArticleType in zizaijiaArticleTypeList:
        dataMap = {}
        dataMap['id'] = zizaijiaArticleType.id
        dataMap['name'] = zizaijiaArticleType.name
        dataList.append(dataMap)
    result['data'] = dataList
    result['msg'] = '添加成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def updateArticleType(request):
    result = {}
    typeId = request.GET.get('typeId')
    name = request.GET.get('name')
    zizaijiaArticleType = ZizaijiaArticleType.objects.get(id=typeId)
    zizaijiaArticleType.name = name
    zizaijiaArticleType.save()
    result['msg'] = '更新成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

def delArticleType(request):
    result = {}
    typeId = request.GET.get('typeId')
    zizaijiaArticleType = ZizaijiaArticleType.objects.get(id=typeId)
    zizaijiaArticleType.op_status = -1
    zizaijiaArticleType.save()
    result['msg'] = '删除成功'
    result['result'] = 1
    return HttpResponse(json.dumps(result), content_type="application/json")

@login_required
def articleIndex(request):
    return render_to_response('article/index.html')

@login_required
def createArticleIndex(request):
    return render_to_response('article/create.html')

@login_required
def articleInteractIndex(request):
    return render_to_response('article/interact.html')

def getWeixinArticle(request):
    url = request.POST.get('url')
    socket.setdefaulttimeout(6)
    page = urllib.urlopen(url)
    html = page.read().decode("utf-8")
    html = html.replace('data-src', 'src')
    soup = BeautifulSoup(html)
    [s.extract() for s in soup(['iframe', 'qqmusic', 'script'])]
    result = soup.find_all(id='js_content')[0]
    imgList = result.find_all('img')
    for img in imgList:
        u = img['src'].replace('http', 'https')
        # img['src'] = u
        # del img['data-src']
    return HttpResponse(result, content_type="text/html")
