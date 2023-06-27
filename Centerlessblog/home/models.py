#!/usr/bin/python
# -*- coding: UTF-8 -*-
from django.db import models
from pymysql import Time
from django.utils import timezone


# Create your models here.

class ArticleCategory(models.Model):
    # 分类名称
    sort_title = models.CharField(max_length=100, blank=True)
    # 创建时间
    sore_created = models.DateTimeField(default=timezone.now)
    # 子标签类型
    sort_level = models.CharField(max_length=50, blank=True)
    # 备注
    sort_remark = models.CharField(max_length=50, blank=True )

    # admin站点显示，调试查看对象方便给
    def __str__(self):
        return self.sort_title

    class Meta:
        db_table='tb_category'
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name
