# BA Toolkit 测试框架搭建报告

**日期**: 2026-03-14
**项目**: BA Toolkit (Business Analyst AI Assistant)

---

## 📋 执行摘要

本次工作完成了 BA Toolkit 项目的测试框架搭建，包括前端 (Vitest) 和后端 (pytest) 的测试基础设施，同时修复了关键的安全配置问题 (P0)。

### 关键成果

| 指标 | 结果 |
|------|------|
| 前端测试 | 5 个测试全部通过 |
| 后端测试 | 20 个测试全部通过 |
| 安全修复 | 1 个 P0 级别问题已修复 |
| 代码变更 | 6 个文件修改 |

---

## 🔐 P0 安全修复

### 问题描述

`JWT_SECRET_KEY` 原本使用默认值，存在严重安全隐患。攻击者可利用默认密钥伪造 JWT Token。

### 修复方案

**文件**: `backend/app/config.py`

| 配置项 | 修复前 | 修复后 |
|--------|--------|--------|
| `JWT_SECRET_KEY` | 默认值 `"dev-secret-key"` | **必填**，最少 32 字符 |
| `AZURE_OPENAI_API_KEY` | 可选 | **必填** |
| `AZURE_OPENAI_ENDPOINT` | 可选 | **必填** |
| `OPENAI_API_KEY` | 可选 | **必填** |

### 启动时验证

```python
class Settings(BaseSettings):
    JWT_SECRET_KEY: str = Field(min_length=32)
    # ... 其他必填字段

    @model_validator(mode='after')
    def validate_secrets(self):
        if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return self
```

应用启动时如果缺少必要环境变量将直接报错退出，实现 **fail-fast** 原则。

---

## 🧪 测试框架

### 前端测试 (Vitest)

**配置文件**:
- `vitest.config.ts` - Vitest 配置
- `src/test/setup.ts` - 测试环境设置

**依赖添加**:

```json
{
  "devDependencies": {
    "vitest": "^1.6.1",
    "@testing-library/react": "^14.3.1",
    "@testing-library/jest-dom": "^6.9.1",
    "jsdom": "^24.1.3"
  }
}
```

**测试文件**:

| 文件 | 测试数 | 覆盖范围 |
|------|--------|----------|
| `authStore.test.ts` | 3 | 状态管理、登录/登出流程 |
| `ProtectedRoute.test.tsx` | 2 | 路由保护、重定向逻辑 |

**运行命令**:

```bash
cd frontend
npm run test        # 交互模式
npm run test:run    # 单次执行
```

### 后端测试 (pytest)

**配置文件**:
- `pytest.ini` - pytest 配置
- `tests/conftest.py` - 测试 fixtures 和环境设置

**依赖添加**:

```text
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
```

**测试文件**:

| 文件 | 测试数 | 覆盖范围 |
|------|--------|----------|
| `test_config_security.py` | 4 | 配置安全验证 |
| `test_auth_api.py` | 6 | 认证 API 端点 |
| `test_auth_security.py` | 10 | 认证中间件安全 |

**运行命令**:

```bash
cd backend
python -m pytest -v           # 详细输出
python -m pytest --cov=app    # 覆盖率报告
```

---

## 🐛 问题修复

### 1. pydantic-ai 依赖问题

**问题**: `pydantic-ai 0.0.14` 依赖 `_griffe` 编译扩展，在测试环境导入失败。

**解决方案**: 在 `tests/conftest.py` 中 mock `pydantic_ai` 及其子模块。

```python
# Mock pydantic_ai before app imports
mock_ai = MagicMock()
mock_models = MagicMock()
mock_providers = MagicMock()
sys.modules["pydantic_ai"] = mock_ai
sys.modules["pydantic_ai.models"] = mock_models
sys.modules["pydantic_ai.providers"] = mock_providers
```

### 2. SQLite :memory: 数据库问题

**问题**: `:memory:` SQLite 每次连接创建新数据库，导致测试间状态丢失。

**解决方案**: 在 `DatabaseService` 中缓存 `:memory:` 连接，复用同一实例。

```python
def _get_conn(self) -> sqlite3.Connection:
    if self.db_path == ":memory:":
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn
    # ...

def _close_conn(self, conn: sqlite3.Connection) -> None:
    """Close connection unless it's the cached in-memory one."""
    if self.db_path != ":memory:":
        conn.close()
```

---

## 📁 文件变更清单

```
backend/
├── app/
│   ├── config.py              # 修改: 强制必填配置项
│   └── services/
│       └── db_service.py      # 修改: 支持 :memory: 数据库
├── tests/
│   ├── conftest.py            # 修改: 环境变量、mock pydantic_ai
│   ├── test_config_security.py # 新增
│   ├── test_auth_api.py       # 新增
│   └── test_auth_security.py  # 新增
├── pytest.ini                 # 新增
└── .env.example               # 修改: 标注必填字段

frontend/
├── src/test/
│   ├── setup.ts               # 新增
│   ├── authStore.test.ts      # 新增
│   └── ProtectedRoute.test.tsx # 新增
├── vitest.config.ts           # 新增
└── package.json               # 修改: 添加测试依赖
```

---

## ✅ 测试结果

### 前端

```
 ✓ src/test/authStore.test.ts (3 tests) 8ms
 ✓ src/test/ProtectedRoute.test.tsx (2 tests) 14ms

 Test Files  2 passed (2)
      Tests  5 passed (5)
   Duration  397ms
```

### 后端

```
tests/test_auth_api.py::TestAuthEndpoints::test_missing_token_returns_401 PASSED
tests/test_auth_api.py::TestAuthEndpoints::test_invalid_token_returns_401 PASSED
tests/test_auth_api.py::TestAuthEndpoints::test_malformed_auth_header_returns_401 PASSED
tests/test_auth_api.py::TestAuthEndpoints::test_register_with_existing_email_returns_400 PASSED
tests/test_auth_api.py::TestAuthEndpoints::test_login_with_wrong_password_returns_401 PASSED
tests/test_auth_api.py::TestAuthEndpoints::test_login_returns_valid_tokens PASSED
tests/test_auth_security.py::test_missing_token_returns_401 PASSED
tests/test_auth_security.py::test_invalid_token_returns_401 PASSED
tests/test_auth_security.py::test_malformed_auth_header_returns_401 PASSED
tests/test_auth_security.py::test_empty_token_returns_401 PASSED
tests/test_auth_security.py::test_projects_requires_auth PASSED
tests/test_auth_security.py::test_documents_requires_auth PASSED
tests/test_auth_security.py::test_chat_requires_auth PASSED
tests/test_auth_security.py::test_analysis_requires_auth PASSED
tests/test_auth_security.py::test_health_endpoint_no_auth_required PASSED
tests/test_auth_security.py::test_root_endpoint_no_auth_required PASSED
tests/test_config_security.py::TestConfigSecurity::test_jwt_secret_required PASSED
tests/test_config_security.py::TestConfigSecurity::test_jwt_secret_minimum_length PASSED
tests/test_config_security.py::TestConfigSecurity::test_azure_openai_key_required PASSED
tests/test_config_security.py::TestConfigSecurity::test_openai_key_required PASSED

======================== 20 passed in 1.35s ========================
```

---

## 📝 后续建议

1. **测试覆盖率**: 添加更多业务逻辑测试，目标覆盖率 > 80%
2. **E2E 测试**: 引入 Playwright 进行端到端测试
3. **CI 集成**: 在 CI/CD 流水线中自动运行测试
4. **Mock 策略**: 考虑使用 `pytest-mock` 统一 mock 管理
5. **配置迁移**: 将 `Settings` 类的 `Config` 迁移到 `ConfigDict` (Pydantic V2)

---

## 🔗 相关文档

- [Vitest 官方文档](https://vitest.dev/)
- [pytest 官方文档](https://docs.pytest.org/)
- [Pydantic V2 迁移指南](https://docs.pydantic.dev/latest/migration/)
- [Testing Library 最佳实践](https://testing-library.com/docs/react-testing-library/intro/)
