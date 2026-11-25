# LYTCompanySystemv2.0
For creating next version system

## 本地开发

需要 Docker 和 Compose v2。仓库提供 React + TypeScript、FastAPI、
PostgreSQL + pgvector、Redis 和 MinIO 的开发环境。

```sh
docker compose up --build -d
curl --fail http://localhost:8080/api/ready
```

- 前端 http://localhost:8080，API 文档 http://localhost:8000/docs。
- 如需对象存储，运行 `docker compose --profile storage up -d`。MinIO 控制台为 http://localhost:9001，开发账号见 `compose.yaml`。若默认镜像源不可用，可用 `MINIO_IMAGE` 指定可访问的兼容镜像。
- 数据迁移由一次性 `migrate` 服务执行。日常停止用 `docker compose down`。
- Compose 内的固定密码仅用于本地开发。

## 验证

```sh
(cd web && npm ci && npm run build)
python -m venv .venv
.venv/bin/pip install -r api/requirements.txt
(cd api && ../.venv/bin/python -m unittest -v)
```

## 已实现和待接入

- API 提供存活和就绪检查，就绪检查读取 PostgreSQL 并探测 Redis。
- 模型网关适配兼容 OpenAI 的 embeddings 接口。使用时通过本地环境或密钥管理器设置
  `MODEL_BASE_URL`（含 API 版本路径）、`MODEL_API_KEY`、`EMBEDDING_MODEL`。
  pgvector 检索、S3 客户端、审计写入和 Agent 工具注册均为内部接口，
  尚未开放业务 API 或实现文档摄入。更换 embedding 模型需重新生成现有向量。
- Agent 工具默认要求人工审批，在审批后端未接入前拒绝执行此类工具。
  SSO、Vault、完整审计与审批工作流尚未接入。
- API 暴露 `/metrics/`，Prometheus 采集、Grafana 面板和 Loki 日志聚合尚未配置。
- 暂不引入消息队列。可按异步任务量和交付语义选择 RabbitMQ 或 Kafka。

## 部署模板

`infra/k8s/` 提供应用、迁移 Job 和默认暂停的 CronJob。
替换镜像占位符并在相同命名空间准备 `lyt-runtime` Secret，
至少配置 `DATABASE_URL` 和 `REDIS_URL`。先运行迁移 Job，成功后再部署应用。
生产环境应使用独立的迁移和应用数据库账号，并通过 Vault 等系统供给密钥。
模板不创建数据库、Redis、S3、Ingress 或 TLS。
`.harness/pipeline.yaml` 是需替换连接器和项目参数的构建验证示例，不会自动部署。

### 构建环境使用 HTTPS 代理时

如果容器下载依赖时不信任组织代理签发的证书，请将可信的 PEM CA 证书包通过 BuildKit
secret 提供给构建。证书包须包含环境所需的根证书，不要包含私钥。

```sh
LYT_BUILD_CA=/path/to/trusted-ca-bundle.pem \
  docker compose -f compose.yaml -f compose.build-ca.yaml up --build -d
curl --fail http://localhost:8080/api/ready
```

该覆盖配置不会关闭 TLS 校验，也不会把 CA 证书包复制进最终镜像。
Harness 模板还会运行 `api/acceptance.py`，使用流水线临时 PostgreSQL/Redis 验证迁移、
就绪检查、检索、审计和指标。脚本会写入测试数据，只能对一次性测试数据库运行。
