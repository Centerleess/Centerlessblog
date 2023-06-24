#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
import re
from random import randint
from django.db import DatabaseError
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from libs.captcha.captcha import captcha
from django.http.response import JsonResponse
from libs.yuntongxun.sms import CCP
from users.models import User
from utils.response_code import RETCODE

# 篇日志日志器
logger = logging.getLogger("django_log")


# Create your views here.
class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, "register.html")

    def post(self, request):
        # 获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')

        # 判断参数
        if not all([mobile, password, password2, smscode]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, "errmsg": "缺少必传参数"})
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少必传参数')
            # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')
            # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
            # 判断两次密码是否一致
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')

        # 验证短信验证码
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != sms_code_server.decode():
            return HttpResponseBadRequest('短信验证码错误')
        # 保存注册数据,create_user 可对密码加密
        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
            logger.info(user)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')

        # 响应注册结果
        return HttpResponse('注册成功，重定向到首页')


class ImageCodeView(View):
    """ 图片验证码 """

    def get(self, request):
        # 获取前端传递过来的参数
        uuid = request.GET.get('uuid')
        # 判断参数是否为None
        if uuid is None:
            return HttpResponseBadRequest('请求参数错误')
        # 获取验证码内容和验证码图片二进制数据
        text, image = captcha.generate_captcha()
        # 将图片验内容保存到redis中，并设置过期时间（ uuid:value(uuid:图片)）
        redis_conn = get_redis_connection('default')
        # key :uuid
        # seconds : 验证码时效
        # value ： text
        redis_conn.setex('img:%s' % uuid, 300, text)
        # 返回响应，将生成的图片以content_type为image/jpeg的形式返回给请求（返回二进制文件）
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):
    """  获取验证码 """

    def get(self, request):

        ccp = CCP()
        # 接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        mobile = request.GET.get('mobile')

        # 校验参数
        if not all([image_code_client, uuid, mobile]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})

        # 图片验证码验证
        redis_conn = get_redis_connection("default")
        image_code_server = redis_conn.get(f"img:{uuid}")
        # 判断验证码
        if image_code_server is None:
            return JsonResponse({"code": RETCODE.IMAGECODEERR, "errmsg": "图片验证码已过期,请重新获取!"})
        # 校验后删除图片验证码
        try:
            redis_conn.delete(f"img:{uuid}")
        except Exception as e:
            logger.error(e)
        # # 验证码比对 (注意大小写.redis的数据类型是bytes类型)
        image_code_server = image_code_server.decode()  # bytes转字符串
        if image_code_client.lower() != image_code_server.lower():  # 转小写后比较
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})

        # 生成短信验证码：生成6位数验证码
        sms_code = '%04d' % randint(0, 9999)
        logger.info(sms_code)
        # 保存短信验证码到redis中，并设置有效期
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)

        # send_template_sms 参数：手机号、[验证码， 有效时常], 模板ID,测试的短信模板编号为1
        # 发送短信验证码
        ccp.send_template_sms(mobile, [sms_code, 5], 1)
        # 响应结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})
