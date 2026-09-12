#!/bin/bash
set -e

open -a Docker --background --hide

# 等待 Docker daemon 就绪
until docker info >/dev/null 2>&1; do sleep 1; done

# 清理旧容器（不存在也不报错）
docker stop postgres 2>/dev/null || true
docker rm postgres 2>/dev/null || true

# 启动 PostgreSQL
docker run --name postgres \
  -e POSTGRES_PASSWORD=111111 \
  -e POSTGRES_DB=stock \
  -p 5432:5432 \
  -v /Users/wangwei/PostgreSQL/data:/var/lib/postgresql \
  -v /Users/wangwei/PythonProject/tools-py/out:/tmp \
  -d \
  postgres:18

# 启动 Superset
docker-compose -f /Users/wangwei/IdeaProjects/superset/docker-compose-image-tag.yml up -d


# 看 postgres
docker ps | grep postgres

# 测 postgres 连接
docker exec -it postgres psql -U postgres -d stock -c '\l'

# 看 superset 全部容器
docker-compose -f /Users/wangwei/IdeaProjects/superset/docker-compose-image-tag.yml ps