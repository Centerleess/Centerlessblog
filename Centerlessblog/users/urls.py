#!/usr/bin/python
# -*- coding: UTF-8 -*-

# 进行users子应用的路由
from django.urls import path

from users.views import RegisterView, ImageCodeView

urlpatterns = [

    # path参数：path(路由， 视图函数 ，别名)
    #     第一个参数：register/
    #     第二个参数：
    #     第三个参数：

    path("register/", RegisterView.as_view(), name="register"),
    # 参数1：路由
    # 参数2：视图函数
    # 参数3：路由名，方便通过reverse来获取路由
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
]
