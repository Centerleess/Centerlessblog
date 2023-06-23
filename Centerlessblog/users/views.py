#!/usr/bin/python
# -*- coding: UTF-8 -*-
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection

from libs.captcha.captcha import captcha


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
