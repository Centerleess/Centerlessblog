#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views import View

from home.models import ArticleCategory


logger = logging.getLogger("django_log")
# Create your views here.
class IndexView(View):
    """首页广告"""
    def get(self, request):
        """
        页面展示
        :param request:
        :return:
        """
        # 标签分类展示
        categories = ArticleCategory.objects.all()
        # 用户点击的分类ID
        cat_id = request.GET.get('cat_id', 1)
        # 判断id
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist as e:
            logger.error(e)
            return HttpResponseBadRequest("没有此分类")
        # 传递给模板
        context = {
            "categories": categories,
            "category": category,
        }
        return render(request, 'index.html', context=context)
