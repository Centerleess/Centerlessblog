#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging

from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render
from django.views import View

from home.models import ArticleCategory, Article

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
        # 获取分页参数
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        # 根据分类查数据
        articles = Article.objects.filter(category=category)

        # 创建分页器
        paginator = Paginator(articles, page_size)
        # 进行分页处理
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            # 如果没有分页数据，默认给用户404
            return HttpResponseNotFound('empty page')

        # 总页数
        total_page = paginator.num_pages
        # 传递给模板
        context = {
            "categories": categories,
            "category": category,
            # 分类数据
            "articles": page_articles,
            "page_size": page_size,
            "page_num": page_num,
            "total_page": total_page
        }
        return render(request, 'index.html', context=context)


class DetailView(View):
    """ 详情页面展示 """

    def get(self, request):
        # 接受数据
        id = request.GET.get('id')

        # 根据文章的id进行文章数据的查询
        # 获取博客分类信息
        categories = ArticleCategory.objects.all()

        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist as e:
            logger.error(e)
            pass

        # 组织模板数据
        context = {
            "categories": categories,
            "category": article.category,
            "article": article,
        }
        return render(request, 'detail.html', context=context)
