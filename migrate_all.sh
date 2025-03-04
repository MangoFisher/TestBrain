#!/bin/bash

# 执行数据库迁移命令脚本

# 生成数据库迁移文件
echo "正在生成数据库迁移文件..."
python manage.py makemigrations

# 执行数据库迁移
echo "正在执行数据库迁移..."
python manage.py migrate

echo "数据库迁移完成！"