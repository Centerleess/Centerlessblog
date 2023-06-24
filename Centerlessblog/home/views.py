#!/usr/bin/python
# -*- coding: UTF-8 -*-
from django.shortcuts import render
from django.views import View


# Create your views here.
class IndexView(View):
    """首页广告"""
    def get(self, request):
        """
        重定向首页
        :param request:
        :return:
        """
        return render(request, 'index.html')
