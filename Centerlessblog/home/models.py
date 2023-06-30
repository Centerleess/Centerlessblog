#!/usr/bin/python
# -*- coding: UTF-8 -*-
from django.db import models
from pymysql import Time
from django.utils import timezone

from users.models import User


# Create your models here.

class ArticleCategory(models.Model):
    # 分类名称
    sort_title = models.CharField(max_length=100, blank=True)
    # 创建时间
    sore_created = models.DateTimeField(default=timezone.now)
    # 子标签类型
    sort_level = models.CharField(max_length=50, blank=True)
    # 备注
    sort_remark = models.CharField(max_length=50, blank=True)

    # admin站点显示，调试查看对象方便给
    def __str__(self):
        return self.sort_title

    # 创建管理员必输入字段
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table = 'tb_category'
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name


class Article(models.Model):
    # 作者信息
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    # 标题图片
    avatar = models.ImageField(upload_to='article/%Y%m%d', blank=True)
    # 标题
    title = models.CharField(max_length=100, null=False, blank=False)
    # 标签分类
    category = models.ForeignKey(
        ArticleCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='article'
    )
    # 标签
    tags = models.CharField(max_length=20, blank=True)
    # 摘要信息
    sumary = models.CharField(max_length=200, null=False, blank=False)
    # 文章正文
    content = models.TextField()
    # 浏览量
    total_views = models.PositiveIntegerField(default=0)
    # 文章评论数
    comments_count = models.PositiveIntegerField(default=0)
    # 创建时间
    # 参数 default=timezone.now 指定其在创建数据时将默认写入当前的时间
    created = models.DateTimeField(default=timezone.now)
    # 文章更新时间。
    # 参数 auto_now=True 指定每次数据更新时自动写入当前时间
    updated = models.DateTimeField(auto_now=True)

    # 内部类 class Meta 用于给 model 定义元数据
    class Meta:
        # ordering 指定模型返回的数据的排列顺序
        # '-created' 表明数据应该以倒序排列
        ordering = ('-created',)
        db_table = 'tb_article'
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name

    # 函数 __str__ 定义当调用对象的 str() 方法时的返回值内容
    # 它最常见的就是在Django管理后台中做为对象的显示值。因此应该总是为 __str__ 返回一个友好易读的字符串
    def __str__(self):
        # 将文章标题返回
        return self.title


class Comment(models.Model):
    # 评论内容
    content = models.TextField()
    # 评论文章
    article = models.ForeignKey(Article,
                                on_delete=models.SET_NULL,
                                null=True)
    # 发表用户
    user = models.ForeignKey('users.User',
                             on_delete=models.SET_NULL,
                             null=True)
    # 评论时间
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'tb_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name
