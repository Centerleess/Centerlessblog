#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
from random import randint

import redis
from django.http import HttpResponseBadRequest, HttpResponse, request
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from libs.captcha.captcha import captcha
from django.http.response import JsonResponse

from libs.yuntongxun.sms import CCP
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
        # 将验证码输出在控制台，以方便调试
        logger.info(sms_code)
        # 保存短信验证码到redis中，并设置有效期
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)

        # send_template_sms 参数：手机号、[验证码， 有效时常], 模板ID,测试的短信模板编号为1
        # 发送短信验证码
        ccp.send_template_sms(mobile, [sms_code, 5], 1)
        # 响应结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})
