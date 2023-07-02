#!/usr/bin/python
# -*- coding: UTF-8 -*-
import codecs
import logging
import os
import re
from random import randint

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection

from home.models import ArticleCategory, Article
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
        # 保存注册数据,tb_user 可对密码加密
        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
            logger.info(user)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')

        # 响应注册结果
        """  
            redirect : 重定向
            reversed : 是通过namespace:name 获取到试图对应路由
        """
        login(request, user)
        response = redirect(reverse('home:index'))
        # 设置cookie ，登录状态，会话结束自动过期
        response.set_cookie('is_login', True)
        # 设置用户名7天后过期
        response.set_cookie('username', user.username.encode('utf-8').decode('latin1'), max_age=7 * 24 * 3600)

        return response


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


class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        if not all([mobile, password]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})
            # 判断手机号是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号')

            # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码最少8位，最长20位')

            # 认证登录 # 认证字段已经在User模型中的USERNAME_FIELD = 'mobile' 修改
        user = authenticate(mobile=mobile, password=password)

        if user is None:
            return HttpResponseBadRequest('用户名或密码错误！')
            # 实现状态保持
        login(request, user)

        # 相应登录状态
        # 获取next参数，进行页面跳转
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))
        # 设置状态时长
        if remember != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
            # 设置cookie
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username.encode('utf-8').decode('latin1'), max_age=30 * 24 * 3600)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiry(None)
            # 设置cookie
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username.encode('utf-8').decode('latin1'), max_age=30 * 24 * 3600)
            # 相应结果
        return response


class LogoutView(View):
    """View 清除cookie 退出登录"""

    def get(self, request):
        # 清楚cookie
        logout(request)
        # 退出登录，重定向至首页
        response = redirect(reverse('home:index'))
        # 清楚token
        response.delete_cookie('is_login')
        return response


class ForgetPassword(View):
    """ 忘记密码 """

    def get(self, request):
        """
        忘记密码页面
        :param request:
        :return:
        """
        return render(request, 'forget_password.html')

    def post(self, request):
        """
        修改密码
        :param request:
        :return:
        """
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')

        # 校验参数
        if not all([mobile, password, password2, smscode]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})
            # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')

            # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')

            # 判断两次密码是否一致
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')
        # 判断验证码
        redis_coon = get_redis_connection('default')
        sms_code_server = redis_coon.get(f'sms:{mobile}')
        if sms_code_server is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != sms_code_server.decode():
            return HttpResponseBadRequest('短信验证码错误，请重新获取！')
        # 根据手机好进行用户查询
        try:
            user = User.objects.get(mobile=mobile)
            logger.info('mobile')
        except User.DoesNotExist:
            try:
                # 创建用户
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception as e:
                logger.error(e)
                return HttpResponseBadRequest('修改失败，请稍后再试！')
        else:
            # 修改用户密码
            user.set_password(password)
            # 数据提交
            user.save()
        # 重定向登录页面
        response = redirect(reverse('users:login'))

        return response


# LoginRequiredMixin 判断用户是否登录，封装了判断用户是否登录的操作
class UserCenterView(LoginRequiredMixin, View):
    """ 个人信息 """

    def get(self, request):
        """
        个人中心展示
        :param request:
        :return:
        """
        user = request.user
        context = {
            "username": user.username,
            "mobile": user.mobile,
            "avatar": user.avatar,
            "user_desc": user.user_desc
        }
        return render(request, 'center.html', context=context)

    def post(self, request):
        """
        修改用户信息
        :param request:
        :return:
        """''
        # 接收数据
        user = request.user
        avatar = request.FILES.get('avatar')
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)

        # 修改数据库数据
        try:
            user.username = username
            user.user_desc = user_desc

            # 这里需要实现一个上传图片替换原图片的方式
            # 删除原来的图片
            if avatar and user.avatar:
                old_avatar_path = user.avatar.path
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)

            # 保存新图片
            if avatar:
                user.avatar = avatar

            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('更新失败，请稍后再试！')

        # 返回响应，刷新页面
        response = redirect(reverse('users:center'))

        # 更新cookie信息
        response.set_cookie('username', user.username.encode('utf-8').decode('latin1'), max_age=30 * 24 * 3600)
        return response


class WriteBlogView(LoginRequiredMixin, View):
    """ 写博客"""

    def get(self, request):
        # 查询分类信息
        categories = ArticleCategory.objects.all()
        context = {
            "categories": categories
        }
        # 返回查询结果
        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        # 获取数据
        # 标题图
        avatar = request.FILES.get('avatar')
        # 文章标题
        title = request.POST.get('title')
        # 分类ID
        category_id = request.POST.get('category')
        # 文章标签
        tags = request.POST.get('tags')
        # 概要信息
        sumary = request.POST.get('sumary')
        # 文章正文
        content = request.POST.get('content')

        user = request.user

        if not all([avatar, title, category_id, sumary, content]):
            return HttpResponseBadRequest('参数不全,请重新输入！')

        # 判断分类标签
        try:
            article_category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist as e:
            logger.error(e)
            return HttpResponseBadRequest('没有此分类信息')

        # 提交数据
        try:
            Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                tags=tags,
                title=title,
                sumary=sumary,
                content=content
            )
        except Article.DoesNotExist as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后再试')

        # 返回响应，跳转到文章详情页面
        # 暂时先跳转到首页
        return redirect(reverse('home:index'))
